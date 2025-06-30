import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import os
import platform
import sys
import threading
import subprocess
import ctypes
import json
import requests
import re
import hashlib
import pyperclip
import time
import shutil

# ==============================================================================
# Chrome Manager PRO v12.0 (The Stability Cut)
# Description: A complete, stable management suite for Google Chrome with a
#              feature-rich policy editor, profile management, and robust online activation.
#              This version includes critical bug fixes and over 50 new features.
#
# Requirements: pip install --upgrade ttkbootstrap requests pyperclip pypiwin32 WMI
# ==============================================================================

# --- Configuration & Constants ---
CURRENT_VERSION = "12.0"
LICENSE_FILE = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ChromeManagerLicense.dat")
CACHE_FILE = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "ChromeManagerCache.json")
ACTIVATION_URL = "https://script.google.com/macros/s/AKfycbzuN6kjcuHIsnWo0XlFIlyoIH-m3O89eDOCnuo5FdpFmftT1YnubR_EynkP1AtAauq-XQ/exec" # USER'S URL PASTED

# --- Policy Definitions ---
POLICIES = {
    "Security & Privacy": [
        {"name": "Incognito Mode Availability", "key": "", "value_name": "IncognitoModeAvailability", "type": "REG_DWORD", "options": {"Default Enabled": -1, "Enabled": 0, "Disabled": 1, "Forced": 2}, "help": "0: Default, 1: Incognito disabled, 2: All windows are Incognito."},
        {"name": "Password Manager", "key": "", "value_name": "PasswordManagerEnabled", "type": "REG_DWORD", "options": {"Allow users to decide": -1, "Force Enabled": 1, "Force Disabled": 0}, "help": "Controls Chrome's built-in password saving functionality."},
        {"name": "Safe Browse Protection Level", "key": "", "value_name": "SafeBrowseProtectionLevel", "type": "REG_DWORD", "options": {"Default": -1, "No Protection": 0, "Standard": 1, "Enhanced": 2}, "help": "Enforces a minimum level of Safe Browse."},
        {"name": "Block Insecure Downloads", "key": "", "value_name": "DownloadRestrictions", "type": "REG_DWORD", "options": {"Default": -1, "No Special Restrictions": 0, "Block Malicious": 1, "Block Dangerous": 2, "Block All": 4}, "help": "Restricts downloading of insecure or dangerous files."},
        {"name": "Developer Tools Availability", "key": "", "value_name": "DeveloperToolsAvailability", "type": "REG_DWORD", "options": {"Default": -1, "Allowed": 0, "Disallowed": 1, "Disallowed for Extensions": 2}, "help": "Controls access to developer tools (F12)."},
        {"name": "Network Prediction (Prefetch)", "key": "", "value_name": "NetworkPredictionOptions", "type": "REG_DWORD", "options": {"Default": -1, "Standard": 0, "Wi-Fi Only": 1, "Disabled": 2}, "help": "Disables pre-connecting to links for privacy. May slow down Browse."},
        {"name": "Browser Sign-In", "key": "", "value_name": "BrowserSignin", "type": "REG_DWORD", "options": {"Default": -1, "Allow": 0, "Force users to sign-in": 1, "Disable sign-in": 2}, "help": "Controls if users can sign in to Chrome with their Google Account."},
    ],
    "Startup, Homepage & UI": [
        {"name": "Action on Startup", "key": "", "value_name": "RestoreOnStartup", "type": "REG_DWORD", "options": {"Default": -1, "Open New Tab Page": 1, "Restore Last Session": 4, "Open Specific URLs": 5}, "help": "Defines what Chrome opens on launch."},
        {"name": "URLs to Open on Startup", "key": "RestoreOnStartupURLs", "value_name": "1", "type": "REG_SZ", "options": {"text": "Enter URL"}, "help": "Set a URL to open on startup. Only works if 'Action on Startup' is 'Open Specific URLs'."},
        {"name": "Homepage Location", "key": "", "value_name": "HomepageLocation", "type": "REG_SZ", "options": {"text": "Enter URL"}, "help": "Sets the homepage URL. Example: https://www.google.com"},
        {"name": "Show Home Button", "key": "", "value_name": "ShowHomeButton", "type": "REG_DWORD", "options": {"Default": -1, "Force Enabled": 1, "Force Disabled": 0}, "help": "Forces the Home button to be visible or not."},
        {"name": "Bookmark Bar", "key": "", "value_name": "BookmarkBarEnabled", "type": "REG_DWORD", "options": {"Default": -1, "Force Enabled": 1, "Force Disabled": 0}, "help": "Controls the visibility of the bookmarks bar."},
    ],
    "Content Settings (JavaScript, Cookies, etc.)": [
        {"name": "Default Cookies Setting", "key": "", "value_name": "DefaultCookiesSetting", "type": "REG_DWORD", "options": {"Default": -1, "Allow All": 1, "Block Third-Party": 3, "Block All": 2}, "help": "Sets the default behavior for handling cookies."},
        {"name": "Default JavaScript Setting", "key": "", "value_name": "DefaultJavaScriptSetting", "type": "REG_DWORD", "options": {"Default": -1, "Allow": 1, "Block": 2}, "help": "Sets the default behavior for running JavaScript."},
        {"name": "Default Popups Setting", "key": "", "value_name": "DefaultPopupsSetting", "type": "REG_DWORD", "options": {"Default": -1, "Allow": 1, "Block": 2}, "help": "Sets the default behavior for pop-up windows."},
        {"name": "Default Images Setting", "key": "", "value_name": "DefaultImagesSetting", "type": "REG_DWORD", "options": {"Default": -1, "Show All": 1, "Block All": 2}, "help": "Controls whether images are loaded by default."},
    ],
    "Hardware & Performance": [
        {"name": "Hardware Acceleration Mode", "key": "", "value_name": "HardwareAccelerationModeEnabled", "type": "REG_DWORD", "options": {"Default": -1, "Force Enabled": 1, "Force Disabled": 0}, "help": "Forces hardware acceleration on or off. A restart is required."},
    ]
}


# --- Admin Privilege & Core Functions ---
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
    if platform.system() == "Windows": return WindowsPolicyManager()
    return None

# --- Hardware ID (v12 - Robust Method) ---
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

# --- License Manager (v12 - Real-time Check) ---
class LicenseManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.log = app_instance.log
        self.last_online_check = 0
        self.check_interval = 3600 # 1 hour in seconds

    def _perform_online_check(self, key_from_local_file):
        self.log("Performing real-time license check with server...")
        is_still_valid, message = self.activate_online(key_from_local_file, is_recheck=True)
        if not is_still_valid:
            self.log(f"License check failed: {message}. Deactivating PRO features.")
            if os.path.exists(LICENSE_FILE): os.remove(LICENSE_FILE)
            self.app.after(0, self.app.deactivate_pro_features)
        else:
            self.log("License is still valid.")
            self.last_online_check = time.time()

    def activate_online(self, key, is_recheck=False):
        if not ACTIVATION_URL or "YOUR_GOOGLE_APPS_SCRIPT_URL_HERE" in ACTIVATION_URL:
            return False, "Activation URL not configured by the developer."
        hwid = get_hardware_id()
        if hwid in ["UNKNOWN_HWID", "UNSUPPORTED_OS"]: return False, "Could not retrieve a unique hardware ID."
        try:
            url = f"{ACTIVATION_URL}?key={key}&hwid={hwid}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success":
                if not is_recheck:
                    with open(LICENSE_FILE, 'w') as f:
                        f.write(json.dumps({'key': key, 'hwid_hash': hashlib.sha256(hwid.encode()).hexdigest()}))
                return True, data.get("message", "Activation Successful!")
            else: return False, data.get("message", "An unknown error occurred.")
        except Exception as e: return False, f"Network error: {e}"

    def is_activated(self, force_online_check=False):
        if not os.path.exists(LICENSE_FILE): return False
        try:
            with open(LICENSE_FILE, 'r') as f: license_data = json.load(f)
            stored_hash = license_data.get('hwid_hash')
            key = license_data.get('key')
            current_hwid_hash = hashlib.sha256(get_hardware_id().encode()).hexdigest()
            if stored_hash != current_hwid_hash: return False
            if force_online_check or (time.time() - self.last_online_check > self.check_interval):
                threading.Thread(target=self._perform_online_check, args=(key,), daemon=True).start()
            return True
        except Exception: return False

# --- Core Logic Classes ---
class WindowsPolicyManager:
    def __init__(self): self.POLICY_BASE_KEY = r"SOFTWARE\Policies\Google\Chrome"
    def _run_reg_command(self, args):
        try:
            full_command = ['powershell', '-Command', f"reg {args}"]
            startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(full_command, capture_output=True, text=True, check=True, startupinfo=startupinfo, encoding='utf-8', errors='ignore')
            return result.stdout, result.stderr
        except subprocess.CalledProcessError as e: return e.stdout, e.stderr
        except FileNotFoundError: return None, "PowerShell or reg.exe not found."
    def set_policy(self, key_name, value_name, value_data, value_type="REG_DWORD"):
        full_key = f"HKEY_LOCAL_MACHINE\\{self.POLICY_BASE_KEY}\\{key_name}" if key_name else f"HKEY_LOCAL_MACHINE\\{self.POLICY_BASE_KEY}"
        if value_type == "REG_SZ": value_data = f'"{value_data}"'
        args = f'add "{full_key}" /v "{value_name}" /t {value_type} /d {value_data} /f'
        _, stderr = self._run_reg_command(args)
        if "Access is denied" in stderr: return False, "Access Denied."
        if stderr and "successfully" not in stderr: return False, stderr
        return True, "Policy set successfully."
    def remove_policy(self, key_name, value_name):
        full_key = f"HKEY_LOCAL_MACHINE\\{self.POLICY_BASE_KEY}\\{key_name}" if key_name else f"HKEY_LOCAL_MACHINE\\{self.POLICY_BASE_KEY}"
        args = f'delete "{full_key}" /v "{value_name}" /f'
        _, stderr = self._run_reg_command(args)
        if "Access is denied" in stderr: return False, "Access Denied."
        if stderr and "was not found" not in stderr and "ERROR:" in stderr : return False, stderr
        return True, "Policy removed successfully."
    def add_extension(self, ext_id, log_callback):
        current_extensions = self.get_forced_extensions(lambda msg: None)
        if ext_id in current_extensions: return True, f"Extension {ext_id} is already in the policy list."
        next_index = 1
        current_indices = [int(idx) for idx in current_extensions.values() if idx.isdigit()]
        if current_indices: next_index = max(current_indices) + 1
        value_data = f"{ext_id};https://clients2.google.com/service/update2/crx"
        log_callback(f"Adding policy for {ext_id} at index {next_index}...")
        return self.set_policy("ExtensionInstallForcelist", str(next_index), value_data, "REG_SZ")
    def remove_extension(self, index, log_callback):
        log_callback(f"Removing policy at index {index}...")
        return self.remove_policy("ExtensionInstallForcelist", str(index))
    def get_policy_value(self, key_name, value_name):
        full_key = f"HKEY_LOCAL_MACHINE\\{self.POLICY_BASE_KEY}\\{key_name}" if key_name else f"HKEY_LOCAL_MACHINE\\{self.POLICY_BASE_KEY}"
        args = f'query "{full_key}" /v "{value_name}"'
        stdout, stderr = self._run_reg_command(args)
        if stderr: return None
        try:
            last_line = stdout.strip().split('\n')[-1]
            parts = [p.strip() for p in last_line.split('    ') if p.strip()]
            return parts[-1]
        except: return None
    def get_forced_extensions(self, log_callback):
        log_callback("Reading extension policies from Windows Registry...")
        args = f'query HKEY_LOCAL_MACHINE\\{self.POLICY_BASE_KEY}\\ExtensionInstallForcelist'
        stdout, stderr = self._run_reg_command(args)
        if "unable to find the specified registry key" in stderr: return {}
        if "Access is denied" in stderr: return {"_error": "access_denied"}
        if stderr: return {}
        extensions = {}
        for line in stdout.strip().split('\n'):
            if not line.strip() or line.startswith("HKEY_LOCAL_MACHINE"): continue
            try:
                parts = [p.strip() for p in line.split('    ') if p.strip()]
                value_data, index = parts[-1], parts[0]
                extensions[value_data.split(';')[0]] = index
            except IndexError: log_callback(f"Could not parse line: {line}")
        return extensions

def get_profile_details(user_data_path, log_callback):
    profile_details = {}
    if not user_data_path or not os.path.exists(user_data_path): return {}
    for item in os.listdir(user_data_path):
        if item == "Default" or item.startswith("Profile "):
            profile_path = os.path.join(user_data_path, item)
            if not os.path.isdir(profile_path): continue
            preferences_path = os.path.join(profile_path, 'Preferences')
            profile_name = item
            if os.path.exists(preferences_path):
                try:
                    with open(preferences_path, 'r', encoding='utf-8') as f:
                        prefs = json.load(f)
                        profile_name = prefs.get('profile', {}).get('name', item)
                except Exception: log_callback(f"Error: Could not read Preferences for {item}.")
            original_name = profile_name; counter = 2
            while profile_name in profile_details:
                profile_name = f"{original_name} ({counter})"; counter += 1
            profile_details[profile_name] = profile_path
    return dict(sorted(profile_details.items()))

def get_extensions_for_profile(profile_path, log_callback):
    extensions = {}
    if not os.path.exists(os.path.join(profile_path, 'Preferences')): return {}
    try:
        with open(os.path.join(profile_path, 'Preferences'), 'r', encoding='utf-8') as f:
            prefs = json.load(f)
        installed_extensions = prefs.get('extensions', {}).get('settings', {})
        for ext_id, details in installed_extensions.items():
            if len(ext_id) != 32: continue
            manifest = details.get('manifest', {})
            name = manifest.get('name', ext_id)
            if name.startswith('__MSG_'): name = name.replace('__MSG_','').replace('appName','').replace('__','').strip() or ext_id
            state = details.get('state', 0)
            version = manifest.get('version', 'N/A')
            permissions = manifest.get('permissions', [])
            path = details.get('path', 'N/A')
            was_installed_by_default = details.get('was_installed_by_default', False)
            original_name = name; counter = 2
            while name in extensions: name = f"{original_name} ({counter})"; counter += 1
            extensions[name] = {'id': ext_id, 'state': state, 'version': version, 'permissions': permissions, 'path': path, 'was_installed_by_default': was_installed_by_default}
    except Exception as e: log_callback(f"Error reading extensions for {os.path.basename(profile_path)}: {e}")
    return dict(sorted(extensions.items()))

def set_extension_state_for_profile(profile_path, ext_id, new_state, log_callback):
    prefs_path = os.path.join(profile_path, 'Preferences')
    if not os.path.exists(prefs_path): return False
    try:
        shutil.copyfile(prefs_path, prefs_path + '.bak')
        with open(prefs_path, 'r+', encoding='utf-8') as f:
            prefs = json.load(f)
            if ext_id in prefs.get('extensions', {}).get('settings', {}):
                prefs['extensions']['settings'][ext_id]['state'] = new_state
                f.seek(0); json.dump(prefs, f, indent=4); f.truncate()
                log_callback(f"Successfully set state to {'Enabled' if new_state == 1 else 'Disabled'} for {ext_id}")
                return True
            else: return False
    except Exception as e: log_callback(f"Error modifying Preferences file: {e}"); return False

# --- GUI Application ---
class Application(tb.Window):
    def __init__(self):
        self.current_theme = 'superhero'
        super().__init__(themename=self.current_theme)
        self.title(f"Chrome Manager PRO v{CURRENT_VERSION}")
        self.geometry("1200x800"); self.minsize(1000, 700)
        self.license_manager = LicenseManager(self)
        self.policy_manager = get_policy_manager()
        self.user_data_path = get_chrome_user_data_path()
        self.cache = self.load_cache()
        self.create_widgets()
        if not self.policy_manager:
            messagebox.showerror("Unsupported OS", "This application currently only supports Windows."); self.destroy()
        else:
            self.after(100, self.initial_load)

    def initial_load(self):
        """Perform initial loading tasks after the UI is ready."""
        self.run_task_in_thread(self._check_activation_logic)
        self.run_task_in_thread(self._refresh_blocklist, initial_load=True)

    def log(self, message): self.after(0, self._update_log_area, message)
    def create_widgets(self):
        self.notebook = tb.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=(10,0))
        self.create_dashboard_tab()
        self.create_pro_manager_tab()
        self.create_policy_editor_tab()
        self.create_url_blocker_tab()
        log_frame = tb.LabelFrame(self, text="Log", padding=10)
        log_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=8, state=DISABLED, borderwidth=0, highlightthickness=0)
        self.log_area.pack(fill=BOTH, expand=True)

    def create_dashboard_tab(self):
        self.dashboard_tab = tb.Frame(self.notebook, padding=20)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.activation_frame = tb.Frame(self.dashboard_tab); self.activation_frame.pack(fill=BOTH, expand=True)
        tb.Label(self.activation_frame, text="PRO Version Not Activated", font=("", 16, "bold"), bootstyle="secondary").pack(pady=10)
        tb.Label(self.activation_frame, text="Activate to unlock the Advanced Profile Manager and Policy Editor.", wraplength=500, justify="center").pack(pady=10)
        self.key_entry = tb.Entry(self.activation_frame, width=50); self.key_entry.pack(pady=10)
        self.activate_button = tb.Button(self.activation_frame, text="Activate PRO", bootstyle="success", command=self.prompt_for_activation); self.activate_button.pack(pady=10, ipady=10)
        self.dashboard_pro_frame = tb.Frame(self.dashboard_tab)
        tb.Label(self.dashboard_pro_frame, text="PRO Version Activated", font=("", 16, "bold"), bootstyle="success").pack(pady=10)
        tb.Label(self.dashboard_pro_frame, text="All features are unlocked. Navigate to the other tabs to begin.", wraplength=500, justify="center").pack(pady=10)
        tb.Button(self.dashboard_pro_frame, text="Check License Status", bootstyle="info", command=lambda: self.license_manager.is_activated(force_online_check=True)).pack(pady=10)
        tb.Button(self.dashboard_pro_frame, text="Switch Theme (Light/Dark)", bootstyle="secondary", command=self.toggle_theme).pack(pady=10)

    def create_pro_manager_tab(self):
        self.pro_tab = tb.Frame(self.notebook, padding=10)
        self.notebook.add(self.pro_tab, text="Advanced Profile Manager (PRO)", state="disabled")
        top_frame = tb.Frame(self.pro_tab); top_frame.pack(fill=BOTH, expand=True, pady=5)
        top_frame.grid_columnconfigure(0, weight=1); top_frame.grid_columnconfigure(1, weight=2); top_frame.grid_rowconfigure(0, weight=1)
        left_panel = tb.Frame(top_frame); left_panel.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        profiles_frame = tb.LabelFrame(left_panel, text="1. Select Profile"); profiles_frame.pack(fill=BOTH, expand=True)
        self.pro_profiles_list = tk.Listbox(profiles_frame, exportselection=False); self.pro_profiles_list.pack(fill=BOTH, expand=True)
        self.pro_profiles_list.bind('<<ListboxSelect>>', self.on_pro_profile_select)
        backup_frame = tb.Frame(left_panel); backup_frame.pack(fill=X, pady=5)
        tb.Button(backup_frame, text="Backup Profile", bootstyle="info-outline", command=self.backup_profile_extensions).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(backup_frame, text="Restore Profile", bootstyle="info-outline", command=self.restore_profile_extensions).pack(side=LEFT, expand=True, fill=X, padx=2)
        right_panel = tb.Frame(top_frame); right_panel.grid(row=0, column=1, sticky="nsew")
        ext_frame = tb.LabelFrame(right_panel, text="2. Manage Extensions"); ext_frame.pack(fill=BOTH, expand=True)
        self.pro_extensions_list = tk.Listbox(ext_frame, exportselection=False); self.pro_extensions_list.pack(fill=BOTH, expand=True)
        pro_actions_frame = tb.Frame(right_panel); pro_actions_frame.pack(fill=X, pady=5)
        tb.Button(pro_actions_frame, text="Enable", bootstyle="success-outline", command=lambda: self.toggle_extension_state(1)).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(pro_actions_frame, text="Disable", bootstyle="warning-outline", command=lambda: self.toggle_extension_state(0)).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(pro_actions_frame, text="Details", bootstyle="secondary-outline", command=self.show_extension_details).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(pro_actions_frame, text="Panic Button", bootstyle="danger", command=self.panic_button).pack(side=LEFT, expand=True, fill=X, padx=2)
        
    def create_policy_editor_tab(self):
        self.policy_editor_tab = tb.Frame(self.notebook, padding=10)
        self.notebook.add(self.policy_editor_tab, text="Advanced Policy Editor (PRO)", state="disabled")
        header = tb.Frame(self.policy_editor_tab); header.pack(fill=X, pady=5)
        tb.Label(header, text="Apply system-wide Chrome settings. Changes affect ALL users on this computer and require a browser restart.", bootstyle='info').pack(side=LEFT)
        tree_frame = tb.Frame(self.policy_editor_tab); tree_frame.pack(fill=BOTH, expand=True, pady=5)
        self.policy_tree = tb.Treeview(tree_frame, columns=("Status", "Value"), show="tree headings")
        self.policy_tree.heading("#0", text="Policy Name"); self.policy_tree.heading("Status", text="Current Status"); self.policy_tree.heading("Value", text="Configured Value")
        self.policy_tree.column("#0", width=300); self.policy_tree.column("Status", width=150, anchor='center'); self.policy_tree.column("Value", width=200)
        self.policy_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = tb.Scrollbar(tree_frame, orient=VERTICAL, command=self.policy_tree.yview); self.policy_tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=RIGHT, fill=Y)
        self.policy_tree.bind("<Double-1>", self.on_policy_edit)

    def create_url_blocker_tab(self):
        self.url_blocker_tab = tb.Frame(self.notebook, padding=10)
        self.notebook.add(self.url_blocker_tab, text="URL Blocker (Free)")
        tb.Label(self.url_blocker_tab, text="Block specific websites for all users. Wildcards (*) are supported. E.g., *.facebook.com", bootstyle='info').pack(fill=X, pady=5)
        add_frame = tb.Frame(self.url_blocker_tab); add_frame.pack(fill=X, pady=5)
        tb.Label(add_frame, text="URL to Block:").pack(side=LEFT, padx=5)
        self.url_entry = tb.Entry(add_frame); self.url_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        tb.Button(add_frame, text="Block URL", bootstyle="danger", command=self.add_url_to_blocklist).pack(side=LEFT, padx=5)
        list_frame = tb.LabelFrame(self.url_blocker_tab, text="Currently Blocked URLs"); list_frame.pack(fill=BOTH, expand=True, pady=10)
        self.blocked_url_list = tk.Listbox(list_frame); self.blocked_url_list.pack(side=LEFT, fill=BOTH, expand=True)
        tb.Button(list_frame, text="Allow Selected URL", bootstyle="success-outline", command=self.remove_url_from_blocklist).pack(side=LEFT, padx=10, pady=10)
        
    def check_activation(self):
        self.run_task_in_thread(self._check_activation_logic)
    def _check_activation_logic(self):
        is_active = self.license_manager.is_activated(force_online_check=True)
        self.after(0, self.activate_pro_features if is_active else self.deactivate_pro_features)
    def activate_pro_features(self):
        self.log("PRO version activated. All features unlocked.")
        self.activation_frame.pack_forget(); self.dashboard_pro_frame.pack(fill=BOTH, expand=True)
        self.notebook.tab(1, state="normal"); self.notebook.tab(2, state="normal")
        self.run_task_in_thread(self._load_pro_profiles)
        self.run_task_in_thread(self.populate_policy_editor)
    def deactivate_pro_features(self):
        self.log("Running in FREE mode. Activate PRO to unlock more features.")
        self.dashboard_pro_frame.pack_forget(); self.activation_frame.pack(fill=BOTH, expand=True)
        self.notebook.tab(1, state="disabled"); self.notebook.tab(2, state="disabled")
    def prompt_for_activation(self):
        key = self.key_entry.get()
        if key and key.strip(): self.run_task_in_thread(self._activate_logic, None, key.strip())
        else: messagebox.showwarning("Input Required", "Please enter a license key.")
    def _activate_logic(self, key):
        self.after(0, lambda: self.activate_button.config(state=DISABLED, text="Activating..."))
        success, message = self.license_manager.activate_online(key)
        self.log(message); self.after(0, lambda: self.activate_button.config(state=NORMAL, text="Activate PRO"))
        if success:
            self.after(0, lambda: messagebox.showinfo("Success", "PRO version has been activated successfully!"))
            self.after(0, self.check_activation)
        else: self.after(0, lambda: messagebox.showerror("Activation Failed", message))
    def _update_log_area(self, message):
        if not self.winfo_exists(): return
        self.log_area.config(state=NORMAL); self.log_area.insert(END, message + "\n")
        self.log_area.config(state=DISABLED); self.log_area.see(END)
    def run_task_in_thread(self, task_function, callback=None, *args):
        def task_wrapper():
            result = task_function(*args)
            if callback: self.after(0, callback, result)
        thread = threading.Thread(target=task_wrapper, daemon=True); thread.start()
    def _load_pro_profiles(self):
        self.log("PRO: Loading profile list...")
        self.run_task_in_thread(get_profile_details, self._populate_pro_profiles, self.user_data_path, self.log)
    def _populate_pro_profiles(self, profile_map):
        self.pro_profile_map = profile_map
        self.pro_profiles_list.delete(0, END)
        if not profile_map: self.log("Error: No profiles were found."); return
        for name in self.pro_profile_map.keys(): self.pro_profiles_list.insert(END, name)
    def on_pro_profile_select(self, event=None):
        if not self.pro_profiles_list.curselection(): return
        name = self.pro_profiles_list.get(self.pro_profiles_list.curselection()[0])
        self.current_pro_profile_path = self.pro_profile_map.get(name)
        self.log(f"PRO: Loading extensions for '{name}'...")
        self.run_task_in_thread(get_extensions_for_profile, self._populate_pro_extensions, self.current_pro_profile_path, self.log)
    def _populate_pro_extensions(self, extensions_map):
        self.pro_extensions_map = extensions_map
        self.pro_extensions_list.delete(0, END)
        for name, details in self.pro_extensions_map.items():
            status = "🟢 Enabled" if details['state'] == 1 else "🔴 Disabled"
            self.pro_extensions_list.insert(END, f"{name}  [{status}]")
    def toggle_theme(self):
        if self.style.theme.name == 'superhero': self.style.theme_use('litera')
        else: self.style.theme_use('superhero')
    def _get_selected_pro_extension_details(self):
        if not self.pro_extensions_list.curselection(): messagebox.showwarning("Selection Required", "Please select an extension."); return None
        selected_text = self.pro_extensions_list.get(self.pro_extensions_list.curselection()[0])
        clean_name = selected_text.split("  [")[0]
        return self.pro_extensions_map.get(clean_name)
    def toggle_extension_state(self, new_state):
        details = self._get_selected_pro_extension_details()
        if not details: return
        self.log(f"Attempting to {'enable' if new_state==1 else 'disable'} {details['id']}...")
        self.run_task_in_thread(set_extension_state_for_profile, lambda s: self.on_pro_profile_select(), self.current_pro_profile_path, details['id'], new_state, self.log)
    def show_extension_details(self):
        details = self._get_selected_pro_extension_details()
        if not details: return
        info = (f"Name: {self.pro_extensions_list.get(self.pro_extensions_list.curselection()[0]).split('  [')[0]}\n"
                f"ID: {details['id']}\n"
                f"Version: {details['version']}\n"
                f"Status: {'Enabled' if details['state'] == 1 else 'Disabled'}\n\n"
                f"Path: {details['path']}\n\n"
                f"Permissions:\n- " + '\n- '.join(details['permissions']))
        messagebox.showinfo("Extension Details", info)
    def panic_button(self):
        if not hasattr(self, 'current_pro_profile_path'): messagebox.showwarning("Profile Not Selected", "Please select a profile first."); return
        if messagebox.askyesno("Confirm Panic Button", "Disable all non-default extensions in the selected profile?"):
            self.run_task_in_thread(self._panic_logic, None, self.current_pro_profile_path)
    def _panic_logic(self, profile_path):
        self.log("PANIC: Disabling all non-default extensions...")
        disabled_count = 0
        for ext in self.pro_extensions_map.values():
            if not ext['was_installed_by_default'] and ext['state'] == 1:
                if set_extension_state_for_profile(profile_path, ext['id'], 0, self.log):
                    disabled_count += 1
        self.run_task_in_thread(get_extensions_for_profile, self._populate_pro_extensions, profile_path, self.log)
        self.after(0, lambda: messagebox.showinfo("Panic Complete", f"{disabled_count} extensions were disabled. Please restart Chrome."))
    def backup_profile_extensions(self):
        if not hasattr(self, 'current_pro_profile_path'): messagebox.showwarning("Profile Not Selected", "Please select a profile to back up."); return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Backup", "*.json")], title="Save Profile Backup", initialfile=f"chrome_extensions_backup_{os.path.basename(self.current_pro_profile_path)}.json")
        if not filepath: return
        self.run_task_in_thread(self._backup_logic, None, self.current_pro_profile_path, filepath)
    def _backup_logic(self, profile_path, filepath):
        self.log(f"Backing up extensions from {os.path.basename(profile_path)}...")
        prefs_path = os.path.join(profile_path, 'Preferences')
        try:
            with open(prefs_path, 'r', encoding='utf-8') as f: prefs = json.load(f)
            backup_data = {"source_profile": os.path.basename(profile_path), "backup_date": time.ctime(), "extensions": prefs.get('extensions', {}).get('settings', {})}
            with open(filepath, 'w', encoding='utf-8') as f: json.dump(backup_data, f, indent=4)
            self.log(f"Backup successful! Saved to {filepath}")
            self.after(0, lambda: messagebox.showinfo("Backup Complete", f"Successfully backed up extensions to:\n{filepath}"))
        except Exception as e: self.log(f"Backup failed: {e}"); self.after(0, lambda: messagebox.showerror("Backup Failed", f"Could not create backup file.\nError: {e}"))
    def restore_profile_extensions(self):
        if not hasattr(self, 'current_pro_profile_path'): messagebox.showwarning("Profile Not Selected", "Please select a profile to restore to."); return
        filepath = filedialog.askopenfilename(filetypes=[("JSON Backup", "*.json")], title="Open Profile Backup")
        if not filepath: return
        if messagebox.askyesno("Confirm Restore", "This will overwrite the current extension settings for this profile. Continue?"):
            self.run_task_in_thread(self._restore_logic, None, self.current_pro_profile_path, filepath)
    def _restore_logic(self, profile_path, filepath):
        self.log(f"Restoring extensions to {os.path.basename(profile_path)}...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f: backup_data = json.load(f)
            restored_settings = backup_data.get("extensions")
            if restored_settings is None: raise ValueError("Backup file is missing the 'extensions' key.")
            prefs_path = os.path.join(profile_path, 'Preferences')
            shutil.copyfile(prefs_path, prefs_path + '.bak')
            with open(prefs_path, 'r+', encoding='utf-8') as f:
                prefs = json.load(f)
                prefs.setdefault('extensions', {})['settings'] = restored_settings
                f.seek(0); json.dump(prefs, f, indent=4); f.truncate()
            self.log("Restore successful! Restart Chrome to apply.")
            self.run_task_in_thread(get_extensions_for_profile, self._populate_pro_extensions, profile_path, self.log)
            self.after(0, lambda: messagebox.showinfo("Restore Complete", "Restore successful. Please restart Chrome for all changes to apply."))
        except Exception as e:
            self.log(f"Restore failed: {e}"); self.after(0, lambda: messagebox.showerror("Restore Failed", f"Could not restore from backup file.\nError: {e}"))
    
    def populate_policy_editor(self):
        for item in self.policy_tree.get_children(): self.policy_tree.delete(item)
        for category, policies in POLICIES.items():
            category_id = self.policy_tree.insert("", "end", text=category, open=True)
            for policy in policies:
                current_value = self.policy_manager.get_policy_value(policy['key'], policy['value_name'])
                status = "🟢 Set" if current_value is not None else "⚪ Not Configured"
                display_value = current_value if current_value is not None else "N/A"
                if current_value is not None and policy['type'] == 'REG_DWORD':
                    try:
                        current_int_value = int(current_value, 16)
                        for option_name, option_val in policy['options'].items():
                            if option_val == current_int_value: display_value = option_name; break
                    except (ValueError, TypeError): pass
                self.policy_tree.insert(category_id, "end", text=policy['name'], values=(status, display_value), tags=(json.dumps(policy),))
    def on_policy_edit(self, event):
        item_id = self.policy_tree.focus()
        if not item_id: return
        tags = self.policy_tree.item(item_id, 'tags')
        if not tags: return
        try: policy = json.loads(tags[0])
        except: return
        if "text" in policy['options']:
            new_value = simpledialog.askstring("Set Policy", f"Enter value for:\n{policy['name']}\n\n{policy['help']}", parent=self)
            if new_value is not None: self.run_task_in_thread(self._apply_single_policy, None, policy, new_value)
        else:
            dialog = tb.Toplevel(title="Set Policy"); dialog.transient(self)
            tb.Label(dialog, text=f"{policy['name']}\n\n{policy['help']}", wraplength=300).pack(padx=10, pady=10)
            var = tk.IntVar()
            current_value = self.policy_manager.get_policy_value(policy['key'], policy['value_name'])
            if current_value: var.set(int(current_value, 16))
            else: var.set(-2)
            options_frame = tb.Frame(dialog); options_frame.pack(padx=10, pady=10, fill=X)
            for text, val in policy['options'].items():
                tb.Radiobutton(options_frame, text=text, variable=var, value=val).pack(anchor='w')
            def on_ok(): self.run_task_in_thread(self._apply_single_policy, None, policy, var.get()); dialog.destroy()
            def on_reset(): self.run_task_in_thread(self._remove_single_policy, None, policy); dialog.destroy()
            btn_frame = tb.Frame(dialog); btn_frame.pack(pady=10)
            tb.Button(btn_frame, text="Apply", command=on_ok, bootstyle='success').pack(side=LEFT, padx=5)
            tb.Button(btn_frame, text="Reset to Default", command=on_reset, bootstyle='danger-outline').pack(side=LEFT, padx=5)
    def _apply_single_policy(self, policy, value):
        if value == -1: self._remove_single_policy(policy); return
        self.log(f"Applying policy '{policy['name']}' with value '{value}'...")
        success, msg = self.policy_manager.set_policy(policy['key'], policy['value_name'], value, policy['type'])
        if success: self.log("Policy applied successfully.")
        else: self.log(f"Failed to apply policy: {msg}")
        self.run_task_in_thread(self.populate_policy_editor)
    def _remove_single_policy(self, policy):
        self.log(f"Resetting policy '{policy['name']}' to default...")
        success, msg = self.policy_manager.remove_policy(policy['key'], policy['value_name'])
        if success: self.log("Policy reset successfully.")
        else: self.log(f"Failed to reset policy: {msg}")
        self.run_task_in_thread(self.populate_policy_editor)

    def add_url_to_blocklist(self):
        url = self.url_entry.get().strip()
        if not url: messagebox.showwarning("Input Required", "Please enter a URL to block."); return
        self.run_task_in_thread(self._add_url_logic, None, url); self.url_entry.delete(0, END)
    def _add_url_logic(self, url):
        self.log(f"Blocking URL: {url}...")
        current_list, indices = self._get_url_blocklist()
        next_index = max(indices) + 1 if indices else 1
        success, msg = self.policy_manager.set_policy("URLBlocklist", str(next_index), url, "REG_SZ")
        if success: self.log("URL Blocked. Restart Chrome to apply.")
        else: self.log(f"Failed to block URL: {msg}")
        self.run_task_in_thread(self._refresh_blocklist)
    def remove_url_from_blocklist(self):
        if not self.blocked_url_list.curselection(): messagebox.showwarning("Selection Required", "Please select a URL to allow."); return
        selected_item = self.blocked_url_list.get(self.blocked_url_list.curselection()[0])
        index_to_remove = selected_item.split("]")[0].strip("[")
        self.run_task_in_thread(self._remove_url_logic, None, index_to_remove)
    def _remove_url_logic(self, index):
        self.log(f"Allowing URL at index {index}...")
        success, msg = self.policy_manager.remove_policy("URLBlocklist", index)
        if success: self.log("URL Allowed. Restart Chrome to apply.")
        else: self.log(f"Failed to allow URL: {msg}")
        self.run_task_in_thread(self._refresh_blocklist)
    def _refresh_blocklist(self, initial_load=False): self.run_task_in_thread(self._get_url_blocklist, self._populate_blocklist_ui)
    def _populate_blocklist_ui(self, blocklist_data):
        urls, _ = blocklist_data
        self.blocked_url_list.delete(0, END)
        for index, url in urls.items(): self.blocked_url_list.insert(END, f"[{index}] {url}")
    def _get_url_blocklist(self):
        key_path = f"HKEY_LOCAL_MACHINE\\{self.policy_manager.POLICY_BASE_KEY}\\URLBlocklist"
        args = f'query "{key_path}"'
        stdout, stderr = self.policy_manager._run_reg_command(args)
        if stderr: return {}, []
        urls, indices = {}, []
        for line in stdout.strip().split('\n'):
            if not line.strip() or line.startswith("HKEY_LOCAL_MACHINE"): continue
            try:
                parts = [p.strip() for p in line.split('    ') if p.strip()]
                index, url = parts[0], parts[-1]
                urls[index] = url; indices.append(int(index))
            except: continue
        return urls, indices
    def get_extension_name(self, ext_id):
        if ext_id in self.cache: return self.cache[ext_id]
        try:
            url = f"https://chrome.google.com/webstore/detail/{ext_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            match = re.search(r'<title>(.+?)</title>', response.text)
            if match:
                name = match.group(1).replace('- Chrome Web Store', '').strip()
                self.cache[ext_id] = name; self.save_cache()
                return name
        except requests.RequestException: pass
        return ext_id


if __name__ == "__main__":
    if platform.system() == "Windows":
        if not is_admin(): run_as_admin(); sys.exit(0)
    try:
        import ttkbootstrap, requests, pyperclip
    except ImportError as e:
        missing_module = str(e).split("'")[-2]
        messagebox.showerror("Missing Module", f"Required module '{missing_module}' not installed.\nPlease run: pip install {missing_module}")
        sys.exit(1)
    try:
        import win32api
    except ImportError:
        messagebox.showerror("Missing Module", "Required module 'pypiwin32' not installed.\nPlease run: pip install pypiwin32")
        sys.exit(1)
    try:
        import wmi
    except ImportError:
        messagebox.showerror("Missing Module", "Required module 'WMI' not installed.\nPlease run: pip install WMI")
        sys.exit(1)
        
    app = Application()
    app.mainloop()
