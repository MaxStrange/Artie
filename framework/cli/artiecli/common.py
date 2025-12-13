"""
Common code for all the modules.
"""
from artie_tooling import errors as tooling_errors
from typing import Any, Dict

try:
    import rpyc
    from rpyc.utils import factory
    LOCAL_ONLY = False
except ImportError:
    # Local-only version of CLI is used.
    LOCAL_ONLY = True


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
    if LOCAL_ONLY:
        raise OSError(f"Running a local version of CLI. Cannot access any RPyC services. Install with [remote] dependencies if possible.")

    # TODO: Deal with authentication when trying to access K3S service
    # TODO: Deal with ports and hosts when on K3S
    connection = factory.ssl_connect(host, port, ipv6=ipv6)
    return _ConnectionWrapper(connection)

def in_test_mode(args) -> bool:
    """
    Returns True if we are in unit-test mode.
    """
    return args.unit_test

def int_or_hex_type(val):
    """
    Check if the given argument is an int or if it is a string that can be converted
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

def format_print_result(result: tooling_errors.HTTPError|Any, module: str, submodule: str, artie_id: str):
    """
    Prints ({artie_id}) {module} {submodule}: {msg}

    If `result` is an instance of `tooling_errors.HTTPError`, 'msg' is
    read from `result.message`. Otherwise, 'msg' is just `result`.
    """
    if issubclass(type(result), tooling_errors.HTTPError):
        msg = result.message
    else:
        msg = str(result)

    print(f"({artie_id}) {module} {submodule}: {msg}")

def format_print_status_result(result, module: str, artie_id: str):
    """
    Prints the result of a status check.

    Results look like this:

    ```
    (artie-id) module:
        submodule01: [working, degraded, not working, or unknown]
        submodule02: [working, degraded, not working, or unknown]
        etc.
    ```

    If an instance of `tooling_errors.HTTPError` is given for `result`, we print a message of the
    form:

    ```
    (artie-id) module:
        Error: [<error message>]
    ```
    """
    s = f"({artie_id}) {module}:\n"
    if issubclass(type(result), tooling_errors.HTTPError):
        s += f"    Error: [{result.message}]"
    else:
        ordered_response = [(k, v) for k, v in result.get('submodule-statuses', {}).items()]
        ordered_response = sorted(ordered_response, key=lambda x: x[0])
        for k, v in ordered_response:
            s += f"    {k}: [{v}]\n"

    print(s)
