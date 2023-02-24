import getpass
import os
import grp
import platform
import pwd
import subprocess

# Cache password for sudo use during development.
# The Yocto image should not make use of sudo.
password = None

# Determine if we are root
is_root = platform.system() == "Linux" and os.geteuid() == 0

# Determine if we are in the i2c group
user = getpass.getuser()
groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
gid = pwd.getpwnam(user).pw_gid
groups.append(grp.getgrgid(gid).gr_name)
in_i2c_group = "i2c" in set(groups)

# Do we have i2c access?
have_i2c_access = is_root or in_i2c_group

def on_linux() -> bool:
    """
    Return whether we are on Linux or not.
    """
    return platform.system() == "Linux"

def _get_password() -> str:
    """
    Gets the user's sudo password if we don't already have it. Otherwise a cached password is returned.

    This is suitable for development, but this method shouldn't be used in release images,
    as it stores the password in plaintext in RAM.
    """
    global password
    if password is None:
        password = getpass.getpass("Sudo password:")
    return password

def run_cmd(cmd: str):
    """
    Run the given command. If we need a password, we prompt the user for one.
    """
    if cmd.strip().startswith("sudo"):
        if have_i2c_access:
            cmd = cmd.lstrip().removeprefix("sudo").lstrip().removeprefix("-S").lstrip()
            return subprocess.run(cmd.split(), capture_output=True, encoding='utf-8')
        else:
            return subprocess.run(cmd.split(), input=_get_password(), capture_output=True, encoding='utf-8')
    else:
        return subprocess.run(cmd.split(), capture_output=True, encoding='utf-8')
