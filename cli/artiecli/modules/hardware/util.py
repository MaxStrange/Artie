import getpass
import platform
import subprocess

password = None

def on_linux() -> bool:
    """
    Return whether we are on Linux or not.
    """
    return platform.system() == "Linux"

def get_password() -> str:
    """
    Gets the user's sudo password if we don't already have it. Otherwise a cached password is returned.
    """
    global password
    if password is None:
        password = getpass.getpass("Sudo password:")
    return password

def run_cmd(cmd: str):
    """
    Run the given command. If it starts with 'sudo', we prompt for a password if we don't already have one.
    """
    if cmd.strip().startswith("sudo"):
        return subprocess.run(cmd.split(), input=get_password(), capture_output=True, encoding='utf-8')
    else:
        return subprocess.run(cmd.split(), capture_output=True, encoding='utf-8')
