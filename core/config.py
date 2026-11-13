"""
Módulo de Configuração Persistente
DualPointer Pro
"""

import json
import os
import sys
from typing import Dict, Any

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(APP_DIR, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "DualPointer Pro",
        "version": "1.0.0",
        "author": "Caio Monteiro",
        "github": "chacalbl4ck"
    },
    "mouse1": {
        "workspace_name": "Área de Trabalho 1 (Estação A)",
        "hwid": "VID_046D&PID_C077",
        "instance_id": "",
        "friendly_name": "Mouse Principal",
        "monitors": [1],
        "sensitivity": 1.0,
        "cursor": {
            "shape": "sleek",        # sleek, fluent, cyber, precision, capsule, stylus
            "color": "#38BDF8",       # Ciano Ártico Moderno
            "border_color": "#FFFFFF",
            "size": 28,
            "glow": True,
            "show_label": True,
            "label_text": "1"
        }
    },
    "mouse2": {
        "workspace_name": "Área de Trabalho 2 (Estação B)",
        "hwid": "",
        "instance_id": "",
        "friendly_name": "Mouse Secundário",
        "monitors": [2],
        "sensitivity": 1.0,
        "cursor": {
            "shape": "sleek",        # sleek, fluent, cyber, precision, capsule, stylus
            "color": "#FB923C",       # Sunset Coral Moderno
            "border_color": "#FFFFFF",
            "size": 28,
            "glow": True,
            "show_label": True,
            "label_text": "2"
        }
    },
    "system": {
        "autostart": False,
        "active_on_launch": True,
        "simulation_mode": False,
        "failsafe_hotkey": "F12",
        "hide_os_cursor": True,
        "suppress_os_cursor": True,
        "isolate_workspaces": True,
        "multiseat_mode": True
    }
}

def load_config() -> Dict[str, Any]:
    """Carrega as configurações salvas ou cria o arquivo padrão se não existir."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))
        
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            # Mescla com os padrões para garantir que novas chaves existam
            merged = json.loads(json.dumps(DEFAULT_CONFIG))
            _deep_update(merged, cfg)
            return merged
    except Exception as e:
        print(f"Erro ao carregar config.json: {e}. Restaurando padrão.")
        return json.loads(json.dumps(DEFAULT_CONFIG))

def save_config(cfg: Dict[str, Any]) -> bool:
    """Salva o dicionário de configurações no arquivo JSON."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao salvar config.json: {e}")
        return False

def _deep_update(base: dict, update: dict):
    for k, v in update.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
