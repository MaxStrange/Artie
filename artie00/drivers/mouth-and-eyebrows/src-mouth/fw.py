"""
Code pertaining to the FW subsystem.
"""
from artie_i2c import i2c
from artie_service_client import client as asc
from artie_util import artie_logging as alog
from artie_util import boardconfig_controller as board
from artie_util import constants
from artie_util import util
import os
import time

# TODO: Decide on proper MCU naming conventions
MOUTH_MCU_NAME = "mouth"

class FirmwareSubmodule:
    def __init__(self, fw_fpath: str, ipv6=False) -> None:
        self._fw_fpath = fw_fpath
        self._fw_status = constants.SubmoduleStatuses.UNKNOWN
        self._ipv6 = ipv6

    def _set_status(self, worked: bool):
        if worked:
            self._fw_status = constants.SubmoduleStatuses.WORKING
        else:
            self._fw_status = constants.SubmoduleStatuses.NOT_WORKING

    def status(self):
        if util.in_test_mode():
            alog.test("Mocking FW status.", tests=['mouth-driver-integration-tests:status'])

        return {
            "FW": self._fw_status
        }

    def self_check(self):
        alog.test("Checking FW subsystem...", tests=['mouth-driver-unit-tests:self-check', 'mouth-driver-integration-tests:self-check'])
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

        # No CAN bus in test mode
        if util.in_test_mode():
            alog.test("Mocking MCU FW load.", tests=['mouth-driver-unit-tests:init-mcu'])

        # Use CAN to load the FW file
        # TODO
        pass

        # Reset the MCU to start running the new FW
        worked = self.reset()
        time.sleep(0.1)  # Give it a moment to come back online

        # Sanity check that the MCU is present on the I2C bus
        worked &= self._check_mcu()
        self._set_status(worked)
        return worked

    def reset(self) -> bool:
        """
        Attempt to reset the MCU. Return True if we succeed, False if we fail.
        """
        alog.info(f"Reseting {board.MCU_RESET_ADDR_MOUTH}")

        # No CAN bus in test mode
        if util.in_test_mode():
            alog.test("Mocking a CAN call for reset.", tests=['*-integration-tests:*'])
            return True

        # TODO: Use CAN to reset the MCU
        worked = True
        return worked

    def version(self) -> str:
        """
        Return the firmware version string of the MCU.
        """
        # No CAN bus in test mode
        if util.in_test_mode():
            alog.test("Mocking a CAN call for version.", tests=['mouth-driver-integration-tests:mcu-version'])
            return "MOUTH_MCU_FW_V1.0.0-MOCK"

        # TODO: Use CAN to get the version string
        version_str = "unknown"
        return version_str

    def _check_mcu(self) -> bool:
        """
        Check whether the MCU is present on the I2C bus.
        Log the results and return `False` if not found or `True`
        if it is.
        """
        # TODO: Update to use CAN
        i2cinstance = i2c.check_for_address(board.I2C_ADDRESS_MOUTH_MCU)
        if i2cinstance is None:
            alog.error("Cannot find mouth on the I2C bus. Mouth will not be available.")
            self._set_status(False)
            return False
        self._set_status(True)
        return True
