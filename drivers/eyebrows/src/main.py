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
from artie_i2c import i2c
import argparse
import errno
import logging
import numpy as np
import os
import subprocess
import zerorpc

# I2C address for each eyebrow MCU
MCU_ADDRESS_MAP = {
    "left": 0x17,
    "right": 0x18,
}

CMD_MODULE_ID_LEDS = 0x00
CMD_MODULE_ID_LCD = 0x40
CMD_MODULE_ID_SERVO = 0x80

class DriverServer:
    def __init__(self, fw_fpath: str):
        # Load the FW files
        self._left_i2c, self._right_i2c = self._initialize_mcus(fw_fpath)

    def led_on(self, side: str):
        """
        RPC method to turn led on.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        logging.info(f"Received request for {side} LED -> ON.")
        address = self._get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
        i2c.write_bytes_to_address(address, led_on_bytes)

    def led_off(self, side: str):
        """
        RPC method to turn led off.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        logging.info(f"Received request for {side} LED -> OFF.")
        address = self._get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
        i2c.write_bytes_to_address(address, led_on_bytes)

    def led_heartbeat(self, side: str):
        """
        RPC method to turn the led to heartbeat mode.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        logging.info(f"Received request for {side} LED -> HEARTBEAT.")
        address = self._get_address(side)
        led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
        i2c.write_bytes_to_address(address, led_heartbeat_bytes)

    def lcd_test(self, side: str):
        """
        RPC method to test the LCD.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        logging.info(f"Received request for {side} LCD -> TEST.")
        address = self._get_address(side)
        lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
        i2c.write_bytes_to_address(address, lcd_test_bytes)

    def lcd_off(self, side: str):
        """
        RPC method to turn the LCD off.

        Args
        ----
        - side: One of 'left' or 'right'
        """
        logging.info(f"Received request for {side} LCD -> OFF.")
        address = self._get_address(side)
        lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
        i2c.write_bytes_to_address(address, lcd_off_bytes)

    def lcd_draw(self, side: str, eyebrow_state):
        """
        RPC method to draw a specified eyebrow state to the LCD.

        Args
        ----
        - side: One of 'left' or 'right'
        - eyebrow_stat: A list of 'H' or 'L'
        """
        logging.info(f"Received request for {side} LCD -> DRAW.")
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

    def servo_go(self, side: str, servo_degrees: float):
        """
        RPC method to move the servo to the given location.

        Args
        ----
        - side: One of 'left' or 'right'
        - servo_degrees: Any value in the interval [0, 180]
        """
        logging.info(f"Received request for {side} SERVO -> GO.")

        if servo_degrees < 0 or servo_degrees > 180:
            errmsg = f"Need a servo value in range [0, 180] but got {servo_degrees}"
            logging.error(errmsg)
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
            logging.error(errmsg)
            raise ValueError(errmsg)
        else:
            return address

    def _load_fw_file(self, fw_fpath: str, side: str):
        """
        Attempt to load the FW file into the appropriate MCU.

        Parameters
        ----------
        - fw_fpath: File path of the .elf file to load.
        - side: Either 'right' or 'left'.

        """
        left_iface_fname = "raspberrypi-swd.cfg"
        right_iface_fname = "raspberrypi-right-swd.cfg"
        openocd_cmds = f'program {fw_fpath} verify reset exit'
        match side:
            case "left":
                logging.info(f"Attempting to load {fw_fpath} into LEFT eyebrow MCU...")
                cmd = f'openocd -f interface/{left_iface_fname} -f target/rp2040.cfg -c '
                result = subprocess.run(cmd.split() + [openocd_cmds], capture_output=True, encoding='utf-8')
            case "right":
                logging.info(f"Attempting to load {fw_fpath} into RIGHT eyebrow MCU...")
                cmd = f'openocd -f interface/{right_iface_fname} -f target/rp2040.cfg -c '
                result = subprocess.run(cmd.split() + [openocd_cmds], capture_output=True, encoding='utf-8')
            case _:
                errmsg = f"Invalid argument for MCU side. Given {side}, but must be 'left' or 'right'"
                logging.error(errmsg)
                raise ValueError(errmsg)

        if result.returncode != 0:
            logging.error(f"Non-zero return code when attempting to load FW. Got return code {result.returncode}")
            logging.error(f"{side.capitalize()} eyebrow MCU may be non-responsive.")
            logging.error(f"Got stdout and stderr from openocd subprocess:")
            logging.error(f"STDOUT: {result.stdout}")
            logging.error(f"STDERR: {result.stderr}")
        else:
            logging.info("Loaded FW successfully.")

    def _check_mcu(self, mcu: str):
        """
        Check whether the given ('left' or 'right') MCU is present on the I2C bus.
        Log the results and return `None` if not found or the correct I2C bus instance
        if it is.
        """
        addr = MCU_ADDRESS_MAP[mcu]
        i2cinstance = i2c.check_for_address(addr)
        if i2cinstance is None:
            logging.error(f"Cannot find {mcu} on the I2C bus. Eyebrow will not be available.")

        return i2cinstance

    def _initialize_mcus(self, fw_fpath: str):
        """
        Attempt to load FW files into the two eyebrow MCUs.

        Parameters
        ------
        - fw_fpath: The path to the FW file. It's the same for both eyebrow MCUs and must be an .elf file.

        Returns
        -------
        - (left i2c instance, right i2c instnce)
        """
        # Check that we have FW files
        if not os.path.isfile(fw_fpath):
            logging.error(f"Given a FW file path of {fw_fpath}, but it doesn't exist.")
            exit(errno.ENOENT)

        # Use SWD to load the two FW files
        self._load_fw_file(fw_fpath, "left")
        self._load_fw_file(fw_fpath, "right")

        # Sanity check that both MCUs are present on the I2C bus
        i2cinstance_l = self._check_mcu("left")
        i2cinstance_r = self._check_mcu("right")

        return i2cinstance_l, i2cinstance_r

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fw_fpath", metavar="fw-fpath", type=str, help="The path to the FW file. It must be an .elf file.")
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=4242, help="The port to bind for the RPC server.")
    args = parser.parse_args()

    # Set up logging
    format = "%(asctime)s %(threadName)s %(levelname)s: %(message)s"
    logging.basicConfig(format=format, level=getattr(logging, args.loglevel.upper()))

    driver_server = DriverServer(args.fw_fpath)

    # Set up RPC client to accept method invocations
    server = zerorpc.Server(driver_server)
    server.bind(f"tcp://0.0.0.0:{args.port}")
    server.run()
