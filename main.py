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

def main():
    # Carrega configurações salvas
    config = load_config()
    
    # Inicializa o motor Dual Mouse
    engine = DualPointerEngine(config)
    engine.start()
    
    # Inicializa a Interface Gráfica Tkinter
    root = tk.Tk()
    
    # Atalho global de teclado dentro da aplicação (F12) para pausar/retomar imediatamente
    root.bind("<F12>", lambda e: app._on_toggle_engine_clicked())
    
    app = DualPointerApp(root, engine, config)
    
    def on_closing():
        try:
            save_config(app.config)
            engine.stop()
        except Exception as e:
            print(f"Erro ao encerrar motor: {e}")
        finally:
            root.destroy()
            sys.exit(0)
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Loop principal da interface
    root.mainloop()

if __name__ == "__main__":
    main()
