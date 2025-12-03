"""
Code pertaining to the firmware submodule.
"""
from artie_util import artie_logging as alog
from artie_util import util
from artie_util import boardconfig_controller as board
from artie_util import constants
from artie_i2c import i2c
from artie_service_client import client as asc
from . import ebcommon
from typing import Dict
import os
import time

class FirmwareSubmodule:
    def __init__(self, fw_fpath: str, ipv6=False) -> None:
        self._fw_fpath = fw_fpath
        self._left_status = constants.SubmoduleStatuses.UNKNOWN
        self._right_status = constants.SubmoduleStatuses.UNKNOWN
        self.firmware_status = constants.SubmoduleStatuses.UNKNOWN
        self._ipv6 = ipv6

    def _set_mcu_status(self, mcu: str, status):
        if mcu == 'left':
            self._left_status = status
        else:
            self._right_status = status

    def _check_mcu(self, mcu: str) -> bool:
        """
        Check whether the given ('left' or 'right') MCU is present on the I2C bus.
        Log the results and return `None` if not found or the correct I2C bus instance
        if it is.
        """
        addr = ebcommon.MCU_ADDRESS_MAP[mcu]
        i2cinstance = i2c.check_for_address(addr)
        if i2cinstance is None:
            alog.error(f"Cannot find {mcu} on the I2C bus. Eyebrow will not be available.")
            self._set_mcu_status(mcu, constants.SubmoduleStatuses.NOT_WORKING)
            return False
        else:
            self._set_mcu_status(mcu, constants.SubmoduleStatuses.WORKING)
            return True

    def self_check(self):
        alog.test("Checking FW subsystem...", tests=['eyebrows-driver-unit-tests:self-check'])
        self._check_mcu('left')
        self._check_mcu('right')
        if self._left_status == constants.SubmoduleStatuses.WORKING and self._right_status == constants.SubmoduleStatuses.WORKING:
            self.firmware_status = constants.SubmoduleStatuses.WORKING
        elif self._left_status == constants.SubmoduleStatuses.NOT_WORKING and self._right_status == constants.SubmoduleStatuses.NOT_WORKING:
            self.firmware_status = constants.SubmoduleStatuses.NOT_WORKING
        else:
            self.firmware_status = constants.SubmoduleStatuses.DEGRADED

    def status(self) -> Dict[str, str]:
        return {
            "FW": self.firmware_status
        }

    def initialize_mcus(self) -> bool:
        """
        Attempt to load FW files into the two eyebrow MCUs.
        """
        worked = True
        # Check that we have FW files
        if not os.path.isfile(self._fw_fpath):
            alog.error(f"Given a FW file path of {self._fw_fpath}, but it doesn't exist. Unlikely that we can operate the eyebrows.")
            return False

        if util.in_test_mode():
            alog.test("Mocking MCU FW load.", tests=['eyebrows-driver-unit-tests:init-mcu'])

        # Use CAN to load the two FW files
        # TODO
        pass

        # Reset the eyebrows
        worked &= asc.reset(board.MCU_RESET_ADDR_RL_EYEBROWS, ipv6=self._ipv6)
        time.sleep(0.1)  # Give it a moment to come back online

        # Sanity check that both MCUs are present on the I2C bus
        worked &= self._check_mcu("left")
        worked &= self._check_mcu("right")
        return worked
