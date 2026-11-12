"""
Motor Central de Gerenciamento Dual Mouse e Multi-Monitor
DualPointer Pro
Desenvolvido por Caio Monteiro (chacalbl4ck)
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import Dict, Any, Optional, Tuple, Callable

from core.monitors import get_monitor_bounds_for_indices, get_virtual_desktop_rect, clamp_to_bounds
from core.devices import matches_device
from gui.cursor_draw import get_cursor_polygon, hex_to_rgb

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# Constantes do Win32
WM_INPUT = 0x00FF
WM_PAINT = 0x000F
WM_DESTROY = 0x0002

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

LWA_COLORKEY = 0x00000001
TRANSPARENT_COLOR = 0x00FF00FF  # Magenta puro como chave de transparência

RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0

WH_MOUSE_LL = 14
LLMHF_INJECTED = 0x00000001
EXTRA_INFO_MAGIC = 0x12345678  # Marcador único para cliques injetados pelo DualPointer

# IDs de Cursores Nativos do Windows para ocultação
SYSTEM_CURSOR_IDS = [
    32512,  # OCR_NORMAL
    32513,  # OCR_IBEAM
    32514,  # OCR_WAIT
    32515,  # OCR_CROSS
    32516,  # OCR_UP
    32642,  # OCR_SIZENWSE
    32643,  # OCR_SIZENESW
    32644,  # OCR_SIZEWE
    32645,  # OCR_SIZENS
    32646,  # OCR_SIZEALL
    32648,  # OCR_NO
    32649,  # OCR_HAND
    32650   # OCR_APPSTARTING
]

# Estruturas do Win32
class POINT(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

class RECT(ctypes.Structure):
    _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG), ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ('hdc', wintypes.HDC),
        ('fErase', wintypes.BOOL),
        ('rcPaint', RECT),
        ('fRestore', wintypes.BOOL),
        ('fIncUpdate', wintypes.BOOL),
        ('rgbReserved', ctypes.c_byte * 32)
    ]

class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ('dwType', wintypes.DWORD),
        ('dwSize', wintypes.DWORD),
        ('hDevice', wintypes.HANDLE),
        ('wParam', wintypes.WPARAM),
    ]

class RAWMOUSE_BUTTONS(ctypes.Structure):
    _fields_ = [
        ('usButtonFlags', wintypes.USHORT),
        ('usButtonData', wintypes.USHORT),
    ]

class RAWMOUSE_UNION(ctypes.Union):
    _fields_ = [
        ('ulButtons', wintypes.ULONG),
        ('buttons', RAWMOUSE_BUTTONS),
    ]

class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ('usFlags', wintypes.USHORT),
        ('union', RAWMOUSE_UNION),
        ('ulRawButtons', wintypes.ULONG),
        ('lLastX', wintypes.LONG),
        ('lLastY', wintypes.LONG),
        ('ulExtraInformation', ctypes.c_ulonglong),
    ]

class RAWINPUT(ctypes.Structure):
    _fields_ = [
        ('header', RAWINPUTHEADER),
        ('mouse', RAWMOUSE),
    ]

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ('usUsagePage', wintypes.USHORT),
        ('usUsage', wintypes.USHORT),
        ('dwFlags', wintypes.DWORD),
        ('hwndTarget', wintypes.HWND)
    ]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('pt', POINT),
        ('mouseData', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_ulonglong)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_ulonglong)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [('mi', MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('u', INPUT_UNION)
    ]

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('style', wintypes.UINT),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HANDLE),
        ('hCursor', wintypes.HANDLE),
        ('hbrBackground', wintypes.HANDLE),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
        ('hIconSm', wintypes.HANDLE)
    ]

# Configuração de assinaturas das funções do Win32
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_longlong

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
user32.RegisterRawInputDevices.restype = wintypes.BOOL

user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputData.restype = wintypes.UINT

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_longlong

user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND

user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.CreateIcon.argtypes = [
    wintypes.HINSTANCE, ctypes.c_int, ctypes.c_int,
    ctypes.c_byte, ctypes.c_byte,
    ctypes.c_void_p, ctypes.c_void_p
]
user32.CreateIcon.restype = wintypes.HICON

user32.SetSystemCursor.argtypes = [wintypes.HICON, wintypes.DWORD]
user32.SetSystemCursor.restype = wintypes.BOOL

user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
user32.SystemParametersInfoW.restype = wintypes.BOOL

user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = wintypes.HDC

user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.EndPaint.restype = wintypes.BOOL

user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), wintypes.HBRUSH]
user32.FillRect.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC

gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP

gdi32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
gdi32.BitBlt.restype = wintypes.BOOL

gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH

gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
gdi32.CreatePen.restype = wintypes.HPEN

gdi32.Polygon.argtypes = [wintypes.HDC, ctypes.POINTER(POINT), ctypes.c_int]
gdi32.Polygon.restype = wintypes.BOOL

gdi32.Ellipse.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdi32.Ellipse.restype = wintypes.BOOL

gdi32.RoundRect.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdi32.RoundRect.restype = wintypes.BOOL

gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetTextColor.restype = wintypes.COLORREF

gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int

gdi32.TextOutW.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int]
gdi32.TextOutW.restype = wintypes.BOOL

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = wintypes.HGDIOBJ

gdi32.MoveToEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
gdi32.MoveToEx.restype = wintypes.BOOL

gdi32.LineTo.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.LineTo.restype = wintypes.BOOL


class DualPointerEngine:
    """
    Motor avançado de múltiplos mouses simultâneos e independentes.
    Mantém 2 ponteiros totalmente isolados entre monitores (movimentos, cliques,
    arraste contínuo e rolagem não se misturam nem se interferem).
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        
        # Coordenadas dos ponteiros (Mouse 1 e Mouse 2)
        self.pos1 = [250.0, 250.0]
        self.pos2 = [650.0, 350.0]
        
        # Limites dos monitores
        self.bounds1 = (0, 0, 1920, 1080)
        self.bounds2 = (0, 0, 1920, 1080)
        self.virtual_rect = (0, 0, 1920, 1080)
        
        # Mapeamento de identificadores de hardware para dispositivos
        self.device_map: Dict[int, str] = {} # handle -> 'm1' ou 'm2'
        self.active_handles: Dict[str, int] = {} # 'm1'/'m2' -> handle
        
        # Estado de botões pressionados (Garante isolamento de arraste)
        self.m1_down = False
        self.m1_rdown = False
        self.m2_down = False
        self.m2_rdown = False
        self.active_mouse = "m1"
        
        # Janelas ativas por monitor
        self.active_wnd_m1: Optional[int] = None
        self.active_wnd_m2: Optional[int] = None
        
        # Janelas e Hook Win32
        self.hwnd_overlay: Optional[int] = None
        self.hook: Optional[int] = None
        self._hook_cb_ref = None
        self._wnd_proc_ref = None
        self._cursors_hidden = False
        
        # Estado de simulação (para testes com 1 mouse físico)
        self.simulation_mode = config.get("system", {}).get("simulation_mode", False)
        self._sim_dir = 1.0
        
        # Callbacks para interface gráfica
        self.on_positions_updated: Optional[Callable[[float, float, float, float], None]] = None
        self.on_device_activity: Optional[Callable[[str], None]] = None
        
        # Inicializa coordenadas e limites
        self._refresh_geometry()

    def _refresh_geometry(self):
        """Recalcula dimensões dos monitores atribuídos a cada mouse."""
        self.virtual_rect = get_virtual_desktop_rect()
        m1_monitors = self.config.get("mouse1", {}).get("monitors", [1])
        m2_monitors = self.config.get("mouse2", {}).get("monitors", [2])
        
        self.bounds1 = get_monitor_bounds_for_indices(m1_monitors)
        self.bounds2 = get_monitor_bounds_for_indices(m2_monitors)
        
        self.pos1[0], self.pos1[1] = clamp_to_bounds(self.pos1[0], self.pos1[1], self.bounds1)
        self.pos2[0], self.pos2[1] = clamp_to_bounds(self.pos2[0], self.pos2[1], self.bounds2)

    def hide_system_cursor(self):
        """Oculta todos os cursores padrão do Windows substituindo-os por cursor transparente."""
        if self._cursors_hidden:
            return
        try:
            and_mask = (ctypes.c_byte * 128)(*([0xFF] * 128))
            xor_mask = (ctypes.c_byte * 128)(*([0x00] * 128))
            for cid in SYSTEM_CURSOR_IDS:
                hBlank = user32.CreateIcon(None, 32, 32, 1, 1, and_mask, xor_mask)
                if hBlank:
                    user32.SetSystemCursor(hBlank, cid)
            self._cursors_hidden = True
        except Exception as e:
            print(f"Erro ao ocultar cursor do sistema: {e}")

    def restore_system_cursor(self):
        """Restaura todos os cursores padrão do Windows."""
        if not self._cursors_hidden:
            return
        try:
            user32.SystemParametersInfoW(0x0057, 0, None, 0) # SPI_SETCURSORS
            self._cursors_hidden = False
        except Exception as e:
            print(f"Erro ao restaurar cursores do sistema: {e}")

    def start(self):
        """Inicia a captura de Raw Input, o hook e o overlay transparente em uma thread dedicada."""
        if self._running:
            return
        self._running = True
        self._paused = False
        
        if self.config.get("system", {}).get("hide_os_cursor", True):
            self.hide_system_cursor()
            
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="DualPointerEngineThread")
        self._thread.start()

    def stop(self):
        """Para o motor de separação, restaura cursores padrão e fecha o overlay."""
        if not self._running:
            return
        self._running = False
        self.restore_system_cursor()
        
        if self.hwnd_overlay:
            user32.PostMessageW(self.hwnd_overlay, 0x0010, 0, 0) # WM_CLOSE
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def toggle_pause(self) -> bool:
        """Pausa ou retoma a separação dos mouses."""
        self._paused = not self._paused
        if self._paused:
            self.restore_system_cursor()
        else:
            if self.config.get("system", {}).get("hide_os_cursor", True):
                self.hide_system_cursor()
                
        if self.hwnd_overlay:
            user32.InvalidateRect(self.hwnd_overlay, None, True)
        return not self._paused

    def is_active(self) -> bool:
        return self._running and not self._paused

    def update_config(self, new_config: Dict[str, Any]):
        """Atualiza dinamicamente as configurações de cursores, mouses e monitores."""
        self.config = new_config
        self.simulation_mode = new_config.get("system", {}).get("simulation_mode", False)
        self._refresh_geometry()
        self.device_map.clear()
        
        should_hide = new_config.get("system", {}).get("hide_os_cursor", True)
        if not self._paused:
            if should_hide:
                self.hide_system_cursor()
            else:
                self.restore_system_cursor()
                
        if self.hwnd_overlay:
            user32.InvalidateRect(self.hwnd_overlay, None, True)

    def _resolve_device_target(self, hDevice: int) -> str:
        """Determina se um handle de Raw Input pertence ao Mouse 1 ou Mouse 2."""
        if hDevice in self.device_map:
            return self.device_map[hDevice]

        sz = wintypes.UINT(0)
        user32.GetRawInputDeviceInfoW(hDevice, 0x20000007, None, ctypes.byref(sz))
        dev_path = ""
        if sz.value > 0:
            buf = ctypes.create_unicode_buffer(sz.value + 1)
            if user32.GetRawInputDeviceInfoW(hDevice, 0x20000007, buf, ctypes.byref(sz)) > 0:
                dev_path = buf.value

        m1_hwid = self.config.get("mouse1", {}).get("hwid", "")
        m1_inst = self.config.get("mouse1", {}).get("instance_id", "")
        m2_hwid = self.config.get("mouse2", {}).get("hwid", "")
        m2_inst = self.config.get("mouse2", {}).get("instance_id", "")

        mock_dev = {'hwid': dev_path, 'device_path': dev_path, 'instance_id': dev_path}

        target = "m1"
        if m2_hwid and matches_device(mock_dev, m2_hwid, m2_inst):
            target = "m2"
        elif m1_hwid and matches_device(mock_dev, m1_hwid, m1_inst):
            target = "m1"
        else:
            if 'm1' not in self.active_handles:
                self.active_handles['m1'] = hDevice
                target = 'm1'
            elif 'm2' not in self.active_handles and self.active_handles['m1'] != hDevice:
                self.active_handles['m2'] = hDevice
                target = 'm2'
            elif self.active_handles.get('m2') == hDevice:
                target = 'm2'
            else:
                target = 'm1'

        self.device_map[hDevice] = target
        return target

    def _inject_click(self, x: int, y: int, btn_flags: int, raw_button_data: int):
        """
        Posiciona o cursor e despacha o clique cirurgicamente nas coordenadas do mouse correto.
        Garante que janelas clicadas pelo mouse fiquem em primeiro plano.
        """
        # Posiciona o cursor do sistema no alvo
        user32.SetCursorPos(x, y)
        
        # Identifica a janela sob o ponto de clique e a ativa em primeiro plano
        # (Somente se for clique de botão, rolagem não rouba foco)
        if btn_flags & (0x0001 | 0x0004 | 0x0010): # DOWN buttons
            pt = POINT(x, y)
            target_wnd = user32.WindowFromPoint(pt)
            if target_wnd and target_wnd != self.hwnd_overlay:
                root_wnd = user32.GetAncestor(target_wnd, 2) # GA_ROOT
                wnd_to_activate = root_wnd if root_wnd else target_wnd
                user32.SetForegroundWindow(wnd_to_activate)
        
        events = []
        if btn_flags & 0x0001: events.append((0x0002, 0)) # LEFTDOWN
        if btn_flags & 0x0002: events.append((0x0004, 0)) # LEFTUP
        if btn_flags & 0x0004: events.append((0x0008, 0)) # RIGHTDOWN
        if btn_flags & 0x0008: events.append((0x0010, 0)) # RIGHTUP
        if btn_flags & 0x0010: events.append((0x0020, 0)) # MIDDLEDOWN
        if btn_flags & 0x0020: events.append((0x0040, 0)) # MIDDLEUP
        if btn_flags & 0x0400: # MOUSEWHEEL
            wheel_delta = ctypes.c_short(raw_button_data).value
            events.append((0x0800, wheel_delta))

        for flag, data in events:
            inp = INPUT()
            inp.type = 0 # INPUT_MOUSE
            inp.u.mi.dx = 0
            inp.u.mi.dy = 0
            inp.u.mi.mouseData = data
            inp.u.mi.dwFlags = flag
            inp.u.mi.time = 0
            inp.u.mi.dwExtraInfo = EXTRA_INFO_MAGIC
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def _draw_cursor_gdi(self, hdc: int, cx: int, cy: int, cursor_cfg: Dict[str, Any], default_label: str = "1"):
        """
        Desenho GDI moderno, elegante e de alta precisão com sombra suave (Drop Shadow),
        borda nítida, corpo de cor vibrante e Pill Badge estilizado.
        """
        shape = cursor_cfg.get("shape", "sleek").lower()
        color_hex = cursor_cfg.get("color", "#38BDF8")
        border_hex = cursor_cfg.get("border_color", "#FFFFFF")
        size = int(cursor_cfg.get("size", 28))
        glow = cursor_cfg.get("glow", True)
        show_label = cursor_cfg.get("show_label", True)
        label_text = cursor_cfg.get("label_text", default_label) or default_label
        
        r, g, b = hex_to_rgb(color_hex)
        br_color = (b << 16) | (g << 8) | r
        
        rb, gb, bb = hex_to_rgb(border_hex)
        border_color = (bb << 16) | (gb << 8) | rb
        
        null_brush = gdi32.GetStockObject(5) # NULL_BRUSH
        shadow_brush = gdi32.CreateSolidBrush(0x000F0A05) # Sombra carvão profundo
        shadow_pen = gdi32.CreatePen(0, 1, 0x000F0A05)

        # 1. Aura Glow Elegante e Sutil
        if glow:
            pen_glow = gdi32.CreatePen(0, 1, br_color)
            old_pen = gdi32.SelectObject(hdc, pen_glow)
            old_brush = gdi32.SelectObject(hdc, null_brush)
            
            gr = int(size * 0.72)
            gdi32.Ellipse(hdc, cx - gr, cy - gr, cx + gr, cy + gr)
            
            gdi32.SelectObject(hdc, old_pen)
            gdi32.SelectObject(hdc, old_brush)
            gdi32.DeleteObject(pen_glow)

        # 2. Desenho das Formas Modernas
        if shape in ["sleek", "arrow", "fluent", "cyber", "stylus"]:
            poly = get_cursor_polygon(shape, size)
            num_pts = len(poly)
            
            # A) Sombra suave (Drop Shadow)
            s_offset = 2
            shadow_pts = (POINT * num_pts)()
            for i, (px, py) in enumerate(poly):
                shadow_pts[i].x = int(cx + px + s_offset)
                shadow_pts[i].y = int(cy + py + s_offset)
                
            old_p = gdi32.SelectObject(hdc, shadow_pen)
            old_b = gdi32.SelectObject(hdc, shadow_brush)
            gdi32.Polygon(hdc, shadow_pts, num_pts)
            
            # B) Corpo principal com borda
            pts = (POINT * num_pts)()
            for i, (px, py) in enumerate(poly):
                pts[i].x = int(cx + px)
                pts[i].y = int(cy + py)

            pen = gdi32.CreatePen(0, 2, border_color)
            brush = gdi32.CreateSolidBrush(br_color)
            
            gdi32.SelectObject(hdc, pen)
            gdi32.SelectObject(hdc, brush)
            gdi32.Polygon(hdc, pts, num_pts)
            
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)
            gdi32.DeleteObject(pen)
            gdi32.DeleteObject(brush)

        elif shape in ["precision", "crosshair"]:
            # Mira Minimalista de Alta Precisão
            r_c = int(size * 0.38)
            gap = int(size * 0.12)
            ext = int(size * 0.55)
            
            pen_body = gdi32.CreatePen(0, 2, br_color)
            pen_border = gdi32.CreatePen(0, 1, border_color)
            old_p = gdi32.SelectObject(hdc, pen_body)
            old_b = gdi32.SelectObject(hdc, null_brush)
            
            gdi32.Ellipse(hdc, cx - r_c, cy - r_c, cx + r_c, cy + r_c)
            
            gdi32.MoveToEx(hdc, cx - ext, cy, None)
            gdi32.LineTo(hdc, cx - gap, cy)
            gdi32.MoveToEx(hdc, cx + gap, cy, None)
            gdi32.LineTo(hdc, cx + ext, cy)
            gdi32.MoveToEx(hdc, cx, cy - ext, None)
            gdi32.LineTo(hdc, cx, cy - gap)
            gdi32.MoveToEx(hdc, cx, cy + gap, None)
            gdi32.LineTo(hdc, cx, cy + ext)
            
            # Ponto central
            white_b = gdi32.CreateSolidBrush(0x00FFFFFF)
            gdi32.SelectObject(hdc, white_b)
            gdi32.Ellipse(hdc, cx - 2, cy - 2, cx + 2, cy + 2)
            
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)
            gdi32.DeleteObject(pen_body)
            gdi32.DeleteObject(pen_border)
            gdi32.DeleteObject(white_b)

        elif shape in ["capsule", "dot"]:
            # Ponto Halo Minimalista
            cr = int(size * 0.32)
            pen_b = gdi32.CreatePen(0, 2, border_color)
            brush_b = gdi32.CreateSolidBrush(br_color)
            
            old_p = gdi32.SelectObject(hdc, pen_b)
            old_b = gdi32.SelectObject(hdc, brush_b)
            gdi32.Ellipse(hdc, cx - cr, cy - cr, cx + cr, cy + cr)
            
            core_b = gdi32.CreateSolidBrush(0x00FFFFFF)
            gdi32.SelectObject(hdc, core_b)
            gdi32.Ellipse(hdc, cx - 2, cy - 2, cx + 2, cy + 2)
            
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)
            gdi32.DeleteObject(pen_b)
            gdi32.DeleteObject(brush_b)
            gdi32.DeleteObject(core_b)

        # 3. Pill Badge Estilizado (M1 / M2 ou 1 / 2)
        if show_label and label_text:
            bx = cx + int(size * 0.72)
            by = cy + int(size * 0.62)
            pw = max(9, len(label_text) * 4 + 3)
            ph = 7
            
            # Sombra da pílula
            gdi32.SelectObject(hdc, shadow_pen)
            gdi32.SelectObject(hdc, shadow_brush)
            gdi32.RoundRect(hdc, bx - pw + 1, by - ph + 1, bx + pw + 1, by + ph + 1, 6, 6)
            
            # Fundo da pílula (Dark Slate) e borda na cor do mouse
            pill_brush = gdi32.CreateSolidBrush(0x001E170F)
            pill_pen = gdi32.CreatePen(0, 1, br_color)
            gdi32.SelectObject(hdc, pill_pen)
            gdi32.SelectObject(hdc, pill_brush)
            gdi32.RoundRect(hdc, bx - pw, by - ph, bx + pw, by + ph, 6, 6)
            
            # Texto da pílula em branco puro
            gdi32.SetTextColor(hdc, 0x00FFFFFF)
            gdi32.SetBkMode(hdc, 1) # TRANSPARENT
            stock_font = gdi32.GetStockObject(17) # DEFAULT_GUI_FONT
            old_font = gdi32.SelectObject(hdc, stock_font)
            
            # Centraliza o texto
            t_offset_x = 3 if len(label_text) == 1 else 6
            gdi32.TextOutW(hdc, bx - t_offset_x, by - 6, label_text, len(label_text))
            
            gdi32.SelectObject(hdc, old_font)
            gdi32.DeleteObject(pill_brush)
            gdi32.DeleteObject(pill_pen)

        gdi32.DeleteObject(shadow_brush)
        gdi32.DeleteObject(shadow_pen)

    def _run_loop(self):
        """Loop de mensagens Win32 em segundo plano para Raw Input, Hook e Overlay."""
        hInst = kernel32.GetModuleHandleW(None)
        
        v_left, v_top, v_right, v_bottom = self.virtual_rect
        v_width = v_right - v_left
        v_height = v_bottom - v_top

        def _wnd_proc(hwnd, msg, wp, lp):
            if msg == WM_PAINT:
                ps = PAINTSTRUCT()
                hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
                
                # MemDC para double buffering e transparência perfeita
                mem_dc = gdi32.CreateCompatibleDC(hdc)
                mem_bmp = gdi32.CreateCompatibleBitmap(hdc, v_width, v_height)
                old_bmp = gdi32.SelectObject(mem_dc, mem_bmp)
                
                # Preenche com a chave de cor de transparência (Magenta)
                bg_brush = gdi32.CreateSolidBrush(TRANSPARENT_COLOR)
                rc = RECT(0, 0, v_width, v_height)
                user32.FillRect(mem_dc, ctypes.byref(rc), bg_brush)
                gdi32.DeleteObject(bg_brush)
                
                # Desenha os dois cursores somente se o motor estiver ativo
                if not self._paused:
                    cx1 = int(self.pos1[0] - v_left)
                    cy1 = int(self.pos1[1] - v_top)
                    cx2 = int(self.pos2[0] - v_left)
                    cy2 = int(self.pos2[1] - v_top)
                    
                    self._draw_cursor_gdi(mem_dc, cx1, cy1, self.config.get("mouse1", {}).get("cursor", {}), "1")
                    self._draw_cursor_gdi(mem_dc, cx2, cy2, self.config.get("mouse2", {}).get("cursor", {}), "2")
                
                gdi32.BitBlt(hdc, 0, 0, v_width, v_height, mem_dc, 0, 0, 0x00CC0020) # SRCCOPY
                
                gdi32.SelectObject(mem_dc, old_bmp)
                gdi32.DeleteObject(mem_bmp)
                gdi32.DeleteDC(mem_dc)
                user32.EndPaint(hwnd, ctypes.byref(ps))
                return 0
                
            elif msg == WM_INPUT:
                dwSize = wintypes.UINT(0)
                user32.GetRawInputData(wintypes.HANDLE(lp), RID_INPUT, None, ctypes.byref(dwSize), ctypes.sizeof(RAWINPUTHEADER))
                if dwSize.value > 0:
                    buf = ctypes.create_string_buffer(dwSize.value)
                    if user32.GetRawInputData(wintypes.HANDLE(lp), RID_INPUT, buf, ctypes.byref(dwSize), ctypes.sizeof(RAWINPUTHEADER)) == dwSize.value:
                        raw = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
                        if raw.header.dwType == RIM_TYPEMOUSE:
                            hDev = raw.header.hDevice
                            
                            # DESCARTA imediatamente qualquer entrada injetada pelo SendInput
                            # (hDev nulo ou dwExtraInfo igual ao nosso marcador mágico)
                            # Isso elimina 100% qualquer risco de disparo contínuo ou eco.
                            if not hDev or raw.mouse.ulExtraInformation == EXTRA_INFO_MAGIC:
                                return user32.DefWindowProcW(hwnd, msg, wp, lp)

                            dx = raw.mouse.lLastX
                            dy = raw.mouse.lLastY
                            btn_flags = raw.mouse.union.buttons.usButtonFlags
                            btn_data = raw.mouse.union.buttons.usButtonData
                            
                            target = self._resolve_device_target(hDev)
                            if self.on_device_activity:
                                self.on_device_activity(target)
                                
                            if not self._paused:
                                # Rastreamento de estado de botões pressionados (Hold & Drag)
                                if btn_flags & 0x0001:  # LEFT_DOWN
                                    if target == 'm1': self.m1_down = True
                                    else: self.m2_down = True
                                if btn_flags & 0x0002:  # LEFT_UP
                                    if target == 'm1': self.m1_down = False
                                    else: self.m2_down = False
                                if btn_flags & 0x0004:  # RIGHT_DOWN
                                    if target == 'm1': self.m1_rdown = True
                                    else: self.m2_rdown = True
                                if btn_flags & 0x0008:  # RIGHT_UP
                                    if target == 'm1': self.m1_rdown = False
                                    else: self.m2_rdown = False

                                # 1. MOUSE 1 (MONITOR X)
                                if target == 'm1':
                                    sens1 = float(self.config.get("mouse1", {}).get("sensitivity", 1.0))
                                    if dx or dy:
                                        self.pos1[0] += dx * sens1
                                        self.pos1[1] += dy * sens1
                                        self.pos1[0], self.pos1[1] = clamp_to_bounds(self.pos1[0], self.pos1[1], self.bounds1)
                                    
                                    # Se Mouse 2 não estiver segurando arraste no Monitor Y:
                                    if not self.m2_down and not self.m2_rdown:
                                        user32.SetCursorPos(int(self.pos1[0]), int(self.pos1[1]))
                                        self.active_mouse = 'm1'
                                        
                                    # Injeta clique/rolagem cirurgicamente no Monitor X
                                    # (Se Mouse 2 estiver arrastando, não interrompe o drag do 2)
                                    if btn_flags:
                                        if not self.m2_down and not self.m2_rdown:
                                            self._inject_click(int(self.pos1[0]), int(self.pos1[1]), btn_flags, btn_data)

                                # 2. MOUSE 2 (MONITOR Y)
                                else:
                                    sens2 = float(self.config.get("mouse2", {}).get("sensitivity", 1.0))
                                    if dx or dy:
                                        self.pos2[0] += dx * sens2
                                        self.pos2[1] += dy * sens2
                                        self.pos2[0], self.pos2[1] = clamp_to_bounds(self.pos2[0], self.pos2[1], self.bounds2)
                                    
                                    # Se Mouse 1 não estiver segurando arraste no Monitor X:
                                    if not self.m1_down and not self.m1_rdown:
                                        user32.SetCursorPos(int(self.pos2[0]), int(self.pos2[1]))
                                        self.active_mouse = 'm2'
                                        
                                    # Injeta clique/rolagem cirurgicamente no Monitor Y
                                    # (Se Mouse 1 estiver arrastando, não interrompe o drag do 1)
                                    if btn_flags:
                                        if not self.m1_down and not self.m1_rdown:
                                            self._inject_click(int(self.pos2[0]), int(self.pos2[1]), btn_flags, btn_data)
                                
                                # Modo de simulação para testes com 1 mouse
                                if self.simulation_mode and target == 'm1':
                                    self.pos2[0] += dx * 0.8 * self._sim_dir
                                    self.pos2[1] += dy * 0.8
                                    self.pos2[0], self.pos2[1] = clamp_to_bounds(self.pos2[0], self.pos2[1], self.bounds2)
                                    
                                if self.hwnd_overlay:
                                    user32.InvalidateRect(self.hwnd_overlay, None, False)
                                    
                                if self.on_positions_updated:
                                    self.on_positions_updated(self.pos1[0], self.pos1[1], self.pos2[0], self.pos2[1])
                                    
                return user32.DefWindowProcW(hwnd, msg, wp, lp)
                
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
                
            return user32.DefWindowProcW(hwnd, msg, wp, lp)

        self._wnd_proc_ref = WNDPROC(_wnd_proc)
        
        cls_name = "DualPointerOverlayClass"
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wnd_proc_ref
        wc.hInstance = hInst
        wc.lpszClassName = cls_name
        user32.RegisterClassExW(ctypes.byref(wc))

        # Criação da janela overlay transparente cobrindo todos os monitores
        ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        self.hwnd_overlay = user32.CreateWindowExW(
            ex_style, cls_name, "DualPointer Overlay",
            WS_POPUP | WS_VISIBLE,
            v_left, v_top, v_width, v_height,
            None, None, hInst, None
        )
        
        user32.SetLayeredWindowAttributes(self.hwnd_overlay, TRANSPARENT_COLOR, 0, LWA_COLORKEY)
        
        # Registra o recebimento de Raw Input para mouses
        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01  # Generic Desktop
        rid.usUsage = 0x02      # Mouse
        rid.dwFlags = RIDEV_INPUTSINK
        rid.hwndTarget = self.hwnd_overlay
        user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE))

        # Hook de Baixo Nível (WH_MOUSE_LL)
        # Cancela cliques físicos brutos que seriam entregues na coordenada desatualizada/errada
        # Permite que apenas cliques cirurgicamente injetados pelo DualPointer passem para a janela certa
        def _hook_callback(nCode, wParam, lParam):
            if nCode >= 0 and not self._paused:
                hook_data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                is_injected = bool(hook_data.flags & LLMHF_INJECTED)
                
                # Se foi injetado pelo DualPointer, deixa passar para a aplicação destino!
                if is_injected or hook_data.dwExtraInfo == EXTRA_INFO_MAGIC:
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)
                
                # Se for clique físico direto do hardware, cancela na coordenada antiga
                # para que o motor possa reposicionar o cursor e disparar exatamente onde o mouse está!
                if wParam in (0x0201, 0x0202, 0x0204, 0x0205, 0x0207, 0x0208, 0x020A):
                    return 1  # Bloqueia o clique descalibrado do Windows
                    
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._hook_cb_ref = HOOKPROC(_hook_callback)
        self.hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._hook_cb_ref, None, 0)

        # Loop de mensagens padrão do Windows
        msg = wintypes.MSG()
        while self._running:
            bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if bRet == 0 or bRet == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Limpeza de recursos ao encerrar
        if self.hook:
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None

        if self.hwnd_overlay:
            user32.DestroyWindow(self.hwnd_overlay)
            self.hwnd_overlay = None
            
        user32.UnregisterClassW(cls_name, hInst)
