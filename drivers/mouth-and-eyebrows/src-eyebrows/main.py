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
has access to both SWD and I2C on the Controller Node.
"""
from artie_driver_client import client as adc
from artie_i2c import i2c
from artie_swd import swd
from artie_util import artie_logging as alog
from artie_util import boardconfig_controller as board
from artie_util import util
import argparse
import numpy as np
import os
import rpyc
import time

SERVICE_NAME = "eyebrows-service"

# I2C address for each eyebrow MCU
MCU_ADDRESS_MAP = {
    "left": board.I2C_ADDRESS_EYEBROWS_MCU_LEFT,
    "right": board.I2C_ADDRESS_EYEBROWS_MCU_RIGHT,
}

CMD_MODULE_ID_LEDS = 0x00
CMD_MODULE_ID_LCD = 0x40
CMD_MODULE_ID_SERVO = 0x80

@rpyc.service
class DriverServer(rpyc.Service):
    def __init__(self, fw_fpath: str, ipv6=False):
        self._fw_fpath = fw_fpath
        self._ipv6 = ipv6

        # Load FW
        self._initialize_mcus()

    @rpyc.exposed
    @alog.function_counter("whoami")
    def whoami(self) -> str:
        """
        Return the name of this service and the version.
        """
        return f"artie-eyebrow-driver:{util.get_git_tag()}"

    @rpyc.exposed
    @alog.function_counter("led_on")
    def led_on(self, side: str):
        """
        RPC method to turn led on.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        alog.test(f"Received request for {side} LED -> ON.", tests=['eyebrows-driver-unit-tests:led-on'])
        address = self._get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
        i2c.write_bytes_to_address(address, led_on_bytes)

    @rpyc.exposed
    @alog.function_counter("led_off")
    def led_off(self, side: str):
        """
        RPC method to turn led off.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        alog.test(f"Received request for {side} LED -> OFF.", tests=['eyebrows-driver-unit-tests:led-off'])
        address = self._get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
        i2c.write_bytes_to_address(address, led_on_bytes)

    @rpyc.exposed
    @alog.function_counter("led_heartbeat")
    def led_heartbeat(self, side: str):
        """
        RPC method to turn the led to heartbeat mode.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        alog.test(f"Received request for {side} LED -> HEARTBEAT.", tests=['eyebrows-driver-unit-tests:led-heartbeat'])
        address = self._get_address(side)
        led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
        i2c.write_bytes_to_address(address, led_heartbeat_bytes)

    @rpyc.exposed
    @alog.function_counter("lcd_test")
    def lcd_test(self, side: str):
        """
        RPC method to test the LCD.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        alog.test(f"Received request for {side} LCD -> TEST.", tests=['eyebrows-driver-unit-tests:lcd-test'])
        address = self._get_address(side)
        lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
        i2c.write_bytes_to_address(address, lcd_test_bytes)

    @rpyc.exposed
    @alog.function_counter("lcd_off")
    def lcd_off(self, side: str):
        """
        RPC method to turn the LCD off.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        alog.test(f"Received request for {side} LCD -> OFF.", tests=['eyebrows-driver-unit-tests:lcd-off'])
        address = self._get_address(side)
        lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
        i2c.write_bytes_to_address(address, lcd_off_bytes)

    @rpyc.exposed
    @alog.function_counter("lcd_draw")
    def lcd_draw(self, side: str, eyebrow_state):
        """
        RPC method to draw a specified eyebrow state to the LCD.

        Args
        ----
        - side: One of 'left' or 'right'
        - eyebrow_state: A list of 'H' or 'L'
        """
        alog.test(f"Received request for {side} LCD -> DRAW.", tests=['eyebrows-driver-unit-tests:lcd-draw'])
        address = self._get_address(side)
        # An eyebrow state is encoded as follows:
        # Six bits (3 msb, 3 lsb)
        # The 3 lsb determine UP (1) or DOWN (0) for each of the three vertex pairs
        # The 3 msb override the corresponding lsb to show MIDDLE if set.
        # HOWEVER, if an msb is set, its corresponding lsb must be cleared, otherwise
        # it is interpreted as one of the special LCD commands like OFF or TEST.
        lsbs = [0, 0, 0]
        msbs = [0, 0, 0]
        for i, pos in enumerate(eyebrow_state):
            if pos.startswith('H'):
                msbs[i] = 0
                lsbs[i] = 1
            elif pos.startswith('L'):
                msbs[i] = 0
                lsbs[i] = 0
            else:
                msbs[i] = 1
                lsbs[i] = 0

        eyebrow_state_bytes = 0x00
        all = lsbs + msbs
        for i in range(len(all)):
            if all[i] == 1:
                eyebrow_state_bytes |= (0x01 << i)

        lcd_draw_bytes = CMD_MODULE_ID_LCD | eyebrow_state_bytes
        i2c.write_bytes_to_address(address, lcd_draw_bytes)

    @rpyc.exposed
    @alog.function_counter("firmware_load")
    def firmware_load(self):
        """
        RPC method to (re)load the FW on both MCUs.
        """
        alog.info("Reloading FW...")
        self._initialize_mcus()

    @rpyc.exposed
    @alog.function_counter("servo_go")
    def servo_go(self, side: str, servo_degrees: float):
        """
        RPC method to move the servo to the given location.

        Args
        ----
        - side: One of 'left' or 'right'
        - servo_degrees: Any value in the interval [0, 180]
        """
        alog.test(f"Received request for {side} SERVO -> GO.", tests=['eyebrows-driver-unit-tests:servo-go'])

        if servo_degrees < 0 or servo_degrees > 180:
            errmsg = f"Need a servo value in range [0, 180] but got {servo_degrees}"
            alog.error(errmsg)
            raise ValueError(errmsg)

        address = self._get_address(side)
        go_val_bytes = int(round(np.interp(servo_degrees, [0, 180], [0, 63]))) # map 0 to 180 into 0 to 63
        go_val_bytes = 0b00000000 if go_val_bytes < 0b00000000 else go_val_bytes
        go_val_bytes = 0b00111111 if go_val_bytes > 0b00111111 else go_val_bytes
        servo_go_bytes = CMD_MODULE_ID_SERVO | go_val_bytes
        i2c.write_bytes_to_address(address, servo_go_bytes)

    def _get_address(self, side: str):
        """
        Return the address corresponding to the given `side`.
        Raise a ValueError if 'side' is not one of 'left' or 'right'.
        """
        address = MCU_ADDRESS_MAP.get(side, None)
        if address is None:
            errmsg = f"Given side: '{side}', but must be 'left' or 'right'."
            alog.error(errmsg)
            raise ValueError(errmsg)
        else:
            return address

    def _check_mcu(self, mcu: str):
        """
        Check whether the given ('left' or 'right') MCU is present on the I2C bus.
        Log the results and return `None` if not found or the correct I2C bus instance
        if it is.
        """
        addr = MCU_ADDRESS_MAP[mcu]
        i2cinstance = i2c.check_for_address(addr)
        if i2cinstance is None:
            alog.error(f"Cannot find {mcu} on the I2C bus. Eyebrow will not be available.")

    def _initialize_mcus(self):
        """
        Attempt to load FW files into the two eyebrow MCUs.
        """
        # Check that we have FW files
        if not os.path.isfile(self._fw_fpath):
            msg = f"Given a FW file path of {self._fw_fpath}, but it doesn't exist."
            alog.error(msg)
            raise FileNotFoundError(msg)

        left_iface_fname = os.environ.get("SWD_CONFIG_LEFT", None)
        if left_iface_fname is None:
            alog.warning(f"The SWD_CONFIG_LEFT env variable is not set. Will attempt a default location/name.")
            left_iface_fname = "raspberrypi-swd.cfg"

        right_iface_fname = os.environ.get("SWD_CONFIG_RIGHT", None)
        if right_iface_fname is None:
            alog.warning(f"The SWD_CONFIG_RIGHT env variable is not set. Will attempt a default location/name.")
            right_iface_fname = "raspberrypi-right-swd.cfg"

        if util.in_test_mode():
            alog.test("Mocking MCU FW load.", tests=['eyebrows-driver-unit-tests:init-mcu'])

        # Use SWD to load the two FW files
        swd.load_fw_file(self._fw_fpath, left_iface_fname)
        swd.load_fw_file(self._fw_fpath, right_iface_fname)
        adc.reset(board.MCU_RESET_ADDR_RL_EYEBROWS, ipv6=self._ipv6)
        time.sleep(0.1)  # Give it a moment to come back online

        # Sanity check that both MCUs are present on the I2C bus
        self._check_mcu("left")
        self._check_mcu("right")

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
        i2c.manually_initialize(i2c_instances=[0], instance_to_address_map={0: [MCU_ADDRESS_MAP['left'], MCU_ADDRESS_MAP['right']]})

    # Instantiate the single (multi-tenant) server instance and block forever, serving
    server = DriverServer(args.fw_fpath, ipv6=args.ipv6)
    t = util.create_rpc_server(server, keyfpath, certfpath, args.port, ipv6=args.ipv6)
    t.start()
