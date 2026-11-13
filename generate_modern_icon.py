"""
Script para geração de Ícone Ultra-Moderno em Alta Resolução com Pillow
DualPointer Pro - Desenvolvido por Caio Monteiro (chacalbl4ck)
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os
import math

def create_modern_icon(output_path="assets/icon.ico"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Renderiza em alta resolução 1024x1024 para anti-aliasing perfeito
    S = 1024
    master = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    
    # 1. Sombra Suave (Drop Shadow) do ícone
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    margin = 80
    corner_radius = 210
    
    # Sombra projetada para baixo
    s_draw.rounded_rectangle(
        [margin, margin + 40, S - margin, S - margin + 40],
        radius=corner_radius,
        fill=(2, 6, 23, 160)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=36))
    master.alpha_composite(shadow)
    
    # 2. Camada do Fundo (Squircle Dark Slate Glass)
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(base)
    
    # Fundo em degradê escuro sofisticado
    # Cria máscara do squircle
    mask = Image.new("L", (S, S), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle(
        [margin, margin, S - margin, S - margin],
        radius=corner_radius,
        fill=255
    )
    
    # Preenchimento em gradiente vertical escuro (Deep Slate / Obsidian)
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grad)
    for y in range(margin, S - margin):
        ratio = (y - margin) / (S - 2 * margin)
        # De #0B1120 (11, 17, 32) para #1E293B (30, 41, 59)
        r = int(11 + ratio * 19)
        g = int(17 + ratio * 24)
        b = int(32 + ratio * 27)
        g_draw.line([(margin, y), (S - margin, y)], fill=(r, g, b, 255))
        
    base.paste(grad, (0, 0), mask)
    
    # 3. Borda com Brilho Neon Duplo (Ciano no topo-esquerdo, Laranja na base-direita)
    # Desenha anel de contorno elegante
    b_draw.rounded_rectangle(
        [margin, margin, S - margin, S - margin],
        radius=corner_radius,
        outline=(56, 189, 248, 180), # Cyan glow border
        width=8
    )
    # Arco inferior em neon orange
    b_draw.arc(
        [margin, margin, S - margin, S - margin],
        start=0, end=90,
        fill=(251, 146, 60, 220), # Orange
        width=10
    )
    
    # 4. Representação Gráfica dos Dois Monitores (Dual Display Setup)
    # Monitor 1 (Esquerda)
    mon_y1 = margin + 140
    mon_y2 = S - margin - 220
    mon1_x1 = margin + 100
    mon1_x2 = S // 2 - 25
    
    # Monitor 2 (Direita)
    mon2_x1 = S // 2 + 25
    mon2_x2 = S - margin - 100
    
    mon_radius = 28
    
    # Telas dos monitores (Glass transparente com borda fina)
    b_draw.rounded_rectangle(
        [mon1_x1, mon_y1, mon1_x2, mon_y2],
        radius=mon_radius,
        fill=(15, 23, 42, 180),
        outline=(56, 189, 248, 120),
        width=4
    )
    b_draw.rounded_rectangle(
        [mon2_x1, mon_y1, mon2_x2, mon_y2],
        radius=mon_radius,
        fill=(15, 23, 42, 180),
        outline=(251, 146, 60, 120),
        width=4
    )
    
    # Base/Suporte sutil dos monitores
    stand_y = mon_y2 + 40
    b_draw.rectangle([S // 2 - 120, mon_y2 + 2, S // 2 + 120, stand_y], fill=(30, 41, 59, 200))
    b_draw.rounded_rectangle([S // 2 - 180, stand_y, S // 2 + 180, stand_y + 16], radius=8, fill=(71, 85, 105, 255))
    
    # Indicador de tela 1 e tela 2 (números sutis no topo da tela)
    b_draw.ellipse([mon1_x1 + 30, mon_y1 + 30, mon1_x1 + 65, mon_y1 + 65], fill=(56, 189, 248, 50), outline=(56, 189, 248, 180), width=2)
    b_draw.ellipse([mon2_x2 - 65, mon_y1 + 30, mon2_x2 - 30, mon_y1 + 65], fill=(251, 146, 60, 50), outline=(251, 146, 60, 180), width=2)

    master.alpha_composite(base)
    
    # 5. Desenho dos Dois Ponteiros Modernos e Aerodinâmicos
    # Função auxiliar para desenhar ponteiro com sombra e borda precisa
    def draw_pointer(cx, cy, scale, fill_color, border_color, badge_text, badge_color):
        ptr_img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(ptr_img)
        
        # Geometria moderna do cursor tipo Sleek Fluent
        raw_poly = [
            (0.0, 0.0),
            (0.0, 0.88),
            (0.24, 0.68),
            (0.44, 1.00),
            (0.60, 0.90),
            (0.38, 0.60),
            (0.72, 0.60)
        ]
        
        poly_pts = [(cx + px * scale, cy + py * scale) for px, py in raw_poly]
        
        # Sombra do cursor
        shadow_pts = [(x + 8, y + 14) for x, y in poly_pts]
        p_draw.polygon(shadow_pts, fill=(0, 0, 0, 140))
        
        # Glow suave do cursor
        glow_r = scale * 0.8
        p_draw.ellipse(
            [cx - glow_r * 0.2, cy - glow_r * 0.2, cx + glow_r * 1.2, cy + glow_r * 1.2],
            outline=(fill_color[0], fill_color[1], fill_color[2], 60),
            width=8
        )
        
        # Borda externa branca pura
        p_draw.polygon(poly_pts, fill=border_color)
        
        # Corpo interno colorido (levemente reduzido para criar borda perfeita)
        # Calcula centróide para encolher ligeiramente
        centroid_x = sum(p[0] for p in poly_pts) / len(poly_pts)
        centroid_y = sum(p[1] for p in poly_pts) / len(poly_pts)
        inner_pts = []
        shrink = 0.90
        for px, py in poly_pts:
            nx = centroid_x + (px - centroid_x) * shrink
            ny = centroid_y + (py - centroid_y) * shrink
            inner_pts.append((nx, ny))
            
        p_draw.polygon(inner_pts, fill=fill_color)
        
        # Pill Badge flutuante (1 ou 2)
        bx = cx + scale * 0.76
        by = cy + scale * 0.64
        pw = scale * 0.24
        ph = scale * 0.20
        
        # Sombra do Badge
        p_draw.rounded_rectangle([bx - pw + 3, by - ph + 4, bx + pw + 3, by + ph + 4], radius=14, fill=(0, 0, 0, 120))
        # Fundo escuro do badge
        p_draw.rounded_rectangle([bx - pw, by - ph, bx + pw, by + ph], radius=14, fill=(15, 23, 42, 255), outline=badge_color, width=4)
        
        # Tenta carregar fonte para o badge ou desenha o caractere
        try:
            font = ImageFont.truetype("arial.ttf", int(scale * 0.26))
        except Exception:
            font = ImageFont.load_default()
            
        # Desenha número no badge
        p_draw.text((bx, by), badge_text, fill=(255, 255, 255, 255), font=font, anchor="mm")
        
        return ptr_img

    # Mouse 1: Ciano Elétrico apontando na Tela 1
    ptr1 = draw_pointer(
        cx=mon1_x1 + 80,
        cy=mon_y1 + 100,
        scale=260,
        fill_color=(0, 229, 255, 255),   # #00E5FF
        border_color=(255, 255, 255, 255),
        badge_text="1",
        badge_color=(0, 229, 255, 255)
    )
    master.alpha_composite(ptr1)
    
    # Mouse 2: Laranja Neon apontando na Tela 2
    ptr2 = draw_pointer(
        cx=mon2_x1 + 90,
        cy=mon_y1 + 170,
        scale=260,
        fill_color=(255, 109, 0, 255),   # #FF6D00
        border_color=(255, 255, 255, 255),
        badge_text="2",
        badge_color=(255, 109, 0, 255)
    )
    master.alpha_composite(ptr2)
    
    # 6. Salva nos formatos ICO com múltiplos tamanhos (256, 128, 64, 48, 32, 16)
    # Redimensiona com filtro LANCZOS para máxima nitidez em cada resolução
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    
    # Salva o arquivo .ico
    master.save(
        output_path,
        format="ICO",
        sizes=icon_sizes
    )
    
    # Também salva um PNG preview de alta definição para visualização
    png_path = output_path.replace(".ico", ".png")
    master.resize((512, 512), Image.Resampling.LANCZOS).save(png_path, format="PNG")
    print(f"Ícone gerado com sucesso em: {output_path} e {png_path}")

if __name__ == "__main__":
    create_modern_icon()
