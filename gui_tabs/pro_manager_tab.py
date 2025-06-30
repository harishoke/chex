import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import os
import json # For backup/restore logic
import time # For backup logic
import shutil # For backup/restore logic

# Assuming profile_utils.py is in the parent directory or accessible in PYTHONPATH
from profile_utils import get_profile_details, get_extensions_for_profile, set_extension_state_for_profile

class ProManagerTab(tb.Frame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, padding=10, **kwargs)
        self.app = app_instance  # Reference to the main Application instance
        self.current_pro_profile_path = None
        self.pro_profile_map = {}
        self.pro_extensions_map = {}
        self._create_widgets()

    def _create_widgets(self):
        top_frame = tb.Frame(self)
        top_frame.pack(fill=BOTH, expand=True, pady=5)
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=2)
        top_frame.grid_rowconfigure(0, weight=1)

        # Left Panel: Profile List & Backup/Restore
        left_panel = tb.Frame(top_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        profiles_frame = tb.LabelFrame(left_panel, text="1. Select Profile")
        profiles_frame.pack(fill=BOTH, expand=True)
        self.pro_profiles_list = tk.Listbox(profiles_frame, exportselection=False)
        self.pro_profiles_list.pack(fill=BOTH, expand=True)
        self.pro_profiles_list.bind('<<ListboxSelect>>', self.on_pro_profile_select)

        backup_frame = tb.Frame(left_panel)
        backup_frame.pack(fill=X, pady=5)
        tb.Button(backup_frame, text="Backup Profile", bootstyle="info-outline", command=self.backup_profile_extensions).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(backup_frame, text="Restore Profile", bootstyle="info-outline", command=self.restore_profile_extensions).pack(side=LEFT, expand=True, fill=X, padx=2)

        # Right Panel: Extensions List & Actions
        right_panel = tb.Frame(top_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")

        ext_frame = tb.LabelFrame(right_panel, text="2. Manage Extensions")
        ext_frame.pack(fill=BOTH, expand=True)
        self.pro_extensions_list = tk.Listbox(ext_frame, exportselection=False)
        self.pro_extensions_list.pack(fill=BOTH, expand=True)

        pro_actions_frame = tb.Frame(right_panel)
        pro_actions_frame.pack(fill=X, pady=5)
        tb.Button(pro_actions_frame, text="Enable", bootstyle="success-outline", command=lambda: self.toggle_extension_state_ui(1)).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(pro_actions_frame, text="Disable", bootstyle="warning-outline", command=lambda: self.toggle_extension_state_ui(0)).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(pro_actions_frame, text="Details", bootstyle="secondary-outline", command=self.show_extension_details).pack(side=LEFT, expand=True, fill=X, padx=2)
        tb.Button(pro_actions_frame, text="Panic Button", bootstyle="danger", command=self.panic_button_ui).pack(side=LEFT, expand=True, fill=X, padx=2)

    def load_initial_data(self):
        self.app.log("PRO Manager: Loading profile list...")
        # Call get_profile_details via app's run_task_in_thread
        self.app.run_task_in_thread(get_profile_details, self._populate_pro_profiles_ui, self.app.user_data_path, self.app.log)

    def _populate_pro_profiles_ui(self, profile_map):
        self.pro_profile_map = profile_map
        self.pro_profiles_list.delete(0, END)
        if not profile_map:
            self.app.log("PRO Manager Error: No profiles were found.")
            return
        for name in self.pro_profile_map.keys():
            self.pro_profiles_list.insert(END, name)
        self.app.log(f"PRO Manager: Loaded {len(profile_map)} profiles.")

    def on_pro_profile_select(self, event=None):
        if not self.pro_profiles_list.curselection():
            return
        name = self.pro_profiles_list.get(self.pro_profiles_list.curselection()[0])
        self.current_pro_profile_path = self.pro_profile_map.get(name)
        if self.current_pro_profile_path:
            self.app.log(f"PRO Manager: Loading extensions for '{name}'...")
            self.app.run_task_in_thread(get_extensions_for_profile, self._populate_pro_extensions_ui, self.current_pro_profile_path, self.app.log)
        else:
            self.app.log(f"PRO Manager Error: Could not find path for profile '{name}'.")
            self.pro_extensions_list.delete(0, END) # Clear extensions list

    def _populate_pro_extensions_ui(self, extensions_map):
        self.pro_extensions_map = extensions_map
        self.pro_extensions_list.delete(0, END)
        if not extensions_map:
            self.app.log(f"PRO Manager: No extensions found for {os.path.basename(self.current_pro_profile_path or 'current profile')}.")
            return
        for name, details in self.pro_extensions_map.items():
            status = "🟢 Enabled" if details['state'] == 1 else "🔴 Disabled"
            self.pro_extensions_list.insert(END, f"{name}  [{status}]")
        self.app.log(f"PRO Manager: Loaded {len(extensions_map)} extensions for {os.path.basename(self.current_pro_profile_path)}.")

    def _get_selected_pro_extension_details_from_ui(self):
        if not self.pro_extensions_list.curselection():
            messagebox.showwarning("Selection Required", "Please select an extension.", parent=self)
            return None
        selected_text = self.pro_extensions_list.get(self.pro_extensions_list.curselection()[0])
        clean_name = selected_text.split("  [")[0] # Extract name part
        return self.pro_extensions_map.get(clean_name)

    def toggle_extension_state_ui(self, new_state):
        details = self._get_selected_pro_extension_details_from_ui()
        if not details:
            return
        if not self.current_pro_profile_path:
            messagebox.showerror("Error", "No profile selected or profile path is invalid.", parent=self)
            return

        self.app.log(f"PRO Manager: Attempting to {'enable' if new_state==1 else 'disable'} extension {details['id']}...")
        # The callback for set_extension_state_for_profile will refresh the extension list
        self.app.run_task_in_thread(set_extension_state_for_profile,
                                    lambda success: self.on_pro_profile_select() if success else None,
                                    self.current_pro_profile_path, details['id'], new_state, self.app.log)

    def show_extension_details(self):
        details = self._get_selected_pro_extension_details_from_ui()
        if not details:
            return

        selected_list_item = self.pro_extensions_list.get(self.pro_extensions_list.curselection()[0])
        display_name = selected_list_item.split("  [")[0]

        info = (f"Name: {display_name}\n"
                f"ID: {details['id']}\n"
                f"Version: {details['version']}\n"
                f"Status: {'Enabled' if details['state'] == 1 else 'Disabled'}\n\n"
                f"Path: {details['path']}\n\n"
                f"Permissions:\n- " + ('\n- '.join(details['permissions']) if details['permissions'] else "None"))
        messagebox.showinfo("Extension Details", info, parent=self)

    def panic_button_ui(self):
        if not self.current_pro_profile_path:
            messagebox.showwarning("Profile Not Selected", "Please select a profile first.", parent=self)
            return
        if messagebox.askyesno("Confirm Panic Button", "This will disable all non-default, currently enabled extensions in the selected profile. Are you sure?", parent=self):
            self.app.run_task_in_thread(self._panic_logic_task, None, self.current_pro_profile_path)

    def _panic_logic_task(self, profile_path):
        self.app.log("PRO Manager PANIC: Disabling all non-default enabled extensions...")
        disabled_count = 0
        # Iterate over a copy of values if modifying the underlying map through set_extension_state_for_profile
        # or ensure the map is refreshed before this loop if state changes are reflected immediately.
        # For simplicity, assuming pro_extensions_map is reasonably up-to-date before panic.
        extensions_to_disable = [ext for ext in self.pro_extensions_map.values() if not ext['was_installed_by_default'] and ext['state'] == 1]

        for ext_details in extensions_to_disable:
            self.app.log(f"PANIC: Disabling {ext_details['id']}...")
            success = set_extension_state_for_profile(profile_path, ext_details['id'], 0, self.app.log)
            if success:
                disabled_count += 1

        # Refresh the extensions list in the UI after all operations
        self.app.run_task_in_thread(get_extensions_for_profile, self._populate_pro_extensions_ui, profile_path, self.app.log)
        self.app.after(0, lambda: messagebox.showinfo("Panic Complete", f"{disabled_count} extensions were disabled. Please restart Chrome if it was running.", parent=self.app))


    def backup_profile_extensions(self):
        if not self.current_pro_profile_path:
            messagebox.showwarning("Profile Not Selected", "Please select a profile to back up its extensions.", parent=self)
            return

        profile_folder_name = os.path.basename(self.current_pro_profile_path)
        initial_filename = f"chrome_extensions_backup_{profile_folder_name}_{time.strftime('%Y%m%d')}.json"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Backup", "*.json")],
            title="Save Profile Extensions Backup",
            initialfile=initial_filename,
            parent=self
        )
        if not filepath:
            return # User cancelled

        self.app.run_task_in_thread(self._backup_logic_task, None, self.current_pro_profile_path, filepath)

    def _backup_logic_task(self, profile_path, filepath):
        self.app.log(f"PRO Manager: Backing up extensions from {os.path.basename(profile_path)} to {filepath}...")
        prefs_path = os.path.join(profile_path, 'Preferences')
        if not os.path.exists(prefs_path):
            self.app.log(f"Backup Error: Preferences file not found at {prefs_path}")
            self.app.after(0, lambda: messagebox.showerror("Backup Failed", f"Preferences file not found for the selected profile.", parent=self.app))
            return

        try:
            with open(prefs_path, 'r', encoding='utf-8') as f:
                prefs = json.load(f)

            # Ensure extensions and settings keys exist to avoid KeyError
            extensions_settings = prefs.get('extensions', {}).get('settings', {})

            backup_data = {
                "source_profile_folder": os.path.basename(profile_path),
                "backup_date": time.ctime(),
                "extensions_settings": extensions_settings # Store the 'settings' dict directly
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=4)

            self.app.log(f"Backup successful! Saved to {filepath}")
            self.app.after(0, lambda: messagebox.showinfo("Backup Complete", f"Successfully backed up extensions settings to:\n{filepath}", parent=self.app))
        except json.JSONDecodeError as e:
            self.app.log(f"Backup failed: Error decoding Preferences JSON. {e}")
            self.app.after(0, lambda: messagebox.showerror("Backup Failed", f"Could not read Preferences file (JSON error).\nError: {e}", parent=self.app))
        except IOError as e:
            self.app.log(f"Backup failed: IOError. {e}")
            self.app.after(0, lambda: messagebox.showerror("Backup Failed", f"Could not write backup file.\nError: {e}", parent=self.app))
        except Exception as e:
            self.app.log(f"Backup failed: Unexpected error. {e}")
            self.app.after(0, lambda: messagebox.showerror("Backup Failed", f"An unexpected error occurred during backup.\nError: {e}", parent=self.app))

    def restore_profile_extensions(self):
        if not self.current_pro_profile_path:
            messagebox.showwarning("Profile Not Selected", "Please select a profile to restore extensions to.", parent=self)
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Backup", "*.json")],
            title="Open Profile Extensions Backup",
            parent=self
        )
        if not filepath:
            return # User cancelled

        confirm_msg = (f"This will overwrite the current extension settings for profile "
                       f"'{os.path.basename(self.current_pro_profile_path)}' "
                       f"with the data from the backup file. This action cannot be undone easily.\n\n"
                       f"Are you sure you want to continue?")
        if messagebox.askyesno("Confirm Restore", confirm_msg, parent=self, icon='warning'):
            self.app.run_task_in_thread(self._restore_logic_task, None, self.current_pro_profile_path, filepath)

    def _restore_logic_task(self, profile_path, backup_filepath):
        self.app.log(f"PRO Manager: Restoring extensions to {os.path.basename(profile_path)} from {backup_filepath}...")
        prefs_path = os.path.join(profile_path, 'Preferences')
        if not os.path.exists(prefs_path):
            self.app.log(f"Restore Error: Preferences file not found at {prefs_path}")
            self.app.after(0, lambda: messagebox.showerror("Restore Failed", "Preferences file not found for the selected profile.", parent=self.app))
            return

        # Create a backup of the current Preferences file before overwriting
        current_prefs_backup_path = prefs_path + f".before_restore_{time.strftime('%Y%m%d%H%M%S')}.bak"
        try:
            shutil.copyfile(prefs_path, current_prefs_backup_path)
            self.app.log(f"Created backup of current preferences: {current_prefs_backup_path}")
        except IOError as e:
            self.app.log(f"Warning: Could not create pre-restore backup of Preferences file: {e}")
            # Decide if you want to proceed without backup or abort
            if not messagebox.askyesno("Backup Warning", f"Could not create a backup of the current Preferences file.\nError: {e}\n\nProceed with restore anyway?", parent=self.app, icon='warning'):
                self.app.log("Restore aborted by user due to backup failure.")
                return


        try:
            with open(backup_filepath, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            restored_settings = backup_data.get("extensions_settings")
            if restored_settings is None: # Check if the key exists and is not None
                raise ValueError("Backup file is missing the 'extensions_settings' key or it's empty.")

            with open(prefs_path, 'r+', encoding='utf-8') as f:
                prefs = json.load(f) # Load current preferences
                # Ensure 'extensions' key exists, then overwrite 'settings'
                if 'extensions' not in prefs:
                    prefs['extensions'] = {}
                prefs['extensions']['settings'] = restored_settings # Overwrite with backup

                f.seek(0) # Rewind
                json.dump(prefs, f, indent=4) # Write modified data
                f.truncate() # Truncate if new data is smaller

            self.app.log("Restore successful! Restart Chrome to apply changes.")
            # Refresh the UI
            self.app.run_task_in_thread(get_extensions_for_profile, self._populate_pro_extensions_ui, profile_path, self.app.log)
            self.app.after(0, lambda: messagebox.showinfo("Restore Complete", "Restore successful. Please restart Chrome for all changes to take effect.", parent=self.app))

        except json.JSONDecodeError as e:
            self.app.log(f"Restore failed: Error decoding JSON from backup or Preferences. {e}")
            self.app.after(0, lambda: messagebox.showerror("Restore Failed", f"Could not read backup or Preferences file (JSON error).\nError: {e}", parent=self.app))
        except ValueError as e: # For specific error like missing key
            self.app.log(f"Restore failed: {e}")
            self.app.after(0, lambda: messagebox.showerror("Restore Failed", f"Invalid backup file format.\nError: {e}", parent=self.app))
        except IOError as e:
            self.app.log(f"Restore failed: IOError. {e}")
            self.app.after(0, lambda: messagebox.showerror("Restore Failed", f"Could not read/write Preferences file.\nError: {e}", parent=self.app))
        except Exception as e:
            self.app.log(f"Restore failed: Unexpected error. {e}")
            self.app.after(0, lambda: messagebox.showerror("Restore Failed", f"An unexpected error occurred during restore.\nError: {e}", parent=self.app))
            # Attempt to restore the pre-restore backup if something went wrong
            if os.path.exists(current_prefs_backup_path):
                try:
                    shutil.copyfile(current_prefs_backup_path, prefs_path)
                    self.app.log(f"Attempted to restore pre-restore backup to {prefs_path}")
                    messagebox.showwarning("Restore Attempted", "An error occurred during restore. Attempted to revert to the pre-restore state of Preferences. Please check.", parent=self.app)
                except Exception as re_e:
                    self.app.log(f"CRITICAL: Failed to restore pre-restore backup after error: {re_e}")
                    messagebox.showerror("Critical Error", "Failed to restore after an error AND failed to revert to pre-restore backup. Preferences file might be corrupt.", parent=self.app)


    def clear_data(self):
        """Clears data from the lists in this tab."""
        self.pro_profiles_list.delete(0, END)
        self.pro_extensions_list.delete(0, END)
        self.current_pro_profile_path = None
        self.pro_profile_map = {}
        self.pro_extensions_map = {}
        self.app.log("PRO Manager: Data cleared.")
