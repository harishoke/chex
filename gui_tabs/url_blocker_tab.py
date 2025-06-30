import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class URLBlockerTab(tb.Frame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, padding=10, **kwargs)
        self.app = app_instance # Reference to the main Application instance
        self._create_widgets()

    def _create_widgets(self):
        tb.Label(self, text="Block specific websites for all users. Wildcards (*) are supported. E.g., *.facebook.com", bootstyle='info').pack(fill=X, pady=5)

        add_frame = tb.Frame(self)
        add_frame.pack(fill=X, pady=5)
        tb.Label(add_frame, text="URL to Block:").pack(side=LEFT, padx=5)
        self.url_entry = tb.Entry(add_frame)
        self.url_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        tb.Button(add_frame, text="Block URL", bootstyle="danger", command=self.add_url_to_blocklist_ui).pack(side=LEFT, padx=5)

        list_frame = tb.LabelFrame(self, text="Currently Blocked URLs")
        list_frame.pack(fill=BOTH, expand=True, pady=10)
        self.blocked_url_list = tk.Listbox(list_frame)
        self.blocked_url_list.pack(side=LEFT, fill=BOTH, expand=True)

        # It's good practice to have a scrollbar for the listbox
        scrollbar = tb.Scrollbar(list_frame, orient=VERTICAL, command=self.blocked_url_list.yview)
        self.blocked_url_list.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

        tb.Button(list_frame, text="Allow Selected URL", bootstyle="success-outline", command=self.remove_url_from_blocklist_ui).pack(side=LEFT, padx=10, pady=10, anchor='center')


    def load_initial_data(self):
        self.app.log("URL Blocker: Refreshing blocklist...")
        self.app.run_task_in_thread(self._get_url_blocklist_task, self._populate_blocklist_ui_callback)

    def _populate_blocklist_ui_callback(self, blocklist_data):
        if not self.winfo_exists(): return # Check if widget still exists
        self.blocked_url_list.delete(0, END)
        if blocklist_data:
            urls, _ = blocklist_data # We only need urls for display
            for index, url_val in sorted(urls.items(), key=lambda item: int(item[0])): # Sort by index
                self.blocked_url_list.insert(END, f"[{index}] {url_val}")
            self.app.log(f"URL Blocker: Displayed {len(urls)} blocked URLs.")
        else:
            self.app.log("URL Blocker: No blocked URLs to display or error fetching list.")

    def _get_url_blocklist_task(self):
        """Task to fetch the URL blocklist from the registry. Runs in a thread."""
        if not self.app.policy_manager:
            self.app.log("URL Blocker Error: Policy Manager not available.")
            return {}, [] # Return empty data

        key_path = f"HKEY_LOCAL_MACHINE\\{self.app.policy_manager.POLICY_BASE_KEY}\\URLBlocklist"
        args = f'query "{key_path}"'
        # _run_reg_command is part of WindowsPolicyManager instance
        stdout, stderr = self.app.policy_manager._run_reg_command(args)

        urls, indices = {}, []
        if stderr and "unable to find the specified registry key" not in stderr.lower() and "error" in stderr.lower() :
            self.app.log(f"URL Blocker: Error querying registry for URLBlocklist: {stderr}")
            return {}, [] # Return empty on significant error
        if "unable to find the specified registry key" in stderr.lower() or not stdout : # Key doesn't exist or is empty
             self.app.log("URL Blocker: URLBlocklist registry key not found or empty.")
             return {}, []


        for line in stdout.strip().split('\n'):
            if not line.strip() or line.strip().startswith("HKEY_LOCAL_MACHINE") or not line.strip().startswith(" "): # Filter header and non-value lines
                # A more robust parsing would be to check for REG_SZ type
                # Example line: "    1    REG_SZ    *.example.com"
                # Split by multiple spaces, then filter empty strings
                parts = [p.strip() for p in line.split('    ') if p.strip()]
                if len(parts) >= 2 and parts[1] == "REG_SZ": # Check if it looks like a value line
                    index, url_val = parts[0], parts[-1]
                    try:
                        indices.append(int(index))
                        urls[index] = url_val
                    except ValueError:
                        self.app.log(f"URL Blocker: Could not parse index from line: {line}")
                    except Exception as e:
                         self.app.log(f"URL Blocker: Error parsing line '{line}': {e}")
                elif len(parts) >=3 and parts[0].isdigit() and parts[1] == "REG_SZ": # Alternative parsing for some reg outputs
                    index, url_val = parts[0], parts[2] # Value might be third part
                    try:
                        indices.append(int(index))
                        urls[index] = url_val
                    except ValueError:
                        self.app.log(f"URL Blocker: Could not parse index from alternative line format: {line}")
                # else:
                #     self.app.log(f"URL Blocker: Skipping unparsable line: {line}")


        return urls, indices

    def add_url_to_blocklist_ui(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a URL to block.", parent=self)
            return
        self.app.run_task_in_thread(self._add_url_logic_task, None, url)
        self.url_entry.delete(0, END)

    def _add_url_logic_task(self, url_to_block):
        """Task to add a URL to the blocklist. Runs in a thread."""
        self.app.log(f"URL Blocker: Attempting to block URL: {url_to_block}...")
        if not self.app.policy_manager:
            self.app.log("URL Blocker Error: Policy Manager not available for adding URL.")
            return

        # Fetch current list to determine next available index
        current_urls, current_indices = self._get_url_blocklist_task() # This is a direct call, intended to run within this thread

        # Check if URL already exists (value check, not just index)
        for idx, existing_url in current_urls.items():
            if existing_url == url_to_block:
                self.app.log(f"URL Blocker: URL '{url_to_block}' is already blocked at index {idx}.")
                self.app.after(0, lambda: messagebox.showinfo("Already Blocked", f"The URL '{url_to_block}' is already in the blocklist.", parent=self.app))
                # Refresh UI in case indices were not contiguous or something else changed
                self.app.run_task_in_thread(self._get_url_blocklist_task, self._populate_blocklist_ui_callback)
                return

        next_index = 1
        if current_indices:
            next_index = max(current_indices) + 1

        success, msg = self.app.policy_manager.set_policy("URLBlocklist", str(next_index), url_to_block, "REG_SZ")

        if success:
            self.app.log(f"URL '{url_to_block}' blocked successfully at index {next_index}. Restart Chrome to apply.")
        else:
            self.app.log(f"URL Blocker: Failed to block URL '{url_to_block}': {msg}")
            self.app.after(0, lambda: messagebox.showerror("Blocking Failed", f"Failed to block URL '{url_to_block}':\n{msg}", parent=self.app))

        # Refresh the list in the UI by calling the task chain again
        self.app.run_task_in_thread(self._get_url_blocklist_task, self._populate_blocklist_ui_callback)

    def remove_url_from_blocklist_ui(self):
        if not self.blocked_url_list.curselection():
            messagebox.showwarning("Selection Required", "Please select a URL to allow.", parent=self)
            return

        selected_item_text = self.blocked_url_list.get(self.blocked_url_list.curselection()[0])
        # Extract index, e.g., from "[123] some.url.com"
        try:
            index_to_remove = selected_item_text.split("]")[0].strip("[")
            int(index_to_remove) # Validate it's an integer
        except (IndexError, ValueError):
            messagebox.showerror("Error", "Could not parse the selected URL's index.", parent=self)
            self.app.log(f"URL Blocker Error: Could not parse index from '{selected_item_text}'")
            return

        self.app.run_task_in_thread(self._remove_url_logic_task, None, index_to_remove)

    def _remove_url_logic_task(self, index_str_to_remove):
        """Task to remove a URL from the blocklist using its index. Runs in a thread."""
        self.app.log(f"URL Blocker: Attempting to allow URL at registry index {index_str_to_remove}...")
        if not self.app.policy_manager:
            self.app.log("URL Blocker Error: Policy Manager not available for removing URL.")
            return

        success, msg = self.app.policy_manager.remove_policy("URLBlocklist", index_str_to_remove)

        if success:
            self.app.log(f"URL at index {index_str_to_remove} allowed successfully. Restart Chrome to apply.")
        else:
            self.app.log(f"URL Blocker: Failed to allow URL at index {index_str_to_remove}: {msg}")
            # Only show error if it's not a "not found" type of message
            if "was not found" not in msg and "ERROR:" in msg :
                 self.app.after(0, lambda: messagebox.showerror("Allow Failed", f"Failed to allow URL at index {index_str_to_remove}:\n{msg}", parent=self.app))

        self.app.run_task_in_thread(self._get_url_blocklist_task, self._populate_blocklist_ui_callback)

    def clear_data(self):
        """Clears data from the lists in this tab."""
        if hasattr(self, 'blocked_url_list'):
            self.blocked_url_list.delete(0, END)
        self.app.log("URL Blocker: Data cleared.")
