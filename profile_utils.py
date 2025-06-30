import os
import json
import shutil

def get_profile_details(user_data_path, log_callback):
    profile_details = {}
    if not user_data_path or not os.path.exists(user_data_path):
        log_callback(f"Error: Chrome user data path not found or invalid: {user_data_path}")
        return {}

    log_callback(f"Scanning for profiles in: {user_data_path}")
    found_profiles_count = 0
    for item in os.listdir(user_data_path):
        if item == "Default" or item.startswith("Profile "):
            profile_path = os.path.join(user_data_path, item)
            if not os.path.isdir(profile_path):
                continue

            preferences_path = os.path.join(profile_path, 'Preferences')
            profile_name = item # Default to folder name

            if os.path.exists(preferences_path):
                try:
                    with open(preferences_path, 'r', encoding='utf-8') as f:
                        prefs = json.load(f)
                        profile_name_from_prefs = prefs.get('profile', {}).get('name')
                        if profile_name_from_prefs and profile_name_from_prefs.strip():
                             profile_name = profile_name_from_prefs
                        else:
                            log_callback(f"Profile '{item}' has no custom name in Preferences, using folder name.")
                except json.JSONDecodeError:
                    log_callback(f"Error: Could not decode Preferences JSON for profile '{item}'. Using folder name.")
                except Exception as e:
                    log_callback(f"Error reading Preferences for profile '{item}': {e}. Using folder name.")
            else:
                log_callback(f"Preferences file not found for profile '{item}'. Using folder name.")

            original_name = profile_name
            counter = 2
            while profile_name in profile_details: # Ensure unique profile names in our map
                profile_name = f"{original_name} ({counter})"
                counter += 1

            profile_details[profile_name] = profile_path
            found_profiles_count +=1
            log_callback(f"Found profile: '{profile_name}' at {profile_path}")

    if found_profiles_count == 0:
        log_callback("No Chrome profiles found (Default or Profile X).")
    else:
        log_callback(f"Finished scanning. Found {found_profiles_count} profile(s).")

    return dict(sorted(profile_details.items()))


def get_extensions_for_profile(profile_path, log_callback):
    extensions = {}
    preferences_file = os.path.join(profile_path, 'Preferences')
    if not os.path.exists(preferences_file):
        log_callback(f"Preferences file not found for profile: {os.path.basename(profile_path)}")
        return {}

    try:
        with open(preferences_file, 'r', encoding='utf-8') as f:
            prefs = json.load(f)

        installed_extensions = prefs.get('extensions', {}).get('settings', {})
        if not installed_extensions:
            log_callback(f"No extensions found in Preferences for profile: {os.path.basename(profile_path)}")
            return {}

        for ext_id, details in installed_extensions.items():
            if len(ext_id) != 32:  # Basic validation for extension ID format
                log_callback(f"Skipping invalid extension ID: {ext_id}")
                continue

            manifest = details.get('manifest', {})
            name = manifest.get('name', ext_id)
            # Clean up common localization placeholders in names
            if name.startswith('__MSG_') and name.endswith('__'):
                name = name.replace('__MSG_','').replace('__','').replace('appName','').strip() or ext_id

            state = details.get('state', 0) # 0: disabled, 1: enabled
            version = manifest.get('version', 'N/A')
            permissions = manifest.get('permissions', [])
            path_to_extension = details.get('path', 'N/A') # Renamed for clarity
            was_installed_by_default = details.get('was_installed_by_default', False)

            original_name = name
            counter = 2
            while name in extensions: # Ensure unique names in our map
                name = f"{original_name} ({counter})"
                counter += 1

            extensions[name] = {
                'id': ext_id,
                'state': state,
                'version': version,
                'permissions': permissions,
                'path': path_to_extension,
                'was_installed_by_default': was_installed_by_default
            }
        log_callback(f"Found {len(extensions)} extensions for profile: {os.path.basename(profile_path)}")
    except json.JSONDecodeError as e:
        log_callback(f"Error decoding Preferences JSON for {os.path.basename(profile_path)}: {e}")
        return {} # Return empty if prefs are corrupt
    except Exception as e:
        log_callback(f"Error reading extensions for {os.path.basename(profile_path)}: {e}")
        return {} # Return empty on other errors

    return dict(sorted(extensions.items()))


def set_extension_state_for_profile(profile_path, ext_id, new_state, log_callback):
    prefs_path = os.path.join(profile_path, 'Preferences')
    if not os.path.exists(prefs_path):
        log_callback(f"Error: Preferences file not found at {prefs_path}")
        return False

    # Create a backup before modifying
    backup_path = prefs_path + '.bak'
    try:
        shutil.copyfile(prefs_path, backup_path)
        log_callback(f"Backup of Preferences created at {backup_path}")
    except IOError as e:
        log_callback(f"Warning: Could not create backup of Preferences file: {e}")

    try:
        with open(prefs_path, 'r+', encoding='utf-8') as f:
            prefs = json.load(f)

            if 'extensions' not in prefs or 'settings' not in prefs['extensions']:
                log_callback(f"Error: 'extensions.settings' structure not found in Preferences for {ext_id}.")
                return False

            if ext_id not in prefs['extensions']['settings']:
                log_callback(f"Error: Extension ID {ext_id} not found in Preferences.")
                return False

            prefs['extensions']['settings'][ext_id]['state'] = new_state

            f.seek(0)  # Rewind to the beginning of the file
            json.dump(prefs, f, indent=4) # Write changes
            f.truncate() # Remove trailing content if new data is smaller

            log_callback(f"Successfully set state to {'Enabled' if new_state == 1 else 'Disabled'} for extension {ext_id} in profile {os.path.basename(profile_path)}")
            return True

    except json.JSONDecodeError as e:
        log_callback(f"Error decoding Preferences JSON while setting state for {ext_id}: {e}")
        # Attempt to restore backup if modification failed
        if os.path.exists(backup_path):
            try:
                shutil.copyfile(backup_path, prefs_path)
                log_callback(f"Restored Preferences from backup due to error.")
            except IOError as re:
                log_callback(f"FATAL: Could not restore Preferences from backup: {re}")
        return False
    except Exception as e:
        log_callback(f"Error modifying Preferences file for extension {ext_id}: {e}")
        if os.path.exists(backup_path): # Same restoration attempt
            try:
                shutil.copyfile(backup_path, prefs_path)
                log_callback(f"Restored Preferences from backup due to error.")
            except IOError as re:
                log_callback(f"FATAL: Could not restore Preferences from backup: {re}")
        return False
