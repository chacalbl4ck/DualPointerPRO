"""
Interface Gráfica de Configuração (GUI)
DualPointer Pro - Gerenciador Multi-Mouse & Multi-Monitor
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import webbrowser
import os
import sys
from typing import Dict, Any, List

from core.config import load_config, save_config
from core.devices import get_connected_mice
from core.monitors import get_monitors
from core.startup import is_startup_enabled, set_startup_enabled
from core.engine import DualPointerEngine
from gui.cursor_draw import draw_cursor_on_canvas

# Cores do Tema Moderno Dark Slate
BG_DARK = "#0F172A"       # Fundo principal
BG_CARD = "#1E293B"       # Cartões e containers
BG_HOVER = "#334155"      # Elementos com hover
BG_INPUT = "#0F172A"      # Campos de entrada
TEXT_PRIMARY = "#F8FAFC"  # Texto principal branco
TEXT_MUTED = "#94A3B8"    # Texto secundário acinzentado
ACCENT_BLUE = "#38BDF8"   # Destaque azul
ACCENT_GREEN = "#10B981"  # Verde ativo
ACCENT_ORANGE = "#F59E0B" # Laranja aviso
BORDER_COLOR = "#334155"  # Bordas sutis

PALETTE_PRESETS = [
    ("#38BDF8", "Ciano Ártico"),
    ("#FB923C", "Sunset Coral"),
    ("#10B981", "Verde Esmeralda"),
    ("#F43F5E", "Rosa Neon"),
    ("#A855F7", "Roxo Cyber"),
    ("#FBBF24", "Âmbar / Dourado"),
    ("#FFFFFF", "Branco Puro"),
    ("#64748B", "Cinza Titânio")
]

class DualPointerApp:
    def __init__(self, root: tk.Tk, engine: DualPointerEngine, config: Dict[str, Any]):
        self.root = root
        self.engine = engine
        self.config = config
        
        self.root.title("DualPointer Pro - Gerenciador Multi-Mouse & Multi-Monitor")
        self.root.geometry("860x700")
        self.root.minsize(780, 620)
        self.root.configure(bg=BG_DARK)
        
        # Define ícone da janela
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "assets", "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(sys.executable), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Dados em tempo real
        self.connected_mice: List[Dict] = []
        self.connected_monitors: List[Dict] = []
        
        self._init_styles()
        self._build_header()
        self._build_notebook()
        self._build_footer()
        
        # Atualiza listas iniciais
        self.refresh_devices()
        self.refresh_monitors()
        
        # Conecta callbacks do motor
        self.engine.on_device_activity = self._on_device_activity
        
    def _init_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        
        # Abas
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=TEXT_MUTED, padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
            background=[("selected", BG_HOVER), ("active", BG_CARD)],
            foreground=[("selected", ACCENT_BLUE), ("active", TEXT_PRIMARY)]
        )
        
        # Combobox
        style.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_CARD, foreground=TEXT_PRIMARY, arrowcolor=ACCENT_BLUE)
        style.map("TCombobox", fieldbackground=[("readonly", BG_INPUT)], foreground=[("readonly", TEXT_PRIMARY)])
        
        # Sliders (Scale)
        style.configure("TScale", background=BG_CARD, troughcolor=BG_DARK)
        
        # Checkbuttons
        style.configure("TCheckbutton", background=BG_CARD, foreground=TEXT_PRIMARY, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", BG_CARD)], foreground=[("active", ACCENT_BLUE)])

    def _build_header(self):
        header_frame = tk.Frame(self.root, bg=BG_DARK, pady=12, padx=20)
        header_frame.pack(fill=tk.X)
        
        # Título e Subtítulo
        title_box = tk.Frame(header_frame, bg=BG_DARK)
        title_box.pack(side=tk.LEFT)
        
        lbl_title = tk.Label(
            title_box, text="DUALPOINTER PRO",
            font=("Segoe UI", 16, "bold"), fg=TEXT_PRIMARY, bg=BG_DARK
        )
        lbl_title.pack(anchor="w")
        
        lbl_sub = tk.Label(
            title_box, text="Controle independente e simultâneo de múltiplos mouses e telas",
            font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_DARK
        )
        lbl_sub.pack(anchor="w")
        
        # Controles do Topo (Status e Botão Mestre)
        controls_box = tk.Frame(header_frame, bg=BG_DARK)
        controls_box.pack(side=tk.RIGHT)
        
        self.lbl_status_pill = tk.Label(
            controls_box, text="● ATIVO",
            font=("Segoe UI", 9, "bold"), fg=ACCENT_GREEN, bg="#064E3B",
            padx=12, pady=4
        )
        self.lbl_status_pill.pack(side=tk.LEFT, padx=10)
        
        self.btn_toggle_engine = tk.Button(
            controls_box, text="Pausar Motor",
            font=("Segoe UI", 9, "bold"), fg="#FFFFFF", bg="#DC2626",
            activebackground="#B91C1C", activeforeground="#FFFFFF",
            relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
            command=self._on_toggle_engine_clicked
        )
        self.btn_toggle_engine.pack(side=tk.LEFT)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        
        # Criação das Abas
        self.tab_mice = tk.Frame(self.notebook, bg=BG_DARK, padx=12, pady=12)
        self.tab_cursors = tk.Frame(self.notebook, bg=BG_DARK, padx=12, pady=12)
        self.tab_system = tk.Frame(self.notebook, bg=BG_DARK, padx=12, pady=12)
        self.tab_about = tk.Frame(self.notebook, bg=BG_DARK, padx=12, pady=12)
        
        self.notebook.add(self.tab_mice, text=" 🖱️ Mouses & Hardware (USB) ")
        self.notebook.add(self.tab_cursors, text=" 🎨 Design dos Ponteiros ")
        self.notebook.add(self.tab_system, text=" 🖥️ Monitores & Sistema ")
        self.notebook.add(self.tab_about, text=" ℹ️ Sobre ")
        
        self._setup_tab_mice()
        self._setup_tab_cursors()
        self._setup_tab_system()
        self._setup_tab_about()

    def _setup_tab_mice(self):
        # Container com 2 colunas para Mouse 1 e Mouse 2
        cards_container = tk.Frame(self.tab_mice, bg=BG_DARK)
        cards_container.pack(fill=tk.BOTH, expand=True)
        cards_container.columnconfigure(0, weight=1)
        cards_container.columnconfigure(1, weight=1)
        
        # --- CARD MOUSE 1 ---
        card_m1 = tk.LabelFrame(
            cards_container, text="  Mouse 1 (Primário)  ",
            bg=BG_CARD, fg=ACCENT_BLUE, font=("Segoe UI", 11, "bold"),
            relief=tk.GROOVE, padx=14, pady=12
        )
        card_m1.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        
        tk.Label(card_m1, text="Dispositivo USB (Hardware ID):", font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w", pady=(2, 4))
        self.cb_m1_device = ttk.Combobox(card_m1, state="readonly", font=("Segoe UI", 9))
        self.cb_m1_device.pack(fill=tk.X, pady=(0, 8))
        self.cb_m1_device.bind("<<ComboboxSelected>>", self._on_m1_device_selected)
        
        self.lbl_m1_hwid_detail = tk.Label(card_m1, text="HWID: --", font=("Consolas", 8), fg=TEXT_MUTED, bg=BG_CARD, wraplength=340, justify="left")
        self.lbl_m1_hwid_detail.pack(anchor="w", pady=(0, 10))
        
        tk.Label(card_m1, text="Monitor Atribuído:", font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w", pady=(4, 2))
        self.cb_m1_monitor = ttk.Combobox(card_m1, state="readonly", font=("Segoe UI", 9))
        self.cb_m1_monitor.pack(fill=tk.X, pady=(0, 10))
        self.cb_m1_monitor.bind("<<ComboboxSelected>>", self._on_m1_monitor_selected)
        
        # Sensibilidade
        sens_box1 = tk.Frame(card_m1, bg=BG_CARD)
        sens_box1.pack(fill=tk.X, pady=(4, 10))
        tk.Label(sens_box1, text="Sensibilidade:", font=("Segoe UI", 9), fg=TEXT_PRIMARY, bg=BG_CARD).pack(side=tk.LEFT)
        self.lbl_m1_sens_val = tk.Label(sens_box1, text="1.0x", font=("Segoe UI", 9, "bold"), fg=ACCENT_BLUE, bg=BG_CARD)
        self.lbl_m1_sens_val.pack(side=tk.RIGHT)
        
        self.scale_m1_sens = ttk.Scale(card_m1, from_=0.4, to=2.5, command=self._on_m1_sens_changed)
        self.scale_m1_sens.set(float(self.config.get("mouse1", {}).get("sensitivity", 1.0)))
        self.scale_m1_sens.pack(fill=tk.X)
        
        # Indicador de atividade
        self.lbl_m1_active = tk.Label(card_m1, text="● Aguardando movimento", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_m1_active.pack(anchor="w", pady=(12, 0))
        
        # --- CARD MOUSE 2 ---
        card_m2 = tk.LabelFrame(
            cards_container, text="  Mouse 2 (Secundário)  ",
            bg=BG_CARD, fg=ACCENT_ORANGE, font=("Segoe UI", 11, "bold"),
            relief=tk.GROOVE, padx=14, pady=12
        )
        card_m2.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        
        tk.Label(card_m2, text="Dispositivo USB (Hardware ID):", font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w", pady=(2, 4))
        self.cb_m2_device = ttk.Combobox(card_m2, state="readonly", font=("Segoe UI", 9))
        self.cb_m2_device.pack(fill=tk.X, pady=(0, 8))
        self.cb_m2_device.bind("<<ComboboxSelected>>", self._on_m2_device_selected)
        
        self.lbl_m2_hwid_detail = tk.Label(card_m2, text="HWID: --", font=("Consolas", 8), fg=TEXT_MUTED, bg=BG_CARD, wraplength=340, justify="left")
        self.lbl_m2_hwid_detail.pack(anchor="w", pady=(0, 10))
        
        tk.Label(card_m2, text="Monitor Atribuído:", font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w", pady=(4, 2))
        self.cb_m2_monitor = ttk.Combobox(card_m2, state="readonly", font=("Segoe UI", 9))
        self.cb_m2_monitor.pack(fill=tk.X, pady=(0, 10))
        self.cb_m2_monitor.bind("<<ComboboxSelected>>", self._on_m2_monitor_selected)
        
        # Sensibilidade
        sens_box2 = tk.Frame(card_m2, bg=BG_CARD)
        sens_box2.pack(fill=tk.X, pady=(4, 10))
        tk.Label(sens_box2, text="Sensibilidade:", font=("Segoe UI", 9), fg=TEXT_PRIMARY, bg=BG_CARD).pack(side=tk.LEFT)
        self.lbl_m2_sens_val = tk.Label(sens_box2, text="1.0x", font=("Segoe UI", 9, "bold"), fg=ACCENT_ORANGE, bg=BG_CARD)
        self.lbl_m2_sens_val.pack(side=tk.RIGHT)
        
        self.scale_m2_sens = ttk.Scale(card_m2, from_=0.4, to=2.5, command=self._on_m2_sens_changed)
        self.scale_m2_sens.set(float(self.config.get("mouse2", {}).get("sensitivity", 1.0)))
        self.scale_m2_sens.pack(fill=tk.X)
        
        self.lbl_m2_active = tk.Label(card_m2, text="● Aguardando movimento", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_m2_active.pack(anchor="w", pady=(12, 0))

        # Barra inferior de ações
        action_bar = tk.Frame(self.tab_mice, bg=BG_DARK)
        action_bar.pack(fill=tk.X, pady=(12, 0))
        
        btn_refresh = tk.Button(
            action_bar, text="🔄 Redetectar Mouses e Portas USB",
            font=("Segoe UI", 9), fg=TEXT_PRIMARY, bg=BG_CARD,
            activebackground=BG_HOVER, relief=tk.FLAT, padx=12, pady=6,
            command=self.refresh_devices
        )
        btn_refresh.pack(side=tk.LEFT)

    def _setup_tab_cursors(self):
        # Seletor do mouse a configurar (Mouse 1 / Mouse 2)
        top_sel = tk.Frame(self.tab_cursors, bg=BG_DARK)
        top_sel.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(top_sel, text="Personalizar Design do Cursor para:", font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_DARK).pack(side=tk.LEFT, padx=(0, 10))
        
        self.cursor_target_var = tk.StringVar(value="mouse1")
        rb1 = tk.Radiobutton(
            top_sel, text="Mouse 1 (Primário)", variable=self.cursor_target_var, value="mouse1",
            font=("Segoe UI", 9, "bold"), fg=ACCENT_BLUE, bg=BG_DARK, selectcolor=BG_CARD,
            activebackground=BG_DARK, activeforeground=ACCENT_BLUE,
            command=self._on_cursor_target_changed
        )
        rb1.pack(side=tk.LEFT, padx=6)
        
        rb2 = tk.Radiobutton(
            top_sel, text="Mouse 2 (Secundário)", variable=self.cursor_target_var, value="mouse2",
            font=("Segoe UI", 9, "bold"), fg=ACCENT_ORANGE, bg=BG_DARK, selectcolor=BG_CARD,
            activebackground=BG_DARK, activeforeground=ACCENT_ORANGE,
            command=self._on_cursor_target_changed
        )
        rb2.pack(side=tk.LEFT, padx=6)

        # Layout dividido: Lado esquerdo configurações, Lado direito Pré-visualização
        split_frame = tk.Frame(self.tab_cursors, bg=BG_DARK)
        split_frame.pack(fill=tk.BOTH, expand=True)
        split_frame.columnconfigure(0, weight=3)
        split_frame.columnconfigure(1, weight=2)
        
        # Painel de Opções (Esquerda)
        opts_card = tk.LabelFrame(
            split_frame, text="  Estilo e Propriedades  ",
            bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"),
            padx=16, pady=12, relief=tk.GROOVE
        )
        opts_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        
        # Formato do ponteiro
        tk.Label(opts_card, text="Formato do Ponteiro:", font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w", pady=(4, 2))
        self.shape_var = tk.StringVar(value="sleek")
        shape_names = [
            ("Seta Minimalista Sleek (Moderna)", "sleek"),
            ("Seta Aerodinâmica Fluent (Win 11)", "fluent"),
            ("Seta Gamer Cyber (Angular)", "cyber"),
            ("Mira de Precisão (Crosshair Pro)", "precision"),
            ("Ponto Halo Neon (Capsule)", "capsule"),
            ("Caneta Stylus Designer", "stylus")
        ]
        self.cb_shape = ttk.Combobox(opts_card, state="readonly", values=[s[0] for s in shape_names], font=("Segoe UI", 9))
        self.cb_shape.pack(fill=tk.X, pady=(0, 10))
        self.shape_name_map = {s[0]: s[1] for s in shape_names}
        self.shape_rev_map = {s[1]: s[0] for s in shape_names}
        # Compatibilidade com formatos legados
        self.shape_rev_map["arrow"] = "Seta Minimalista Sleek (Moderna)"
        self.shape_rev_map["crosshair"] = "Mira de Precisão (Crosshair Pro)"
        self.shape_rev_map["dot"] = "Ponto Halo Neon (Capsule)"
        self.cb_shape.bind("<<ComboboxSelected>>", self._on_cursor_prop_changed)

        # Cor do Ponteiro
        tk.Label(opts_card, text="Cor do Ponteiro:", font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w", pady=(4, 2))
        palette_frame = tk.Frame(opts_card, bg=BG_CARD)
        palette_frame.pack(fill=tk.X, pady=(0, 6))
        
        self.color_preview_btn = tk.Button(
            palette_frame, text="   ", bg="#00D2FF", relief=tk.SOLID, bd=1,
            command=self._pick_custom_color, cursor="hand2"
        )
        self.color_preview_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        for hex_code, name in PALETTE_PRESETS:
            b = tk.Button(
                palette_frame, bg=hex_code, relief=tk.FLAT, bd=0, width=2, height=1,
                cursor="hand2", command=lambda c=hex_code: self._set_cursor_color(c)
            )
            b.pack(side=tk.LEFT, padx=2)
            
        btn_custom_col = tk.Button(
            palette_frame, text="Mais Cores...", font=("Segoe UI", 8),
            fg=TEXT_PRIMARY, bg=BG_HOVER, relief=tk.FLAT, padx=6,
            command=self._pick_custom_color, cursor="hand2"
        )
        btn_custom_col.pack(side=tk.LEFT, padx=6)
        
        # Tamanho do Ponteiro
        size_box = tk.Frame(opts_card, bg=BG_CARD)
        size_box.pack(fill=tk.X, pady=(6, 2))
        tk.Label(size_box, text="Tamanho do Cursor:", font=("Segoe UI", 9, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD).pack(side=tk.LEFT)
        self.lbl_size_val = tk.Label(size_box, text="28px", font=("Segoe UI", 9, "bold"), fg=ACCENT_BLUE, bg=BG_CARD)
        self.lbl_size_val.pack(side=tk.RIGHT)
        
        self.scale_cursor_size = ttk.Scale(opts_card, from_=18, to=54, command=self._on_cursor_size_scale)
        self.scale_cursor_size.pack(fill=tk.X, pady=(0, 10))
        
        # Checkboxes Efeito Glow e Rótulo
        self.chk_glow_var = tk.BooleanVar(value=True)
        chk_glow = ttk.Checkbutton(opts_card, text="Aura Luminosa (Glow) para Alta Visibilidade", variable=self.chk_glow_var, command=self._on_cursor_prop_changed)
        chk_glow.pack(anchor="w", pady=4)
        
        self.chk_label_var = tk.BooleanVar(value=True)
        chk_label = ttk.Checkbutton(opts_card, text="Exibir Etiqueta de Identificação (M1 / M2)", variable=self.chk_label_var, command=self._on_cursor_prop_changed)
        chk_label.pack(anchor="w", pady=4)
        
        # Painel de Pré-visualização Interativo (Direita)
        preview_card = tk.LabelFrame(
            split_frame, text="  Pré-visualização em Tempo Real  ",
            bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"),
            padx=14, pady=12, relief=tk.GROOVE
        )
        preview_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        
        self.preview_canvas = tk.Canvas(preview_card, bg="#0A0E17", highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, pady=6)
        
        tk.Label(
            preview_card, text="Passe o mouse sobre a área acima para testar o movimento visual do cursor.",
            font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_CARD, wraplength=220, justify="center"
        ).pack(pady=(4, 0))
        
        self.preview_canvas.bind("<Motion>", self._on_canvas_motion)
        self._load_cursor_form("mouse1")

    def _setup_tab_system(self):
        # Card Inicialização com o Windows
        card_start = tk.LabelFrame(
            self.tab_system, text="  Inicialização com o Windows  ",
            bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"),
            padx=16, pady=14, relief=tk.GROOVE
        )
        card_start.pack(fill=tk.X, padx=6, pady=6)
        
        self.chk_autostart_var = tk.BooleanVar(value=is_startup_enabled())
        chk_autostart = ttk.Checkbutton(
            card_start, text="Iniciar o DualPointer Pro automaticamente junto com o Windows",
            variable=self.chk_autostart_var, command=self._on_autostart_toggled
        )
        chk_autostart.pack(anchor="w", pady=(2, 6))
        
        self.lbl_autostart_path = tk.Label(
            card_start,
            text=f"Atalho na pasta: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup",
            font=("Consolas", 8), fg=TEXT_MUTED, bg=BG_CARD
        )
        self.lbl_autostart_path.pack(anchor="w")

        # Card Visibilidade do Cursor Nativo do Windows
        card_vis = tk.LabelFrame(
            self.tab_system, text="  Visibilidade do Cursor do Windows  ",
            bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"),
            padx=16, pady=12, relief=tk.GROOVE
        )
        card_vis.pack(fill=tk.X, padx=6, pady=6)
        
        self.chk_hide_os_var = tk.BooleanVar(value=self.config.get("system", {}).get("hide_os_cursor", True))
        chk_hide_os = ttk.Checkbutton(
            card_vis, text="Ocultar ponteiro padrão do Windows (evita que a seta branca nativa fique por cima do cursor do app)",
            variable=self.chk_hide_os_var, command=self._on_hide_os_cursor_toggled
        )
        chk_hide_os.pack(anchor="w", pady=(2, 4))
        tk.Label(
            card_vis, text="Mantém visíveis exclusivamente os seus ponteiros personalizados com cores, glow e etiquetas.",
            font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_CARD
        ).pack(anchor="w")

        # Card Monitores Conectados
        card_mon = tk.LabelFrame(
            self.tab_system, text="  Monitores Detectados no Computador  ",
            bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"),
            padx=16, pady=14, relief=tk.GROOVE
        )
        card_mon.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        self.monitors_listbox_frame = tk.Frame(card_mon, bg=BG_CARD)
        self.monitors_listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        # Card Modo de Simulação / Teste
        card_sim = tk.LabelFrame(
            self.tab_system, text="  Modo de Simulação & Demonstração  ",
            bg=BG_CARD, fg=ACCENT_ORANGE, font=("Segoe UI", 10, "bold"),
            padx=16, pady=12, relief=tk.GROOVE
        )
        card_sim.pack(fill=tk.X, padx=6, pady=6)
        
        self.chk_sim_var = tk.BooleanVar(value=self.config.get("system", {}).get("simulation_mode", False))
        chk_sim = ttk.Checkbutton(
            card_sim, text="Ativar Modo de Simulação (move o Mouse 2 automaticamente para testes com 1 mouse físico)",
            variable=self.chk_sim_var, command=self._on_sim_mode_toggled
        )
        chk_sim.pack(anchor="w")

    def _setup_tab_about(self):
        about_card = tk.LabelFrame(
            self.tab_about, text="  Informações do Desenvolvedor e Software  ",
            bg=BG_CARD, fg=ACCENT_BLUE, font=("Segoe UI", 11, "bold"),
            padx=24, pady=20, relief=tk.GROOVE
        )
        about_card.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Logo simbólico
        tk.Label(
            about_card, text="🖱️⚡🖥️",
            font=("Segoe UI", 32), bg=BG_CARD
        ).pack(pady=(6, 2))
        
        tk.Label(
            about_card, text="DualPointer Pro",
            font=("Segoe UI", 18, "bold"), fg=TEXT_PRIMARY, bg=BG_CARD
        ).pack()
        
        tk.Label(
            about_card, text="Versão 1.0.0 Pro • Windows 10/11 x64",
            font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_CARD
        ).pack(pady=(0, 16))
        
        # Linha divisória
        tk.Frame(about_card, height=1, bg=BORDER_COLOR).pack(fill=tk.X, pady=8)
        
        # Bloco com o nome e github
        dev_frame = tk.Frame(about_card, bg=BG_CARD)
        dev_frame.pack(pady=12)
        
        tk.Label(
            dev_frame, text="Desenvolvido por:",
            font=("Segoe UI", 10), fg=TEXT_MUTED, bg=BG_CARD
        ).pack()
        
        tk.Label(
            dev_frame, text="Caio Monteiro",
            font=("Segoe UI", 16, "bold"), fg=ACCENT_BLUE, bg=BG_CARD
        ).pack(pady=2)
        
        # Botão GitHub
        github_btn = tk.Button(
            dev_frame, text="🐙 GitHub: chacalbl4ck",
            font=("Segoe UI", 10, "bold"), fg="#FFFFFF", bg="#24292F",
            activebackground="#1B1F23", activeforeground=ACCENT_BLUE,
            relief=tk.FLAT, padx=16, pady=8, cursor="hand2",
            command=lambda: webbrowser.open("https://github.com/chacalbl4ck")
        )
        github_btn.pack(pady=8)
        
        desc_text = (
            "Software de alta performance para permitir a conexão e utilização simultânea "
            "e independente de dois mouses em computadores com múltiplos monitores.\n\n"
            "• Identificação direta por USB Hardware ID (VID & PID)\n"
            "• Suporte e delimitação de telas por monitor\n"
            "• Personalização completa da forma, cor e tamanho do ponteiro\n"
            "• Supressão de conflitos via Low-Level Hook e Windows Raw Input API\n"
            "• Inicialização automática integrada com o Windows"
        )
        tk.Label(
            about_card, text=desc_text,
            font=("Segoe UI", 9), fg=TEXT_PRIMARY, bg=BG_CARD,
            justify="center", wraplength=550
        ).pack(pady=14)

    def _build_footer(self):
        footer = tk.Frame(self.root, bg=BG_DARK, pady=10, padx=20)
        footer.pack(fill=tk.X)
        
        self.btn_save = tk.Button(
            footer, text="💾 Salvar Configurações",
            font=("Segoe UI", 10, "bold"), fg="#FFFFFF", bg="#0284C7",
            activebackground="#0369A1", relief=tk.FLAT, padx=16, pady=7,
            cursor="hand2", command=self.save_and_apply
        )
        self.btn_save.pack(side=tk.RIGHT)

        lbl_failsafe = tk.Label(
            footer, text="Atalho de Emergência para Pausar/Ativar: F12 ou Botão Mestre",
            font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_DARK
        )
        lbl_failsafe.pack(side=tk.LEFT)

    # --- LÓGICA DE ATUALIZAÇÃO E EVENTOS ---

    def refresh_devices(self):
        """Busca mouses conectados e atualiza os dropdowns."""
        self.connected_mice = get_connected_mice()
        labels = [m['display_label'] for m in self.connected_mice]
        
        self.cb_m1_device['values'] = labels
        self.cb_m2_device['values'] = labels
        
        # Seleciona Mouse 1 com base no config
        m1_hwid = self.config.get("mouse1", {}).get("hwid", "")
        sel_idx_1 = 0
        for i, m in enumerate(self.connected_mice):
            if m1_hwid and m1_hwid in m['hwid']:
                sel_idx_1 = i
                break
        if labels:
            self.cb_m1_device.current(sel_idx_1)
            self._update_m1_hwid_label(self.connected_mice[sel_idx_1])
            
        # Seleciona Mouse 2
        m2_hwid = self.config.get("mouse2", {}).get("hwid", "")
        sel_idx_2 = 1 if len(labels) > 1 else 0
        for i, m in enumerate(self.connected_mice):
            if m2_hwid and m2_hwid in m['hwid']:
                sel_idx_2 = i
                break
        if labels:
            self.cb_m2_device.current(sel_idx_2)
            self._update_m2_hwid_label(self.connected_mice[sel_idx_2])

    def refresh_monitors(self):
        """Busca monitores conectados e atualiza os dropdowns e a lista visual."""
        self.connected_monitors = get_monitors()
        mon_options = ["Todos os Monitores"] + [m['label'] for m in self.connected_monitors]
        
        self.cb_m1_monitor['values'] = mon_options
        self.cb_m2_monitor['values'] = mon_options
        
        # Seleção Mouse 1
        m1_mons = self.config.get("mouse1", {}).get("monitors", [1])
        if 0 in m1_mons or not m1_mons:
            self.cb_m1_monitor.current(0)
        else:
            idx = m1_mons[0]
            self.cb_m1_monitor.current(idx if idx <= len(self.connected_monitors) else 0)
            
        # Seleção Mouse 2
        m2_mons = self.config.get("mouse2", {}).get("monitors", [2])
        if 0 in m2_mons or not m2_mons:
            self.cb_m2_monitor.current(0)
        else:
            idx = m2_mons[0]
            self.cb_m2_monitor.current(idx if idx <= len(self.connected_monitors) else 0)

        # Atualiza a exibição de monitores na aba Sistema
        for widget in self.monitors_listbox_frame.winfo_children():
            widget.destroy()
            
        for mon in self.connected_monitors:
            row = tk.Frame(self.monitors_listbox_frame, bg=BG_DARK, pady=8, padx=10)
            row.pack(fill=tk.X, pady=3)
            
            p_badge = " [PRINCIPAL]" if mon['primary'] else ""
            tk.Label(
                row, text=f"🖥️ {mon['label']}",
                font=("Segoe UI", 10, "bold"), fg=TEXT_PRIMARY, bg=BG_DARK
            ).pack(side=tk.LEFT)
            
            tk.Label(
                row, text=f"Posição: ({mon['left']}, {mon['top']}) até ({mon['right']}, {mon['bottom']})",
                font=("Consolas", 8), fg=TEXT_MUTED, bg=BG_DARK
            ).pack(side=tk.RIGHT)

    def _update_m1_hwid_label(self, dev: Dict):
        hwid = dev.get('hwid', '')
        inst = dev.get('instance_id', '')
        self.lbl_m1_hwid_detail.config(text=f"Hardware ID: {hwid} | Instância: {inst}")

    def _update_m2_hwid_label(self, dev: Dict):
        hwid = dev.get('hwid', '')
        inst = dev.get('instance_id', '')
        self.lbl_m2_hwid_detail.config(text=f"Hardware ID: {hwid} | Instância: {inst}")

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

    # --- PERSONALIZAÇÃO DE CURSORES ---

    def _on_cursor_target_changed(self):
        target = self.cursor_target_var.get()
        self._load_cursor_form(target)

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
        """Redesenha o cursor no canvas de pré-visualização."""
        self.preview_canvas.delete("all")
        target = self.cursor_target_var.get()
        c_cfg = self.config.get(target, {}).get("cursor", {})
        
        # Desenha grade de fundo estilo display
        w = self.preview_canvas.winfo_width() or 240
        h = self.preview_canvas.winfo_height() or 200
        for x in range(0, w, 30):
            self.preview_canvas.create_line(x, 0, x, h, fill="#131B2E", width=1)
        for y in range(0, h, 30):
            self.preview_canvas.create_line(0, y, w, y, fill="#131B2E", width=1)
            
        draw_cursor_on_canvas(self.preview_canvas, mouse_x, mouse_y, c_cfg, scale=1.2)

    def _on_canvas_motion(self, event):
        self._render_preview(event.x, event.y)

    # --- INICIALIZAÇÃO E SISTEMA ---

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

    def _on_sim_mode_toggled(self):
        sim = self.chk_sim_var.get()
        self.config["system"]["simulation_mode"] = sim
        self.engine.simulation_mode = sim
        self.engine.update_config(self.config)

    def _on_hide_os_cursor_toggled(self):
        hide = self.chk_hide_os_var.get()
        self.config["system"]["hide_os_cursor"] = hide
        self.engine.update_config(self.config)

    def _on_toggle_engine_clicked(self):
        is_active = self.engine.toggle_pause()
        if is_active:
            self.lbl_status_pill.config(text="● ATIVO", fg=ACCENT_GREEN, bg="#064E3B")
            self.btn_toggle_engine.config(text="Pausar Motor", bg="#DC2626", activebackground="#B91C1C")
        else:
            self.lbl_status_pill.config(text="❚❚ PAUSADO", fg=ACCENT_ORANGE, bg="#78350F")
            self.btn_toggle_engine.config(text="Ativar Motor", bg="#16A34A", activebackground="#15803D")

    def _on_device_activity(self, target: str):
        """Atualiza indicadores visuais de atividade quando um mouse se move."""
        if target == 'm1':
            self.lbl_m1_active.config(text="● Movendo / Clicando...", fg=ACCENT_GREEN)
            self.root.after(300, lambda: self.lbl_m1_active.config(text="● Conectado e Ativo", fg=TEXT_MUTED))
        else:
            self.lbl_m2_active.config(text="● Movendo / Clicando...", fg=ACCENT_ORANGE)
            self.root.after(300, lambda: self.lbl_m2_active.config(text="● Conectado e Ativo", fg=TEXT_MUTED))

    def save_and_apply(self):
        save_config(self.config)
        self.engine.update_config(self.config)
        messagebox.showinfo("Configurações Salvas", "As configurações dos mouses, monitores e cursores foram salvas com sucesso!")
