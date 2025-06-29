import tkinter as tk
from tkinter import messagebox, scrolledtext
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import os
import json
import shutil
import platform
import sys
import threading
import requests
import re

# ==============================================================================
# Chrome Extension Manager v3.0
# Description: A user-friendly GUI tool to manage Chrome extensions across
#              multiple profiles. Easily sync (install) or remove extensions
#              for all profiles at once.
#
# Requirements: pip install ttkbootstrap requests
#
# Important: For changes to take effect after an operation, you must fully
#            restart Google Chrome.
# ==============================================================================

# --- Configuration ---
CURRENT_VERSION = "3.0"
# !!! IMPORTANT !!!
# Replace this URL with the raw content link to your script on GitHub.
# For example: "https://raw.githubusercontent.com/YourUsername/YourRepo/main/app.py"
UPDATE_URL = "YOUR_GITHUB_RAW_FILE_URL_HERE"


# --- Backend Logic ---

def get_chrome_user_data_path():
    """Returns the path to the Chrome User Data folder based on the OS."""
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data')
    elif system == "Darwin":
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Google', 'Chrome')
    elif system == "Linux":
        return os.path.join(os.path.expanduser('~'), '.config', 'google-chrome')
    else:
        return None

def get_profile_details(user_data_path, log_callback):
    """Scans and returns the actual names and paths of all profiles."""
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
            original_name = profile_name
            counter = 2
            while profile_name in profile_details:
                profile_name = f"{original_name} ({counter})"
                counter += 1
            profile_details[profile_name] = profile_path
    return dict(sorted(profile_details.items()))

def get_extensions_for_profile(profile_path, log_callback):
    """Returns a dictionary of extension names and their IDs for a given profile."""
    extensions = {}
    extensions_dir = os.path.join(profile_path, 'Extensions')
    if not os.path.exists(extensions_dir): return {}
    for ext_id in os.listdir(extensions_dir):
        ext_path = os.path.join(extensions_dir, ext_id)
        if not os.path.isdir(ext_path): continue
        version_dirs = [d for d in os.listdir(ext_path) if os.path.isdir(os.path.join(ext_path, d))]
        if not version_dirs: continue
        latest_version_dir = sorted(version_dirs)[-1]
        manifest_path = os.path.join(ext_path, latest_version_dir, 'manifest.json')
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    ext_name = manifest.get('name', 'Unnamed Extension')
                    if ext_name.startswith('__MSG_') and 'default_locale' in manifest:
                        locale = manifest['default_locale']
                        messages_path = os.path.join(ext_path, latest_version_dir, '_locales', locale, 'messages.json')
                        if os.path.exists(messages_path):
                            with open(messages_path, 'r', encoding='utf-8') as mf:
                                messages = json.load(mf)
                                key = ext_name.replace('__MSG_', '').replace('__', '')
                                if key in messages: ext_name = messages[key].get('message', ext_name)
                    original_name = ext_name
                    counter = 2
                    while ext_name in extensions:
                        ext_name = f"{original_name} ({counter})"
                        counter += 1
                    extensions[ext_name] = ext_id
            except Exception as e: log_callback(f"Error reading manifest for {ext_id}: {e}")
    return dict(sorted(extensions.items()))


# --- GUI Application ---

class Application(tb.Window):
    def __init__(self):
        super().__init__(themename="litera")
        self.title(f"Chrome Extension Manager v{CURRENT_VERSION}")
        self.geometry("950x700")
        self.minsize(800, 550)
        self.user_data_path = get_chrome_user_data_path()
        self.all_profiles_map = {}
        self.create_widgets()
        if not self.user_data_path:
            messagebox.showerror("Error", "Could not find Chrome User Data folder.")
            self.destroy()
        else:
            self.run_task_in_thread(self.load_profiles_async)
            self.run_task_in_thread(self.check_for_updates)

    def log(self, message):
        """Thread-safely logs a message to the UI."""
        self.after(0, self._update_log_area, message)

    def _update_log_area(self, message):
        if not self.winfo_exists() or not self.log_area.winfo_exists(): return
        self.log_area.config(state=NORMAL)
        self.log_area.insert(END, message + "\n")
        self.log_area.config(state=DISABLED)
        self.log_area.see(END)

    def create_widgets(self):
        main_frame = tb.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)
        instruction_label = tb.Label(main_frame, text="Important: You must fully restart Chrome after any operation for changes to take effect.", bootstyle="warning", anchor="center")
        instruction_label.pack(fill=X, pady=(0, 10))

        top_frame = tb.Frame(main_frame)
        top_frame.pack(fill=BOTH, expand=True, pady=(0, 15))
        top_frame.grid_columnconfigure(0, weight=1, uniform="group1")
        top_frame.grid_columnconfigure(1, weight=2, uniform="group1")
        top_frame.grid_rowconfigure(0, weight=1)

        profiles_frame = tb.LabelFrame(top_frame, text=" 1. Select Source Profile ", padding=10)
        profiles_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        profiles_frame.grid_rowconfigure(0, weight=1); profiles_frame.grid_columnconfigure(0, weight=1)
        self.profiles_listbox = tk.Listbox(profiles_frame, exportselection=False, borderwidth=0, highlightthickness=0)
        self.profiles_listbox.grid(row=0, column=0, sticky="nsew")
        profile_scrollbar = tb.Scrollbar(profiles_frame, orient=VERTICAL, command=self.profiles_listbox.yview, bootstyle="round")
        profile_scrollbar.grid(row=0, column=1, sticky="ns"); self.profiles_listbox.config(yscrollcommand=profile_scrollbar.set)
        self.profiles_listbox.bind('<<ListboxSelect>>', self.on_profile_select)

        extensions_frame = tb.LabelFrame(top_frame, text=" 2. Select Extension to Manage ", padding=10)
        extensions_frame.grid(row=0, column=1, sticky="nsew")
        extensions_frame.grid_rowconfigure(0, weight=1); extensions_frame.grid_columnconfigure(0, weight=1)
        self.extensions_listbox = tk.Listbox(extensions_frame, exportselection=False, borderwidth=0, highlightthickness=0)
        self.extensions_listbox.grid(row=0, column=0, sticky="nsew")
        ext_scrollbar = tb.Scrollbar(extensions_frame, orient=VERTICAL, command=self.extensions_listbox.yview, bootstyle="round")
        ext_scrollbar.grid(row=0, column=1, sticky="ns"); self.extensions_listbox.config(yscrollcommand=ext_scrollbar.set)

        actions_frame = tb.LabelFrame(main_frame, text=" 3. Choose an Action ", padding=10)
        actions_frame.pack(fill=X, pady=(0, 15))
        self.install_button = tb.Button(actions_frame, text="Install to Other Profiles", command=self.install_selected_extension, state=DISABLED, bootstyle="success")
        self.install_button.pack(side=LEFT, expand=True, fill=X, padx=5)
        self.uninstall_button = tb.Button(actions_frame, text="Uninstall from ALL Profiles", command=self.uninstall_selected_extension, state=DISABLED, bootstyle="danger")
        self.uninstall_button.pack(side=LEFT, expand=True, fill=X, padx=5)

        log_frame = tb.LabelFrame(main_frame, text="Log", padding=10)
        log_frame.pack(fill=BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state=DISABLED, borderwidth=0, highlightthickness=0)
        self.log_area.pack(fill=BOTH, expand=True)
        
        # Status bar for updates
        self.status_bar = tb.Frame(self, padding=(5, 2))
        self.status_bar.pack(side=BOTTOM, fill=X)
        self.update_label = tb.Label(self.status_bar, text="")
        self.update_label.pack(side=LEFT, padx=5)
        self.update_button = tb.Button(self.status_bar, text="Update Now", bootstyle="info", command=self.prompt_update)

    def load_profiles_async(self):
        """Loads profile details in the background."""
        self.log("Disclaimer: This is an unofficial tool. Use at your own risk. The developer is not responsible for any data loss or damage.")
        self.log("Always back up your Chrome profile data before making major changes.")
        self.log("-" * 50)
        self.log("Searching for Chrome profiles...")
        self.all_profiles_map = get_profile_details(self.user_data_path, self.log)
        self.after(0, self.populate_profiles_list)

    def populate_profiles_list(self):
        if not self.winfo_exists(): return
        self.profiles_listbox.delete(0, END)
        if not self.all_profiles_map:
            self.log("No Chrome profiles found.")
            messagebox.showerror("Error", "No Chrome profiles found.")
            return
        for name in self.all_profiles_map.keys(): self.profiles_listbox.insert(END, name)
        self.log(f"Found {len(self.all_profiles_map)} profiles. Please select one.")

    def on_profile_select(self, event=None):
        if not self.profiles_listbox.curselection(): return
        selected_profile_name = self.profiles_listbox.get(self.profiles_listbox.curselection()[0])
        selected_profile_path = self.all_profiles_map.get(selected_profile_name)
        if not selected_profile_path: return
        self.log(f"\nLoading extensions for '{selected_profile_name}'...")
        self.extensions_listbox.delete(0, END)
        self.run_task_in_thread(self.load_extensions_async, selected_profile_path)

    def load_extensions_async(self, profile_path):
        """Loads extensions for a selected profile."""
        self.extensions_map = get_extensions_for_profile(profile_path, self.log)
        self.after(0, self.populate_extensions_listbox)

    def populate_extensions_listbox(self):
        if not self.winfo_exists(): return
        self.extensions_listbox.delete(0, END)
        if not self.extensions_map:
            self.log("No extensions found in this profile.")
            return
        for display_name in self.extensions_map.keys(): self.extensions_listbox.insert(END, display_name)
        self.log(f"Found {len(self.extensions_map)} extensions.")

    def run_task_in_thread(self, task_function, *args):
        self.install_button.config(state=DISABLED)
        self.uninstall_button.config(state=DISABLED)
        thread = threading.Thread(target=self.check_and_run, args=(task_function, *args), daemon=True)
        thread.start()

    def check_and_run(self, task_function, *args):
        """Wrapper to run a task and re-enable buttons upon completion."""
        task_function(*args)
        if self.profiles_listbox.curselection():
             self.after(0, self.install_button.config, {'state': NORMAL})
             self.after(0, self.uninstall_button.config, {'state': NORMAL})

    def install_selected_extension(self):
        if not self.extensions_listbox.curselection(): messagebox.showwarning("Selection Required", "Please select an extension to install."); return
        display_name = self.extensions_listbox.get(self.extensions_listbox.curselection()[0])
        source_profile_name = self.profiles_listbox.get(self.profiles_listbox.curselection()[0])
        if messagebox.askyesno("Confirm Install", f"Are you sure you want to install '{display_name}' to all other profiles?"):
            self.run_task_in_thread(self._install_logic, display_name)

    def _install_logic(self, display_name):
        ext_id = self.extensions_map[display_name]
        source_profile_name = self.profiles_listbox.get(self.profiles_listbox.curselection()[0])
        source_profile_path = self.all_profiles_map[source_profile_name]
        self.log("\n" + "="*20 + f"\nStarting installation of '{display_name}'...")
        source_ext_folder = os.path.join(source_profile_path, 'Extensions', ext_id)
        install_count = 0
        for profile_name, profile_path in self.all_profiles_map.items():
            if profile_path == source_profile_path: continue
            self.log(f"-> Installing to '{profile_name}'...")
            target_ext_folder = os.path.join(profile_path, 'Extensions', ext_id)
            if os.path.exists(target_ext_folder): self.log("    - Already exists. Skipping."); continue
            try: shutil.copytree(source_ext_folder, target_ext_folder); self.log("    - Copied successfully."); install_count += 1
            except Exception as e: self.log(f"    - Error: {e}")
        final_msg = f"Successfully installed '{display_name}' to {install_count} other profiles."
        self.log(f"\nFinished! {final_msg}")
        self.after(0, lambda: messagebox.showinfo("Task Complete - Restart Required", f"{final_msg}\n\nPlease fully close and restart Google Chrome for changes to take effect."))

    def uninstall_selected_extension(self):
        if not self.extensions_listbox.curselection(): messagebox.showwarning("Selection Required", "Please select an extension to uninstall."); return
        display_name = self.extensions_listbox.get(self.extensions_listbox.curselection()[0])
        if messagebox.askyesno("Confirm Uninstall", f"Are you sure you want to uninstall '{display_name}' from ALL profiles?\n\nThis action cannot be undone.", parent=self):
            self.run_task_in_thread(self._uninstall_logic, display_name)

    def _uninstall_logic(self, display_name):
        ext_id = self.extensions_map[display_name]
        self.log("\n" + "="*20 + f"\nStarting uninstallation of '{display_name}'...")
        uninstall_count = 0
        for profile_name, profile_path in self.all_profiles_map.items():
            self.log(f"-> Checking profile '{profile_name}'...")
            extension_folder_path = os.path.join(profile_path, 'Extensions', ext_id)
            if os.path.exists(extension_folder_path):
                try: shutil.rmtree(extension_folder_path); self.log("    - Extension folder deleted."); uninstall_count += 1
                except Exception as e: self.log(f"    - Error deleting folder: {e}")
            else: self.log("    - Extension not found in this profile.")
        final_msg = f"Successfully uninstalled '{display_name}' from {uninstall_count} profiles."
        self.log(f"\nFinished! {final_msg}")
        self.after(0, lambda: messagebox.showinfo("Task Complete - Restart Required", f"{final_msg}\n\nPlease fully close and restart Google Chrome for changes to take effect."))

    # --- Update Logic ---
    def check_for_updates(self):
        """Checks GitHub for a new version of the script."""
        if UPDATE_URL == "YOUR_GITHUB_RAW_FILE_URL_HERE":
             self.log("\nUpdate Check: Please set the UPDATE_URL in the script file.")
             return
        try:
            self.log("\nChecking for updates...")
            response = requests.get(UPDATE_URL, timeout=5)
            response.raise_for_status()
            remote_script = response.text
            match = re.search(r'CURRENT_VERSION\s*=\s*["\'](\d+\.\d+)["\']', remote_script)
            if match:
                remote_version = match.group(1)
                if float(remote_version) > float(CURRENT_VERSION):
                    self.log(f"Update found! New version: {remote_version}")
                    self.after(0, self.show_update_notification, remote_version)
                else:
                    self.log("You are using the latest version.")
            else:
                self.log("Could not determine remote version.")
        except Exception as e:
            self.log(f"Update check failed: {e}")

    def show_update_notification(self, version):
        """Makes the update notification visible in the UI."""
        self.update_label.config(text=f"Update Available: v{version}")
        self.update_button.pack(side=RIGHT, padx=5)

    def prompt_update(self):
        """Asks the user to confirm the update."""
        if messagebox.askyesno("Confirm Update", "A new version is available. Do you want to update now?\nThe application will restart."):
            self.update_button.config(state=DISABLED, text="Updating...")
            self.run_task_in_thread(self.perform_update)

    def perform_update(self):
        """Downloads the new script and replaces the current one."""
        try:
            response = requests.get(UPDATE_URL, timeout=10)
            response.raise_for_status()
            
            script_path = os.path.realpath(sys.argv[0])
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            self.after(0, self.restart_app)
        except Exception as e:
            self.after(0, messagebox.showerror, "Update Failed", f"Could not update the application.\nError: {e}")
            self.after(0, self.update_button.config, {'state': NORMAL, 'text': "Update Now"})

    def restart_app(self):
        """Restarts the application after a successful update."""
        messagebox.showinfo("Update Successful", "The application has been updated and will now restart.")
        os.execl(sys.executable, sys.executable, *sys.argv)

if __name__ == "__main__":
    try:
        import ttkbootstrap
        import requests
    except ImportError as e:
        missing_module = str(e).split("'")[-2]
        print(f"Error: Required module '{missing_module}' is not installed.")
        print(f"Please install it by running: pip install {missing_module}")
        sys.exit(1)
        
    app = Application()
    app.mainloop()
