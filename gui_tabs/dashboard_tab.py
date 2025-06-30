import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class DashboardTab(tb.Frame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, padding=20, **kwargs)
        self.app = app_instance # Reference to the main Application instance

        self._create_widgets()

    def _create_widgets(self):
        # Frame for when PRO is NOT activated
        self.activation_frame = tb.Frame(self)
        self.activation_frame.pack(fill=BOTH, expand=True)

        tb.Label(self.activation_frame, text="PRO Version Not Activated", font=("", 16, "bold"), bootstyle="secondary").pack(pady=10)
        tb.Label(self.activation_frame, text="Activate to unlock the Advanced Profile Manager and Policy Editor.", wraplength=500, justify="center").pack(pady=10)

        self.key_entry = tb.Entry(self.activation_frame, width=50)
        self.key_entry.pack(pady=10)

        # Button calls prompt_for_activation on the main app instance
        self.activate_button = tb.Button(self.activation_frame, text="Activate PRO", bootstyle="success", command=self.app.prompt_for_activation)
        self.activate_button.pack(pady=10, ipady=10)

        # Frame for when PRO IS activated
        self.dashboard_pro_frame = tb.Frame(self)
        # dashboard_pro_frame is initially not packed, will be shown by show_pro_features()

        tb.Label(self.dashboard_pro_frame, text="PRO Version Activated", font=("", 16, "bold"), bootstyle="success").pack(pady=10)
        tb.Label(self.dashboard_pro_frame, text="All features are unlocked. Navigate to the other tabs to begin.", wraplength=500, justify="center").pack(pady=10)

        # Button calls license_manager.is_activated on the main app instance's license_manager
        tb.Button(self.dashboard_pro_frame, text="Check License Status", bootstyle="info", command=lambda: self.app.license_manager.is_activated(force_online_check=True)).pack(pady=10)

        # Button calls toggle_theme on the main app instance
        tb.Button(self.dashboard_pro_frame, text="Switch Theme (Light/Dark)", bootstyle="secondary", command=self.app.toggle_theme).pack(pady=10)

    def show_activation_needed(self):
        """Displays UI elements for when PRO version is not activated."""
        self.dashboard_pro_frame.pack_forget()
        self.activation_frame.pack(fill=BOTH, expand=True)
        self.key_entry.delete(0, END) # Clear key entry

    def show_pro_features_active(self):
        """Displays UI elements for when PRO version is activated."""
        self.activation_frame.pack_forget()
        self.dashboard_pro_frame.pack(fill=BOTH, expand=True)

    def get_key_entry_value(self):
        return self.key_entry.get()

    def set_activate_button_state(self, state, text=None):
        self.activate_button.config(state=state)
        if text:
            self.activate_button.config(text=text)
