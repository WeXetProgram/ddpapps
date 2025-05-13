import os
import shutil
import winreg
import subprocess
from pathlib import Path

def create_shortcut(target_path, shortcut_name):
    """Create a Windows desktop shortcut"""
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
    
    # Create shortcut using PowerShell
    ps_command = f'''
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
    $Shortcut.TargetPath = "{target_path}"
    $Shortcut.Save()
    '''
    
    subprocess.run(['powershell', '-Command', ps_command], capture_output=True)
    return shortcut_path

def remove_shortcut(shortcut_name):
    """Remove a Windows desktop shortcut"""
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
    
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)

def get_installed_apps():
    """Get list of installed apps from registry"""
    installed_apps = []
    
    # Check both 32-bit and 64-bit registry
    for registry in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        try:
            with winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                installed_apps.append(name)
                            except WindowsError:
                                pass
                        i += 1
                    except WindowsError:
                        break
        except WindowsError:
            continue
            
    return installed_apps
