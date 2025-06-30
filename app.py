import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import os
import platform
import sys
import threading
import subprocess # Kept for main app's potential direct use, though most subprocess moved
import ctypes   # Kept for main app's potential direct use
import json     # Kept for main app's potential direct use (e.g. cache)
import requests # Kept for get_extension_name
import re       # Kept for get_extension_name
import hashlib  # Kept for main app if any direct hashing is needed outside modules
import pyperclip # Kept for main app if any direct clipboard ops are needed
import time     # Kept for main app if any direct time ops are needed
import shutil   # Kept for main app if any direct file ops are needed

# Import configurations
import config
import policy_definitions # Though POLICIES primarily used in PolicyEditorTab, good to have accessible if needed

# Import utilities
from utils import is_admin, run_as_admin, get_chrome_user_data_path, get_policy_manager # get_hardware_id is used by LicenseManager

# Import Core Logic Classes (now Modules)
from windows_policy_manager import WindowsPolicyManager
from license_manager_module import LicenseManager

# Import profile utilities (though most direct uses are now in ProManagerTab)
from profile_utils import get_profile_details, get_extensions_for_profile, set_extension_state_for_profile

# Import GUI Tabs
from gui_tabs.dashboard_tab import DashboardTab
from gui_tabs.pro_manager_tab import ProManagerTab
from gui_tabs.policy_editor_tab import PolicyEditorTab
from gui_tabs.url_blocker_tab import URLBlockerTab

# ==============================================================================
# Chrome Manager PRO v12.0 (The Stability Cut)
# Description: A complete, stable management suite for Google Chrome with a
#              feature-rich policy editor, profile management, and robust online activation.
#              This version includes critical bug fixes and over 50 new features.
#
# Requirements: pip install --upgrade ttkbootstrap requests pyperclip pypiwin32 WMI
# ==============================================================================


# --- GUI Application ---
class Application(tb.Window):
    def __init__(self):
        self.current_theme = 'superhero' # Default theme
        super().__init__(themename=self.current_theme)
        self.title(f"Chrome Manager PRO v{config.CURRENT_VERSION}")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # Initialize core components
        self.policy_manager = get_policy_manager() # Must be initialized before tabs that use it
        self.license_manager = LicenseManager(self) # Needs self for callbacks like log, deactivate_pro_features
        self.user_data_path = get_chrome_user_data_path()
        self.cache = self.load_cache() # For extension name caching

        self.create_widgets()

        if not self.policy_manager and platform.system() == "Windows": # Check if policy_manager failed on Windows
            messagebox.showerror("Initialization Error", "Failed to initialize Windows Policy Manager. Ensure you have necessary permissions or try running as administrator if not already.")
            self.destroy()
            return
        elif platform.system() != "Windows":
             messagebox.showerror("Unsupported OS", "This application currently only supports Windows for full functionality.")
             # Allow to run but some features might be disabled by the tabs themselves or policy_manager being None

        self.after(100, self.initial_load) # Delay initial load slightly

    def create_widgets(self):
        self.notebook = tb.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=(10,0))

        # Instantiate and add Dashboard Tab
        self.dashboard_tab_instance = DashboardTab(self.notebook, self)
        self.notebook.add(self.dashboard_tab_instance, text="Dashboard")

        # Instantiate and add Pro Manager Tab
        self.pro_manager_tab_instance = ProManagerTab(self.notebook, self)
        self.notebook.add(self.pro_manager_tab_instance, text="Adv. Profile Mgr (PRO)", state="disabled")

        # Instantiate and add Policy Editor Tab
        self.policy_editor_tab_instance = PolicyEditorTab(self.notebook, self)
        self.notebook.add(self.policy_editor_tab_instance, text="Adv. Policy Editor (PRO)", state="disabled")

        # Instantiate and add URL Blocker Tab
        self.url_blocker_tab_instance = URLBlockerTab(self.notebook, self)
        self.notebook.add(self.url_blocker_tab_instance, text="URL Blocker (Free)")

        # Log Area
        log_frame = tb.LabelFrame(self, text="Log", padding=10)
        log_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=8, state=DISABLED, borderwidth=0, highlightthickness=0)
        self.log_area.pack(fill=BOTH, expand=True)

    def initial_load(self):
        """Perform initial loading tasks after the UI is ready."""
        self.log(f"Chrome Manager PRO v{config.CURRENT_VERSION} starting...")
        self.run_task_in_thread(self._check_activation_logic)
        if hasattr(self, 'url_blocker_tab_instance'):
            self.url_blocker_tab_instance.load_initial_data()
        self.log("Application initialized.")


    def log(self, message):
        """Safely logs a message to the text area from any thread."""
        if hasattr(self, 'log_area') and self.log_area.winfo_exists():
            def _update_log():
                if self.log_area.winfo_exists(): # Double check before widget ops
                    self.log_area.config(state=NORMAL)
                    self.log_area.insert(END, f"{time.strftime('%H:%M:%S')} - {message}\n")
                    self.log_area.config(state=DISABLED)
                    self.log_area.see(END)
            self.after(0, _update_log) # Schedule UI update in main thread
        else:
            print(f"LOG (UI not ready): {message}")


    def check_activation(self): # Called by LicenseManager or PRO dashboard
        """Re-checks activation status and updates UI accordingly."""
        self.run_task_in_thread(self._check_activation_logic)

    def _check_activation_logic(self):
        is_active = self.license_manager.is_activated(force_online_check=True)
        if is_active:
            self.after(0, self.activate_pro_features)
        else:
            # LicenseManager's _perform_online_check might also call this if a real-time check fails
            self.after(0, self.deactivate_pro_features)


    def activate_pro_features(self):
        self.log("PRO version activated. All features unlocked.")
        if hasattr(self, 'dashboard_tab_instance'):
            self.dashboard_tab_instance.show_pro_features_active()

        # Enable Pro Manager Tab and load its data
        self.notebook.tab(1, state="normal")
        if hasattr(self, 'pro_manager_tab_instance'):
             self.pro_manager_tab_instance.load_initial_data()

        # Enable Policy Editor Tab and load its data
        self.notebook.tab(2, state="normal")
        if hasattr(self, 'policy_editor_tab_instance'):
            self.policy_editor_tab_instance.load_initial_data()

    def deactivate_pro_features(self):
        self.log("Running in FREE mode. PRO features deactivated.")
        if hasattr(self, 'dashboard_tab_instance'):
            self.dashboard_tab_instance.show_activation_needed()

        # Disable Pro Manager Tab and clear its data
        self.notebook.tab(1, state="disabled")
        if hasattr(self, 'pro_manager_tab_instance'):
            self.pro_manager_tab_instance.clear_data()

        # Disable Policy Editor Tab and clear its data
        self.notebook.tab(2, state="disabled")
        if hasattr(self, 'policy_editor_tab_instance'):
            self.policy_editor_tab_instance.clear_data()


    def prompt_for_activation(self):
        key = self.dashboard_tab_instance.get_key_entry_value() if hasattr(self, 'dashboard_tab_instance') else None
        if key and key.strip():
            self.run_task_in_thread(self._activate_logic_task, None, key.strip())
        else:
            messagebox.showwarning("Input Required", "Please enter a license key.", parent=self)

    def _activate_logic_task(self, key):
        if hasattr(self, 'dashboard_tab_instance'):
            self.dashboard_tab_instance.set_activate_button_state(DISABLED, "Activating...")

        success, message = self.license_manager.activate_online(key) # This is a blocking call in the thread
        self.log(message)

        if hasattr(self, 'dashboard_tab_instance'):
             self.dashboard_tab_instance.set_activate_button_state(NORMAL, "Activate PRO")

        if success:
            self.after(0, lambda: messagebox.showinfo("Success", "PRO version has been activated successfully!", parent=self))
            self.after(0, self._check_activation_logic) # Re-check and update UI fully
        else:
            self.after(0, lambda: messagebox.showerror("Activation Failed", message, parent=self))


    def _update_log_area(self, message): # This is the direct UI update, called by self.log via self.after
        if not self.winfo_exists(): return
        self.log_area.config(state=NORMAL)
        self.log_area.insert(END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_area.config(state=DISABLED)
        self.log_area.see(END)


    def run_task_in_thread(self, task_function, callback=None, *args):
        """
        Runs a given task in a separate thread to prevent UI freezing.
        The task_function itself should handle its own exceptions and log them.
        The callback, if provided, is run on the main thread with the result of the task.
        """
        def task_wrapper():
            try:
                result = task_function(*args)
                if callback:
                    if self.winfo_exists(): # Check if app window still exists
                        self.after(0, callback, result)
            except Exception as e:
                # Log error from the thread. Avoid direct UI calls from thread.
                self.log(f"Error in threaded task '{task_function.__name__}': {e}")
                # If callback expects a result, maybe pass an error indicator
                # if callback and self.winfo_exists():
                #    self.after(0, callback, None) # Or some error object

        thread = threading.Thread(target=task_wrapper, daemon=True)
        thread.start()


    def toggle_theme(self):
        if self.style.theme.name == 'superhero':
            self.style.theme_use('litera')
            self.current_theme = 'litera'
        else:
            self.style.theme_use('superhero')
            self.current_theme = 'superhero'
        self.log(f"Theme switched to {self.current_theme}.")

    # --- Cache and Extension Name ---
    def load_cache(self):
        if os.path.exists(config.CACHE_FILE):
            try:
                with open(config.CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.log(f"Error loading cache file: {e}")
                return {}
        return {}

    def save_cache(self):
        try:
            os.makedirs(os.path.dirname(config.CACHE_FILE), exist_ok=True)
            with open(config.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=4)
        except IOError as e:
            self.log(f"Error saving cache file: {e}")

    def get_extension_name(self, ext_id):
        """ Fetches extension name from cache or web. For UI display.
            This might be called by tabs needing extension names not in profile data.
        """
        if ext_id in self.cache:
            return self.cache[ext_id]
        try:
            # Consider moving URL to config.py if it's configurable
            url = f"https://chrome.google.com/webstore/detail/{ext_id}"
            headers = {'User-Agent': 'Mozilla/5.0'} # Basic user-agent
            response = requests.get(url, headers=headers, timeout=10) # Increased timeout
            response.raise_for_status()
            match = re.search(r'<title>(.+?)</title>', response.text, re.IGNORECASE)
            if match:
                name = match.group(1).replace('- Chrome Web Store', '').strip()
                if name: # Ensure name is not empty after stripping
                    self.cache[ext_id] = name
                    self.save_cache() # Save cache after new entry
                    return name
            self.log(f"Could not parse extension name for {ext_id} from web store page.")
        except requests.RequestException as e:
            self.log(f"Error fetching extension name for {ext_id}: {e}")
        except Exception as e: # Catch any other unexpected error
            self.log(f"Unexpected error in get_extension_name for {ext_id}: {e}")
        return ext_id # Fallback to ID if name cannot be fetched


if __name__ == "__main__":
    # Ensure admin rights on Windows before creating the app window
    if platform.system() == "Windows":
        if not is_admin():
            # This will re-launch the script with admin rights and the original script will exit.
            # No UI shown by the non-admin instance.
            run_as_admin()
            sys.exit(0) # Exit the non-admin instance

    # Dependency checks (moved before app instantiation)
    missing_modules = []
    try: import ttkbootstrap
    except ImportError: missing_modules.append("ttkbootstrap")
    try: import requests
    except ImportError: missing_modules.append("requests")
    try: import pyperclip
    except ImportError: missing_modules.append("pyperclip")

    if platform.system() == "Windows":
        try: import win32api
        except ImportError: missing_modules.append("pypiwin32")
        try: import wmi
        except ImportError: missing_modules.append("WMI")

    if missing_modules:
        # Use a simple Tkinter root for pre-app error message if ttkbootstrap is missing
        # or if other critical non-UI modules are missing.
        root = tk.Tk()
        root.withdraw() # Hide the main Tk window
        modules_str = ", ".join(missing_modules)
        messagebox.showerror("Missing Modules",
                             f"Required module(s) '{modules_str}' not installed.\n"
                             f"Please run: pip install {' '.join(missing_modules)}")
        root.destroy()
        sys.exit(1)
        
    app = Application()
    app.mainloop()
