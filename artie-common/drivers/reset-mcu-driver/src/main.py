"""
This is the user-space driver for the reset MCU,
which is responsible for routing reset commands
to the appropriate MCU in the system.

This driver is responsible for:

* Loading MCU firmware
* Sending reset requests, along with an MCU address to the MCU

This driver must be run on a node with CAN access.
"""
from artie_gpio import gpio
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import boardconfig_controller as board
from artie_util import constants
from artie_util import rpycserver
from artie_util import util
from typing import Dict
import argparse
import datetime
import os
import rpyc
import time

SERVICE_NAME = "reset-driver"

@rpyc.service
class ResetMcuDriver(rpycserver.Service):
    """
    This class is a Singleton service. Each time a client
    connects to our server, the one instance of this Service object
    is reused, but on a separate thread (from the thread pool).

    As such, this whole class (except for the initialization code)
    should be reentrant.
    """
    def __init__(self, fw_fpath: str) -> None:
        super().__init__()
        self._fw_fpath = fw_fpath
        self._reset_pin = board.RESET_RESET
        self._mcu_status = constants.SubmoduleStatuses.UNKNOWN

        # Initialize GPIO
        gpio.setup(self._reset_pin, gpio.OUT)
        gpio.output(self._reset_pin, gpio.LOW)

        # Initialize the MCU (load firmware and check that the MCU is present on the I2C bus)
        self._init_mcu()

    def _check_mcu(self):
        """
        Check whether the MCU is present on the I2C bus.
        Log the results.
        """
        i2cinstance = i2c.check_for_address(board.I2C_ADDRESS_RESET_MCU)
        if i2cinstance is None:
            alog.error("Cannot find reset MCU on the I2C bus. We may not be able to reset other MCUs.")
            self._mcu_status = constants.SubmoduleStatuses.NOT_WORKING
        else:
            self._mcu_status = constants.SubmoduleStatuses.WORKING

    def _init_mcu(self):
        """
        Attempt to initialize the reset MCU on the i2c bus. Raise an exception
        if something goes wrong.
        """
        if not os.path.isfile(self._fw_fpath):
            msg = f"Cannot find FW at specified fpath: {self._fw_fpath}"
            alog.error(msg)
            raise FileNotFoundError(msg)

        if util.in_test_mode():
            alog.test("Mocking MCU FW load.", tests=['reset-driver-unit-tests:init-mcu'])

        # Use CAN to load the FW file
        # TODO
        pass

        # Reset the MCU by toggling its reset pin
        gpio.output(self._reset_pin, gpio.HIGH)
        time.sleep(0.1)  # Give it a moment to reset
        gpio.output(self._reset_pin, gpio.LOW)
        time.sleep(1)    # Give the MCU a moment to come back online

        # Sanity check that the MCU is present on the I2C bus and set status
        self._check_mcu()

    def on_connect(self, conn):
        pass

    def on_disconnect(self, conn):
        pass

    @rpyc.exposed
    @alog.function_counter("whoami", alog.MetricSWCodePathAPIOrder.CALLS)
    def whoami(self) -> str:
        """
        Return the name of this service and the version.
        """
        return f"artie-reset-driver:{util.get_git_tag()}"

    @rpyc.exposed
    @alog.function_counter("status", alog.MetricSWCodePathAPIOrder.CALLS)
    def status(self) -> Dict[str, str]:
        """
        Return the status of this service's submodules.
        """
        return {"MCU": str(self._mcu_status)}

    @rpyc.exposed
    @alog.function_counter("self_check", alog.MetricSWCodePathAPIOrder.CALLS)
    def self_check(self):
        """
        Run a self diagnostics check and set our submodule statuses appropriately.
        """
        alog.test("Running self check...", tests=['reset-driver-unit-tests:self-check'])
        self._check_mcu()

    @rpyc.exposed
    @alog.function_counter("reset_target", alog.MetricSWCodePathAPIOrder.CALLS)
    def reset_target(self, addr) -> bool:
        """
        Attempts to reset the device at the given `addr`. See boardconfig_controller.py for the
        list of valid addresses. Returns `True` if we think we succeeded, otherwise `False`
        and we log whatever error we encountered.
        """
        if addr == board.MCU_RESET_BROADCAST:
            alog.test("Resetting ALL MCU-class devices", tests=['reset-all-mcus'])

        ts = datetime.datetime.now().timestamp()
        try:
            alog.test(f"Writing {hex(addr)} to {hex(board.I2C_ADDRESS_RESET_MCU)}", tests=['reset-single-mcu', '*-hardware-tests:init-mcu', '*-hardware-tests:fw-load'])
            i2c.write_bytes_to_address(board.I2C_ADDRESS_RESET_MCU, [addr])
        except Exception as e:
            alog.exception(f"Could not reset target {addr}", e, stack_trace=True)
            return False
        duration_s = datetime.datetime.now().timestamp() - ts
        alog.update_histogram(duration_s, "adc-reset", alog.MetricSWCodePathAPIOrder.LATENCY, unit=alog.Units.SECONDS, description="Durations of reset calls over the network.", attributes={"target_addr": hex(addr), alog.KnownMetricAttributes.FUNCTION_NAME: "reset_target"})
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fw_fpath", metavar="fw-fpath", type=str, help="The path to the FW file. It must be an .elf file.")
    parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=18861, help="The port to bind for the RPC server.")
    args = parser.parse_args()

    # Set up logging
    alog.init(SERVICE_NAME, args)

    # Generate our self-signed certificate (if not already present)
    certfpath = "/etc/cert.pem"
    keyfpath = "/etc/pkey.pem"
    util.generate_self_signed_cert(certfpath, keyfpath, days=None, force=True)

    # If we are in testing mode, we need to manually initialize some stuff
    if util.in_test_mode():
        i2c.manually_initialize(i2c_instances=[0], instance_to_address_map={0: [board.I2C_ADDRESS_RESET_MCU]})

    # Instantiate the single (multi-tenant) server instance and block forever, serving
    server = ResetMcuDriver(args.fw_fpath)
    t = util.create_rpc_server(server, keyfpath, certfpath, args.port, ipv6=args.ipv6)
    t.start()
