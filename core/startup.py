"""
Módulo de Gerenciamento de Inicialização com o Windows
DualPointer Pro
"""

import os
import sys
import ctypes
from ctypes import wintypes
import uuid

STARTUP_FOLDER = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
SHORTCUT_NAME = "DualPointerPro.lnk"
SHORTCUT_PATH = os.path.join(STARTUP_FOLDER, SHORTCUT_NAME)

CLSID_ShellLink = "{00021401-0000-0000-C000-000000000046}"
IID_IShellLinkW = "{000214F9-0000-0000-C000-000000000046}"
IID_IPersistFile = "{0000010B-0000-0000-C000-000000000046}"

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', wintypes.DWORD),
        ('Data2', wintypes.WORD),
        ('Data3', wintypes.WORD),
        ('Data4', ctypes.c_byte * 8)
    ]

def _guid_from_str(s: str) -> GUID:
    b = uuid.UUID(s).bytes_le
    return GUID.from_buffer_copy(b)

class IShellLinkWVtbl(ctypes.Structure):
    _fields_ = [
        ('QueryInterface', ctypes.c_void_p),
        ('AddRef', ctypes.c_void_p),
        ('Release', ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)),
        ('GetPath', ctypes.c_void_p),
        ('GetIDList', ctypes.c_void_p),
        ('SetIDList', ctypes.c_void_p),
        ('GetDescription', ctypes.c_void_p),
        ('SetDescription', ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR)),
        ('GetWorkingDirectory', ctypes.c_void_p),
        ('SetWorkingDirectory', ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR)),
        ('GetArguments', ctypes.c_void_p),
        ('SetArguments', ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR)),
        ('GetHotkey', ctypes.c_void_p),
        ('SetHotkey', ctypes.c_void_p),
        ('GetShowCmd', ctypes.c_void_p),
        ('SetShowCmd', ctypes.c_void_p),
        ('GetIconLocation', ctypes.c_void_p),
        ('SetIconLocation', ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_int)),
        ('SetRelativePath', ctypes.c_void_p),
        ('Resolve', ctypes.c_void_p),
        ('SetPath', ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR)),
    ]

class IShellLinkW(ctypes.Structure):
    _fields_ = [('lpVtbl', ctypes.POINTER(IShellLinkWVtbl))]

class IPersistFileVtbl(ctypes.Structure):
    _fields_ = [
        ('QueryInterface', ctypes.c_void_p),
        ('AddRef', ctypes.c_void_p),
        ('Release', ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)),
        ('GetClassID', ctypes.c_void_p),
        ('IsDirty', ctypes.c_void_p),
        ('Load', ctypes.c_void_p),
        ('Save', ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.LPCWSTR, wintypes.BOOL)),
        ('SaveCompleted', ctypes.c_void_p),
        ('GetCurFile', ctypes.c_void_p),
    ]

class IPersistFile(ctypes.Structure):
    _fields_ = [('lpVtbl', ctypes.POINTER(IPersistFileVtbl))]

def is_startup_enabled() -> bool:
    """Verifica se o atalho do programa existe na pasta Inicializar do Windows."""
    return os.path.exists(SHORTCUT_PATH)

def set_startup_enabled(enabled: bool) -> bool:
    """
    Ativa ou desativa a inicialização automática com o Windows,
    criando ou removendo o atalho .lnk na pasta Inicializar.
    """
    if not enabled:
        if os.path.exists(SHORTCUT_PATH):
            try:
                os.remove(SHORTCUT_PATH)
                return True
            except Exception as e:
                print(f"Erro ao remover atalho de inicialização: {e}")
                return False
        return True
    
    # Criação do Atalho
    try:
        ole32 = ctypes.oledll.ole32
        ole32.CoInitialize(None)
        
        clsid = _guid_from_str(CLSID_ShellLink)
        iid_link = _guid_from_str(IID_IShellLinkW)
        iid_persist = _guid_from_str(IID_IPersistFile)
        
        pLink = ctypes.POINTER(IShellLinkW)()
        hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid_link), ctypes.byref(pLink))
        if hr != 0:
            ole32.CoUninitialize()
            return False
            
        if getattr(sys, 'frozen', False):
            target_exe = sys.executable
            arguments = ""
            work_dir = os.path.dirname(sys.executable)
            icon_path = sys.executable
        else:
            py_exe = sys.executable
            pyw_exe = os.path.join(os.path.dirname(py_exe), "pythonw.exe")
            target_exe = pyw_exe if os.path.exists(pyw_exe) else py_exe
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_script = os.path.join(root_dir, "main.py")
            arguments = f'"{main_script}"'
            work_dir = root_dir
            icon_path = os.path.join(root_dir, "assets", "icon.ico")
        
        vtbl = pLink.contents.lpVtbl.contents
        vtbl.SetPath(pLink, target_exe)
        if arguments:
            vtbl.SetArguments(pLink, arguments)
        vtbl.SetWorkingDirectory(pLink, work_dir)
        vtbl.SetDescription(pLink, "DualPointer Pro - Gerenciador Multi-Mouse & Multi-Monitor")
        
        if os.path.exists(icon_path):
            vtbl.SetIconLocation(pLink, icon_path, 0)
            
        # Salva o arquivo de atalho
        pPersist = ctypes.POINTER(IPersistFile)()
        QI = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(vtbl.QueryInterface)
        hr_qi = QI(pLink, ctypes.byref(iid_persist), ctypes.byref(pPersist))
        
        saved = False
        if hr_qi == 0:
            persist_vtbl = pPersist.contents.lpVtbl.contents
            hr_save = persist_vtbl.Save(pPersist, SHORTCUT_PATH, True)
            saved = (hr_save == 0)
            persist_vtbl.Release(pPersist)
            
        vtbl.Release(pLink)
        ole32.CoUninitialize()
        return saved
    except Exception as e:
        print(f"Erro ao criar atalho de inicialização: {e}")
        return False
