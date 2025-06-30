import os
import json
import hashlib
import time
import threading
import requests

import config
from utils import get_hardware_id

class LicenseManager:
    def __init__(self, app_instance):
        self.app = app_instance  # app_instance is the main Application object
        self.log = app_instance.log
        self.last_online_check = 0
        self.check_interval = 3600 # 1 hour in seconds

    def _perform_online_check(self, key_from_local_file):
        self.log("Performing real-time license check with server...")
        is_still_valid, message = self.activate_online(key_from_local_file, is_recheck=True)
        if not is_still_valid:
            self.log(f"License check failed: {message}. Deactivating PRO features.")
            if os.path.exists(config.LICENSE_FILE):
                try:
                    os.remove(config.LICENSE_FILE)
                except OSError as e:
                    self.log(f"Error removing license file: {e}")
            # Schedule deactivation on the main thread
            self.app.after(0, self.app.deactivate_pro_features)
        else:
            self.log("License is still valid.")
            self.last_online_check = time.time()

    def activate_online(self, key, is_recheck=False):
        if not config.ACTIVATION_URL or "YOUR_GOOGLE_APPS_SCRIPT_URL_HERE" in config.ACTIVATION_URL:
            return False, "Activation URL not configured by the developer."

        hwid = get_hardware_id()
        if hwid in ["UNKNOWN_HWID", "UNSUPPORTED_OS"]:
            return False, "Could not retrieve a unique hardware ID."

        try:
            url = f"{config.ACTIVATION_URL}?key={key}&hwid={hwid}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()  # Raises an exception for HTTP errors
            data = response.json()

            if data.get("status") == "success":
                if not is_recheck:
                    # Ensure the directory exists before writing
                    os.makedirs(os.path.dirname(config.LICENSE_FILE), exist_ok=True)
                    with open(config.LICENSE_FILE, 'w') as f:
                        f.write(json.dumps({'key': key, 'hwid_hash': hashlib.sha256(hwid.encode()).hexdigest()}))
                return True, data.get("message", "Activation Successful!")
            else:
                return False, data.get("message", "An unknown error occurred during activation.")
        except requests.exceptions.RequestException as e:
            self.log(f"Network error during activation: {e}")
            return False, f"Network error: {e}"
        except json.JSONDecodeError as e:
            self.log(f"Error decoding server response: {e}")
            return False, "Invalid response from server."
        except IOError as e:
            self.log(f"File error saving license: {e}")
            return False, f"Could not save license information: {e}"
        except Exception as e:
            self.log(f"Unexpected error during activation: {e}")
            return False, f"An unexpected error occurred: {e}"

    def is_activated(self, force_online_check=False):
        if not os.path.exists(config.LICENSE_FILE):
            return False
        try:
            with open(config.LICENSE_FILE, 'r') as f:
                license_data = json.load(f)

            stored_hash = license_data.get('hwid_hash')
            key = license_data.get('key') # Get key for re-check
            if not key:
                self.log("License key not found in local file.")
                return False

            current_hwid = get_hardware_id()
            if current_hwid in ["UNKNOWN_HWID", "UNSUPPORTED_OS"]:
                 self.log("Could not verify hardware ID for activation check.")
                 return False # Cannot verify if HWID is not obtainable

            current_hwid_hash = hashlib.sha256(current_hwid.encode()).hexdigest()

            if stored_hash != current_hwid_hash:
                self.log("Hardware ID mismatch. License invalid for this machine.")
                return False

            # Perform online check if forced or interval has passed
            if force_online_check or (time.time() - self.last_online_check > self.check_interval):
                # Run the online check in a separate thread to avoid blocking the GUI
                threading.Thread(target=self._perform_online_check, args=(key,), daemon=True).start()

            return True # Assumed valid locally, online check will confirm/deny later
        except json.JSONDecodeError as e:
            self.log(f"Error reading license file: {e}")
            return False
        except IOError as e:
            self.log(f"Could not open license file: {e}")
            return False
        except Exception as e:
            self.log(f"Unexpected error checking activation status: {e}")
            return False
