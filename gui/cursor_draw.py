"""
Módulo de Desenho e Renderização de Cursores Customizados
DualPointer Pro
Compatível com Canvas Tkinter e GDI do Windows.
"""

from typing import Dict, Any, List, Tuple

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converte '#RRGGBB' em (R, G, B)."""
    hex_clean = hex_str.lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = ''.join([c*2 for c in hex_clean])
    if len(hex_clean) != 6:
        return (0, 210, 255)
    return (int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16))

def get_cursor_polygon(shape: str, size: int) -> List[Tuple[float, float]]:
    """
    Retorna os vértices de polígono do cursor com base na forma e tamanho.
    O ponto de clique (hotspot) é (0, 0).
    """
    s = float(size)
    shape = shape.lower()
    
    if shape == "cyber":
        return [
            (0.0, 0.0),
            (0.0, s * 0.82),
            (s * 0.22, s * 0.68),
            (s * 0.38, s * 0.95),
            (s * 0.52, s * 0.88),
            (s * 0.36, s * 0.60),
            (s * 0.78, s * 0.40),
            (s * 0.40, s * 0.38)
        ]
    elif shape == "stylus":
        return [
            (0.0, 0.0),
            (s * 0.30, s * 0.06),
            (s * 0.85, s * 0.70),
            (s * 0.70, s * 0.85),
            (s * 0.06, s * 0.30)
        ]
    else: # "arrow" padrão moderno
        return [
            (0.0, 0.0),
            (0.0, s * 0.85),
            (s * 0.24, s * 0.65),
            (s * 0.44, s * 0.98),
            (s * 0.58, s * 0.90),
            (s * 0.38, s * 0.58),
            (s * 0.68, s * 0.58)
        ]

def draw_cursor_on_canvas(canvas, cx: float, cy: float, cursor_cfg: Dict[str, Any], scale: float = 1.0):
    """
    Desenha o cursor com design personalizado dentro de um Canvas do Tkinter.
    cx, cy: posição do ponteiro dentro do canvas.
    """
    shape = cursor_cfg.get("shape", "arrow").lower()
    color = cursor_cfg.get("color", "#00D2FF")
    border_color = cursor_cfg.get("border_color", "#FFFFFF")
    size = int(cursor_cfg.get("size", 28) * scale)
    glow = cursor_cfg.get("glow", True)
    show_label = cursor_cfg.get("show_label", True)
    label_text = cursor_cfg.get("label_text", "M1")
    
    # 1. Desenha Glow / Aura se ativado
    if glow:
        glow_radius = size * 0.85
        # Anel externo translúcido
        canvas.create_oval(
            cx - glow_radius, cy - glow_radius,
            cx + glow_radius, cy + glow_radius,
            outline=color, width=2
        )
        glow_inner = size * 0.55
        canvas.create_oval(
            cx - glow_inner, cy - glow_inner,
            cx + glow_inner, cy + glow_inner,
            outline=color, width=1
        )

    # 2. Desenha a forma do cursor
    if shape in ["arrow", "cyber", "stylus"]:
        poly = get_cursor_polygon(shape, size)
        points = []
        for px, py in poly:
            points.extend([cx + px, cy + py])
            
        # Sombra suave
        shadow_pts = [p + 2 for p in points]
        canvas.create_polygon(shadow_pts, fill="#0A0E17", outline="", smooth=False)
        
        # Corpo do ponteiro com borda
        canvas.create_polygon(
            points,
            fill=color,
            outline=border_color,
            width=2,
            smooth=False
        )
    elif shape == "crosshair":
        r = size * 0.4
        # Mira circular
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=border_color, width=2)
        canvas.create_oval(cx - r*0.8, cy - r*0.8, cx + r*0.8, cy + r*0.8, outline=color, width=1.5)
        # Linhas cruzadas
        ext = r * 1.4
        canvas.create_line(cx - ext, cy, cx - r*0.3, cy, fill=color, width=2)
        canvas.create_line(cx + r*0.3, cy, cx + ext, cy, fill=color, width=2)
        canvas.create_line(cx, cy - ext, cx, cy - r*0.3, fill=color, width=2)
        canvas.create_line(cx, cy + r*0.3, cx, cy + ext, fill=color, width=2)
        # Ponto central
        canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=border_color, outline=color)
    elif shape == "dot":
        r = size * 0.35
        # Círculo externo
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=border_color, width=2)
        # Núcleo brilhante
        core_r = r * 0.4
        canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r, fill="#FFFFFF", outline="")

    # 3. Desenha etiqueta / badge de identificação (M1 / M2)
    if show_label and label_text:
        badge_x = cx + size * 0.75
        badge_y = cy + size * 0.65
        pad_w = max(10, len(label_text) * 4 + 4)
        pad_h = 8
        
        # Fundo do badge
        canvas.create_rectangle(
            badge_x - pad_w, badge_y - pad_h,
            badge_x + pad_w, badge_y + pad_h,
            fill="#0F172A", outline=color, width=1.5
        )
        # Texto
        canvas.create_text(
            badge_x, badge_y,
            text=label_text,
            fill="#FFFFFF",
            font=("Segoe UI", int(max(7, size * 0.3)), "bold")
        )
