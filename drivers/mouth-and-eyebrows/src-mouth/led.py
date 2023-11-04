"""
Code pertaining to the LED subsystem.
"""
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import boardconfig_controller as board
from artie_util import constants
import time

CMD_MODULE_ID_LEDS = 0x00

class LedSubmodule:
    def __init__(self) -> None:
        self._led_state = None
        self._led_status = constants.SubmoduleStatuses.UNKNOWN

    def _set_status(self, worked: bool):
        if worked:
            self._led_status = constants.SubmoduleStatuses.WORKING
        else:
            self._led_status = constants.SubmoduleStatuses.NOT_WORKING

    def status(self):
        return {
            "LED": self._led_state
        }

    def self_check(self):
        # Store previous state
        prev_state = self._led_state

        # Turn on, then off
        self.on()
        time.sleep(0.1)
        self.off()
        time.sleep(0.1)

        # Set back to previous state
        match prev_state:
            case 'on':
                self.on()
            case 'off':
                self.off()
            case 'heartbeat':
                self.heartbeat()

    def on(self) -> bool:
        alog.test("Received request for mouth LED -> ON.", tests=['mouth-driver-unit-tests:led-on'])
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
        worked = i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, led_on_bytes)
        self._led_state = 'on'
        self._set_status(worked)
        return worked

    def off(self) -> bool:
        alog.test("Received request for mouth LED -> OFF.", tests=['mouth-driver-unit-tests:led-off'])
        led_on_bytes = CMD_MODULE_ID_LEDS | 0x01
        worked = i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, led_on_bytes)
        self._led_state = 'off'
        self._set_status(worked)
        return worked

    def heartbeat(self) -> bool:
        alog.test("Received request for mouth LED -> HEARTBEAT.", tests=['mouth-driver-unit-tests:led-heartbeat'])
        led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
        worked = i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, led_heartbeat_bytes)
        self._led_state = 'heartbeat'
        self._set_status(worked)
        return worked

    def get(self) -> str:
        alog.test(f"Received request for mouth LED -> State: {self._led_state}", tests=['mouth-driver-unit-tests:led-get'])
        return self._led_state
