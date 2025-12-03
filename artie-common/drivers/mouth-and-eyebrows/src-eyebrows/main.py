"""
User-space driver for Artie's eyebrows MCUs.

This driver is responsible for:

* Loading eyebrow MCU firmware
* Animating eyebrows
* Moving eyes

This driver accepts ZeroRPC requests and controls the
MCUs over the Controller Node's I2C bus. It is
therefore meant to be run on the Controller Node,
and it needs to be run inside a container that
has access to CAN on the Controller Node.
"""
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import util
from artie_util import rpycserver
from typing import Dict, List
from . import ebcommon
from . import fw
from . import lcd
from . import led
from . import servo
import argparse
import rpyc

SERVICE_NAME = "eyebrows-service"


@rpyc.service
class DriverServer(rpycserver.Service):
    def __init__(self, fw_fpath: str, ipv6=False):
        self._servo_submodule = servo.ServoSubmodule()
        self._led_submodule = led.LedSubmodule()
        self._lcd_submodule = lcd.LcdSubmodule()
        self._fw_submodule = fw.FirmwareSubmodule(fw_fpath, ipv6=ipv6)

        # Load FW
        self._fw_submodule.initialize_mcus()

        # Initialize
        self._led_submodule.initialize()
        self._lcd_submodule.initialize()

    @rpyc.exposed
    @alog.function_counter("whoami")
    def whoami(self) -> str:
        """
        Return the name of this service and the version.
        """
        return f"artie-eyebrow-driver:{util.get_git_tag()}"

    @rpyc.exposed
    @alog.function_counter("status")
    def status(self) -> Dict[str, str]:
        """
        Return the status of this service's submodules.
        """
        status = self._fw_submodule.status() | self._led_submodule.status() | self._lcd_submodule.status() | self._servo_submodule.status()
        alog.info(f"Received request for status. Status: {status}")
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
        self._servo_submodule.self_check()

    @rpyc.exposed
    @alog.function_counter("led_on")
    def led_on(self, side: str) -> bool:
        """
        RPC method to turn led on.

        Args
        ----
        - side: One of 'left' or 'right'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._led_submodule.on(side)

    @rpyc.exposed
    @alog.function_counter("led_off")
    def led_off(self, side: str) -> bool:
        """
        RPC method to turn led off.

        Args
        ----
        - side: One of 'left' or 'right'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._led_submodule.off(side)

    @rpyc.exposed
    @alog.function_counter("led_heartbeat")
    def led_heartbeat(self, side: str) -> bool:
        """
        RPC method to turn the led to heartbeat mode.

        Args
        ----
        - side: One of 'left' or 'right'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._led_submodule.heartbeat(side)

    @rpyc.exposed
    @alog.function_counter("led_get")
    def led_get(self, side: str) -> str:
        """
        RPC method to get the state of the given LED.
        """
        return self._led_submodule.get(side)

    @rpyc.exposed
    @alog.function_counter("lcd_test")
    def lcd_test(self, side: str) -> bool:
        """
        RPC method to test the LCD.

        Args
        ----
        - side: One of 'left' or 'right'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._lcd_submodule.test(side)

    @rpyc.exposed
    @alog.function_counter("lcd_off")
    def lcd_off(self, side: str) -> bool:
        """
        RPC method to turn the LCD off.

        Args
        ----
        - side: One of 'left' or 'right'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._lcd_submodule.off(side)

    @rpyc.exposed
    @alog.function_counter("lcd_draw")
    def lcd_draw(self, side: str, eyebrow_state: List[str]) -> bool:
        """
        RPC method to draw a specified eyebrow state to the LCD.

        Args
        ----
        - side: One of 'left' or 'right'
        - eyebrow_state: A list of 'H' or 'L' or 'M'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._lcd_submodule.draw(side, eyebrow_state)

    @rpyc.exposed
    @alog.function_counter("lcd_get")
    def lcd_get(self, side: str) -> List[str]|str:
        """
        RPC method to get the LCD value that we think
        we are displaying on the given side. Will return either
        a list of vertices, 'test', 'clear', or 'error'.
        """
        return self._lcd_submodule.get(side)

    @rpyc.exposed
    @alog.function_counter("firmware_load")
    def firmware_load(self) -> bool:
        """
        RPC method to (re)load the FW on both MCUs. This will also
        reinitialize the LCDs and LEDs.

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        alog.info("Reloading FW...")
        worked = self._fw_submodule.initialize_mcus()

        # Initialize
        worked &= self._led_submodule.initialize()
        worked &= self._lcd_submodule.initialize()

        return worked

    @rpyc.exposed
    @alog.function_counter("servo_get")
    def servo_get(self, side: str) -> float:
        """
        RPC method to get the servo's degrees. This could be off
        due to inaccuracies of the servo, but also due to limiting on the left
        and right extreme ends as found during servo calibration.

        Returns
        -------
        Degrees (float).
        """
        return self._servo_submodule.get(side)

    @rpyc.exposed
    @alog.function_counter("servo_go")
    def servo_go(self, side: str, servo_degrees: float) -> bool:
        """
        RPC method to move the servo to the given location.

        Args
        ----
        - side: One of 'left' or 'right'
        - servo_degrees: Any value in the interval [0, 180]

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._servo_submodule.go(side, servo_degrees)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fw_fpath", metavar="fw-fpath", type=str, help="The path to the FW file. It must be an .elf file.")
    parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=18863, help="The port to bind for the RPC server.")
    args = parser.parse_args()

    # Set up logging
    alog.init(SERVICE_NAME, args)

    # Generate our self-signed certificate (if not already present)
    certfpath = "/etc/cert.pem"
    keyfpath = "/etc/pkey.pem"
    util.generate_self_signed_cert(certfpath, keyfpath, days=None, force=True)

    # If we are in testing mode, we need to manually initialize some stuff
    if util.in_test_mode():
        i2c.manually_initialize(i2c_instances=[0], instance_to_address_map={0: [ebcommon.MCU_ADDRESS_MAP['left'], ebcommon.MCU_ADDRESS_MAP['right']]})

    # Instantiate the single (multi-tenant) server instance and block forever, serving
    server = DriverServer(args.fw_fpath, ipv6=args.ipv6)
    t = util.create_rpc_server(server, keyfpath, certfpath, args.port, ipv6=args.ipv6)
    t.start()
