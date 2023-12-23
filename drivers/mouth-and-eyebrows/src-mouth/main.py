"""
User-space driver for Artie's mouth MCU.

This driver is responsible for:

* Loading mouth MCU firmware
* Animating the mouth

This driver accepts ZeroRPC requests and controls the
MCU over the Controller Node's I2C bus. It is therefore
meant to be run on the Controller Node, and it needs to
be run inside a container that has access to both SWD
and I2C on the Controller Node.
"""
from artie_i2c import i2c
from artie_util import boardconfig_controller as board
from artie_util import artie_logging as alog
from artie_util import rpycserver
from artie_util import util
from typing import Dict
from . import fw
from . import lcd
from . import led
import argparse
import rpyc

SERVICE_NAME = "mouth-driver"

@rpyc.service
class DriverServer(rpycserver.Service):
    def __init__(self, fw_fpath: str, ipv6=False):
        self._fw_submodule = fw.FirmwareSubmodule(fw_fpath, ipv6=ipv6)
        self._led_submodule = led.LedSubmodule()
        self._lcd_submodule = lcd.LcdSubmodule()

        # Load the FW file
        self._fw_submodule.load()

        # Set up the starting display
        self.lcd_draw("SMILE")

        # Set up the LED
        self.led_heartbeat()

    @rpyc.exposed
    @alog.function_counter("whoami")
    def whoami(self) -> str:
        """
        Return the name of this service and the version.
        """
        return f"artie-mouth-driver:{util.get_git_tag()}"

    @rpyc.exposed
    @alog.function_counter("status")
    def status(self) -> Dict[str, str]:
        """
        Return the status of this service's submodules.
        """
        status = self._fw_submodule.status() | self._led_submodule.status() | self._lcd_submodule.status()
        alog.info(f"Received request for status: {status}")
        return {k: str(v) for k, v in status.items()}

    @rpyc.exposed
    @alog.function_counter("self_check")
    def self_check(self):
        """
        Run a self diagnostics check and set our submodule statuses appropriately.
        """
        alog.info("Running self check...")
        self._fw_submodule.self_check()
        self._led_submodule.self_check()
        self._lcd_submodule.self_check()

    @rpyc.exposed
    @alog.function_counter("led_on")
    def led_on(self) -> bool:
        """
        RPC method to turn led on.

        Returns
        ----
        True if it worked. False otherwise.
        """
        return self._led_submodule.on()

    @rpyc.exposed
    @alog.function_counter("led_off")
    def led_off(self) -> bool:
        """
        RPC method to turn led off.

        Returns
        ----
        True if it worked. False otherwise.

        """
        return self._led_submodule.off()

    @rpyc.exposed
    @alog.function_counter("led_heartbeat")
    def led_heartbeat(self) -> bool:
        """
        RPC method to turn the led to heartbeat mode.

        Returns
        ----
        True if it worked. False otherwise.

        """
        return self._led_submodule.heartbeat()

    @rpyc.exposed
    @alog.function_counter("led_get")
    def led_get(self) -> str:
        """
        RPC method to get the LED state.
        """
        return self._led_submodule.get()

    @rpyc.exposed
    @alog.function_counter("lcd_test")
    def lcd_test(self) -> bool:
        """
        RPC method to test the LCD.

        Returns
        ----
        True if it worked. False otherwise.
        """
        return self._lcd_submodule.test()

    @rpyc.exposed
    @alog.function_counter("lcd_off")
    def lcd_off(self):
        """
        RPC method to turn the LCD off.

        Returns
        ----
        True if it worked. False otherwise.
        """
        return self._lcd_submodule.off()

    @rpyc.exposed
    @alog.function_counter("lcd_draw")
    def lcd_draw(self, val: str):
        """
        RPC method to draw the given configuration on the mouth LCD.

        Args
        ----
        - val: One of the available MOUTH_DRAWING_CHOICES (a string).

        Returns
        ----
        True if it worked. False otherwise.
        """
        return self._lcd_submodule.draw(val)

    @rpyc.exposed
    @alog.function_counter("lcd_get")
    def lcd_get(self) -> str:
        """
        RPC method to get the current value we think we are drawing.
        """
        return self._lcd_submodule.get()

    @rpyc.exposed
    @alog.function_counter("lcd_talk")
    def lcd_talk(self):
        """
        RPC method to have the mouth enter talking mode on LCD.

        Returns
        ----
        True if it worked. False otherwise.

        """
        return self._lcd_submodule.talk()

    @rpyc.exposed
    @alog.function_counter("firmware_load")
    def firmware_load(self):
        """
        RPC method to (re)load the FW on the mouth MCU.
        This will also reinitialize the LED and LCD.

        Returns
        ----
        True if it worked. False otherwise.

        """
        worked = self._fw_submodule.load()

        # Set up the starting display
        self.lcd_draw("SMILE")

        # Set up the LED
        self.led_heartbeat()

        return worked


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fw_fpath", metavar="fw-fpath", type=str, help="The path to the FW file. It must be an .elf file.")
    parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=18862, help="The port to bind for the RPC server.")
    args = parser.parse_args()

    # Set up logging
    alog.init(SERVICE_NAME, args)

    # Generate our self-signed certificate (if not already present)
    certfpath = "/etc/cert.pem"
    keyfpath = "/etc/pkey.pem"
    util.generate_self_signed_cert(certfpath, keyfpath, days=None, force=True)

    # If we are in testing mode, we need to manually initialize some stuff
    if util.in_test_mode():
        i2c.manually_initialize(i2c_instances=[0], instance_to_address_map={0: [board.I2C_ADDRESS_MOUTH_MCU]})

    # Instantiate the single (multi-tenant) server instance and block forever, serving
    server = DriverServer(args.fw_fpath, ipv6=args.ipv6)
    t = util.create_rpc_server(server, keyfpath, certfpath, args.port, ipv6=args.ipv6)
    t.start()
