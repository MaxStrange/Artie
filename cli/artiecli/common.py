"""
Common code for all the modules.
"""
import rpyc
from rpyc.utils import factory


class _ConnectionWrapper:
    """
    Pretends to be the connection.root object instead of the
    connection object, while also providing for cleanup after
    the connection gets deleted/garbage collected.
    """
    def __init__(self, connection) -> None:
        self._connection = connection

    def __getattr__(self, attr):
        try:
            orig_attr = self._connection.root.__getattribute__(attr)
        except AttributeError:
            print(f"Cannot access {attr}")
        if callable(orig_attr):
            def hooked(*args, **kwargs):
                result = orig_attr(*args, **kwargs)
                if result == self._connection.root:
                    return self
                else:
                    return result
            return hooked
        else:
            return orig_attr

    def __del__(self):
        if self._connection:
            self._connection.close()

def connect(host, port=None, ipv6=False):
    """
    Connect to the RPyC server on `host`, which could be an IP address or a
    anything that will DNS-resolve to an IP address.

    If we are running outside the Kubernetes cluster, we will need to do
    some authentication, and our abilities will be limited to connecting
    to only externally-available services.

    If we are running on the cluster, we do not need to do any authentication,
    and we have access to any service.

    If we are running in a test mode, where there is no Kubernetes cluster,
    we will need an IP and port.

    Returns an object that can be considered a proxy of the remote service.
    """
    # TODO: Deal with authentication when trying to access K3S service
    # TODO: Deal with ports and hosts when on K3S
    connection = factory.ssl_connect(host, port, ipv6=ipv6)
    return _ConnectionWrapper(connection)

def int_or_hex_type(val):
    """
    Check if he given argument is an int or if it is a string that can be converted
    to an int, including hexadecimal format (e.g., 0xFF).

    Also checks octal (0o) and binary (0b).
    """
    if type(val) == int:
        return int(val)
    elif type(val) == str and val.startswith("0x") or val.startswith("0X"):
        return int(val, base=16)
    elif type(val) == str and val.startswith("0b") or val.startswith("0B"):
        return int(val, base=2)
    elif type(val) == str and val.startswith("0o") or val.startswith("0O"):
        return int(val, base=8)
    else:
        return int(val)
