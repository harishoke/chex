import subprocess
import os # Added os import for consistency, though not strictly used in current snippet

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
