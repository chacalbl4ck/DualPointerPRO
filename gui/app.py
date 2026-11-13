"""
Interface Gráfica de Configuração Moderna e Elegante (GUI)
DualPointer Pro - Gerenciador Multi-Mouse & Multi-Monitor
Desenvolvido por Caio Monteiro (GitHub: chacalbl4ck)
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import webbrowser
import threading
import time
import os
import sys
from typing import Dict, Any, List

from PIL import Image, ImageTk

from core.config import load_config, save_config
from core.devices import get_connected_mice
from core.monitors import get_monitors
from core.startup import is_startup_enabled, set_startup_enabled
from core.engine import DualPointerEngine
from gui.cursor_draw import draw_cursor_on_canvas

# --- PALETA DE CORES MODERNA (DARK OBSIDIAN & GLASS) ---
BG_MAIN = "#0B0F19"          # Fundo principal ultra-escuro
BG_SURFACE = "#131B2E"       # Superfície dos cartões e containers
BG_SURFACE_LIGHT = "#1C263D" # Hover e elementos secundários
BG_INSET = "#090D16"         # Fundo rebaixado para caixas de telemetria e inputs
BORDER_SUBTLE = "#1F2C45"    # Bordas finas e discretas
BORDER_FOCUS = "#38BDF8"     # Borda de foco / destaque ciano

TEXT_PRIMARY = "#F8FAFC"     # Branco puro para títulos e texto de alto contraste
TEXT_SECONDARY = "#94A3B8"   # Cinza ardósia para rótulos secundários
TEXT_MUTED = "#64748B"       # Cinza atenuado para notas e rodapé

ACCENT_CYAN = "#38BDF8"      # Ciano elétrico (Lugar 1 / Mouse 1)
ACCENT_ORANGE = "#FB923C"    # Laranja cyber (Lugar 2 / Mouse 2)
ACCENT_GREEN = "#10B981"     # Verde esmeralda (Ativo / Online)
ACCENT_RED = "#EF4444"       # Vermelho alerta (Pausado / Atenção)
ACCENT_BLUE = "#0284C7"      # Azul primário para botões principais
ACCENT_PURPLE = "#A855F7"    # Roxo neon complementar

PALETTE_PRESETS = [
    ("#38BDF8", "Ciano Ártico"),
    ("#FB923C", "Laranja Sunset"),
    ("#10B981", "Verde Esmeralda"),
    ("#A855F7", "Roxo Cyber"),
    ("#F43F5E", "Rosa Neon"),
    ("#F59E0B", "Ouro Solar"),
    ("#FFFFFF", "Branco Puro"),
    ("#06B6D4", "Turquesa"),
]


class DualPointerApp:
    def __init__(self, root: tk.Tk, engine: DualPointerEngine, config: Dict[str, Any]):
        self.root = root
        self.engine = engine
        self.config = config
        
        self.root.title("DualPointer Pro - Gerenciador Multi-Mouse & Multi-Monitor")
        self.root.geometry("880x720")
        self.root.minsize(800, 640)
        self.root.configure(bg=BG_MAIN)
        
        # Localização de recursos (ícone .ico e .png)
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assets_dir = os.path.join(base_dir, "assets")
        if not os.path.exists(self.assets_dir):
            self.assets_dir = os.path.join(os.path.dirname(sys.executable), "assets")
            
        icon_path = os.path.join(self.assets_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Referência de imagem da logo para prevenir garbage collection
        self.logo_img = None
        self._load_logo()

        # Dados de hardware
        self.connected_mice: List[Dict] = []
        self.connected_monitors: List[Dict] = []
        self.current_tab = "mice"
        self.tabs: Dict[str, tk.Frame] = {}
        self.tab_buttons: Dict[str, tk.Button] = {}
        
        self._init_ttk_styles()
        self._build_header()
        self._build_navbar()
        self._build_content_area()
        self._build_footer()
        
        # Inicializa dispositivos e monitores
        self.refresh_devices()
        self.refresh_monitors()
        
        # Inicia loop de telemetria a 30 FPS puramente na thread da GUI
        # (Elimina 100% de deadlocks e congelamento ao trocar de aba)
        self._start_telemetry_loop()

    def _load_logo(self):
        png_path = os.path.join(self.assets_dir, "icon.png")
        if os.path.exists(png_path):
            try:
                pil_img = Image.open(png_path).resize((36, 36), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                self.logo_img = None

    def _init_ttk_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        
        # Estilização moderna para Comboboxes
        style.configure(
            "TCombobox",
            fieldbackground=BG_INSET,
            background=BG_SURFACE_LIGHT,
            foreground=TEXT_PRIMARY,
            darkcolor=BORDER_SUBTLE,
            lightcolor=BORDER_SUBTLE,
            arrowcolor=ACCENT_CYAN,
            bordercolor=BORDER_SUBTLE,
            padding=5
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", BG_INSET)],
            selectbackground=[("readonly", BG_SURFACE_LIGHT)],
            selectforeground=[("readonly", TEXT_PRIMARY)],
            foreground=[("readonly", TEXT_PRIMARY)]
        )
        
        # Estilização de Checkbuttons modernos
        style.configure(
            "TCheckbutton",
            background=BG_SURFACE,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 9)
        )
        style.map(
            "TCheckbutton",
            background=[("active", BG_SURFACE)],
            foreground=[("active", ACCENT_CYAN)]
        )
        
        # Estilização de Sliders modernos
        style.configure(
            "Horizontal.TScale",
            background=BG_SURFACE,
            troughcolor=BG_INSET,
            bordercolor=BORDER_SUBTLE,
            lightcolor=ACCENT_CYAN,
            darkcolor=ACCENT_CYAN
        )

    def _bind_combobox_topmost(self, cb: ttk.Combobox):
        """Garante que o cursor overlay permaneça sempre acima da lista suspensa ao clicar."""
        cb.bind("<Button-1>", lambda e: self.engine.assert_topmost(), add="+")
        cb.bind("<FocusIn>", lambda e: self.engine.assert_topmost(), add="+")

    # =========================================================================
    # HEADER BAR
    # =========================================================================
    def _build_header(self):
        header = tk.Frame(self.root, bg=BG_SURFACE, padx=20, pady=12, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        header.pack(fill=tk.X)
        
        # Lado Esquerdo: Identidade Visual e Nome do Software
        brand_frame = tk.Frame(header, bg=BG_SURFACE)
        brand_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        if self.logo_img:
            lbl_logo = tk.Label(brand_frame, image=self.logo_img, bg=BG_SURFACE)
            lbl_logo.pack(side=tk.LEFT, padx=(0, 12))
        else:
            lbl_logo_fallback = tk.Label(brand_frame, text="⚡", font=("Segoe UI", 20, "bold"), fg=ACCENT_CYAN, bg=BG_SURFACE)
            lbl_logo_fallback.pack(side=tk.LEFT, padx=(0, 10))
            
        title_box = tk.Frame(brand_frame, bg=BG_SURFACE)
        title_box.pack(side=tk.LEFT)
        
        top_title = tk.Frame(title_box, bg=BG_SURFACE)
        top_title.pack(anchor="w")
        
        lbl_title = tk.Label(top_title, text="DualPointer Pro", font=("Segoe UI", 14, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE)
        lbl_title.pack(side=tk.LEFT)
        
        lbl_ver = tk.Label(
            top_title, text=" v1.1 Multi-Seat ", font=("Segoe UI", 8, "bold"),
            fg=ACCENT_CYAN, bg="#0E2238", padx=6, pady=1
        )
        lbl_ver.pack(side=tk.LEFT, padx=(8, 0))
        
        lbl_sub = tk.Label(
            title_box, text="Isolamento Total de Movimentos, Cliques e Janelas Multi-Monitor",
            font=("Segoe UI", 8), fg=TEXT_SECONDARY, bg=BG_SURFACE
        )
        lbl_sub.pack(anchor="w", pady=(1, 0))
        
        # Lado Direito: Status e Controle Mestre
        ctrl_frame = tk.Frame(header, bg=BG_SURFACE)
        ctrl_frame.pack(side=tk.RIGHT)
        
        is_active = self.engine.is_active()
        status_text = "● MOTOR ATIVO" if is_active else "❚❚ PAUSADO"
        status_fg = ACCENT_GREEN if is_active else ACCENT_ORANGE
        status_bg = "#064E3B" if is_active else "#78350F"
        
        self.lbl_status_pill = tk.Label(
            ctrl_frame, text=status_text, font=("Segoe UI", 9, "bold"),
            fg=status_fg, bg=status_bg, padx=12, pady=5, relief=tk.FLAT
        )
        self.lbl_status_pill.pack(side=tk.LEFT, padx=(0, 12))
        
        btn_text = "Pausar Motor" if is_active else "Ativar Motor"
        btn_bg = "#DC2626" if is_active else "#16A34A"
        
        self.btn_toggle_engine = tk.Button(
            ctrl_frame, text=btn_text, font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF", bg=btn_bg, activebackground="#991B1B", relief=tk.FLAT,
            padx=14, pady=5, cursor="hand2", command=self._on_toggle_engine_clicked
        )
        self.btn_toggle_engine.pack(side=tk.LEFT)

    # =========================================================================
    # BARRA DE NAVEGAÇÃO SEGMENTADA MODERNA (Substitui ttk.Notebook)
    # =========================================================================
    def _build_navbar(self):
        nav_container = tk.Frame(self.root, bg=BG_MAIN, padx=20, pady=12)
        nav_container.pack(fill=tk.X)
        
        # Barra segmentada em cápsula escura
        nav_bar = tk.Frame(nav_container, bg=BG_SURFACE, padx=4, pady=4, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        nav_bar.pack(fill=tk.X)
        
        nav_items = [
            ("mice", "🏢  Áreas de Trabalho"),
            ("cursors", "🎨  Design dos Ponteiros"),
            ("system", "🖥️  Monitores & Sistema"),
            ("about", "ℹ️  Sobre o Projeto")
        ]
        
        for key, text in nav_items:
            btn = tk.Button(
                nav_bar, text=text, font=("Segoe UI", 9, "bold"),
                fg=TEXT_SECONDARY, bg=BG_SURFACE, activebackground=BG_SURFACE_LIGHT,
                activeforeground=TEXT_PRIMARY, relief=tk.FLAT, padx=16, pady=7,
                cursor="hand2", command=lambda k=key: self.switch_tab(k)
            )
            btn.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
            self.tab_buttons[key] = btn

    def switch_tab(self, tab_key: str):
        """Alterna a aba de forma instantânea sem descarregar nem travar a interface."""
        self.current_tab = tab_key
        
        # Atualiza estilo visual dos botões de navegação
        for k, btn in self.tab_buttons.items():
            if k == tab_key:
                btn.config(bg=ACCENT_BLUE, fg="#FFFFFF")
            else:
                btn.config(bg=BG_SURFACE, fg=TEXT_SECONDARY)
                
        # Mostra o frame correspondente e oculta os demais
        for k, frame in self.tabs.items():
            if k == tab_key:
                frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
            else:
                frame.pack_forget()

    # =========================================================================
    # ÁREA DE CONTEÚDO (CONTAINERS DE CADA ABA)
    # =========================================================================
    def _build_content_area(self):
        self.content_frame = tk.Frame(self.root, bg=BG_MAIN)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Cria frames para cada seção
        self.tabs["mice"] = tk.Frame(self.content_frame, bg=BG_MAIN)
        self.tabs["cursors"] = tk.Frame(self.content_frame, bg=BG_MAIN)
        self.tabs["system"] = tk.Frame(self.content_frame, bg=BG_MAIN)
        self.tabs["about"] = tk.Frame(self.content_frame, bg=BG_MAIN)
        
        self._setup_tab_mice(self.tabs["mice"])
        self._setup_tab_cursors(self.tabs["cursors"])
        self._setup_tab_system(self.tabs["system"])
        self._setup_tab_about(self.tabs["about"])
        
        # Aba padrão inicial
        self.switch_tab("mice")

    # -------------------------------------------------------------------------
    # ABA 1: ÁREAS DE TRABALHO (ESTAÇÕES A & B)
    # -------------------------------------------------------------------------
    def _setup_tab_mice(self, parent: tk.Frame):
        # Banner informativo de topo
        banner = tk.Frame(parent, bg=BG_SURFACE, padx=14, pady=10, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        banner.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            banner, text="🛡️ Arquitetura Multi-Seat Totalmente Isolada",
            font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE
        ).pack(anchor="w")
        
        tk.Label(
            banner,
            text="Cada Área de Trabalho opera com seu mouse e monitor dedicados. Cliques, arraste e foco de janelas de uma área não interferem e nunca bloqueiam a outra.",
            font=("Segoe UI", 8), fg=TEXT_SECONDARY, bg=BG_SURFACE
        ).pack(anchor="w", pady=(2, 0))

        # Grade com 2 Colunas para Lugar 1 e Lugar 2
        cards_grid = tk.Frame(parent, bg=BG_MAIN)
        cards_grid.pack(fill=tk.BOTH, expand=True)
        cards_grid.columnconfigure(0, weight=1)
        cards_grid.columnconfigure(1, weight=1)
        
        # --- CARTÃO ÁREA 1 (LUGAR 1 - ESTAÇÃO A) ---
        card_1 = tk.Frame(cards_grid, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        card_1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        # Cabeçalho do Cartão 1 com acento Ciano
        h1 = tk.Frame(card_1, bg=BG_SURFACE)
        h1.pack(fill=tk.X, pady=(0, 10))
        tk.Label(h1, text="■", font=("Segoe UI", 11, "bold"), fg=ACCENT_CYAN, bg=BG_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(h1, text="Área de Trabalho 1 (Lugar 1 - Estação A)", font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE).pack(side=tk.LEFT)
        
        # Seleção de Dispositivo
        tk.Label(card_1, text="Mouse USB Dedicado (Hardware ID):", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(2, 3))
        self.cb_m1_device = ttk.Combobox(card_1, state="readonly", font=("Segoe UI", 9))
        self.cb_m1_device.pack(fill=tk.X, pady=(0, 5))
        self.cb_m1_device.bind("<<ComboboxSelected>>", self._on_m1_device_selected)
        self._bind_combobox_topmost(self.cb_m1_device)
        
        # HWID Detalhe
        self.lbl_m1_hwid_detail = tk.Label(
            card_1, text="HWID: --", font=("Consolas", 8),
            fg=ACCENT_CYAN, bg=BG_INSET, padx=8, pady=4, relief=tk.FLAT, anchor="w"
        )
        self.lbl_m1_hwid_detail.pack(fill=tk.X, pady=(0, 10))
        
        # Seleção de Monitor
        tk.Label(card_1, text="Monitor Associado ao Lugar 1:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(2, 3))
        self.cb_m1_monitor = ttk.Combobox(card_1, state="readonly", font=("Segoe UI", 9))
        self.cb_m1_monitor.pack(fill=tk.X, pady=(0, 10))
        self.cb_m1_monitor.bind("<<ComboboxSelected>>", self._on_m1_monitor_selected)
        self._bind_combobox_topmost(self.cb_m1_monitor)
        
        # Sensibilidade
        sens_row1 = tk.Frame(card_1, bg=BG_SURFACE)
        sens_row1.pack(fill=tk.X, pady=(0, 2))
        tk.Label(sens_row1, text="Sensibilidade do Ponteiro:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(side=tk.LEFT)
        self.lbl_m1_sens_val = tk.Label(sens_row1, text="1.0x", font=("Segoe UI", 8, "bold"), fg=ACCENT_CYAN, bg=BG_SURFACE)
        self.lbl_m1_sens_val.pack(side=tk.RIGHT)
        
        self.scale_m1_sens = ttk.Scale(card_1, from_=0.4, to=2.5, command=self._on_m1_sens_changed)
        self.scale_m1_sens.set(float(self.config.get("mouse1", {}).get("sensitivity", 1.0)))
        self.scale_m1_sens.pack(fill=tk.X, pady=(0, 12))
        
        # Telemetria em Tempo Real (Lugar 1)
        telem_1 = tk.Frame(card_1, bg=BG_INSET, padx=12, pady=10, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        telem_1.pack(fill=tk.X, pady=(4, 0))
        
        self.lbl_m1_pos = tk.Label(telem_1, text="📍 Posição: X: 0  Y: 0", font=("Consolas", 8, "bold"), fg=ACCENT_CYAN, bg=BG_INSET)
        self.lbl_m1_pos.pack(anchor="w")
        
        self.lbl_m1_window = tk.Label(telem_1, text="🪟 Janela: Aguardando foco...", font=("Segoe UI", 8), fg=TEXT_PRIMARY, bg=BG_INSET)
        self.lbl_m1_window.pack(anchor="w", pady=(3, 3))
        
        self.lbl_m1_active = tk.Label(telem_1, text="● Operando Isoladamente", font=("Segoe UI", 8, "bold"), fg=ACCENT_GREEN, bg=BG_INSET)
        self.lbl_m1_active.pack(anchor="w")

        # --- CARTÃO ÁREA 2 (LUGAR 2 - ESTAÇÃO B) ---
        card_2 = tk.Frame(cards_grid, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        card_2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        
        # Cabeçalho do Cartão 2 com acento Laranja
        h2 = tk.Frame(card_2, bg=BG_SURFACE)
        h2.pack(fill=tk.X, pady=(0, 10))
        tk.Label(h2, text="■", font=("Segoe UI", 11, "bold"), fg=ACCENT_ORANGE, bg=BG_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(h2, text="Área de Trabalho 2 (Lugar 2 - Estação B)", font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE).pack(side=tk.LEFT)
        
        # Seleção de Dispositivo
        tk.Label(card_2, text="Mouse USB Dedicado (Hardware ID):", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(2, 3))
        self.cb_m2_device = ttk.Combobox(card_2, state="readonly", font=("Segoe UI", 9))
        self.cb_m2_device.pack(fill=tk.X, pady=(0, 5))
        self.cb_m2_device.bind("<<ComboboxSelected>>", self._on_m2_device_selected)
        self._bind_combobox_topmost(self.cb_m2_device)
        
        # HWID Detalhe
        self.lbl_m2_hwid_detail = tk.Label(
            card_2, text="HWID: --", font=("Consolas", 8),
            fg=ACCENT_ORANGE, bg=BG_INSET, padx=8, pady=4, relief=tk.FLAT, anchor="w"
        )
        self.lbl_m2_hwid_detail.pack(fill=tk.X, pady=(0, 10))
        
        # Seleção de Monitor
        tk.Label(card_2, text="Monitor Associado ao Lugar 2:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(2, 3))
        self.cb_m2_monitor = ttk.Combobox(card_2, state="readonly", font=("Segoe UI", 9))
        self.cb_m2_monitor.pack(fill=tk.X, pady=(0, 10))
        self.cb_m2_monitor.bind("<<ComboboxSelected>>", self._on_m2_monitor_selected)
        self._bind_combobox_topmost(self.cb_m2_monitor)
        
        # Sensibilidade
        sens_row2 = tk.Frame(card_2, bg=BG_SURFACE)
        sens_row2.pack(fill=tk.X, pady=(0, 2))
        tk.Label(sens_row2, text="Sensibilidade do Ponteiro:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(side=tk.LEFT)
        self.lbl_m2_sens_val = tk.Label(sens_row2, text="1.0x", font=("Segoe UI", 8, "bold"), fg=ACCENT_ORANGE, bg=BG_SURFACE)
        self.lbl_m2_sens_val.pack(side=tk.RIGHT)
        
        self.scale_m2_sens = ttk.Scale(card_2, from_=0.4, to=2.5, command=self._on_m2_sens_changed)
        self.scale_m2_sens.set(float(self.config.get("mouse2", {}).get("sensitivity", 1.0)))
        self.scale_m2_sens.pack(fill=tk.X, pady=(0, 12))
        
        # Telemetria em Tempo Real (Lugar 2)
        telem_2 = tk.Frame(card_2, bg=BG_INSET, padx=12, pady=10, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        telem_2.pack(fill=tk.X, pady=(4, 0))
        
        self.lbl_m2_pos = tk.Label(telem_2, text="📍 Posição: X: 0  Y: 0", font=("Consolas", 8, "bold"), fg=ACCENT_ORANGE, bg=BG_INSET)
        self.lbl_m2_pos.pack(anchor="w")
        
        self.lbl_m2_window = tk.Label(telem_2, text="🪟 Janela: Aguardando foco...", font=("Segoe UI", 8), fg=TEXT_PRIMARY, bg=BG_INSET)
        self.lbl_m2_window.pack(anchor="w", pady=(3, 3))
        
        self.lbl_m2_active = tk.Label(telem_2, text="● Operando Isoladamente", font=("Segoe UI", 8, "bold"), fg=ACCENT_GREEN, bg=BG_INSET)
        self.lbl_m2_active.pack(anchor="w")

        # Barra de Ações Inferior
        action_bar = tk.Frame(parent, bg=BG_MAIN)
        action_bar.pack(fill=tk.X, pady=(12, 0))
        
        btn_refresh = tk.Button(
            action_bar, text="🔄 Redetectar Mouses & Portas USB",
            font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE,
            activebackground=BG_SURFACE_LIGHT, relief=tk.FLAT, padx=14, pady=7,
            cursor="hand2", command=self.refresh_devices
        )
        btn_refresh.pack(side=tk.LEFT)

    # -------------------------------------------------------------------------
    # ABA 2: DESIGN DOS PONTEIROS
    # -------------------------------------------------------------------------
    def _setup_tab_cursors(self, parent: tk.Frame):
        # Seletor do mouse a customizar (Segmented Pill Switch)
        top_sel_box = tk.Frame(parent, bg=BG_SURFACE, padx=14, pady=10, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        top_sel_box.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(top_sel_box, text="Personalizar Ponteiro para:", font=("Segoe UI", 9, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(side=tk.LEFT, padx=(0, 12))
        
        self.cursor_target_var = tk.StringVar(value="mouse1")
        
        self.btn_target_m1 = tk.Button(
            top_sel_box, text="🖱️ Mouse 1 (Primário)", font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF", bg=ACCENT_BLUE, relief=tk.FLAT, padx=14, pady=5,
            cursor="hand2", command=lambda: self._select_cursor_target("mouse1")
        )
        self.btn_target_m1.pack(side=tk.LEFT, padx=4)
        
        self.btn_target_m2 = tk.Button(
            top_sel_box, text="🖱️ Mouse 2 (Secundário)", font=("Segoe UI", 9, "bold"),
            fg=TEXT_SECONDARY, bg=BG_INSET, relief=tk.FLAT, padx=14, pady=5,
            cursor="hand2", command=lambda: self._select_cursor_target("mouse2")
        )
        self.btn_target_m2.pack(side=tk.LEFT, padx=4)

        # Layout dividido: Lado esquerdo configurações, Lado direito Pré-visualização
        split_frame = tk.Frame(parent, bg=BG_MAIN)
        split_frame.pack(fill=tk.BOTH, expand=True)
        split_frame.columnconfigure(0, weight=3)
        split_frame.columnconfigure(1, weight=2)
        
        # Painel Esquerdo: Propriedades e Estilo
        opts_card = tk.Frame(split_frame, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        opts_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        # Formato do ponteiro
        tk.Label(opts_card, text="Formato do Ponteiro:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(0, 3))
        shape_names = [
            ("Seta Minimalista Sleek (Moderna)", "sleek"),
            ("Seta Aerodinâmica Fluent (Win 11)", "fluent"),
            ("Seta Gamer Cyber (Angular)", "cyber"),
            ("Mira de Precisão (Crosshair Pro)", "precision"),
            ("Ponto Halo Neon (Capsule)", "capsule"),
            ("Caneta Stylus Designer", "stylus")
        ]
        self.cb_shape = ttk.Combobox(opts_card, state="readonly", values=[s[0] for s in shape_names], font=("Segoe UI", 9))
        self.cb_shape.pack(fill=tk.X, pady=(0, 12))
        self.shape_name_map = {s[0]: s[1] for s in shape_names}
        self.shape_rev_map = {s[1]: s[0] for s in shape_names}
        self.shape_rev_map["arrow"] = "Seta Minimalista Sleek (Moderna)"
        self.shape_rev_map["crosshair"] = "Mira de Precisão (Crosshair Pro)"
        self.shape_rev_map["dot"] = "Ponto Halo Neon (Capsule)"
        self.cb_shape.bind("<<ComboboxSelected>>", self._on_cursor_prop_changed)
        self._bind_combobox_topmost(self.cb_shape)

        # Cor do Ponteiro
        tk.Label(opts_card, text="Cor do Ponteiro:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(0, 4))
        pal_frame = tk.Frame(opts_card, bg=BG_SURFACE)
        pal_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.color_preview_btn = tk.Button(
            pal_frame, text="   ", bg="#38BDF8", relief=tk.SOLID, bd=1,
            command=self._pick_custom_color, cursor="hand2", padx=6
        )
        self.color_preview_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        for hex_code, name in PALETTE_PRESETS:
            b = tk.Button(
                pal_frame, bg=hex_code, relief=tk.FLAT, bd=0, width=2, height=1,
                cursor="hand2", command=lambda c=hex_code: self._set_cursor_color(c)
            )
            b.pack(side=tk.LEFT, padx=2)
            
        btn_custom = tk.Button(
            pal_frame, text="Mais Cores...", font=("Segoe UI", 8, "bold"),
            fg=TEXT_PRIMARY, bg=BG_SURFACE_LIGHT, relief=tk.FLAT, padx=8, pady=2,
            command=self._pick_custom_color, cursor="hand2"
        )
        btn_custom.pack(side=tk.LEFT, padx=6)
        
        # Tamanho do Ponteiro
        size_box = tk.Frame(opts_card, bg=BG_SURFACE)
        size_box.pack(fill=tk.X, pady=(4, 2))
        tk.Label(size_box, text="Tamanho do Cursor:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(side=tk.LEFT)
        self.lbl_size_val = tk.Label(size_box, text="28px", font=("Segoe UI", 8, "bold"), fg=ACCENT_CYAN, bg=BG_SURFACE)
        self.lbl_size_val.pack(side=tk.RIGHT)
        
        self.scale_cursor_size = ttk.Scale(opts_card, from_=18, to=54, command=self._on_cursor_size_scale)
        self.scale_cursor_size.pack(fill=tk.X, pady=(0, 12))
        
        # Checkboxes Efeito Glow e Rótulo
        self.chk_glow_var = tk.BooleanVar(value=True)
        chk_glow = ttk.Checkbutton(
            opts_card, text="Aura Luminosa (Glow Neon para Alto Contraste)",
            variable=self.chk_glow_var, command=self._on_cursor_prop_changed
        )
        chk_glow.pack(anchor="w", pady=4)
        
        self.chk_label_var = tk.BooleanVar(value=True)
        chk_label = ttk.Checkbutton(
            opts_card, text="Exibir Etiqueta de Identificação do Mouse (1 / 2)",
            variable=self.chk_label_var, command=self._on_cursor_prop_changed
        )
        chk_label.pack(anchor="w", pady=4)

        # Painel Direito: Pré-visualização Interativa em Canvas
        preview_card = tk.Frame(split_frame, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        preview_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        
        tk.Label(preview_card, text="Pré-visualização em Tempo Real:", font=("Segoe UI", 8, "bold"), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(0, 6))
        
        self.preview_canvas = tk.Canvas(preview_card, bg=BG_INSET, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, pady=4)
        
        tk.Label(
            preview_card, text="Mova o ponteiro dentro da grade acima para testar o visual e movimento.",
            font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_SURFACE, wraplength=220, justify="center"
        ).pack(pady=(4, 0))
        
        self.preview_canvas.bind("<Motion>", self._on_canvas_motion)
        self._load_cursor_form("mouse1")

    def _select_cursor_target(self, target: str):
        self.cursor_target_var.set(target)
        if target == "mouse1":
            self.btn_target_m1.config(bg=ACCENT_BLUE, fg="#FFFFFF")
            self.btn_target_m2.config(bg=BG_INSET, fg=TEXT_SECONDARY)
        else:
            self.btn_target_m1.config(bg=BG_INSET, fg=TEXT_SECONDARY)
            self.btn_target_m2.config(bg=ACCENT_BLUE, fg="#FFFFFF")
        self._load_cursor_form(target)

    # -------------------------------------------------------------------------
    # ABA 3: MONITORES & SISTEMA
    # -------------------------------------------------------------------------
    def _setup_tab_system(self, parent: tk.Frame):
        # Card 1: Inicialização com o Windows
        card_start = tk.Frame(parent, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        card_start.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card_start, text="Inicialização Automática com o Windows", font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE).pack(anchor="w")
        tk.Label(card_start, text="Permite que o DualPointer Pro inicie automaticamente junto com o sistema operacional.", font=("Segoe UI", 8), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(2, 8))
        
        self.chk_autostart_var = tk.BooleanVar(value=is_startup_enabled())
        chk_autostart = ttk.Checkbutton(
            card_start, text="Iniciar automaticamente ao ligar o computador (pasta Inicializar)",
            variable=self.chk_autostart_var, command=self._on_autostart_toggled
        )
        chk_autostart.pack(anchor="w")

        # Card 2: Visibilidade do Cursor Nativo
        card_hide = tk.Frame(parent, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        card_hide.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card_hide, text="Visibilidade do Cursor Padrão do Windows", font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE).pack(anchor="w")
        tk.Label(card_hide, text="Substitui o cursor único do sistema para que apenas os 2 ponteiros independentes sejam visíveis.", font=("Segoe UI", 8), fg=TEXT_SECONDARY, bg=BG_SURFACE).pack(anchor="w", pady=(2, 8))
        
        self.chk_hide_cursor_var = tk.BooleanVar(value=self.config.get("system", {}).get("hide_os_cursor", True))
        chk_hide = ttk.Checkbutton(
            card_hide, text="Ocultar ponteiro nativo do Windows enquanto o motor estiver ativo (Recomendado)",
            variable=self.chk_hide_cursor_var, command=self._on_hide_cursor_toggled
        )
        chk_hide.pack(anchor="w")

        # Card 3: Monitores Detectados
        card_mon = tk.Frame(parent, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        card_mon.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(card_mon, text="Monitores Detectados no Computador", font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE).pack(anchor="w")
        self.lbl_mon_summary = tk.Label(card_mon, text="Detectando telas ativas...", font=("Segoe UI", 8), fg=ACCENT_CYAN, bg=BG_SURFACE)
        self.lbl_mon_summary.pack(anchor="w", pady=(4, 0))

        # Card 4: Simulação para Testes com 1 Mouse
        card_sim = tk.Frame(parent, bg=BG_SURFACE, padx=16, pady=14, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        card_sim.pack(fill=tk.X)
        
        tk.Label(card_sim, text="Modo de Simulação & Demonstração", font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE).pack(anchor="w")
        self.chk_sim_var = tk.BooleanVar(value=self.config.get("system", {}).get("simulation_mode", False))
        chk_sim = ttk.Checkbutton(
            card_sim, text="Ativar Modo de Simulação (move o Mouse 2 em espelho para testar com apenas 1 mouse físico conectado)",
            variable=self.chk_sim_var, command=self._on_sim_mode_toggled
        )
        chk_sim.pack(anchor="w", pady=(6, 0))

    # -------------------------------------------------------------------------
    # ABA 4: SOBRE O PROJETO (MODERNA & ELEGANTE)
    # -------------------------------------------------------------------------
    def _setup_tab_about(self, parent: tk.Frame):
        about_card = tk.Frame(parent, bg=BG_SURFACE, padx=24, pady=24, highlightthickness=1, highlightbackground=BORDER_SUBTLE)
        about_card.pack(fill=tk.BOTH, expand=True)
        
        # Emblema / Monograma do Desenvolvedor
        badge_frame = tk.Frame(about_card, bg=BG_SURFACE)
        badge_frame.pack(pady=(4, 8))
        
        tk.Label(
            badge_frame, text="⚡",
            font=("Segoe UI", 32), fg=ACCENT_CYAN, bg=BG_SURFACE
        ).pack()
        
        tk.Label(
            about_card, text="DualPointer Pro",
            font=("Segoe UI", 18, "bold"), fg=TEXT_PRIMARY, bg=BG_SURFACE
        ).pack()
        
        app_ver = self.config.get("app", {}).get("version", "1.1")
        tk.Label(
            about_card, text=f"Versão {app_ver} Multi-Seat Pro • Windows 10/11 x64",
            font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_SURFACE
        ).pack(pady=(1, 14))
        
        # Linha Divisória
        tk.Frame(about_card, height=1, bg=BORDER_SUBTLE).pack(fill=tk.X, pady=8)
        
        # Bloco de Créditos com Destaque
        dev_frame = tk.Frame(about_card, bg=BG_SURFACE)
        dev_frame.pack(pady=10)
        
        tk.Label(
            dev_frame, text="Desenvolvido por:",
            font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_SURFACE
        ).pack()
        
        tk.Label(
            dev_frame, text="Caio Monteiro",
            font=("Segoe UI", 16, "bold"), fg=ACCENT_CYAN, bg=BG_SURFACE
        ).pack(pady=2)
        
        # Botão GitHub (Abertura 100% assíncrona para não travar a GUI)
        github_btn = tk.Button(
            dev_frame, text="🐙  GitHub: chacalbl4ck",
            font=("Segoe UI", 9, "bold"), fg="#FFFFFF", bg="#1E293B",
            activebackground="#0F172A", activeforeground=ACCENT_CYAN,
            relief=tk.FLAT, padx=18, pady=8, cursor="hand2",
            command=self._open_github_async
        )
        github_btn.pack(pady=8)
        
        desc_text = (
            "Software de alta performance projetado para permitir a conexão e utilização simultânea "
            "e totalmente independente de múltiplos mouses em computadores com vários monitores.\n\n"
            "• Roteamento físico direto por USB Hardware ID (VID & PID)\n"
            "• Delimitação independente de limites e telas por monitor\n"
            "• Supressão de interferências via Low-Level Hook e Windows Raw Input API\n"
            "• Design de ponteiros ultra-modernos com tecnologia Pillow e tipografia Segoe UI\n"
            "• Inicialização automática nativa integrada ao Windows"
        )
        tk.Label(
            about_card, text=desc_text,
            font=("Segoe UI", 9), fg=TEXT_PRIMARY, bg=BG_SURFACE,
            justify="center", wraplength=580
        ).pack(pady=12)

    def _open_github_async(self):
        """Abre o link do GitHub de forma assíncrona para não travar o processo."""
        threading.Thread(
            target=webbrowser.open,
            args=("https://github.com/chacalbl4ck",),
            daemon=True
        ).start()

    # =========================================================================
    # FOOTER BAR
    # =========================================================================
    def _build_footer(self):
        footer = tk.Frame(self.root, bg=BG_MAIN, pady=8, padx=20)
        footer.pack(fill=tk.X)
        
        self.btn_save = tk.Button(
            footer, text="💾  Salvar e Aplicar Configurações",
            font=("Segoe UI", 9, "bold"), fg="#FFFFFF", bg=ACCENT_BLUE,
            activebackground="#0369A1", relief=tk.FLAT, padx=18, pady=8,
            cursor="hand2", command=self.save_and_apply
        )
        self.btn_save.pack(side=tk.RIGHT)

        lbl_failsafe = tk.Label(
            footer, text="Atalho Global de Emergência: F12 (Pausar / Retomar)",
            font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_MAIN
        )
        lbl_failsafe.pack(side=tk.LEFT)

    # =========================================================================
    # LOOP DE TELEMETRIA A 30 FPS (RODA 100% NA THREAD DA GUI)
    # =========================================================================
    def _start_telemetry_loop(self):
        self._update_telemetry()

    def _update_telemetry(self):
        """
        Atualiza posições, janela ativa e atividade a 30 FPS sem chamadas entre threads.
        Se a aba atual não for 'mice', nenhuma label é tocada, prevenindo deadlocks.
        """
        try:
            if not self.root.winfo_exists():
                return
            
            if self.current_tab == "mice":
                x1, y1 = self.engine.pos1
                x2, y2 = self.engine.pos2
                
                self.lbl_m1_pos.config(text=f"📍 Posição: X: {int(x1)}  Y: {int(y1)}")
                self.lbl_m2_pos.config(text=f"📍 Posição: X: {int(x2)}  Y: {int(y2)}")
                
                # Atualização suave de títulos de janelas
                t1 = self.engine.active_wnd_m1_title
                t2 = self.engine.active_wnd_m2_title
                c1 = (t1[:30] + '...') if len(t1) > 32 else (t1 or "Área de Trabalho / Desktop")
                c2 = (t2[:30] + '...') if len(t2) > 32 else (t2 or "Área de Trabalho / Desktop")
                self.lbl_m1_window.config(text=f"🪟 Janela: {c1}")
                self.lbl_m2_window.config(text=f"🪟 Janela: {c2}")
                
                # Indicador de atividade recente (< 0.35s)
                now = time.time()
                if (now - self.engine.m1_last_activity) < 0.35:
                    self.lbl_m1_active.config(text="● Clicando / Movendo...", fg=ACCENT_CYAN)
                else:
                    self.lbl_m1_active.config(text="● Operando Isoladamente", fg=ACCENT_GREEN)
                    
                if (now - self.engine.m2_last_activity) < 0.35:
                    self.lbl_m2_active.config(text="● Clicando / Movendo...", fg=ACCENT_ORANGE)
                else:
                    self.lbl_m2_active.config(text="● Operando Isoladamente", fg=ACCENT_GREEN)
        except Exception:
            pass
        finally:
            self.root.after(33, self._update_telemetry)

    # =========================================================================
    # LÓGICA DE DADOS, DISPOSITIVOS E CONFIGURAÇÕES
    # =========================================================================
    def refresh_devices(self):
        self.connected_mice = get_connected_mice()
        labels = [m['display_label'] for m in self.connected_mice]
        
        self.cb_m1_device['values'] = labels
        self.cb_m2_device['values'] = labels
        
        m1_hwid = self.config.get("mouse1", {}).get("hwid", "")
        sel_1 = 0
        for i, m in enumerate(self.connected_mice):
            if m1_hwid and m1_hwid in m['hwid']:
                sel_1 = i
                break
        if labels:
            self.cb_m1_device.current(sel_1)
            self._update_m1_hwid_label(self.connected_mice[sel_1])
            
        m2_hwid = self.config.get("mouse2", {}).get("hwid", "")
        sel_2 = 1 if len(labels) > 1 else 0
        for i, m in enumerate(self.connected_mice):
            if m2_hwid and m2_hwid in m['hwid']:
                sel_2 = i
                break
        if labels:
            self.cb_m2_device.current(sel_2)
            self._update_m2_hwid_label(self.connected_mice[sel_2])

    def refresh_monitors(self):
        self.connected_monitors = get_monitors()
        labels = ["Todos os Monitores (Área Global)"]
        for m in self.connected_monitors:
            prim = " [Principal]" if m.get('primary', False) else ""
            labels.append(f"Monitor {m['index']}: {m['width']}x{m['height']}{prim}")
            
        self.cb_m1_monitor['values'] = labels
        self.cb_m2_monitor['values'] = labels
        
        m1_mons = self.config.get("mouse1", {}).get("monitors", [1])
        idx1 = m1_mons[0] if m1_mons and m1_mons[0] < len(labels) else 1
        if labels:
            self.cb_m1_monitor.current(min(idx1, len(labels) - 1))
            
        m2_mons = self.config.get("mouse2", {}).get("monitors", [2])
        idx2 = m2_mons[0] if m2_mons and m2_mons[0] < len(labels) else (2 if len(labels) > 2 else 1)
        if labels:
            self.cb_m2_monitor.current(min(idx2, len(labels) - 1))
            
        summary = f"{len(self.connected_monitors)} tela(s) ativa(s): " + " • ".join([f"M{m['index']} ({m['width']}x{m['height']})" for m in self.connected_monitors])
        self.lbl_mon_summary.config(text=summary)

    def _update_m1_hwid_label(self, dev: Dict):
        self.lbl_m1_hwid_detail.config(text=f"HWID: {dev['hwid']}  |  {dev['friendly_name']}")

    def _update_m2_hwid_label(self, dev: Dict):
        self.lbl_m2_hwid_detail.config(text=f"HWID: {dev['hwid']}  |  {dev['friendly_name']}")

    def _on_m1_device_selected(self, event=None):
        idx = self.cb_m1_device.current()
        if idx >= 0 and idx < len(self.connected_mice):
            dev = self.connected_mice[idx]
            self.config["mouse1"]["hwid"] = dev['hwid']
            self.config["mouse1"]["instance_id"] = dev['instance_id']
            self.config["mouse1"]["friendly_name"] = dev['friendly_name']
            self._update_m1_hwid_label(dev)

    def _on_m2_device_selected(self, event=None):
        idx = self.cb_m2_device.current()
        if idx >= 0 and idx < len(self.connected_mice):
            dev = self.connected_mice[idx]
            self.config["mouse2"]["hwid"] = dev['hwid']
            self.config["mouse2"]["instance_id"] = dev['instance_id']
            self.config["mouse2"]["friendly_name"] = dev['friendly_name']
            self._update_m2_hwid_label(dev)

    def _on_m1_monitor_selected(self, event=None):
        idx = self.cb_m1_monitor.current()
        self.config["mouse1"]["monitors"] = [0] if idx == 0 else [idx]
        self.engine.update_config(self.config)

    def _on_m2_monitor_selected(self, event=None):
        idx = self.cb_m2_monitor.current()
        self.config["mouse2"]["monitors"] = [0] if idx == 0 else [idx]
        self.engine.update_config(self.config)

    def _on_m1_sens_changed(self, val):
        v = round(float(val), 2)
        self.lbl_m1_sens_val.config(text=f"{v}x")
        self.config["mouse1"]["sensitivity"] = v
        self.engine.update_config(self.config)

    def _on_m2_sens_changed(self, val):
        v = round(float(val), 2)
        self.lbl_m2_sens_val.config(text=f"{v}x")
        self.config["mouse2"]["sensitivity"] = v
        self.engine.update_config(self.config)

    # -------------------------------------------------------------------------
    # PERSONALIZAÇÃO DE CURSORES
    # -------------------------------------------------------------------------
    def _load_cursor_form(self, target: str):
        c_cfg = self.config.get(target, {}).get("cursor", {})
        shape = c_cfg.get("shape", "sleek")
        shape_disp = self.shape_rev_map.get(shape, "Seta Minimalista Sleek (Moderna)")
        self.cb_shape.set(shape_disp)
        
        color = c_cfg.get("color", "#38BDF8")
        self.color_preview_btn.config(bg=color)
        
        size = int(c_cfg.get("size", 28))
        self.scale_cursor_size.set(size)
        self.lbl_size_val.config(text=f"{size}px")
        
        self.chk_glow_var.set(c_cfg.get("glow", True))
        self.chk_label_var.set(c_cfg.get("show_label", True))
        
        self._render_preview()

    def _set_cursor_color(self, hex_color: str):
        target = self.cursor_target_var.get()
        self.config[target]["cursor"]["color"] = hex_color
        self.color_preview_btn.config(bg=hex_color)
        self._render_preview()
        self.engine.update_config(self.config)

    def _pick_custom_color(self):
        target = self.cursor_target_var.get()
        cur_col = self.config[target]["cursor"].get("color", "#38BDF8")
        chosen = colorchooser.askcolor(initialcolor=cur_col, title="Escolha a Cor do Ponteiro")[1]
        if chosen:
            self._set_cursor_color(chosen)

    def _on_cursor_size_scale(self, val):
        s = int(float(val))
        self.lbl_size_val.config(text=f"{s}px")
        target = self.cursor_target_var.get()
        self.config[target]["cursor"]["size"] = s
        self._render_preview()
        self.engine.update_config(self.config)

    def _on_cursor_prop_changed(self, event=None):
        target = self.cursor_target_var.get()
        shape_name = self.cb_shape.get()
        shape_code = self.shape_name_map.get(shape_name, "sleek")
        
        self.config[target]["cursor"]["shape"] = shape_code
        self.config[target]["cursor"]["glow"] = self.chk_glow_var.get()
        self.config[target]["cursor"]["show_label"] = self.chk_label_var.get()
        
        self._render_preview()
        self.engine.update_config(self.config)

    def _render_preview(self, mouse_x: float = 120.0, mouse_y: float = 100.0):
        self.preview_canvas.delete("all")
        target = self.cursor_target_var.get()
        c_cfg = self.config.get(target, {}).get("cursor", {})
        
        # Desenha grade de fundo elegante
        w = self.preview_canvas.winfo_width() or 240
        h = self.preview_canvas.winfo_height() or 200
        for x in range(0, w, 28):
            self.preview_canvas.create_line(x, 0, x, h, fill="#131B2E", width=1)
        for y in range(0, h, 28):
            self.preview_canvas.create_line(0, y, w, y, fill="#131B2E", width=1)
            
        draw_cursor_on_canvas(self.preview_canvas, mouse_x, mouse_y, c_cfg, scale=1.2)

    def _on_canvas_motion(self, event):
        self._render_preview(event.x, event.y)

    # -------------------------------------------------------------------------
    # CONTROLES DE SISTEMA & MOTOR
    # -------------------------------------------------------------------------
    def _on_autostart_toggled(self):
        enabled = self.chk_autostart_var.get()
        success = set_startup_enabled(enabled)
        if success:
            self.config["system"]["autostart"] = enabled
            save_config(self.config)
            msg = "DualPointer Pro configurado para iniciar automaticamente com o Windows!" if enabled else "Inicialização automática desativada."
            messagebox.showinfo("Inicialização com Windows", msg)
        else:
            self.chk_autostart_var.set(not enabled)
            messagebox.showerror("Erro de Permissão", "Não foi possível modificar o atalho na pasta Inicializar.")

    def _on_hide_cursor_toggled(self):
        hide = self.chk_hide_cursor_var.get()
        self.config["system"]["hide_os_cursor"] = hide
        self.engine.update_config(self.config)

    def _on_sim_mode_toggled(self):
        sim = self.chk_sim_var.get()
        self.config["system"]["simulation_mode"] = sim
        self.engine.update_config(self.config)

    def _on_toggle_engine_clicked(self):
        is_active = self.engine.toggle_pause()
        if is_active:
            self.lbl_status_pill.config(text="● MOTOR ATIVO", fg=ACCENT_GREEN, bg="#064E3B")
            self.btn_toggle_engine.config(text="Pausar Motor", bg="#DC2626")
        else:
            self.lbl_status_pill.config(text="❚❚ PAUSADO", fg=ACCENT_ORANGE, bg="#78350F")
            self.btn_toggle_engine.config(text="Ativar Motor", bg="#16A34A")

    def save_and_apply(self):
        save_config(self.config)
        self.engine.update_config(self.config)
        messagebox.showinfo("Configurações Salvas", "As configurações dos mouses, monitores e cursores foram salvas com sucesso!")
