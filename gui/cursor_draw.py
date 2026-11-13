"""
Módulo de Desenho e Renderização de Cursores Customizados Modernos
DualPointer Pro
Compatível com Canvas Tkinter e GDI do Windows.
Desenvolvido por Caio Monteiro (chacalbl4ck)
"""

from typing import Dict, Any, List, Tuple

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converte '#RRGGBB' em (R, G, B)."""
    hex_clean = hex_str.lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = ''.join([c*2 for c in hex_clean])
    if len(hex_clean) != 6:
        return (56, 189, 248) # Default modern cyan
    return (int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16))

def get_cursor_polygon(shape: str, size: int) -> List[Tuple[float, float]]:
    """
    Retorna os vértices do polígono do cursor com base na forma e tamanho.
    O ponto de clique (hotspot) é sempre (0, 0).
    """
    s = float(size)
    shape = shape.lower()
    
    if shape in ["sleek", "arrow"]:
        # Seta Sleek Minimalista Moderna (Proporção Áurea estilo macOS Sonoma / Windows 11 Fluent)
        return [
            (0.0, 0.0),             # Ponta afiada
            (0.0, s * 0.88),         # Borda esquerda vertical reta e limpa
            (s * 0.22, s * 0.70),    # Entalhe interno esquerdo
            (s * 0.44, s * 1.00),    # Haste inferior direita
            (s * 0.58, s * 0.92),    # Ponta da haste
            (s * 0.36, s * 0.62),    # Entalhe interno direito
            (s * 0.70, s * 0.62)     # Asa direita em 45 graus
        ]
    elif shape == "fluent":
        # Seta Aerodinâmica Fluent com base suave
        return [
            (0.0, 0.0),
            (0.0, s * 0.82),
            (s * 0.24, s * 0.66),
            (s * 0.38, s * 0.92),
            (s * 0.50, s * 0.85),
            (s * 0.36, s * 0.58),
            (s * 0.65, s * 0.58)
        ]
    elif shape == "cyber":
        # Seta Angular Futurista
        return [
            (0.0, 0.0),
            (0.0, s * 0.82),
            (s * 0.22, s * 0.68),
            (s * 0.36, s * 0.94),
            (s * 0.48, s * 0.86),
            (s * 0.34, s * 0.60),
            (s * 0.76, s * 0.40),
            (s * 0.38, s * 0.38)
        ]
    elif shape == "stylus":
        # Caneta Stylus / Ponta de Desenho Técnico
        return [
            (0.0, 0.0),
            (s * 0.28, s * 0.05),
            (s * 0.82, s * 0.68),
            (s * 0.68, s * 0.82),
            (s * 0.05, s * 0.28)
        ]
    else:
        # Padrão Sleek
        return [
            (0.0, 0.0),
            (0.0, s * 0.88),
            (s * 0.22, s * 0.70),
            (s * 0.44, s * 1.00),
            (s * 0.58, s * 0.92),
            (s * 0.36, s * 0.62),
            (s * 0.70, s * 0.62)
        ]

def draw_cursor_on_canvas(canvas, cx: float, cy: float, cursor_cfg: Dict[str, Any], scale: float = 1.0):
    """
    Desenha o cursor com design limpo e moderno dentro de um Canvas do Tkinter.
    cx, cy: posição do ponteiro dentro do canvas.
    """
    shape = cursor_cfg.get("shape", "sleek").lower()
    color = cursor_cfg.get("color", "#38BDF8")
    border_color = cursor_cfg.get("border_color", "#FFFFFF")
    size = int(cursor_cfg.get("size", 28) * scale)
    glow = cursor_cfg.get("glow", True)
    show_label = cursor_cfg.get("show_label", True)
    label_text = cursor_cfg.get("label_text", "1")
    
    # 1. Aura / Glow Sutil e Elegante
    if glow:
        gr = size * 0.72
        # Círculo externo fino e translúcido
        canvas.create_oval(
            cx - gr, cy - gr,
            cx + gr, cy + gr,
            outline=color, width=1.5
        )

    # 2. Sombra Suave (Drop Shadow) para dar profundidade e contraste
    shadow_offset = max(2, int(size * 0.08))
    
    if shape in ["sleek", "arrow", "fluent", "cyber", "stylus"]:
        poly = get_cursor_polygon(shape, size)
        
        # Sombra
        shadow_pts = []
        for px, py in poly:
            shadow_pts.extend([cx + px + shadow_offset, cy + py + shadow_offset])
        canvas.create_polygon(shadow_pts, fill="#020617", outline="", smooth=False)
        
        # Corpo principal do cursor
        points = []
        for px, py in poly:
            points.extend([cx + px, cy + py])
            
        canvas.create_polygon(
            points,
            fill=color,
            outline=border_color,
            width=2,
            smooth=False
        )
    elif shape in ["precision", "crosshair"]:
        # Mira Minimalista de Alta Precisão
        r = size * 0.38
        gap = size * 0.12
        ext = size * 0.55
        
        # Sombra da mira
        canvas.create_oval(cx - r + 1, cy - r + 1, cx + r + 1, cy + r + 1, outline="#020617", width=2)
        # Círculo reticular
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=border_color, width=1.5)
        canvas.create_oval(cx - r*0.8, cy - r*0.8, cx + r*0.8, cy + r*0.8, outline=color, width=1)
        
        # Traços de mira com folga no centro
        canvas.create_line(cx - ext, cy, cx - gap, cy, fill=color, width=2)
        canvas.create_line(cx + gap, cy, cx + ext, cy, fill=color, width=2)
        canvas.create_line(cx, cy - ext, cx, cy - gap, fill=color, width=2)
        canvas.create_line(cx, cy + gap, cx, cy + ext, fill=color, width=2)
        
        # Ponto central
        canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill="#FFFFFF", outline=color)
    elif shape in ["capsule", "dot"]:
        # Ponto Halo Minimalista
        r = size * 0.32
        # Sombra
        canvas.create_oval(cx - r + 1.5, cy - r + 1.5, cx + r + 1.5, cy + r + 1.5, fill="#020617", outline="")
        # Círculo principal com borda
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=border_color, width=2)
        # Núcleo branco puro central
        core = r * 0.4
        canvas.create_oval(cx - core, cy - core, cx + core, cy + core, fill="#FFFFFF", outline="")

    # 3. Pill Badge Moderno e Limpo (1 / 2 ou M1 / M2)
    if show_label and label_text:
        badge_x = cx + size * 0.72
        badge_y = cy + size * 0.62
        
        if len(label_text) == 1:
            r = max(6.5, size * 0.22)
            # Sombra
            canvas.create_oval(badge_x - r + 1, badge_y - r + 1, badge_x + r + 1, badge_y + r + 1, fill="#020617", outline="")
            # Círculo Dark Slate com borda da cor do ponteiro
            canvas.create_oval(badge_x - r, badge_y - r, badge_x + r, badge_y + r, fill="#0F172A", outline=color, width=1.5)
        else:
            pw = max(9.0, len(label_text) * 4.5 + 4)
            ph = max(6.5, size * 0.20)
            # Sombra
            canvas.create_rectangle(badge_x - pw + 1, badge_y - ph + 1, badge_x + pw + 1, badge_y + ph + 1, fill="#020617", outline="")
            # Corpo
            canvas.create_rectangle(badge_x - pw, badge_y - ph, badge_x + pw, badge_y + ph, fill="#0F172A", outline=color, width=1.5)
            
        # Texto branco centralizado com fonte Segoe UI
        canvas.create_text(
            badge_x, badge_y,
            text=label_text,
            fill="#FFFFFF",
            font=("Segoe UI", int(max(7, size * 0.26)), "bold")
        )
