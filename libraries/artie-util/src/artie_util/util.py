from . import artie_logging as alog
from rpyc.utils.server import ThreadPoolServer
from rpyc.utils.authenticators import SSLAuthenticator
import enum
import getpass
import os
import platform
import ssl
import subprocess

# Mock interface name
MOCK_IFACE_NAME = "artie.util.util"

# Cache password for sudo use during development.
# The Yocto image should not make use of sudo.
password = None

# Do some initialization if we are on Linux
if platform.system() == "Linux":
    import grp
    import pwd

    # Does 'sudo' exist in this sytem?
    try:
        subprocess.run(["sudo", "--version"]).check_returncode()
        no_sudo = False
    except:
        no_sudo = True

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
else:
    alog.warning("Detected that we are not on Linux. Certain functionality will be limited.")

class ArtieRunModes(enum.StrEnum):
    """
    The different types of run modes.
    """
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    SANITY_TESTING = "sanity"
    UNIT_TESTING = "unit"
    INTEGRATION_TESTING = "integration"

def create_rpc_server(server, keyfpath: str, certfpath: str, port: int, ipv6=False):
    """
    Create and return an RPC server using sane security defaults.
    """
    # Authentication itself is handled by means of the Kubernetes trust boundary
    # i.e., we trust (and do no real authentication of) any pods that are able to connect to us.
    # We prevent unwanted connections at the Kubernetes layer, using a whitelist Network Policy.
    # Encryption however, is a requirement of any data traveling over the network, to prevent
    # packet sniffing. This Authenticator class handles setting up the appropriate encryption.
    authenticator = SSLAuthenticator(
        keyfile=keyfpath,
        certfile=certfpath,
        cert_reqs=ssl.CERT_NONE,
        ciphers=':'.join(get_cipher_list()),
        ssl_version=ssl.PROTOCOL_TLS_SERVER
    )

    protocol = {
        # See: https://rpyc.readthedocs.io/en/latest/api/core_protocol.html#rpyc.core.protocol.DEFAULT_CONFIG
        # 'allow_public_attrs': True
    }

    t = ThreadPoolServer(
        server,
        hostname="0.0.0.0",
        ipv6=ipv6,
        port=port,
        reuse_addr=False,
        authenticator=authenticator,
        registrar=None,  # Do not use a registrar - we make use of Kubernetes Services instead
        protocol_config=protocol
    )
    return t

def get_cipher_list():
    """
    Returns a list of the available ciphers for servers.
    """
    ciphers = [
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-RSA-CHACHA20-POLY1305",
        "ECDHE-RSA-AES256-SHA384",
        "ECDHE-RSA-AES128-SHA256",
        "DHE-RSA-AES256-GCM-SHA384",
        "DHE-RSA-AES128-GCM-SHA256",
        "DHE-RSA-AES256-SHA256",
        "DHE-RSA-AES128-SHA256",
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256",
    ]
    return ciphers

def get_git_tag() -> str:
    """
    Retrieve the git tag from the environment variables.
    """
    return os.environ.get('ARTIE_GIT_TAG', 'unversioned')

def generate_self_signed_cert(certfpath, keyfpath, days=30, force=False):
    """
    Generate a self-signed certificate and place it at `certfpath`. The private
    key will be placed at `keyfpath`. The certificate will be valid for the given number
    of `days`. If `days` is set to `None`, we use ~100 years.
    If `force` is given, we overwrite a certifacte/key already found at
    the given path(s).

    Note that we have no real way of encrypting the private key, so it is stored in plaintext!
    """
    if not force and os.path.isfile(certfpath) and os.path.isfile(keyfpath):
        # Nothing to do
        alog.info("Certificate and key already found and `force` is False. Not generating new cert.")
        return

    timelimit = "36500" if days is None else str(days)
    cmd = f"openssl req -x509 -newkey rsa:4096 -sha256 -days {timelimit} -nodes -keyout {keyfpath} -out {certfpath}"
    sub = f"-subj /C=US/ST=Washington/L=Seattle/O=Artie/OU=Artie/CN=Artie"
    subprocess.run(f"{cmd} {sub}".split(), stdout=subprocess.DEVNULL).check_returncode()

def in_test_mode() -> bool:
    """
    Returns True if we are in a testing mode.
    """
    test_modes = set([ArtieRunModes.UNIT_TESTING, ArtieRunModes.SANITY_TESTING, ArtieRunModes.INTEGRATION_TESTING])
    return os.environ.get('ARTIE_RUN_MODE', 'production') in test_modes

def mode() -> ArtieRunModes:
    """
    Return the run mode we are in.
    """
    return ArtieRunModes(os.environ.get('ARTIE_RUN_MODE', 'production'))

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

def run_cmd(cmd: str, group=None):
    """
    Run the given command. If we need a password, we prompt the user for one.

    If the command starts with 'sudo', a `group` may be given. We check if
    the user has access to the given group and then strip off the 'sudo' if so.
    Otherwise, we run with 'sudo', asking for a password.

    Available groups:

    - i2c
    """
    no_sudo_cmd = cmd.lstrip().removeprefix("sudo").lstrip().removeprefix("-S").lstrip()
    if cmd.strip().startswith("sudo"):
        has_access = {
            "i2c": have_i2c_access,
            None: False
        }[group]
        if has_access:
            return subprocess.run(no_sudo_cmd.split(), capture_output=True, encoding='utf-8')
        elif no_sudo:
            alog.warning(f"No 'sudo' in this system, but the command '{cmd}' starts with it and you don't seem to have the required access. We will attempt to run, but it will likely fail.")
            return subprocess.run(no_sudo_cmd.split(), capture_output=True, encoding='utf-8')
        else:
            return subprocess.run(cmd.split(), input=_get_password(), capture_output=True, encoding='utf-8')
    else:
        return subprocess.run(cmd.split(), capture_output=True, encoding='utf-8')
