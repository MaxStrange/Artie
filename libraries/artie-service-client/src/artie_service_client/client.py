"""
The public interface for the various services is exposed through this module.
"""
from artie_util import artie_logging as alog
from artie_util import constants
from artie_util import dns
from artie_util import util
from rpyc.utils import factory
import datetime
import enum

# A cache to store services that we have determined to be online
online_cache = set()

class Service(enum.Enum):
    RESET_SERVICE = "reset-service"
    EYEBROWS_SERVICE = "eyebrows-service"
    MOUTH_SERVICE = "mouth-service"

class ServiceConnection:
    """
    A ServiceConnection object exposes an easy-to-use API for calling
    a particular micro service. It handles all the connection attempts,
    logging, metrics collecting, and communication mechanism details
    so that clients that make use of this object do not need to worry
    about any of that.
    """
    def __init__(self, service: Service, n_retries=3, artie_id=None, timeout_s=None, ipv6=False) -> None:
        self.n_retries = n_retries
        self.artie_id = artie_id
        self.timeout_s = timeout_s
        self.ipv6 = ipv6
        self.service = service
        self.connection = self._initialize_connection(service)

    def __getattr__(self, attr):
        orig_attr = self.connection.root.__getattribute__(attr)
        if callable(orig_attr):
            def hooked(*args, **kwargs):
                result = self._retry_n_times(orig_attr, args, kwargs)
                if result == self.connection.root:
                    return self
                else:
                    return  result
            return hooked
        else:
            return orig_attr

    def __del__(self):
        if hasattr(self, 'connection'):
            self.connection.close()

    def _retry_n_times(self, f, args, kwargs):
        for _ in range(self.n_retries):
            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                alog.exception(f"Exception when trying to run a function on a service connection (service: {self.service}): ", e, stack_trace=True)
                alog.update_counter(1, "asc-connection-errors", unit=alog.Units.TIMES, description="Number of times we encounter an error when trying to connect to an Artie service.")

    def _initialize_connection(self, service: Service):
        match service:
            case Service.RESET_SERVICE:
                dns_lookup = dns.Lookups.RESET_DRIVER
            case Service.EYEBROWS_SERVICE:
                dns_lookup = dns.Lookups.EYEBROWS_DRIVER
            case Service.MOUTH_SERVICE:
                dns_lookup = dns.Lookups.MOUTH_DRIVER
            case _:
                raise ValueError(f"Given an invalid Service for ServiceConnection: {service}")

        # DNS
        block_until_online(dns_lookup, timeout_s=self.timeout_s, ipv6=self.ipv6, artie_id=self.artie_id)
        host, port = dns.lookup(dns_lookup, artie_id=self.artie_id)

        for _ in range(self.n_retries):
            try:
                return factory.ssl_connect(host, port, ipv6=self.ipv6)
            except Exception as e:
                alog.exception(f"Exception when trying to connect to {host}:{port}: ", e, stack_trace=True)
                alog.update_counter(1, "asc-connection-errors", unit=alog.Units.TIMES, description="Number of times we encounter an error when trying to connect to an Artie service.")

def _try_connect(host: str, port: int, ipv6=False) -> bool:
    """
    Attempts to connect to the given rpyc server and execute the whoami() method.
    Returns True if it succeeds, False otherwise.
    """
    connection = None
    try:
        connection = factory.ssl_connect(host, port, ipv6=ipv6)
        connection.root.whoami()
        return True
    except AttributeError as e:
        alog.error(f"Service running at {host}:{str(port)} does not have a 'whoami' method.")
        return True
    except Exception as e:
        alog.debug(f"Couldn't connect to {host}:{str(port)}")
    finally:
        if connection:
            connection.close()
    return False

def block_until_online(service: dns.Lookups, timeout_s=30, ipv6=False, artie_id=None):
    """
    Blocks until the given service is online.
    """
    # Check cache and return if already done
    global online_cache
    if service in online_cache:
        return

    alog.info(f"Waiting for {service} to come online...")

    # Lookup the service in the DNS
    host, port = dns.lookup(service, artie_id=artie_id)

    # Keep trying to connect forever if no timeout, or until timeout if we have one
    ts = datetime.datetime.now().timestamp()
    success = False
    if timeout_s is None:
        while not success:
            success = _try_connect(host, port, ipv6=ipv6)
    else:
        while not success and datetime.datetime.now().timestamp() - ts < timeout_s:
            success = _try_connect(host, port, ipv6=ipv6)

    # Add to cache or raise an error
    if success:
        online_cache.add(service)
    else:
        raise TimeoutError(f"Timeout while waiting for {service} to come online.")

def reset(addr: int, ipv6=False, n_retries=3, timeout_s=None, artie_id=None) -> bool:
    """
    Attempt to reset a device at target address. See the appropriate board
    config file for valid reset addresses.

    Convenience method for interacting with the reset driver through a ServiceConnection object.
    """
    alog.info(f"Reseting {addr}")

    if util.in_test_mode() and util.mode() != constants.ArtieRunModes.INTEGRATION_TESTING:
        alog.info("Mocking a DNS lookup and RPC call for reset.")
        return

    connection = ServiceConnection(Service.RESET_SERVICE, n_retries=n_retries, timeout_s=timeout_s, artie_id=artie_id, ipv6=ipv6)
    connection.reset_target(addr)
