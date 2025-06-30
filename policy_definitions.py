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
