import tkinter as tk
from tkinter import simpledialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json # For handling policy data in tags

# Assuming policy_definitions.py is accessible
import policy_definitions

class PolicyEditorTab(tb.Frame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, padding=10, **kwargs)
        self.app = app_instance # Reference to the main Application instance
        self._create_widgets()

    def _create_widgets(self):
        header = tb.Frame(self)
        header.pack(fill=X, pady=5)
        tb.Label(header, text="Apply system-wide Chrome settings. Changes affect ALL users on this computer and require a browser restart.", bootstyle='info').pack(side=LEFT)

        tree_frame = tb.Frame(self)
        tree_frame.pack(fill=BOTH, expand=True, pady=5)

        self.policy_tree = tb.Treeview(tree_frame, columns=("Status", "Value"), show="tree headings")
        self.policy_tree.heading("#0", text="Policy Name")
        self.policy_tree.heading("Status", text="Current Status")
        self.policy_tree.heading("Value", text="Configured Value")
        self.policy_tree.column("#0", width=350, stretch=True) # Adjusted width
        self.policy_tree.column("Status", width=150, anchor='center', stretch=False)
        self.policy_tree.column("Value", width=250, stretch=True) # Adjusted width

        self.policy_tree.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = tb.Scrollbar(tree_frame, orient=VERTICAL, command=self.policy_tree.yview)
        self.policy_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.policy_tree.bind("<Double-1>", self.on_policy_edit_ui)

    def load_initial_data(self):
        self.app.log("Policy Editor: Loading policies...")
        # Run populate_policy_editor_ui in a thread as it involves registry access
        self.app.run_task_in_thread(self.populate_policy_editor_ui)

    def populate_policy_editor_ui(self):
        # This method will run in a thread, so UI updates must be scheduled with self.app.after

        # Clear treeview (must be done in main thread)
        def _clear_tree():
            if not self.winfo_exists(): return
            for item in self.policy_tree.get_children():
                self.policy_tree.delete(item)
        self.app.after(0, _clear_tree)

        if not self.app.policy_manager:
            self.app.log("Policy Editor Error: Policy Manager not available.")
            return

        for category, policies in policy_definitions.POLICIES.items():
            # Insert category (must be done in main thread)
            def _insert_category(cat, pol_list):
                if not self.winfo_exists(): return
                category_id = self.policy_tree.insert("", "end", text=cat, open=True, tags=('category',))
                for policy_item in pol_list:
                    current_value = self.app.policy_manager.get_policy_value(policy_item['key'], policy_item['value_name'])
                    status = "🟢 Set" if current_value is not None else "⚪ Not Configured"
                    display_value = current_value if current_value is not None else "N/A"

                    if current_value is not None and policy_item['type'] == 'REG_DWORD':
                        try:
                            current_int_value = int(current_value) # Registry usually returns decimal for DWORD via query
                            # If it's hex from reg.exe output, int(current_value, 16)
                            # For simplicity, assuming get_policy_value standardizes or we handle it here
                            for option_name, option_val in policy_item['options'].items():
                                if option_val == current_int_value:
                                    display_value = option_name
                                    break
                        except (ValueError, TypeError) as e:
                            self.app.log(f"Policy Editor: Error parsing DWORD value '{current_value}' for {policy_item['name']}: {e}")

                    # Policy item data stored as JSON in tags for easy retrieval
                    self.policy_tree.insert(category_id, "end", text=policy_item['name'], values=(status, display_value), tags=(json.dumps(policy_item),))

            self.app.after(0, _insert_category, category, policies)
        self.app.log("Policy Editor: Policies populated.")

    def on_policy_edit_ui(self, event):
        item_id = self.policy_tree.focus()
        if not item_id: return

        item = self.policy_tree.item(item_id)
        tags = item.get('tags')

        if not tags or 'category' in tags : return # Clicked on category row or no tags

        try:
            policy_data_str = tags[0] # First tag should be the JSON string
            policy = json.loads(policy_data_str)
        except (IndexError, json.JSONDecodeError) as e:
            self.app.log(f"Policy Editor Error: Could not decode policy data from Treeview tag: {e}. Tag: {tags}")
            messagebox.showerror("Error", "Could not load policy details.", parent=self)
            return

        if "text" in policy['options']: # REG_SZ type with free text input
            current_full_value = self.app.policy_manager.get_policy_value(policy['key'], policy['value_name'])
            new_value = simpledialog.askstring(
                "Set Policy",
                f"Enter value for:\n{policy['name']}\n\nHelp: {policy['help']}",
                initialvalue=current_full_value if current_full_value is not None else "",
                parent=self # Ensure dialog is child of this tab or app window
            )
            if new_value is not None: # User provided a value (could be empty string)
                self.app.run_task_in_thread(self._apply_single_policy_task, None, policy, new_value)

        else: # REG_DWORD type with predefined options
            dialog = tb.Toplevel(title=f"Set Policy: {policy['name']}", parent=self.app) # Parent to app for modality
            dialog.transient(self.app) # Make it transient to the main app window
            dialog.grab_set() # Make modal
            dialog.geometry("400x350")


            tb.Label(dialog, text=f"{policy['name']}\n\nHelp: {policy['help']}", wraplength=380, justify="left").pack(padx=10, pady=(10,5))

            var = tk.IntVar()
            current_policy_val_str = self.app.policy_manager.get_policy_value(policy['key'], policy['value_name'])

            # Set initial radio button selection
            initial_selection_done = False
            if current_policy_val_str is not None:
                try:
                    current_val_int = int(current_policy_val_str) # Assuming decimal from get_policy_value
                    var.set(current_val_int)
                    initial_selection_done = True
                except ValueError:
                     self.app.log(f"Policy Editor: Could not parse current value '{current_policy_val_str}' for {policy['name']} as int.")

            if not initial_selection_done:
                 # Try to find a "Default" option if current value is not set or not parseable
                default_option_val = policy['options'].get("Default Enabled", policy['options'].get("Default", -2)) # -2 as unselected
                var.set(default_option_val)


            options_frame = tb.Frame(dialog, padding=10)
            options_frame.pack(fill=X, expand=True)

            for text, val in policy['options'].items():
                rb = tb.Radiobutton(options_frame, text=text, variable=var, value=val)
                rb.pack(anchor='w', pady=2)
                if val == var.get(): # Ensure the correct one is selected if var was set
                    rb.invoke()

            btn_frame = tb.Frame(dialog, padding=(0,10))
            btn_frame.pack(fill=X)

            def on_ok():
                selected_value = var.get()
                dialog.destroy()
                self.app.run_task_in_thread(self._apply_single_policy_task, None, policy, selected_value)

            def on_reset():
                dialog.destroy()
                self.app.run_task_in_thread(self._remove_single_policy_task, None, policy)

            def on_cancel():
                dialog.destroy()

            ok_btn = tb.Button(btn_frame, text="Apply", command=on_ok, bootstyle='success')
            ok_btn.pack(side=RIGHT, padx=5)
            reset_btn = tb.Button(btn_frame, text="Reset to Default", command=on_reset, bootstyle='danger-outline')
            reset_btn.pack(side=RIGHT, padx=5)
            cancel_btn = tb.Button(btn_frame, text="Cancel", command=on_cancel, bootstyle='secondary')
            cancel_btn.pack(side=RIGHT, padx=5)


    def _apply_single_policy_task(self, policy, value):
        if value == -1: # Special value for "Default" or "Not Configured" which means remove
            self._remove_single_policy_task(policy)
            return

        self.app.log(f"Policy Editor: Applying policy '{policy['name']}' with value '{value}'...")
        if not self.app.policy_manager:
            self.app.log("Policy Editor Error: Policy Manager not available for applying policy.")
            return

        success, msg = self.app.policy_manager.set_policy(policy['key'], policy['value_name'], value, policy['type'])

        if success:
            self.app.log(f"Policy '{policy['name']}' applied successfully.")
        else:
            self.app.log(f"Policy Editor: Failed to apply policy '{policy['name']}': {msg}")
            self.app.after(0, lambda: messagebox.showerror("Policy Error", f"Failed to apply policy '{policy['name']}':\n{msg}", parent=self.app))

        # Refresh the entire policy editor UI (could be optimized to update one row)
        self.app.run_task_in_thread(self.populate_policy_editor_ui)

    def _remove_single_policy_task(self, policy):
        self.app.log(f"Policy Editor: Resetting policy '{policy['name']}' to default...")
        if not self.app.policy_manager:
            self.app.log("Policy Editor Error: Policy Manager not available for removing policy.")
            return

        success, msg = self.app.policy_manager.remove_policy(policy['key'], policy['value_name'])

        if success:
            self.app.log(f"Policy '{policy['name']}' reset successfully.")
        else:
            self.app.log(f"Policy Editor: Failed to reset policy '{policy['name']}': {msg}")
            # Only show error if it's not a "not found" type of message, which is fine for a reset
            if "was not found" not in msg and "ERROR:" in msg :
                 self.app.after(0, lambda: messagebox.showerror("Policy Error", f"Failed to reset policy '{policy['name']}':\n{msg}", parent=self.app))

        self.app.run_task_in_thread(self.populate_policy_editor_ui)

    def clear_data(self):
        """Clears data from the policy tree."""
        if hasattr(self, 'policy_tree'):
            for item in self.policy_tree.get_children():
                try:
                    self.policy_tree.delete(item)
                except tk.TclError: # Item might already be deleted if called rapidly
                    pass
        self.app.log("Policy Editor: Data cleared.")
