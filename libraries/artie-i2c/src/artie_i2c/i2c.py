"""
This module handles interfacing with an I2C bus,
or with simulating one for development purposes.
"""
from artie_util import util
import logging
import math
import smbus2

# The I2C bus
bus = None

def public_i2c_function(func):
    """
    Initializes the i2c bus if not already initialized.
    """
    def modified_function(*args, **kwargs):
        global bus
        if bus is None:
            bus = I2CBus()

        return func(*args, **kwargs)
    return modified_function

class I2CBus:
    def __init__(self) -> None:
        self.address_to_instance_map = None

        # Populate a hash table of all the addresses on the various bus instances
        self.i2c_instances = _detect_all_i2c_instances()
        self.instance_to_address_map = {instance: _detect_all_addresses_on_i2c_instance(instance) for instance in self.i2c_instances}
        self.address_to_instance_map = {}
        for instance, addresses in self.instance_to_address_map.items():
            for addr in addresses:
                self.address_to_instance_map[addr] = instance

        # Create an instance of smbus
        self._instance_to_bus_map = {instance: smbus2.SMBus(instance) for instance in self.i2c_instances}

    def write(self, address: int, data: int):
        """
        Write the data to the address.
        """
        # Determine how many bytes are in data
        val = 1 if ((data - 1) <= 0) else (data - 1)
        nbytes = int(math.ceil(math.log2(val) / 8))
        nbytes = 1 if nbytes <= 0 else nbytes

        # Sanity check address and convert to hex string
        assert address >= 0 and address <= 255, f"Address must be a single byte, but is the value {address}"
        hex_addr = hex(address)[2:]  # hex() leads with '0x', so strip that off as well

        # Get the bus instance that has the desired address
        instance = self.address_to_instance_map.get(hex_addr, None)
        if instance is None:
            logging.warning(f"Cannot find address 0x{hex_addr} on i2c bus. Trying to write anyway.")

        # Write to the given address on the i2c instance
        # If data is more than one byte, we need to use the first byte as the register
        # Otherwise, use the single byte write function
        if nbytes > 1:
            data_bytes = [int(b) for b in data.to_bytes(nbytes, 'big')]
            self._instance_to_bus_map[instance].write_i2c_block_data(address, data_bytes[0], data_bytes[1:])
        else:
            assert nbytes == 1
            self._instance_to_bus_map[instance].write_byte(address, data)


def _detect_all_i2c_instances():
    """
    Return a list of instances of the I2C bus on this device.
    """
    proc = util.run_cmd("i2cdetect -l")
    lines = proc.stdout.splitlines()
    instances = [line.strip().split()[0] for line in lines]
    return [int(inst.split("-")[1]) for inst in instances]

def _detect_all_addresses_on_i2c_instance(instance):
    """
    Return a list of addresses found on the given I2C instance.
    """
    proc = util.run_cmd(f"i2cdetect -y {instance}")
    addresses = []
    for line in proc.stdout.splitlines()[1:]:
        for val in line.split():
            if val != "--" and not val.endswith(':'):
                # Val is a hex string
                addresses.append(val.strip())
    return addresses

@public_i2c_function
def check_for_address(address: int):
    """
    Check all i2c instances for the given `address`. If found,
    we return the instance. If not, we return `None`.
    """
    if address < 0 or address > 255:
        logging.error(f"Address must be a single byte, but is the value {address}")
    hexaddr = hex(address)[2:]  # hex() leads with '0x', so strip that off as well
    return bus.address_to_instance_map.get(hexaddr, None)

@public_i2c_function
def list_all_instances():
    """
    Return all the instances of i2c bus we can find.
    """
    return bus.i2c_instances

@public_i2c_function
def list_all_addresses_on_instance(instance: int):
    """
    Return all the addresses we can find on the given instance of the i2c bus.
    """
    if instance not in bus.i2c_instances:
        raise ValueError(f"No i2c instance {instance} found.")
    else:
        return bus.instance_to_address_map[instance]

@public_i2c_function
def write_bytes_to_address(address: int, data: int):
    """
    Write the given bytes (which are actually an integer type) to the given address.
    """
    bus.write(address, data)
