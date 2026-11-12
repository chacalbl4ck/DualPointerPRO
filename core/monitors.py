"""
Módulo de Gerenciamento e Enumeração de Monitores
DualPointer Pro
"""

import ctypes
from ctypes import wintypes
from typing import List, Dict, Tuple, Optional

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG)
    ]

class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', RECT),
        ('rcWork', RECT),
        ('dwFlags', wintypes.DWORD),
        ('szDevice', wintypes.WCHAR * 32)
    ]

MONITORENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM
)

def get_monitors() -> List[Dict]:
    """
    Retorna a lista de todos os monitores conectados e ativos com suas coordenadas virtuais.
    """
    monitors = []
    
    def _enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
            rc = info.rcMonitor
            idx = len(monitors) + 1
            is_primary = bool(info.dwFlags & 1)
            monitors.append({
                'index': idx,
                'name': info.szDevice,
                'left': int(rc.left),
                'top': int(rc.top),
                'right': int(rc.right),
                'bottom': int(rc.bottom),
                'width': int(rc.right - rc.left),
                'height': int(rc.bottom - rc.top),
                'primary': is_primary,
                'label': f"Monitor {idx} ({rc.right - rc.left}x{rc.bottom - rc.top}){' [Principal]' if is_primary else ''}"
            })
        return True

    cb = MONITORENUMPROC(_enum_proc)
    user32.EnumDisplayMonitors(None, None, cb, 0)
    
    # Se por alguma razão a enumeração falhar (ex: sandbox restrita), usa métricas de sistema
    if not monitors:
        w = user32.GetSystemMetrics(0) # SM_CXSCREEN
        h = user32.GetSystemMetrics(1) # SM_CYSCREEN
        monitors.append({
            'index': 1,
            'name': r'\\.\DISPLAY1',
            'left': 0,
            'top': 0,
            'right': w,
            'bottom': h,
            'width': w,
            'height': h,
            'primary': True,
            'label': f"Monitor 1 ({w}x{h}) [Principal]"
        })
    return monitors

def get_virtual_desktop_rect() -> Tuple[int, int, int, int]:
    """
    Retorna o retângulo de todo o espaço virtual de trabalho (todos os monitores juntos):
    (left, top, right, bottom)
    """
    monitors = get_monitors()
    left = min(m['left'] for m in monitors)
    top = min(m['top'] for m in monitors)
    right = max(m['right'] for m in monitors)
    bottom = max(m['bottom'] for m in monitors)
    return left, top, right, bottom

def get_monitor_bounds_for_indices(monitor_indices: Optional[List[int]]) -> Tuple[int, int, int, int]:
    """
    Calcula os limites (left, top, right, bottom) permitidos para uma lista de índices de monitores.
    Se a lista for vazia, None ou contiver 0 ('Todos'), retorna o desktop virtual inteiro.
    """
    monitors = get_monitors()
    if not monitor_indices or 0 in monitor_indices:
        return get_virtual_desktop_rect()
    
    selected = [m for m in monitors if m['index'] in monitor_indices]
    if not selected:
        return get_virtual_desktop_rect()
        
    left = min(m['left'] for m in selected)
    top = min(m['top'] for m in selected)
    right = max(m['right'] for m in selected)
    bottom = max(m['bottom'] for m in selected)
    return left, top, right, bottom

def clamp_to_bounds(x: float, y: float, bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """
    Garante que a coordenada (x, y) não saia dos limites do(s) monitor(es) atribuído(s).
    """
    left, top, right, bottom = bounds
    clamped_x = max(left, min(int(x), right - 1))
    clamped_y = max(top, min(int(y), bottom - 1))
    return clamped_x, clamped_y
