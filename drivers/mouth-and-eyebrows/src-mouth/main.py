"""
User-space driver for Artie's mouth MCU.

This driver is responsible for:

* Loading mouth MCU firmware
* Animating the mouth
* Reading sensor values from mouth PCB

This driver accepts ZeroRPC requests and controls the
MCU over the Controller Node's I2C bus. It is therefore
meant to be run on the Controller Node, and it needs to
be run inside a container that has access to both SWD
and I2C on the Controller Node.
"""
from artie_i2c import i2c
from artie_util import boardconfig_controller as board
import argparse
import errno
import logging
import os
import RPi.GPIO as GPIO
import struct
import subprocess
import time
import zerorpc

MCU_MOUTH_ADDRESS = 0x19

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

class DriverServer:
    def __init__(self, fw_fpath: str):
        # Set up GPIO for reset pin
        self._reset_pin = board.MOUTH_RESET_PIN
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._reset_pin, GPIO.OUT)
        GPIO.output(self._reset_pin, GPIO.LOW)

        # Load the FW file
        self.fw_fpath = fw_fpath
        self._i2c = self._initialize_mcu()

    def led_on(self):
        """
        RPC method to turn led on.
        """
        logging.info("Received request for mouth LED -> ON.")
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
        i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, led_on_bytes)

    def led_off(self):
        """
        RPC method to turn led off.
        """
        logging.info("Received request for mouth LED -> OFF.")
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
        i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, led_on_bytes)

    def led_heartbeat(self):
        """
        RPC method to turn the led to heartbeat mode.
        """
        logging.info("Received request for mouth LED -> HEARTBEAT.")
        led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
        i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, led_heartbeat_bytes)

    def lcd_test(self):
        """
        RPC method to test the LCD.
        """
        logging.info("Received request for mouth LCD -> TEST.")
        lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
        i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_test_bytes)

    def lcd_off(self):
        """
        RPC method to turn the LCD off.
        """
        logging.info("Received request for mouth LCD -> OFF.")
        lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
        i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_off_bytes)

    def lcd_draw(self, val: str):
        """
        RPC method to draw the given configuration on the mouth LCD.

        Args
        ----
        - val: One of the available MOUTH_DRAWING_CHOICES (a string).
        """
        logging.info(f"Received request for mouth LCD -> Draw {val}")
        lcd_draw_bytes = MOUTH_DRAWING_CHOICES[val]
        i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_draw_bytes)

    def lcd_talk(self):
        """
        RPC method to have the mouth enter talking mode on LCD.
        """
        logging.info("Received request for mouth LCD -> Talking mode.")
        lcd_talk_bytes = CMD_MODULE_ID_LCD | 0x07
        i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_talk_bytes)

    def firmware_load(self):
        """
        RPC method to (re)load the FW on the mouth MCU.
        """
        logging.info("Reloading FW...")
        self._initialize_mcu()

    def _load_fw_file(self, fw_fpath: str):
        """
        Attempt to load the FW file.

        Parameters
        ----------
        - fw_fpath: File path of the .elf file to load.
        """
        mouth_iface_fname = os.environ.get("SWD_CONFIG_MOUTH", "raspberrypi-mouth-swd.cfg")
        openocd_cmds = f'program {fw_fpath} verify reset exit'
        logging.info(f"Attempting to load {fw_fpath} into LEFT eyebrow MCU...")
        cmd = f'openocd -f interface/{mouth_iface_fname} -f target/rp2040.cfg -c '
        result = subprocess.run(cmd.split() + [openocd_cmds], capture_output=True, encoding='utf-8')

        if result.returncode != 0:
            logging.error(f"Non-zero return code when attempting to load FW. Got return code {result.returncode}")
            logging.error(f"Mouth MCU may be non-responsive.")
            logging.error(f"Got stdout and stderr from openocd subprocess:")
            logging.error(f"STDOUT: {result.stdout}")
            logging.error(f"STDERR: {result.stderr}")
        else:
            logging.info("Loaded FW successfully.")

    def _check_mcu(self):
        """
        Check whether the MCU is present on the I2C bus.
        Log the results and return `None` if not found or the correct I2C bus instance
        if it is.
        """
        i2cinstance = i2c.check_for_address(MCU_MOUTH_ADDRESS)
        if i2cinstance is None:
            logging.error("Cannot find mouth on the I2C bus. Mouth will not be available.")

        return i2cinstance

    def _initialize_mcu(self):
        """
        Attempt to load the FW file into the mouth MCU.

        Returns
        -------
        - The i2c instance of the mouth MCU
        """
        # Check that we have FW files
        if not os.path.isfile(self.fw_fpath):
            logging.error(f"Given a FW file path of {self.fw_fpath}, but it doesn't exist.")
            exit(errno.ENOENT)

        # Use SWD to load the FW file
        self._load_fw_file(self.fw_fpath)
        GPIO.output(self._reset_pin, GPIO.HIGH)
        time.sleep(0.1)  # Give it a moment to reset
        GPIO.output(self._reset_pin, GPIO.LOW)
        time.sleep(1)    # Give the MCU a moment to come back online

        # Sanity check that the MCU is present on the I2C bus
        i2cinstance = self._check_mcu()

        return i2cinstance

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fw_fpath", metavar="fw-fpath", type=str, help="The path to the FW file. It must be an .elf file.")
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=4243, help="The port to bind for the RPC server.")
    args = parser.parse_args()

    # Set up logging
    format = "%(asctime)s %(threadName)s %(levelname)s: %(message)s"
    logging.basicConfig(format=format, level=getattr(logging, args.loglevel.upper()))

    driver_server = DriverServer(args.fw_fpath)

    # Set up RPC client to accept method invocations
    server = zerorpc.Server(driver_server)
    server.bind(f"tcp://0.0.0.0:{args.port}")
    server.run()
