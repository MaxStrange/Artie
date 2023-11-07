"""
Code pertaining to the FW subsystem.
"""
from artie_i2c import i2c
from artie_service_client import client as asc
from artie_swd import swd
from artie_util import artie_logging as alog
from artie_util import boardconfig_controller as board
from artie_util import constants
from artie_util import util
import os
import time

class FirmwareSubmodule:
    def __init__(self, fw_fpath: str) -> None:
        self._fw_fpath = fw_fpath
        self._fw_status = constants.SubmoduleStatuses.UNKNOWN

    def _set_status(self, worked: bool):
        if worked:
            self._fw_status = constants.SubmoduleStatuses.WORKING
        else:
            self._fw_status = constants.SubmoduleStatuses.NOT_WORKING

    def status(self):
        return {
            "FW": self._fw_status
        }

    def self_check(self):
        alog.test("Checking FW subsystem...", tests=['mouth-driver-unit-tests:self-check'])
        self._check_mcu()

    def load(self) -> bool:
        """
        Attempt to load the FW. Return True if we succeed. False if we fail.
        """
        alog.info("Loading FW...")

        # Check that we have FW files
        if not os.path.isfile(self._fw_fpath):
            alog.error(f"Given a FW file path of {self._fw_fpath}, but it doesn't exist.")
            return False

        mouth_iface_fname = os.environ.get("SWD_CONFIG_MOUTH", None)
        if mouth_iface_fname is None:
            alog.warning(f"The SWD_CONFIG_MOUTH env variable is not set. Will attempt a default location/name.")
            mouth_iface_fname = "raspberrypi-mouth-swd.cfg"

        if util.in_test_mode():
            alog.test("Mocking MCU FW load.", tests=['mouth-driver-unit-tests:init-mcu'])

        # Use SWD to load the FW file
        worked = swd.load_fw_file(self._fw_fpath, mouth_iface_fname)
        worked &= asc.reset(board.MCU_RESET_ADDR_MOUTH, ipv6=self._ipv6)
        time.sleep(0.1)  # Give it a moment to come back online

        # Sanity check that the MCU is present on the I2C bus
        worked &= self._check_mcu()
        self._set_status(worked)
        return worked

    def _check_mcu(self) -> bool:
        """
        Check whether the MCU is present on the I2C bus.
        Log the results and return `False` if not found or `True`
        if it is.
        """
        i2cinstance = i2c.check_for_address(board.I2C_ADDRESS_MOUTH_MCU)
        if i2cinstance is None:
            alog.error("Cannot find mouth on the I2C bus. Mouth will not be available.")
            self._set_status(False)
            return False
        self._set_status(True)
        return True
