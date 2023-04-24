"""
The public interface for the drivers is exposed through this module.
"""
from artie_util import artie_logging as alog
from artie_util import dns
from artie_util import util
from rpyc.utils import factory
import datetime

# A cache to store services that we have determined to be online
online_cache = set()

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

def block_until_online(service: dns.Lookups, timeout_s=30, ipv6=False):
    """
    Blocks until the given service is online.
    """
    # Check cache and return if already done
    global online_cache
    if service in online_cache:
        return

    # Lookup the service in the DNS
    host, port = dns.lookup(service)

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

def reset(addr: int, ipv6=False, n_retries=3, timeout_s=None) -> bool:
    """
    Attempt to reset a device at target address. See the appropriate board
    config file for valid reset addresses.
    """
    alog.info(f"Reseting {addr}")

    if util.in_test_mode() and util.mode() != util.ArtieRunModes.INTEGRATION_TESTING:
        alog.info("Mocking a DNS lookup and RPC call for reset.")
        return

    # DNS
    block_until_online(dns.Lookups.RESET_DRIVER, timeout_s=timeout_s, ipv6=ipv6)
    host, port = dns.lookup(dns.Lookups.RESET_DRIVER)

    ts = datetime.datetime.now().timestamp()
    connection = None
    for _ in range(n_retries):
        try:
            connection = factory.ssl_connect(host, port, ipv6=ipv6)
            connection.root.reset_target(addr)
            break  # finally block will still run
        except Exception as e:
            alog.exception(f"Exception when trying to reset {addr}: ", e, stack_trace=True)
            alog.update_counter(1, "adc-reset-errors", unit=alog.Units.TIMES, description="Number of times we encounter an error when using reset over the network.")
        finally:
            if connection:
                connection.close()
    duration_s = datetime.datetime.now().timestamp() - ts
    alog.update_histogram(duration_s, f"adc-reset-{alog.HISTOGRAM_SUFFIX_SECONDS}", unit=alog.Units.SECONDS, description="Durations of reset calls over the network.")
