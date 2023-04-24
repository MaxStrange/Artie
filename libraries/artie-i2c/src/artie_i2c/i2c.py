"""
This module handles interfacing with an I2C bus,
or with simulating one for development purposes.
"""
from artie_util import artie_logging as alog
from artie_util import util
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

class MockBus:
    """
    A mocked up smbus object for testing.
    """
    def __init__(self, instance: int) -> None:
        self.instance = instance

    def write_i2c_block_data(self, addr, register, data):
        alog.info(f"Mocking the write of some data to address {addr}, register {hex(register)} on i2c instance {self.instance}.")

    def write_byte(self, addr, data):
        alog.info(f"Mocking the write of a single byte of data ({data}) to {hex(addr)} on i2c instance {self.instance}.")


class I2CBus:
    def __init__(self, i2c_instances=None, instance_to_address_map=None) -> None:
        """
        Initialize the I2CBus object. By default, scans the I2C hardware bus
        to determine what addresses are present.

        For testing, pass in `i2c_instances` (list of int) and
        pass in the `instance_to_address_map` yourself.
        It should be a dict of the form {int: [addresses]}
        """
        self.address_to_instance_map = None

        # Populate a hash table of all the addresses on the various bus instances
        if i2c_instances is None:
            self.i2c_instances = _detect_all_i2c_instances()
        else:
            self.i2c_instances = i2c_instances

        if instance_to_address_map is None:
            self.instance_to_address_map = {instance: _detect_all_addresses_on_i2c_instance(instance) for instance in self.i2c_instances}
        else:
            self.instance_to_address_map = {}
            for instance, addresses in instance_to_address_map.items():
                converted_addresses = [hex(addr)[2:] for addr in addresses]
                self.instance_to_address_map[instance] = converted_addresses
        alog.info(f"Found i2c instances: {self.instance_to_address_map.keys()}")
        alog.info(f"i2c instances map to addresses: {self.instance_to_address_map}")

        # Reverse the mapping as well
        self.address_to_instance_map = {}
        for instance, addresses in self.instance_to_address_map.items():
            for addr in addresses:
                self.address_to_instance_map[addr] = instance

        # Create an instance of smbus
        try:
            self._instance_to_bus_map = {instance: smbus2.SMBus(instance) for instance in self.i2c_instances}
        except FileNotFoundError:
            self._instance_to_bus_map = {instance: MockBus(instance) for instance in self.i2c_instances}

    def write(self, address: int, data: list):
        """
        Write the data to the address.
        """
        nbytes = len(data)
        if nbytes == 0:
            raise ValueError("Got an empty list of data bytes.")

        # Sanity check each int to make sure each one is a single byte and is positive
        for b in data:
            if b < 0 or b > 255:
                errmsg = f"Each value in the `data` list should be a single, unsigned byte, but the value {b} cannot be interpreted as a single byte."
                alog.error(errmsg)
                raise ValueError(errmsg)

        # Sanity check address and convert to hex string
        assert address >= 0 and address <= 255, f"Address must be a single byte, but is the value {address}"
        hex_addr = hex(address)[2:]  # hex() leads with '0x', so strip that off as well

        # Get the bus instance that has the desired address
        instance = self.address_to_instance_map.get(hex_addr, None)
        if instance is None:
            alog.warning(f"Cannot find address 0x{hex_addr} on i2c bus. Trying to write anyway.")

        # Write to the given address on the i2c instance
        # If data is more than one byte, we need to use the first byte as the register
        # Otherwise, use the single byte write function
        alog.update_counter(nbytes, "i2c-byte-counter", unit=alog.Units.BYTES, description="Number of bytes written to i2c bus", attributes={"i2c.address": hex(address)})
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
                # Val is a hex string (without leading 0x)
                addresses.append(val.strip())
    return addresses

def manually_initialize(i2c_instances=None, instance_to_address_map=None):
    """
    For testing, pass in `i2c_instances` (list of int) and
    pass in the `instance_to_address_map` yourself.
    It should be a dict of the form {int: [addresses]}
    """
    alog.info(f"Manually initializing i2c library.")
    global bus
    bus = I2CBus(i2c_instances=i2c_instances, instance_to_address_map=instance_to_address_map)

@public_i2c_function
def check_for_address(address: int):
    """
    Check all i2c instances for the given `address`. If found,
    we return the instance. If not, we return `None`.
    """
    if address < 0 or address > 255:
        errmsg = f"Address must be a single (unsigned) byte, but is the value {address}"
        alog.error(errmsg)
        raise ValueError(errmsg)
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
def write_bytes_to_address(address: int, data: list):
    """
    Write the given bytes (which are actually a list of ints) to the given address.
    There should be at least one data value, and each value should be >= 0.
    If you need to write negative values to your device, convert the values
    using whatever means the device requires before calling this function.
    """
    try:
        _ = iter(data)
    except TypeError:
        data = [data]

    bus.write(address, data)
