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
from artie_service_client import client as asc
from artie_gpio import gpio
from artie_i2c import i2c
from artie_swd import swd
from artie_util import boardconfig_controller as board
from artie_util import artie_logging as alog
from artie_util import rpycserver
from artie_util import util
import argparse
import os
import rpyc
import time

SERVICE_NAME = "mouth-driver"

CMD_MODULE_ID_LEDS = 0x00
CMD_MODULE_ID_LCD = 0x40

MOUTH_DRAWING_CHOICES = {
    "SMILE":        (CMD_MODULE_ID_LCD | 0x00),
    "FROWN":        (CMD_MODULE_ID_LCD | 0x01),
    "LINE":         (CMD_MODULE_ID_LCD | 0x02),
    "SMIRK":        (CMD_MODULE_ID_LCD | 0x03),
    "OPEN":         (CMD_MODULE_ID_LCD | 0x04),
    "OPEN-SMILE":   (CMD_MODULE_ID_LCD | 0x05),
    "ZIG-ZAG":      (CMD_MODULE_ID_LCD | 0x06),
}

@rpyc.service
class DriverServer(rpycserver.Service):
    def __init__(self, fw_fpath: str, ipv6=False):
        self._fw_fpath = fw_fpath
        self._ipv6 = ipv6
        self._current_display = None
        self._led_state = None

        # Load the FW file
        self._initialize_mcu()

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
    @alog.function_counter("led_on")
    def led_on(self):
        """
        RPC method to turn led on.
        """
        alog.test("Received request for mouth LED -> ON.", tests=['mouth-driver-unit-tests:led-on'])
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
        i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, led_on_bytes)
        self._led_state = 'on'

    @rpyc.exposed
    @alog.function_counter("led_off")
    def led_off(self):
        """
        RPC method to turn led off.
        """
        alog.test("Received request for mouth LED -> OFF.", tests=['mouth-driver-unit-tests:led-off'])
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
        i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, led_on_bytes)
        self._led_state = 'off'

    @rpyc.exposed
    @alog.function_counter("led_heartbeat")
    def led_heartbeat(self):
        """
        RPC method to turn the led to heartbeat mode.
        """
        alog.test("Received request for mouth LED -> HEARTBEAT.", tests=['mouth-driver-unit-tests:led-heartbeat'])
        led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
        i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, led_heartbeat_bytes)
        self._led_state = 'heartbeat'

    @rpyc.exposed
    @alog.function_counter("led_get")
    def led_get(self):
        """
        RPC method to get the LED state.
        """
        alog.test(f"Received request for mouth LED -> State: {self._led_state}", tests=['mouth-driver-unit-tests:led-get'])
        return self._led_state

    @rpyc.exposed
    @alog.function_counter("lcd_test")
    def lcd_test(self):
        """
        RPC method to test the LCD.
        """
        alog.test("Received request for mouth LCD -> TEST.", tests=['mouth-driver-unit-tests:lcd-test'])
        lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
        i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_test_bytes)

    @rpyc.exposed
    @alog.function_counter("lcd_off")
    def lcd_off(self):
        """
        RPC method to turn the LCD off.
        """
        alog.test("Received request for mouth LCD -> OFF.", tests=['mouth-driver-unit-tests:lcd-off'])
        lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
        i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_off_bytes)

    @rpyc.exposed
    @alog.function_counter("lcd_draw")
    def lcd_draw(self, val: str):
        """
        RPC method to draw the given configuration on the mouth LCD.

        Args
        ----
        - val: One of the available MOUTH_DRAWING_CHOICES (a string).
        """
        alog.test(f"Received request for mouth LCD -> Draw {val}", tests=['mouth-driver-unit-tests:lcd-draw-*'])
        lcd_draw_bytes = MOUTH_DRAWING_CHOICES.get(val, None)
        if lcd_draw_bytes is None:
            lcd_draw_bytes = MOUTH_DRAWING_CHOICES.get(val.upper(), None)

        if lcd_draw_bytes is None:
            raise ValueError(f"Cannot draw {val} - choose from: {MOUTH_DRAWING_CHOICES}")

        i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_draw_bytes)
        self._current_display = val

    @rpyc.exposed
    @alog.function_counter("lcd_get")
    def lcd_get(self) -> str:
        """
        RPC method to get the current value we think we are drawing.
        """
        alog.test(f"Received request for mouth LCD -> {self._current_display}", tests=['mouth-driver-unit-tests:lcd-get'])
        return self._current_display

    @rpyc.exposed
    @alog.function_counter("lcd_talk")
    def lcd_talk(self):
        """
        RPC method to have the mouth enter talking mode on LCD.
        """
        alog.test("Received request for mouth LCD -> Talking mode.", tests=['mouth-driver-unit-tests:lcd-draw-talk'])
        lcd_talk_bytes = CMD_MODULE_ID_LCD | 0x07
        i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_talk_bytes)
        self._current_display = "TALKING"

    @rpyc.exposed
    @alog.function_counter("firmware_load")
    def firmware_load(self):
        """
        RPC method to (re)load the FW on the mouth MCU.
        This will also reinitialize the LED and LCD.
        """
        alog.info("Reloading FW...")
        self._initialize_mcu()

        # Set up the starting display
        self.lcd_draw("SMILE")

        # Set up the LED
        self.led_heartbeat()

    def _check_mcu(self):
        """
        Check whether the MCU is present on the I2C bus.
        Log the results and return `None` if not found or the correct I2C bus instance
        if it is.
        """
        i2cinstance = i2c.check_for_address(board.I2C_ADDRESS_MOUTH_MCU)
        if i2cinstance is None:
            alog.error("Cannot find mouth on the I2C bus. Mouth will not be available.")

    def _initialize_mcu(self):
        """
        Attempt to load the FW file into the mouth MCU.

        Returns
        -------
        - The i2c instance of the mouth MCU
        """
        # Check that we have FW files
        if not os.path.isfile(self._fw_fpath):
            msg = f"Given a FW file path of {self._fw_fpath}, but it doesn't exist."
            alog.error(msg)
            raise FileNotFoundError(msg)

        mouth_iface_fname = os.environ.get("SWD_CONFIG_MOUTH", None)
        if mouth_iface_fname is None:
            alog.warning(f"The SWD_CONFIG_MOUTH env variable is not set. Will attempt a default location/name.")
            mouth_iface_fname = "raspberrypi-mouth-swd.cfg"

        if util.in_test_mode():
            alog.test("Mocking MCU FW load.", tests=['mouth-driver-unit-tests:init-mcu'])

        # Use SWD to load the FW file
        swd.load_fw_file(self._fw_fpath, mouth_iface_fname)
        asc.reset(board.MCU_RESET_ADDR_MOUTH, ipv6=self._ipv6)
        time.sleep(0.1)  # Give it a moment to come back online

        # Sanity check that the MCU is present on the I2C bus
        self._check_mcu()

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
