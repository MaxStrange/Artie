"""
Code pertaining to the LED Submodule.
"""
from . import ebcommon
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import constants
from typing import Dict
import time

CMD_MODULE_ID_LEDS = 0x00

class LedSubmodule:
    def __init__(self) -> None:
        self._left_led_state = None
        self._right_led_state = None

        self.left_led_status = constants.SubmoduleStatuses.UNKNOWN
        self.right_led_status = constants.SubmoduleStatuses.UNKNOWN

    def _self_check_one_side(self, side: str):
        prev_state = self._left_led_state if side == 'left' else self._right_led_state
        self.on(side)
        time.sleep(0.1)
        self.off(side)
        time.sleep(0.1)
        match prev_state:
            case 'on':
                self.on(side)
            case 'off':
                self.off(side)
            case 'heartbeat':
                self.heartbeat(side)

    def _set_status(self, side: str, status: constants.SubmoduleStatuses):
        if side == 'left':
            self.left_led_status = status
        else:
            self.right_led_status = status

    def self_check(self):
        alog.test("Checking LED subsystem...", tests=['eyebrows-driver-unit-tests:self-check'])
        self._self_check_one_side('left')
        self._self_check_one_side('right')

    def status(self) -> Dict[str, str]:
        return {
            "LED-LEFT": self.left_led_status,
            "LED-RIGHT": self.right_led_status,
        }

    def initialize(self) -> bool:
        worked = True
        worked &= self.heartbeat('left')
        worked &= self.heartbeat('right')
        return worked

    def on(self, side: str) -> bool:
        alog.test(f"Received request for {side} LED -> ON.", tests=['eyebrows-driver-unit-tests:led-on'])
        address = ebcommon.get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
        wrote = i2c.write_bytes_to_address(address, led_on_bytes)
        if side.lower() == 'left':
            self._left_led_state = 'on'
        else:
            self._right_led_state = 'on'
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def off(self, side: str) -> bool:
        alog.test(f"Received request for {side} LED -> OFF.", tests=['eyebrows-driver-unit-tests:led-off'])
        address = ebcommon.get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
        wrote = i2c.write_bytes_to_address(address, led_on_bytes)
        if side.lower() == 'left':
            self._left_led_state = 'off'
        else:
            self._right_led_state = 'off'
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def heartbeat(self, side: str) -> bool:
        alog.test(f"Received request for {side} LED -> HEARTBEAT.", tests=['eyebrows-driver-unit-tests:led-heartbeat'])
        address = ebcommon.get_address(side)
        led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
        wrote = i2c.write_bytes_to_address(address, led_heartbeat_bytes)
        if side.lower() == 'left':
            self._left_led_state = 'heartbeat'
        else:
            self._right_led_state = 'heartbeat'
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def get(self, side: str) -> str:
        side = side.lower()
        if side not in ('left', 'right'):
            errmsg = f"Invalid eyebrow side: {side}"
            alog.error(errmsg)
            return errmsg
        elif side == 'left':
            alog.test(f"Received request for {side} LED -> State: {self._left_led_state}", tests=['eyebrows-driver-unit-tests:led-get'])
            return self._left_led_state
        else:
            alog.test(f"Received request for {side} LED -> State: {self._right_led_state}", tests=['eyebrows-driver-unit-tests:led-get'])
            return self._right_led_state
