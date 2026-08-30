"""
Code pertaining to the LED Submodule.
"""
from . import ebcommon
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import constants
import time

CMD_MODULE_ID_LEDS = 0x00

class LedSubmodule:
    def __init__(self) -> None:
        self._left_led_state = constants.StatusLEDStates.UNKNOWN
        self._right_led_state = constants.StatusLEDStates.UNKNOWN

        self.left_led_status = constants.SubmoduleStatuses.UNKNOWN
        self.right_led_status = constants.SubmoduleStatuses.UNKNOWN

    def _self_check_one_side(self, side: ebcommon.EyebrowSides):
        prev_state = self._left_led_state if side == ebcommon.EyebrowSides.LEFT else self._right_led_state
        self.on(side)
        time.sleep(0.1)
        self.off(side)
        time.sleep(0.1)
        match prev_state:
            case constants.StatusLEDStates.ON:
                self.on(side)
            case constants.StatusLEDStates.OFF:
                self.off(side)
            case constants.StatusLEDStates.HEARTBEAT:
                self.heartbeat(side)

    def _set_status(self, side: ebcommon.EyebrowSides, status: constants.SubmoduleStatuses):
        if side == ebcommon.EyebrowSides.LEFT:
            self.left_led_status = status
        else:
            self.right_led_status = status

    def self_check(self):
        alog.test("Checking LED subsystem...", tests=['eyebrows-driver-unit-tests:self-check'])
        self._self_check_one_side(ebcommon.EyebrowSides.LEFT)
        self._self_check_one_side(ebcommon.EyebrowSides.RIGHT)

    def status(self) -> dict[str, constants.SubmoduleStatuses]:
        return {
            "LED-LEFT": self.left_led_status,
            "LED-RIGHT": self.right_led_status,
        }

    def initialize(self) -> bool:
        worked = True
        worked &= self.heartbeat(ebcommon.EyebrowSides.LEFT)
        worked &= self.heartbeat(ebcommon.EyebrowSides.RIGHT)
        return worked

    def list(self) -> list[ebcommon.EyebrowSides]:
        return [ebcommon.EyebrowSides.LEFT, ebcommon.EyebrowSides.RIGHT]

    def on(self, side: ebcommon.EyebrowSides) -> bool:
        alog.test(f"Received request for {side} LED -> ON.", tests=['eyebrows-driver-unit-tests:led-on'])
        address = ebcommon.get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
        wrote = i2c.write_bytes_to_address(address, led_on_bytes)
        if side == ebcommon.EyebrowSides.LEFT:
            self._left_led_state = constants.StatusLEDStates.ON
        else:
            self._right_led_state = constants.StatusLEDStates.ON
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def off(self, side: ebcommon.EyebrowSides) -> bool:
        alog.test(f"Received request for {side} LED -> OFF.", tests=['eyebrows-driver-unit-tests:led-off'])
        address = ebcommon.get_address(side)
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
        wrote = i2c.write_bytes_to_address(address, led_on_bytes)
        if side == ebcommon.EyebrowSides.LEFT:
            self._left_led_state = constants.StatusLEDStates.OFF
        else:
            self._right_led_state = constants.StatusLEDStates.OFF
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def heartbeat(self, side: ebcommon.EyebrowSides) -> bool:
        alog.test(f"Received request for {side} LED -> HEARTBEAT.", tests=['eyebrows-driver-unit-tests:led-heartbeat'])
        address = ebcommon.get_address(side)
        led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
        wrote = i2c.write_bytes_to_address(address, led_heartbeat_bytes)
        if side == ebcommon.EyebrowSides.LEFT:
            self._left_led_state = constants.StatusLEDStates.HEARTBEAT
        else:
            self._right_led_state = constants.StatusLEDStates.HEARTBEAT
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def get(self, side: ebcommon.EyebrowSides) -> constants.StatusLEDStates:
        if side not in (ebcommon.EyebrowSides.LEFT, ebcommon.EyebrowSides.RIGHT):
            errmsg = f"Invalid eyebrow side: {side}"
            alog.error(errmsg)
            return errmsg
        elif side == ebcommon.EyebrowSides.LEFT:
            alog.test(f"Received request for {side} LED -> State: {self._left_led_state.value}", tests=['eyebrows-driver-unit-tests:led-get'])
            return self._left_led_state
        else:
            alog.test(f"Received request for {side} LED -> State: {self._right_led_state.value}", tests=['eyebrows-driver-unit-tests:led-get'])
            return self._right_led_state
