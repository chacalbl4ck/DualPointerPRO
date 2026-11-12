"""
Módulo de Enumeração e Identificação de Mouses USB / HID
DualPointer Pro
"""

import ctypes
from ctypes import wintypes
import winreg
import re
from typing import List, Dict, Optional

user32 = ctypes.WinDLL('user32', use_last_error=True)

class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ('hDevice', wintypes.HANDLE),
        ('dwType', wintypes.DWORD)
    ]

user32.GetRawInputDeviceList.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputDeviceList.restype = wintypes.UINT

user32.GetRawInputDeviceInfoW.argtypes = [
    wintypes.HANDLE,
    wintypes.UINT,
    wintypes.LPVOID,
    ctypes.POINTER(wintypes.UINT)
]
user32.GetRawInputDeviceInfoW.restype = wintypes.UINT

# Tabela de Fabricantes USB conhecidos para identificação amigável
KNOWN_VENDORS = {
    '046D': 'Logitech',
    '1532': 'Razer',
    '1B1C': 'Corsair',
    '045E': 'Microsoft',
    '1038': 'SteelSeries',
    '258A': 'Glorious / Machenike',
    '04D9': 'Redragon / Holtek',
    '05AC': 'Apple',
    '0B05': 'ASUS ROG',
    '17EF': 'Lenovo',
    '04F2': 'Chicony',
    '093A': 'PixArt Optical',
    '27DD': 'Mouse USB Óptico',
    '0E8F': 'GreenAsia',
    '195D': 'Itron Tech',
    '24AE': 'Rapoo',
    '0461': 'Primax (Dell / HP)',
    '04CA': 'Lite-On',
    '1BCF': 'SunplusIT',
    '30FA': 'Insta360 / USB Mouse',
    '09DA': 'A4Tech / Bloody',
    '28BD': 'Huion / Tablet',
    '056A': 'Wacom',
    '2717': 'Xiaomi',
}

def get_vendor_name(vid: str) -> str:
    """Retorna o nome do fabricante com base no Vendor ID."""
    vid_clean = vid.upper().replace('0X', '')
    return KNOWN_VENDORS.get(vid_clean, f"Fabricante (VID_{vid_clean})")

def get_registry_device_info(hwid_pattern: str, instance_id: str = "") -> Dict[str, str]:
    """
    Busca informações detalhadas e descrições no Registro do Windows (Enum\\HID e Enum\\USB).
    """
    info = {'desc': '', 'friendly': '', 'class': ''}
    
    roots = [
        r'SYSTEM\CurrentControlSet\Enum\HID',
        r'SYSTEM\CurrentControlSet\Enum\USB'
    ]
    
    for root in roots:
        try:
            root_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root)
            count = winreg.QueryInfoKey(root_key)[0]
            for i in range(count):
                dev_sub = winreg.EnumKey(root_key, i)
                if hwid_pattern.upper() in dev_sub.upper():
                    dev_key = winreg.OpenKey(root_key, dev_sub)
                    inst_count = winreg.QueryInfoKey(dev_key)[0]
                    for j in range(inst_count):
                        inst_name = winreg.EnumKey(dev_key, j)
                        if not instance_id or instance_id.upper() in inst_name.upper():
                            inst_key = winreg.OpenKey(dev_key, inst_name)
                            for val_name, key_name in [('FriendlyName', 'friendly'), ('DeviceDesc', 'desc'), ('Class', 'class')]:
                                try:
                                    val, _ = winreg.QueryValueEx(inst_key, val_name)
                                    if ';' in val:
                                        val = val.split(';')[-1]
                                    if val and not info[key_name]:
                                        info[key_name] = val
                                except Exception:
                                    pass
        except Exception:
            pass
            
    return info

def get_connected_mice() -> List[Dict]:
    """
    Enumera todos os mouses e dispositivos apontadores conectados ao computador,
    obtendo Hardware ID (VID/PID), Instance ID, Descrição e Handle do Raw Input.
    """
    found_devices = []
    seen_ids = set()

    # 1. Busca por RawInput (tempo de execução)
    count = wintypes.UINT(0)
    cbSize = ctypes.sizeof(RAWINPUTDEVICELIST)
    user32.GetRawInputDeviceList(None, ctypes.byref(count), cbSize)
    
    if count.value > 0:
        devs = (RAWINPUTDEVICELIST * count.value)()
        ret = user32.GetRawInputDeviceList(devs, ctypes.byref(count), cbSize)
        
        for i in range(ret):
            d = devs[i]
            # dwType == 0 significa RIM_TYPEMOUSE
            if d.dwType == 0:
                sz = wintypes.UINT(0)
                user32.GetRawInputDeviceInfoW(d.hDevice, 0x20000007, None, ctypes.byref(sz))
                raw_path = ""
                if sz.value > 0:
                    buf = ctypes.create_unicode_buffer(sz.value + 1)
                    if user32.GetRawInputDeviceInfoW(d.hDevice, 0x20000007, buf, ctypes.byref(sz)) > 0:
                        raw_path = buf.value

                # Se obteve caminho do RawInput
                if raw_path:
                    # Exemplo de raw_path: \\?\HID#VID_046D&PID_C077#6&2e70eed6&0&0000#{378de44c...}
                    m_vid_pid = re.search(r'VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})', raw_path, re.IGNORECASE)
                    m_inst = re.search(r'#([^#]+)#{', raw_path)
                    
                    vid = m_vid_pid.group(1).upper() if m_vid_pid else "0000"
                    pid = m_vid_pid.group(2).upper() if m_vid_pid else "0000"
                    hwid = f"VID_{vid}&PID_{pid}"
                    instance_id = m_inst.group(1) if m_inst else ""
                    
                    reg_info = get_registry_device_info(hwid, instance_id)
                    vendor = get_vendor_name(vid)
                    desc = reg_info.get('friendly') or reg_info.get('desc') or "Mouse Compatível com HID"
                    
                    unique_key = f"{hwid}_{instance_id}"
                    if unique_key not in seen_ids:
                        seen_ids.add(unique_key)
                        found_devices.append({
                            'id': unique_key,
                            'handle': d.hDevice,
                            'hwid': hwid,
                            'vid': vid,
                            'pid': pid,
                            'instance_id': instance_id,
                            'vendor': vendor,
                            'friendly_name': desc,
                            'device_path': raw_path,
                            'display_label': f"{vendor} [{hwid}] - {desc}"
                        })

    # 2. Busca pelo driver mouhid no Registro para garantir que todos os mouses USB físicos sejam listados
    try:
        mouhid_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\mouhid\Enum')
        cnt, _ = winreg.QueryValueEx(mouhid_key, 'Count')
        for idx in range(cnt):
            pnp_id, _ = winreg.QueryValueEx(mouhid_key, str(idx))
            # pnp_id ex: HID\VID_046D&PID_C077\6&2e70eed6&0&0000
            m_vid_pid = re.search(r'VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})', pnp_id, re.IGNORECASE)
            parts = pnp_id.split('\\')
            instance_id = parts[-1] if len(parts) >= 3 else ""
            
            vid = m_vid_pid.group(1).upper() if m_vid_pid else "0000"
            pid = m_vid_pid.group(2).upper() if m_vid_pid else "0000"
            hwid = f"VID_{vid}&PID_{pid}"
            
            unique_key = f"{hwid}_{instance_id}"
            if unique_key not in seen_ids:
                seen_ids.add(unique_key)
                reg_info = get_registry_device_info(hwid, instance_id)
                vendor = get_vendor_name(vid)
                desc = reg_info.get('friendly') or reg_info.get('desc') or "Mouse Compatível com HID"
                
                found_devices.append({
                    'id': unique_key,
                    'handle': None,
                    'hwid': hwid,
                    'vid': vid,
                    'pid': pid,
                    'instance_id': instance_id,
                    'vendor': vendor,
                    'friendly_name': desc,
                    'device_path': pnp_id,
                    'display_label': f"{vendor} [{hwid}] - {desc}"
                })
    except Exception:
        pass

    # 3. Se nenhum foi detectado ou apenas 1, inclui dispositivos virtuais para teste/configuração
    if not found_devices:
        found_devices.append({
            'id': 'VID_DEFAULT_M1',
            'handle': None,
            'hwid': 'VID_046D&PID_C077',
            'vid': '046D',
            'pid': 'C077',
            'instance_id': 'PORT_1',
            'vendor': 'Logitech',
            'friendly_name': 'Mouse USB Principal',
            'device_path': r'HID\VID_046D&PID_C077\PORT_1',
            'display_label': 'Logitech [VID_046D&PID_C077] - Mouse Principal'
        })
        
    return found_devices

def matches_device(device_info: Dict, target_hwid: str, target_instance: str = "") -> bool:
    """Verifica se um dispositivo corresponde ao Hardware ID ou Instance ID configurado."""
    if not target_hwid:
        return False
    hwid = device_info.get('hwid', '').upper()
    path = device_info.get('device_path', '').upper()
    inst = device_info.get('instance_id', '').upper()
    target_hwid = target_hwid.upper()
    target_instance = target_instance.upper()
    
    hw_match = (target_hwid in hwid) or (target_hwid in path)
    if not hw_match:
        return False
        
    if target_instance:
        return target_instance in inst or target_instance in path
        
    return True
