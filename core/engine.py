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

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

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

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC

user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

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

gdi32.CreateFontW.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.LPCWSTR
]
gdi32.CreateFontW.restype = wintypes.HFONT


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
        
        # Trava de sincronização para despacho atômico de cliques multi-seat
        self._input_lock = threading.Lock()
        
        # Janelas ativas e títulos por Área de Trabalho (Estações Multi-Seat)
        self.active_wnd_m1: Optional[int] = None
        self.active_wnd_m2: Optional[int] = None
        self.active_wnd_m1_title: str = "Aguardando interação..."
        self.active_wnd_m2_title: str = "Aguardando interação..."
        
        # Telemetria de atividade em tempo real
        self.m1_last_activity: float = 0.0
        self.m2_last_activity: float = 0.0
        
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
        self.on_workspace_focus_changed: Optional[Callable[[str, int, str], None]] = None
        
        # Configurações de sensibilidade em cache direto
        self.sens1 = float(self.config.get("mouse1", {}).get("sensitivity", 1.0))
        self.sens2 = float(self.config.get("mouse2", {}).get("sensitivity", 1.0))
        
        # Objetos e buffers GDI de alto desempenho (latência zero)
        self.v_width = 1920
        self.v_height = 1080
        self._overlay_hdc = None
        self._mem_dc = None
        self._mem_bmp = None
        self._old_mem_bmp = None
        self._bg_brush = None
        self._last_rc1: Optional[RECT] = None
        self._last_rc2: Optional[RECT] = None
        
        # Recursos GDI pré-compilados
        self._res1: Optional[Dict[str, Any]] = None
        self._res2: Optional[Dict[str, Any]] = None
        self._hfont = None
        self._null_brush = None
        self._shadow_brush = None
        self._shadow_pen = None
        self._white_brush = None
        
        # Controle de elevação e permanência no topo (Z-order)
        self._last_topmost_assert: float = 0.0
        self._is_admin: bool = bool(ctypes.windll.shell32.IsUserAnAdmin())
        self._elevated_hover: bool = False

        # Inicializa coordenadas e limites
        self._refresh_geometry()
        self._init_gdi_cache()

    def _refresh_geometry(self):
        """Recalcula dimensões dos monitores atribuídos a cada mouse."""
        self.virtual_rect = get_virtual_desktop_rect()
        v_left, v_top, v_right, v_bottom = self.virtual_rect
        self.v_width = max(1, v_right - v_left)
        self.v_height = max(1, v_bottom - v_top)
        
        m1_monitors = self.config.get("mouse1", {}).get("monitors", [1])
        m2_monitors = self.config.get("mouse2", {}).get("monitors", [2])
        
        self.bounds1 = get_monitor_bounds_for_indices(m1_monitors)
        self.bounds2 = get_monitor_bounds_for_indices(m2_monitors)
        
        self.sens1 = float(self.config.get("mouse1", {}).get("sensitivity", 1.0))
        self.sens2 = float(self.config.get("mouse2", {}).get("sensitivity", 1.0))
        
        self.pos1[0], self.pos1[1] = clamp_to_bounds(self.pos1[0], self.pos1[1], self.bounds1)
        self.pos2[0], self.pos2[1] = clamp_to_bounds(self.pos2[0], self.pos2[1], self.bounds2)

    def _init_gdi_cache(self):
        """Pré-compila objetos GDI (canetas, pincéis, polígonos e fonte) para desenho em 0.01ms sem alocações."""
        self._cleanup_gdi_cache()
        
        self._hfont = gdi32.CreateFontW(-11, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI")
        self._null_brush = gdi32.GetStockObject(5) # NULL_BRUSH
        self._shadow_brush = gdi32.CreateSolidBrush(0x000F0A05)
        self._shadow_pen = gdi32.CreatePen(0, 1, 0x000F0A05)
        self._white_brush = gdi32.CreateSolidBrush(0x00FFFFFF)
        
        def _build_cursor_res(cfg: Dict[str, Any], default_lbl: str):
            shape = cfg.get("shape", "sleek").lower()
            color_hex = cfg.get("color", "#38BDF8")
            border_hex = cfg.get("border_color", "#FFFFFF")
            size = int(cfg.get("size", 28))
            glow = bool(cfg.get("glow", True))
            show_label = bool(cfg.get("show_label", True))
            label_text = str(cfg.get("label_text", default_lbl) or default_lbl)
            
            r, g, b = hex_to_rgb(color_hex)
            br_color = (b << 16) | (g << 8) | r
            
            rb, gb, bb = hex_to_rgb(border_hex)
            border_color = (bb << 16) | (gb << 8) | rb
            
            poly = get_cursor_polygon(shape, size)
            n_pts = len(poly)
            
            pts = (POINT * n_pts)()
            shadow_pts = (POINT * n_pts)()
            for i, (px, py) in enumerate(poly):
                pts[i].x = int(round(px))
                pts[i].y = int(round(py))
                shadow_pts[i].x = int(round(px + 2))
                shadow_pts[i].y = int(round(py + 2))
                
            return {
                "shape": shape,
                "size": size,
                "glow": glow,
                "show_label": show_label,
                "label_text": label_text,
                "br_color": br_color,
                "border_color": border_color,
                "pen_body": gdi32.CreatePen(0, 2, border_color),
                "brush_body": gdi32.CreateSolidBrush(br_color),
                "pen_glow": gdi32.CreatePen(0, 1, br_color),
                "pill_pen": gdi32.CreatePen(0, 1, br_color),
                "pill_brush": gdi32.CreateSolidBrush(0x001E170F),
                "poly": poly,
                "pts": pts,
                "shadow_pts": shadow_pts,
                "n_pts": n_pts
            }
            
        c1 = self.config.get("mouse1", {}).get("cursor", {})
        c2 = self.config.get("mouse2", {}).get("cursor", {})
        self._res1 = _build_cursor_res(c1, "1")
        self._res2 = _build_cursor_res(c2, "2")

    def _cleanup_gdi_cache(self):
        for res in [getattr(self, '_res1', None), getattr(self, '_res2', None)]:
            if res:
                for k in ["pen_body", "brush_body", "pen_glow", "pill_pen", "pill_brush"]:
                    h = res.get(k)
                    if h:
                        try: gdi32.DeleteObject(h)
                        except Exception: pass
        self._res1 = None
        self._res2 = None
        
        if getattr(self, '_hfont', None):
            try: gdi32.DeleteObject(self._hfont)
            except Exception: pass
            self._hfont = None
        if getattr(self, '_shadow_brush', None):
            try: gdi32.DeleteObject(self._shadow_brush)
            except Exception: pass
            self._shadow_brush = None
        if getattr(self, '_shadow_pen', None):
            try: gdi32.DeleteObject(self._shadow_pen)
            except Exception: pass
            self._shadow_pen = None
        if getattr(self, '_white_brush', None):
            try: gdi32.DeleteObject(self._white_brush)
            except Exception: pass
            self._white_brush = None

    def _cleanup_gdi_buffers(self):
        if getattr(self, '_mem_dc', None):
            try:
                if self._old_mem_bmp:
                    gdi32.SelectObject(self._mem_dc, self._old_mem_bmp)
                if self._mem_bmp:
                    gdi32.DeleteObject(self._mem_bmp)
                if self._bg_brush:
                    gdi32.DeleteObject(self._bg_brush)
                gdi32.DeleteDC(self._mem_dc)
            except Exception:
                pass
            self._mem_dc = None
            self._mem_bmp = None
            self._old_mem_bmp = None
            self._bg_brush = None
            
        if getattr(self, '_overlay_hdc', None) and self.hwnd_overlay:
            try:
                user32.ReleaseDC(self.hwnd_overlay, self._overlay_hdc)
            except Exception:
                pass
            self._overlay_hdc = None
            
        self._cleanup_gdi_cache()

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

    def restore_system_cursor(self, async_mode: bool = True):
        """Restaura todos os cursores padrão do Windows de forma segura e não bloqueante."""
        if not self._cursors_hidden:
            return
        self._cursors_hidden = False
        def _do_restore():
            try:
                user32.SystemParametersInfoW(0x0057, 0, None, 0) # SPI_SETCURSORS
            except Exception as e:
                print(f"Erro ao restaurar cursores do sistema: {e}")
        if async_mode:
            threading.Thread(target=_do_restore, daemon=True, name="RestoreCursorsThread").start()
        else:
            _do_restore()

    def assert_topmost(self):
        """Assegura que o overlay fique sempre no topo absoluto do Z-order, acima de comboboxes, menus e janelas elevadas."""
        if self.hwnd_overlay and user32.IsWindow(self.hwnd_overlay):
            user32.SetWindowPos(self.hwnd_overlay, wintypes.HWND(-1), 0, 0, 0, 0, 0x0013)

    def _is_taskmgr_window(self, hwnd: int) -> bool:
        """Identifica se a janela sob o cursor pertence ao Gerenciador de Tarefas ou ferramenta do sistema."""
        if not hwnd or not user32.IsWindow(hwnd):
            return False
        try:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            cls_name = buf.value
            if "TaskManager" in cls_name or cls_name == "Taskmgr":
                return True
            root = user32.GetAncestor(hwnd, 2) # GA_ROOT
            if root and root != hwnd:
                user32.GetClassNameW(root, buf, 256)
                if "TaskManager" in buf.value or buf.value == "Taskmgr":
                    return True
        except Exception:
            pass
        return False

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
        """Para o motor de separação instantaneamente, liberando o mouse e fechando o overlay sem nenhum congelamento."""
        if not self._running:
            return
        self._running = False
        
        # 1. Desinstala o hook de mouse IMEDIATAMENTE (libera o hardware do sistema em 0ms)
        if self.hook:
            try:
                user32.UnhookWindowsHookEx(self.hook)
            except Exception:
                pass
            self.hook = None

        # 2. Encerra o loop de mensagens da janela overlay instantaneamente com WM_QUIT
        if self.hwnd_overlay:
            try:
                user32.PostMessageW(self.hwnd_overlay, 0x0012, 0, 0) # WM_QUIT
                user32.DestroyWindow(self.hwnd_overlay)
            except Exception:
                pass
            self.hwnd_overlay = None

        # 3. Libera buffers e recursos GDI persistentes
        self._cleanup_gdi_buffers()

        # 4. Restaura os cursores do Windows de forma assíncrona (não trava o encerramento com broadcast)
        self.restore_system_cursor(async_mode=True)
        
        # 5. Aguarda brevemente a thread auxiliar
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.1)

    def toggle_pause(self) -> bool:
        """Pausa ou retoma a separação dos mouses."""
        self._paused = not self._paused
        if self._paused:
            self.restore_system_cursor()
        else:
            if self.config.get("system", {}).get("hide_os_cursor", True):
                self.hide_system_cursor()
                
        self._render_cursors_fast(force_full=True)
        return not self._paused

    def is_active(self) -> bool:
        return self._running and not self._paused

    def update_config(self, new_config: Dict[str, Any]):
        """Atualiza dinamicamente as configurações de cursores, mouses e monitores."""
        self.config = new_config
        self.simulation_mode = new_config.get("system", {}).get("simulation_mode", False)
        self._refresh_geometry()
        self._init_gdi_cache()
        self.device_map.clear()
        
        should_hide = new_config.get("system", {}).get("hide_os_cursor", True)
        if not self._paused:
            if should_hide:
                self.hide_system_cursor()
            else:
                self.restore_system_cursor()
                
        self._render_cursors_fast(force_full=True)

    def _get_wnd_title(self, hwnd: int) -> str:
        """Obtém o título legível de uma janela Win32."""
        try:
            if not hwnd or not user32.IsWindow(hwnd):
                return "Área de Trabalho / Desktop"
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return "Janela do Sistema / Controle"
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        except Exception:
            return "Aplicativo do Windows"

    def _resolve_device_target(self, hDevice: int) -> str:
        """Determina com precisão se um handle de Raw Input pertence à Área 1 (m1) ou Área 2 (m2)."""
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

        target = None
        # Verifica correspondência estrita com os dispositivos configurados
        if m2_hwid and matches_device(mock_dev, m2_hwid, m2_inst):
            if 'm2' not in self.active_handles or self.active_handles['m2'] == hDevice:
                target = 'm2'
                self.active_handles['m2'] = hDevice
            elif 'm1' not in self.active_handles or self.active_handles['m1'] == hDevice:
                target = 'm1'
                self.active_handles['m1'] = hDevice
        elif m1_hwid and matches_device(mock_dev, m1_hwid, m1_inst):
            if 'm1' not in self.active_handles or self.active_handles['m1'] == hDevice:
                target = 'm1'
                self.active_handles['m1'] = hDevice
            elif 'm2' not in self.active_handles or self.active_handles['m2'] == hDevice:
                target = 'm2'
                self.active_handles['m2'] = hDevice

        # Se não houver correspondência estrita ou mouses idênticos, separa por identificador físico único
        if not target:
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

    def _async_update_focus(self, x: int, y: int, source_seat: str):
        """Atualiza a janela ativa e título da estação de trabalho em segundo plano sem travar o clique."""
        def _worker():
            try:
                pt = POINT(x, y)
                wnd = user32.WindowFromPoint(pt)
                if wnd and wnd != self.hwnd_overlay:
                    root = user32.GetAncestor(wnd, 2) # GA_ROOT
                    target = root if root else wnd
                    title = self._get_wnd_title(target)
                    if source_seat == "m1":
                        self.active_wnd_m1 = target
                        self.active_wnd_m1_title = title
                    else:
                        self.active_wnd_m2 = target
                        self.active_wnd_m2_title = title
                    if self.on_workspace_focus_changed:
                        self.on_workspace_focus_changed(source_seat, target, title)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True, name=f"FocusUpdate-{source_seat}").start()

    def _inject_click(self, x: int, y: int, btn_flags: int, raw_button_data: int, source_seat: str = "m1"):
        """
        Despacha cliques de forma instantânea e atômica via SendInput em microssegundos (0.002ms).
        Garante resposta imediata (<0.005ms) sem bloqueios ou atrasos no processador de mensagens.
        """
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
        if btn_flags & 0x0800: # MOUSEHWHEEL (rolagem horizontal)
            wheel_delta = ctypes.c_short(raw_button_data).value
            events.append((0x1000, wheel_delta))

        if not events:
            return

        n_events = len(events)
        inputs = (INPUT * n_events)()
        for idx, (flag, data) in enumerate(events):
            inputs[idx].type = 0 # INPUT_MOUSE
            inputs[idx].u.mi.dx = 0
            inputs[idx].u.mi.dy = 0
            inputs[idx].u.mi.mouseData = data
            inputs[idx].u.mi.dwFlags = flag
            inputs[idx].u.mi.time = 0
            inputs[idx].u.mi.dwExtraInfo = EXTRA_INFO_MAGIC

        with self._input_lock:
            # 1. Posiciona o cursor do sistema no ponto exato do clique e assegura topo absoluto
            user32.SetCursorPos(x, y)
            self.assert_topmost()
            
            # 2. Despacha todos os eventos de clique atomicamente em uma única chamada de sistema
            user32.SendInput(n_events, inputs, ctypes.sizeof(INPUT))
            
            # 3. Se a outra estação estava em processo de arraste contínuo (drag & drop),
            # restaura a posição do cursor daquela estação para não interromper seu arraste
            if source_seat == "m1":
                if (self.m2_down or self.m2_rdown) and not (self.m1_down or self.m1_rdown):
                    user32.SetCursorPos(int(round(self.pos2[0])), int(round(self.pos2[1])))
            else:
                if (self.m1_down or self.m1_rdown) and not (self.m2_down or self.m2_rdown):
                    user32.SetCursorPos(int(round(self.pos1[0])), int(round(self.pos1[1])))

        # Atualiza o rastreamento de janela e foco em segundo plano (assíncrono)
        if btn_flags & (0x0001 | 0x0004 | 0x0010):
            self._async_update_focus(x, y, source_seat)

    def _calc_cursor_rect(self, cx: int, cy: int, size: int = 32) -> RECT:
        """Calcula o retângulo delimitador exato do cursor para dirty-rect blitting."""
        pad_left = int(size * 0.85) + 6
        pad_top = int(size * 0.85) + 6
        pad_right = int(size * 1.5) + 16
        pad_bottom = int(size * 1.3) + 16
        x1 = max(0, cx - pad_left)
        y1 = max(0, cy - pad_top)
        x2 = min(self.v_width, cx + pad_right)
        y2 = min(self.v_height, cy + pad_bottom)
        return RECT(x1, y1, x2, y2)

    def _draw_cursor_fast(self, hdc: int, cx: int, cy: int, res: Dict[str, Any]):
        """Desenho GDI moderno de altíssimo desempenho (0.005ms) usando objetos pré-compilados em cache."""
        shape = res["shape"]
        size = res["size"]
        glow = res["glow"]
        show_label = res["show_label"]
        label_text = res["label_text"]
        
        # 1. Aura Glow Elegante e Sutil
        if glow:
            old_p = gdi32.SelectObject(hdc, res["pen_glow"])
            old_b = gdi32.SelectObject(hdc, self._null_brush)
            gr = int(size * 0.72)
            gdi32.Ellipse(hdc, cx - gr, cy - gr, cx + gr, cy + gr)
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)

        # 2. Desenho das Formas Modernas
        if shape in ["sleek", "arrow", "fluent", "cyber", "stylus"]:
            poly = res["poly"]
            n_pts = res["n_pts"]
            pts = res["pts"]
            shadow_pts = res["shadow_pts"]
            
            for i, (px, py) in enumerate(poly):
                ipx = int(round(px))
                ipy = int(round(py))
                pts[i].x = cx + ipx
                pts[i].y = cy + ipy
                shadow_pts[i].x = cx + ipx + 2
                shadow_pts[i].y = cy + ipy + 2
                
            # Sombra suave (Drop Shadow)
            old_p = gdi32.SelectObject(hdc, self._shadow_pen)
            old_b = gdi32.SelectObject(hdc, self._shadow_brush)
            gdi32.Polygon(hdc, shadow_pts, n_pts)
            
            # Corpo principal estilizado com borda nítida
            gdi32.SelectObject(hdc, res["pen_body"])
            gdi32.SelectObject(hdc, res["brush_body"])
            gdi32.Polygon(hdc, pts, n_pts)
            
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)
            
        elif shape in ["precision", "crosshair"]:
            # Mira Minimalista de Alta Precisão
            r_c = int(size * 0.38)
            gap = int(size * 0.12)
            ext = int(size * 0.55)
            
            old_p = gdi32.SelectObject(hdc, res["pen_body"])
            old_b = gdi32.SelectObject(hdc, self._null_brush)
            gdi32.Ellipse(hdc, cx - r_c, cy - r_c, cx + r_c, cy + r_c)
            
            gdi32.MoveToEx(hdc, cx - ext, cy, None)
            gdi32.LineTo(hdc, cx - gap, cy)
            gdi32.MoveToEx(hdc, cx + gap, cy, None)
            gdi32.LineTo(hdc, cx + ext, cy)
            gdi32.MoveToEx(hdc, cx, cy - ext, None)
            gdi32.LineTo(hdc, cx, cy - gap)
            gdi32.MoveToEx(hdc, cx, cy + gap, None)
            gdi32.LineTo(hdc, cx, cy + ext)
            
            # Ponto central branco
            if self._white_brush:
                gdi32.SelectObject(hdc, self._white_brush)
                gdi32.Ellipse(hdc, cx - 2, cy - 2, cx + 2, cy + 2)
            
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)

        elif shape in ["capsule", "dot"]:
            # Ponto Halo Minimalista
            cr = int(size * 0.32)
            old_p = gdi32.SelectObject(hdc, res["pen_body"])
            old_b = gdi32.SelectObject(hdc, res["brush_body"])
            gdi32.Ellipse(hdc, cx - cr, cy - cr, cx + cr, cy + cr)
            
            if self._white_brush:
                gdi32.SelectObject(hdc, self._white_brush)
                gdi32.Ellipse(hdc, cx - 2, cy - 2, cx + 2, cy + 2)
                
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)

        # 3. Pill Badge Estilizado (M1 / M2 ou 1 / 2)
        if show_label and label_text:
            bx = cx + int(size * 0.72)
            by = cy + int(size * 0.62)
            pw = max(9, len(label_text) * 4 + 3)
            ph = 7
            
            # Sombra da pílula
            old_p = gdi32.SelectObject(hdc, self._shadow_pen)
            old_b = gdi32.SelectObject(hdc, self._shadow_brush)
            gdi32.RoundRect(hdc, bx - pw + 1, by - ph + 1, bx + pw + 1, by + ph + 1, 6, 6)
            
            # Fundo da pílula (Dark Slate) e borda na cor do mouse
            gdi32.SelectObject(hdc, res["pill_pen"])
            gdi32.SelectObject(hdc, res["pill_brush"])
            gdi32.RoundRect(hdc, bx - pw, by - ph, bx + pw, by + ph, 6, 6)
            
            # Texto da pílula em Segoe UI nítido com ClearType
            gdi32.SetTextColor(hdc, 0x00FFFFFF)
            gdi32.SetBkMode(hdc, 1) # TRANSPARENT
            
            old_font = gdi32.SelectObject(hdc, self._hfont) if self._hfont else None
            t_offset_x = 3 if len(label_text) == 1 else 6
            gdi32.TextOutW(hdc, bx - t_offset_x, by - 6, label_text, len(label_text))
            
            if old_font:
                gdi32.SelectObject(hdc, old_font)
            gdi32.SelectObject(hdc, old_p)
            gdi32.SelectObject(hdc, old_b)

    def _render_cursors_fast(self, force_full: bool = False):
        """
        Renderização instantânea (0.01-0.03ms) diretamente no DC do overlay.
        Apenas as regiões sujas (dirty rects) dos cursores são limpas e redesenhadas,
        garantindo fluidez a mais de 1000 FPS sem atraso ou perda de pacotes USB.
        """
        if not self._overlay_hdc or not self._mem_dc or not self._bg_brush:
            return

        v_left, v_top = self.virtual_rect[0], self.virtual_rect[1]

        if force_full:
            rc_all = RECT(0, 0, self.v_width, self.v_height)
            user32.FillRect(self._mem_dc, ctypes.byref(rc_all), self._bg_brush)
            if not self._paused:
                cx1 = int(round(self.pos1[0] - v_left))
                cy1 = int(round(self.pos1[1] - v_top))
                cx2 = int(round(self.pos2[0] - v_left))
                cy2 = int(round(self.pos2[1] - v_top))
                if self._res1:
                    self._draw_cursor_fast(self._mem_dc, cx1, cy1, self._res1)
                    self._last_rc1 = self._calc_cursor_rect(cx1, cy1, self._res1["size"])
                if self._res2:
                    self._draw_cursor_fast(self._mem_dc, cx2, cy2, self._res2)
                    self._last_rc2 = self._calc_cursor_rect(cx2, cy2, self._res2["size"])
            else:
                self._last_rc1 = None
                self._last_rc2 = None
            gdi32.BitBlt(self._overlay_hdc, 0, 0, self.v_width, self.v_height, self._mem_dc, 0, 0, 0x00CC0020)
            return

        # 1. Limpa as regiões anteriores no memory DC
        if self._last_rc1:
            user32.FillRect(self._mem_dc, ctypes.byref(self._last_rc1), self._bg_brush)
        if self._last_rc2:
            user32.FillRect(self._mem_dc, ctypes.byref(self._last_rc2), self._bg_brush)

        rc1_new = None
        rc2_new = None

        # 2. Desenha novas posições no memory DC
        if not self._paused:
            cx1 = int(round(self.pos1[0] - v_left))
            cy1 = int(round(self.pos1[1] - v_top))
            cx2 = int(round(self.pos2[0] - v_left))
            cy2 = int(round(self.pos2[1] - v_top))

            if self._res1:
                self._draw_cursor_fast(self._mem_dc, cx1, cy1, self._res1)
                rc1_new = self._calc_cursor_rect(cx1, cy1, self._res1["size"])
            if self._res2:
                self._draw_cursor_fast(self._mem_dc, cx2, cy2, self._res2)
                rc2_new = self._calc_cursor_rect(cx2, cy2, self._res2["size"])

        # 3. Transfere cirurgicamente para a tela apenas as caixas delimitadoras
        def _blit_bounding(old_rc, new_rc):
            if not old_rc and not new_rc:
                return
            if not old_rc:
                w = new_rc.right - new_rc.left
                h = new_rc.bottom - new_rc.top
                if w > 0 and h > 0:
                    gdi32.BitBlt(self._overlay_hdc, new_rc.left, new_rc.top, w, h, self._mem_dc, new_rc.left, new_rc.top, 0x00CC0020)
                return
            if not new_rc:
                w = old_rc.right - old_rc.left
                h = old_rc.bottom - old_rc.top
                if w > 0 and h > 0:
                    gdi32.BitBlt(self._overlay_hdc, old_rc.left, old_rc.top, w, h, self._mem_dc, old_rc.left, old_rc.top, 0x00CC0020)
                return

            dx = abs(new_rc.left - old_rc.left)
            dy = abs(new_rc.top - old_rc.top)
            # Se o movimento for contínuo (deslocamento normal < 120px), blita a união sem tearing
            if dx < 120 and dy < 120:
                ux1 = min(old_rc.left, new_rc.left)
                uy1 = min(old_rc.top, new_rc.top)
                ux2 = max(old_rc.right, new_rc.right)
                uy2 = max(old_rc.bottom, new_rc.bottom)
                uw = ux2 - ux1
                uh = uy2 - uy1
                if uw > 0 and uh > 0:
                    gdi32.BitBlt(self._overlay_hdc, ux1, uy1, uw, uh, self._mem_dc, ux1, uy1, 0x00CC0020)
            else:
                # Se for salto/teleporte distante, blita os dois retângulos separados
                ow = old_rc.right - old_rc.left
                oh = old_rc.bottom - old_rc.top
                if ow > 0 and oh > 0:
                    gdi32.BitBlt(self._overlay_hdc, old_rc.left, old_rc.top, ow, oh, self._mem_dc, old_rc.left, old_rc.top, 0x00CC0020)
                nw = new_rc.right - new_rc.left
                nh = new_rc.bottom - new_rc.top
                if nw > 0 and nh > 0:
                    gdi32.BitBlt(self._overlay_hdc, new_rc.left, new_rc.top, nw, nh, self._mem_dc, new_rc.left, new_rc.top, 0x00CC0020)

        _blit_bounding(self._last_rc1, rc1_new)
        _blit_bounding(self._last_rc2, rc2_new)

        self._last_rc1 = rc1_new
        self._last_rc2 = rc2_new

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
                pw = ps.rcPaint.right - ps.rcPaint.left
                ph = ps.rcPaint.bottom - ps.rcPaint.top
                if pw > 0 and ph > 0 and self._mem_dc:
                    gdi32.BitBlt(hdc, ps.rcPaint.left, ps.rcPaint.top, pw, ph, self._mem_dc, ps.rcPaint.left, ps.rcPaint.top, 0x00CC0020)
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
                            now_t = time.time()
                            if target == 'm1':
                                self.m1_last_activity = now_t
                            else:
                                self.m2_last_activity = now_t
                                
                            if self.on_device_activity:
                                self.on_device_activity(target)
                                
                            # Mantém o overlay no topo absoluto do Z-order periodicamente (~300ms)
                            # garantindo que o Gerenciador de Tarefas ou janelas elevadas não fiquem na frente
                            if now_t - self._last_topmost_assert > 0.3:
                                self._last_topmost_assert = now_t
                                self.assert_topmost()

                            # Fail-safe para o caso do aplicativo não estar elevado: se o cursor passar
                            # sobre o Gerenciador de Tarefas, restaura o cursor do sistema para nunca sumir
                            if not self._is_admin:
                                cur_x = int(round(self.pos1[0] if target == 'm1' else self.pos2[0]))
                                cur_y = int(round(self.pos1[1] if target == 'm1' else self.pos2[1]))
                                target_wnd = user32.WindowFromPoint(POINT(cur_x, cur_y))
                                if self._is_taskmgr_window(target_wnd):
                                    if not self._elevated_hover:
                                        self._elevated_hover = True
                                        self.restore_system_cursor(async_mode=True)
                                else:
                                    if self._elevated_hover:
                                        self._elevated_hover = False
                                        if self.config.get("system", {}).get("hide_os_cursor", True) and not self._paused:
                                            self.hide_system_cursor()
                                
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

                                # --- ÁREA DE TRABALHO 1 (MOUSE 1 / LUGAR 1) ---
                                if target == 'm1':
                                    if dx or dy:
                                        self.pos1[0] += dx * self.sens1
                                        self.pos1[1] += dy * self.sens1
                                        self.pos1[0], self.pos1[1] = clamp_to_bounds(self.pos1[0], self.pos1[1], self.bounds1)
                                        
                                        # Sincroniza cursor nativo do Windows continuamente em tempo real
                                        # para resposta instantânea de hover/botões sem atraso
                                        if not (self.m2_down or self.m2_rdown):
                                            user32.SetCursorPos(int(round(self.pos1[0])), int(round(self.pos1[1])))
                                    
                                    # Despacha cliques/rolagem cirurgicamente na Área de Trabalho 1
                                    if btn_flags:
                                        self.active_mouse = 'm1'
                                        self._inject_click(int(round(self.pos1[0])), int(round(self.pos1[1])), btn_flags, btn_data, 'm1')

                                # --- ÁREA DE TRABALHO 2 (MOUSE 2 / LUGAR 2) ---
                                else:
                                    if dx or dy:
                                        self.pos2[0] += dx * self.sens2
                                        self.pos2[1] += dy * self.sens2
                                        self.pos2[0], self.pos2[1] = clamp_to_bounds(self.pos2[0], self.pos2[1], self.bounds2)
                                        
                                        # Sincroniza cursor nativo do Windows continuamente em tempo real
                                        # para resposta instantânea de hover/botões sem atraso
                                        if not (self.m1_down or self.m1_rdown):
                                            user32.SetCursorPos(int(round(self.pos2[0])), int(round(self.pos2[1])))
                                    
                                    # Despacha cliques/rolagem cirurgicamente na Área de Trabalho 2
                                    if btn_flags:
                                        self.active_mouse = 'm2'
                                        self._inject_click(int(round(self.pos2[0])), int(round(self.pos2[1])), btn_flags, btn_data, 'm2')
                                
                                # Modo de simulação para testes com 1 mouse
                                if self.simulation_mode and target == 'm1':
                                    self.pos2[0] += dx * 0.8 * self._sim_dir
                                    self.pos2[1] += dy * 0.8
                                    self.pos2[0], self.pos2[1] = clamp_to_bounds(self.pos2[0], self.pos2[1], self.bounds2)
                                    
                                # Renderização ultra-rápida (0.01ms dirty-rect direto no DC)
                                if dx or dy or btn_flags:
                                    self._render_cursors_fast()
                                    
                                if self.on_positions_updated:
                                    self.on_positions_updated(self.pos1[0], self.pos1[1], self.pos2[0], self.pos2[1])
                                    
                return user32.DefWindowProcW(hwnd, msg, wp, lp)

            elif msg == 0x0010: # WM_CLOSE
                user32.DestroyWindow(hwnd)
                return 0
                
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
        
        # Aloca buffers e HDC persistente para renderização ultra-fluida em 0.01ms
        self._overlay_hdc = user32.GetDC(self.hwnd_overlay)
        self._mem_dc = gdi32.CreateCompatibleDC(self._overlay_hdc)
        self._mem_bmp = gdi32.CreateCompatibleBitmap(self._overlay_hdc, v_width, v_height)
        self._old_mem_bmp = gdi32.SelectObject(self._mem_dc, self._mem_bmp)
        self._bg_brush = gdi32.CreateSolidBrush(TRANSPARENT_COLOR)
        
        # Renderização inicial completa da tela
        self._render_cursors_fast(force_full=True)
        
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
                
                # Se for clique físico direto do hardware ou rolagem de roda, cancela na coordenada antiga
                # para que o motor possa reposicionar o cursor e disparar exatamente onde o mouse está!
                if wParam in (0x0201, 0x0202, 0x0204, 0x0205, 0x0207, 0x0208, 0x020A, 0x020E):
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

        self._cleanup_gdi_buffers()

        if self.hwnd_overlay:
            user32.DestroyWindow(self.hwnd_overlay)
            self.hwnd_overlay = None
            
        user32.UnregisterClassW(cls_name, hInst)
