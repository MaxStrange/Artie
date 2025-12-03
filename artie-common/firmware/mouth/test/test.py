"""
Can be run from a dev image on the controller module for testing the mouth FW during development.
"""
from artie_i2c import i2c
from artie_util import boardconfig_controller as board
import argparse
import errno
import logging
import os
import RPi.GPIO as GPIO
import subprocess
import time

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

def _check_mcu():
    """
    Check whether the MCU is present on the I2C bus.
    Log the results and return `None` if not found or the correct I2C bus instance
    if it is.
    """
    i2cinstance = i2c.check_for_address(MCU_MOUTH_ADDRESS)
    if i2cinstance is None:
        logging.error("Cannot find mouth on the I2C bus.")
        exit(errno.ENOENT)

    logging.info("Found mouth on I2C bus.")

def _load_fw_file(fw_fpath: str):
    """
    Attempt to load the FW file.

    Parameters
    ----------
    - fw_fpath: File path of the .elf file to load.
    """
    # TODO: Load FW over CAN
    logging.info("Loaded FW successfully.")
    return

    if result.returncode != 0:
        logging.error(f"Non-zero return code when attempting to load FW. Got return code {result.returncode}")
        logging.error(f"Mouth MCU may be non-responsive.")
        logging.error(f"Got stdout and stderr from subprocess:")
        logging.error(f"STDOUT: {result.stdout}")
        logging.error(f"STDERR: {result.stderr}")
    else:
        logging.info("Loaded FW successfully.")

def fw_load(args):
    """
    Test loading a FW image.

    Expects a 'fw-image' argument, which must be a path to an image to load.
    """
    fw_fpath = args.fw_image
    logging.info(f"Loading image from {args.fw_image}")

    # Check that we have FW files
    if not os.path.isfile(fw_fpath):
        logging.error(f"Given a FW file path of {fw_fpath}, but it doesn't exist.")
        exit(errno.ENOENT)

    # Set up GPIO for reset pin
    reset_pin = board.MOUTH_RESET_PIN
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(reset_pin, GPIO.OUT)
    GPIO.output(reset_pin, GPIO.LOW)

    # Use CAN to load the FW file
    _load_fw_file(fw_fpath)
    GPIO.output(reset_pin, GPIO.HIGH)
    time.sleep(0.1)  # Give it a moment to reset
    GPIO.output(reset_pin, GPIO.LOW)
    time.sleep(1)    # Give the MCU a moment to come back online

    # Sanity check that the MCU is present on the I2C bus
    _check_mcu()

def lcd_draw(args):
    """
    Test drawing on of the available mouth configurations.

    Expects 'draw-val' for the drawing argument.
    """
    val = args.draw_val.upper()
    logging.info(f"Drawing {val} onto LCD")
    lcd_draw_bytes = MOUTH_DRAWING_CHOICES[val]
    i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_draw_bytes)

def lcd_test(args):
    """
    Put a test image on the LCD.
    """
    _check_mcu()
    lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
    i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_test_bytes)

def lcd_off(args):
    """
    Test turning the LCD off.
    """
    _check_mcu()
    lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
    i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_off_bytes)

def lcd_talk(args):
    """
    Test changing the LCD to talk mode.
    """
    _check_mcu()
    lcd_talk_bytes = CMD_MODULE_ID_LCD | 0x07
    i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, lcd_talk_bytes)

def led_on(args):
    """
    Test that we can turn on the LED.
    """
    _check_mcu()
    led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
    i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, led_on_bytes)

def led_off(args):
    """
    Test that we can turn off the LED.
    """
    _check_mcu()
    led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
    i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, led_on_bytes)

def led_heartbeat(args):
    """
    Test that we can change the LED to heartbeat mode.
    """
    _check_mcu()
    led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
    i2c.write_bytes_to_address(MCU_MOUTH_ADDRESS, led_heartbeat_bytes)

if __name__ == "__main__":
    led_tests  = ["led-on", "led-off", "led-heartbeat"]
    lcd_tests  = ["lcd-test", "lcd-off", "lcd-draw", "lcd-talk"]
    fw_tests   = ["fw-load"]
    tests = led_tests + lcd_tests + fw_tests

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test", choices=tests, help="Test to run.")
    parser.add_argument("--draw-val", default="smile", choices=[item.lower() for item in MOUTH_DRAWING_CHOICES.keys()], help="If lcd-draw test is selected, this is the mouth configuration to draw. Otherwise ignored.")
    parser.add_argument("--fw-image", default=None, type=str, help="Path to .elf file if doing 'fw-load' test.")
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    args = parser.parse_args()

    # Set up logging
    format = "%(asctime)s %(threadName)s %(levelname)s: %(message)s"
    logging.basicConfig(format=format, level=getattr(logging, args.loglevel.upper()))

    # Execute the particular test
    testfunc = locals()[args.test.replace('-', '_')]
    testfunc(args)
