import ctypes
import platform
import sys
import os
import subprocess
import hashlib
from windows_policy_manager import WindowsPolicyManager

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

def get_chrome_user_data_path():
    system = platform.system()
    if system == "Windows": return os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data')
    return None

def get_policy_manager():
    if platform.system() == "Windows":
        return WindowsPolicyManager()
    return None

def get_hardware_id():
    if platform.system() != "Windows": return "UNSUPPORTED_OS"
    try:
        command = "powershell.exe -Command \"(Get-CimInstance Win32_ComputerSystemProduct).UUID;(Get-CimInstance Win32_BaseBoard).SerialNumber;(Get-CimInstance Win32_Processor).ProcessorId\""
        result = subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        composite_id = result.decode('utf-8', errors='ignore').strip()
        if not composite_id or "FFFF" in composite_id: raise ValueError("Invalid HWID components found")
        return hashlib.sha256(composite_id.encode()).hexdigest()
    except Exception as e:
        print(f"Advanced HWID failed: {e}. Falling back to basic wmic UUID.")
        try:
            command = "wmic csproduct get uuid"
            return subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
        except Exception: return "UNKNOWN_HWID"
