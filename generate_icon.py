import struct
import math

def create_icon(filename="app_icon.ico"):
    sizes = [16, 32, 48, 64]
    images_data = []
    
    for s in sizes:
        # Create BGRA buffer (bottom-up)
        # We will draw:
        # Background: rounded dark slate square with monitor outline
        # Two pointer arrows:
        # Pointer 1: Cyan/Blue pointing top-left
        # Pointer 2: Neon Orange/Gold pointing top-right/center
        pixels = bytearray(s * s * 4)
        
        for y in range(s):
            for x in range(s):
                # normalize coords (0 to 1)
                nx = x / (s - 1)
                # Note: BMP stores rows from bottom to top!
                ny = (s - 1 - y) / (s - 1) # ny=1 is top, ny=0 is bottom
                
                # Default transparent
                b, g, r, a = 0, 0, 0, 0
                
                # Draw rounded rectangle background (badge)
                cx = nx - 0.5
                cy = ny - 0.5
                dist_box = max(abs(cx) - 0.38, abs(cy) - 0.38)
                if dist_box < 0.05:
                    # Dark blue/slate background
                    r, g, b, a = 18, 24, 38, 230
                
                # Monitor frame lines (horizontal bar at bottom, stand)
                if 0.15 <= nx <= 0.85 and abs(ny - 0.22) < 0.03:
                    # Monitor stand bar
                    r, g, b, a = 90, 105, 130, 255
                
                # Pointer 1: Blue/Cyan arrow on left side
                # Triangle tip at (0.22, 0.78)
                p1_tip_x, p1_tip_y = 0.22, 0.78
                dx1 = nx - p1_tip_x
                dy1 = p1_tip_y - ny # downward
                if 0 <= dx1 <= 0.38 and 0 <= dy1 <= 0.38:
                    if dx1 <= dy1 * 0.75 and dy1 <= 0.35:
                        # Inside arrow body
                        r, g, b, a = 0, 210, 255, 255
                    elif abs(dx1 - dy1 * 0.75) < 0.04 or abs(dx1) < 0.04:
                        # Arrow border
                        r, g, b, a = 255, 255, 255, 255
                
                # Pointer 2: Orange/Neon Yellow arrow on right side
                # Triangle tip at (0.55, 0.65)
                p2_tip_x, p2_tip_y = 0.55, 0.65
                dx2 = nx - p2_tip_x
                dy2 = p2_tip_y - ny
                if 0 <= dx2 <= 0.38 and 0 <= dy2 <= 0.38:
                    if dx2 <= dy2 * 0.75 and dy2 <= 0.35:
                        # Inside arrow body
                        r, g, b, a = 255, 130, 0, 255
                    elif abs(dx2 - dy2 * 0.75) < 0.04 or abs(dx2) < 0.04:
                        # Arrow border
                        r, g, b, a = 255, 255, 255, 255
                
                idx = (y * s + x) * 4
                pixels[idx] = b
                pixels[idx + 1] = g
                pixels[idx + 2] = r
                pixels[idx + 3] = a
        
        # BitmapInfoHeader
        # biHeight is s * 2 (image height + mask height)
        bi_size = 40
        bi_width = s
        bi_height = s * 2
        bi_planes = 1
        bi_bit_count = 32
        bi_compression = 0
        bi_size_image = len(pixels)
        
        header = struct.pack('<IIIHHIIIIII',
            bi_size, bi_width, bi_height, bi_planes, bi_bit_count,
            bi_compression, bi_size_image, 0, 0, 0, 0
        )
        
        # AND mask (1 bit per pixel, row padded to 32 bits = 4 bytes)
        mask_row_bytes = ((s + 31) // 32) * 4
        and_mask = bytearray(mask_row_bytes * s)
        # All 0s for 32-bit RGBA (alpha channel handles transparency)
        
        img_bytes = header + pixels + and_mask
        images_data.append((s, img_bytes))

    # Assemble ICO file
    icon_count = len(images_data)
    ico_header = struct.pack('<HHH', 0, 1, icon_count)
    
    offset = 6 + 16 * icon_count
    dir_entries = []
    
    for s, data in images_data:
        w = s if s < 256 else 0
        h = s if s < 256 else 0
        entry = struct.pack('<BBBBHHII',
            w, h, 0, 0, 1, 32, len(data), offset
        )
        dir_entries.append(entry)
        offset += len(data)
        
    with open(filename, 'wb') as f:
        f.write(ico_header)
        for e in dir_entries:
            f.write(e)
        for _, data in images_data:
            f.write(data)
    print(f"Generated icon: {filename} ({offset} bytes)")

if __name__ == '__main__':
    create_icon('assets/icon.ico')
