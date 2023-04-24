"""
This module contains mappings from hostnames to IP addresses/Kubernetes Services, etc.
"""
import enum

@enum.unique
class Lookups(enum.Enum):
    """
    Available items for lookup.
    """
    RESET_DRIVER = 0
    EYEBROWS_DRIVER = 1
    MOUTH_DRIVER = 2

# The ports for each service
_ports = {
    Lookups.RESET_DRIVER: 18861,
    Lookups.EYEBROWS_DRIVER: 18863,
    Lookups.MOUTH_DRIVER: 18862,
}

# The service names. These should be the same in this file, in the Kubernetes Service definitions, and in the Docker-compose tests.
_services = {
    Lookups.RESET_DRIVER: "reset-driver",
    Lookups.EYEBROWS_DRIVER: "eyebrows-driver",
    Lookups.MOUTH_DRIVER: "mouth-driver",
}

def lookup(item: Lookups):
    """
    Look up the given item and return a tuple of the form (host (str), port (int))
    Raise a KeyError if we can't find the given item.
    """
    if item not in _ports:
        raise KeyError(f"Item {item} cannot be found in Artie's DNS library. Allowable values: {_ports.keys()}")

    return _services[item], _ports[item]
