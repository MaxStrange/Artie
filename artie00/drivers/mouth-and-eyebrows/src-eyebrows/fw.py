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
        self.left_status = constants.SubmoduleStatuses.UNKNOWN
        self.right_status = constants.SubmoduleStatuses.UNKNOWN
        self.firmware_status = constants.SubmoduleStatuses.UNKNOWN
        self._ipv6 = ipv6

    def _set_mcu_status(self, mcu: ebcommon.EyebrowSides, status):
        if mcu == ebcommon.EyebrowSides.LEFT:
            self.left_status = status
        else:
            self.right_status = status

    def _check_mcu(self, mcu: ebcommon.EyebrowSides) -> bool:
        """
        Check whether the given ('eyebrow-left' or 'eyebrow-right') MCU is present on the I2C bus.
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

    def self_check_all(self):
        alog.test("Checking FW subsystem...", tests=['eyebrows-driver-unit-tests:self-check'])
        self._check_mcu(ebcommon.EyebrowSides.LEFT)
        self._check_mcu(ebcommon.EyebrowSides.RIGHT)

    def self_check(self, mcu_id: ebcommon.EyebrowSides):
        """
        Run a self diagnostics check on the given MCU ID and set our submodule statuses appropriately.
        """
        alog.info(f"Checking FW subsystem for {mcu_id}...")
        self._check_mcu(mcu_id)
        if self.left_status == constants.SubmoduleStatuses.WORKING and self.right_status == constants.SubmoduleStatuses.WORKING:
            self.firmware_status = constants.SubmoduleStatuses.WORKING
        elif self.left_status == constants.SubmoduleStatuses.NOT_WORKING and self.right_status == constants.SubmoduleStatuses.NOT_WORKING:
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
            alog.test("Mocking MCU FW load.", tests=['eyebrows-driver-unit-tests:init-mcu', 'eyebrows-driver-integration-tests:mcu-reload-fw'])

        # Use CAN to load the two FW files
        # TODO
        pass

        # Reset the eyebrows
        worked &= self.reset(ebcommon.EyebrowSides.LEFT)
        worked &= self.reset(ebcommon.EyebrowSides.RIGHT)
        time.sleep(0.1)  # Give it a moment to come back online

        # Sanity check that both MCUs are present on the I2C bus
        worked &= self._check_mcu(ebcommon.EyebrowSides.LEFT)
        worked &= self._check_mcu(ebcommon.EyebrowSides.RIGHT)
        return worked

    def reset(self, mcu_id: ebcommon.EyebrowSides) -> bool:
        """
        Attempt to reset the given MCU. Return True if we succeed, False if we fail.
        """
        alog.info(f"Reseting {mcu_id} MCU.")

        # No CAN bus in test mode
        if util.in_test_mode():
            alog.test(f"Mocking a CAN call for reset: {mcu_id}", tests=['*-integration-tests:*'])
            return True

        # TODO: Use CAN to reset the MCUs
        worked = True
        return worked

    def version(self, mcu_id: ebcommon.EyebrowSides) -> str:
        """
        Return the firmware version information for the given MCU ID.
        """
        # In test mode, return a mock version
        if util.in_test_mode():
            alog.test("Mocking MCU FW version.", tests=[])  # TODO: Need to add test for this method
            return "1.2.3-mock"

        # TODO: Use CAN to get the version info
        return "unknown"
