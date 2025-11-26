"""
Code pertaining to the servo submodule.
"""
from . import ebcommon
from artie_util import artie_logging as alog
from artie_util import constants
from artie_i2c import i2c
from typing import Dict
import numpy as np

CMD_MODULE_ID_SERVO = 0x80

class ServoSubmodule:
    def __init__(self) -> None:
        self._left_servo_degrees = 90.0
        self._right_servo_degrees = 90.0

        self.left_servo_status = constants.SubmoduleStatuses.UNKNOWN
        self.right_servo_status = constants.SubmoduleStatuses.UNKNOWN

    def _set_status(self, side: str, status: constants.SubmoduleStatuses):
        if side == 'left':
            self.left_servo_status = status
        else:
            self.right_servo_status = status

    def self_check(self):
        # Go to our current position, which shouldn't really move the
        # servos, but should set our statuses appropriately in case we can't write to
        # the I2C bus.
        alog.test("Checking servo subsystem...", tests=['eyebrows-driver-unit-tests:self-check'])
        self.go('left', self._left_servo_degrees)
        self.go('right', self._right_servo_degrees)

    def status(self) -> Dict[str, str]:
        return {
            "LEFT-SERVO": self.left_servo_status,
            "RIGHT-SERVO": self.right_servo_status,
        }

    def get(self, side: str) -> float:
        side = side.lower()
        if side not in ('left', 'right'):
            errmsg = f"Invalid side for servo: {side}"
            alog.error(errmsg)
            return -1.0
        elif side == 'left':
            degrees = self._left_servo_degrees
        else:
            degrees = self._right_servo_degrees
        alog.test(f"Received request for {side} servo position -> {degrees:0.2f}", tests=['eyebrows-driver-unit-tests:servo-get'])
        return degrees

    def go(self, side: str, servo_degrees: float) -> bool:
        alog.test(f"Received request for {side} SERVO -> GO.", tests=['eyebrows-driver-unit-tests:servo-go'])

        if servo_degrees < 0 or servo_degrees > 180:
            errmsg = f"Need a servo value in range [0, 180] but got {servo_degrees}"
            alog.error(errmsg)
            return False

        address = ebcommon.get_address(side)
        go_val_bytes = int(round(np.interp(servo_degrees, [0, 180], [0, 63]))) # map 0 to 180 into 0 to 63
        go_val_bytes = 0b00000000 if go_val_bytes < 0b00000000 else go_val_bytes
        go_val_bytes = 0b00111111 if go_val_bytes > 0b00111111 else go_val_bytes
        servo_go_bytes = CMD_MODULE_ID_SERVO | go_val_bytes
        wrote = i2c.write_bytes_to_address(address, servo_go_bytes)
        if side.lower() == 'left':
            self._left_servo_degrees = servo_degrees
        else:
            self._right_servo_degrees = servo_degrees
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote
