"""
DualPointer Pro - Gerenciador Multi-Mouse & Multi-Monitor
Desenvolvido por Caio Monteiro (GitHub: chacalbl4ck)

Ponto de Entrada Principal da Aplicação.
"""

import sys
import os
import ctypes
import tkinter as tk

# Ajusta DPI no Windows para resolução nítida em telas 1080p, 1440p e 4K
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from core.config import load_config, save_config
from core.engine import DualPointerEngine
from gui.app import DualPointerApp

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def elevate_if_needed():
    """Solicita elevação de privilégios (UAC) para garantir controle de mouse em janelas elevadas como o Gerenciador de Tarefas."""
    if is_admin():
        return True
    try:
        if "--no-elevate" in sys.argv:
            return False
            
        if getattr(sys, 'frozen', False):
            target = sys.executable
            args = ""
        else:
            target = sys.executable
            args = f'"{os.path.abspath(sys.argv[0])}"'
            if len(sys.argv) > 1:
                args += " " + " ".join([f'"{a}"' for a in sys.argv[1:] if a != "--no-elevate"])
                
        # 1 = SW_SHOWNORMAL
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", target, args, None, 1)
        if ret > 32:
            sys.exit(0)
    except Exception as e:
        print(f"Não foi possível auto-elevar: {e}")
    return False

def main():
    elevate_if_needed()
    
    # Carrega configurações salvas
    config = load_config()
    
    # Inicializa o motor Dual Mouse
    engine = DualPointerEngine(config)
    engine.start()
    
    # Inicializa a Interface Gráfica Tkinter
    root = tk.Tk()
    
    app = DualPointerApp(root, engine, config)
    
    # Atalho global de teclado dentro da aplicação (F12) para pausar/retomar imediatamente
    root.bind("<F12>", lambda e: app._on_toggle_engine_clicked())
    
    def on_closing():
        try:
            # Oculta a interface gráfica na mesma hora para retorno visual imediato
            root.withdraw()
            save_config(app.config)
            engine.stop()
        except Exception as e:
            print(f"Erro ao encerrar motor: {e}")
        finally:
            try:
                root.destroy()
            except Exception:
                pass
            os._exit(0)
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Loop principal da interface
    root.mainloop()

if __name__ == "__main__":
    main()
