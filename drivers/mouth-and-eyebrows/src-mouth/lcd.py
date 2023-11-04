"""
All the code pertaining to the LCD Submodule.
"""
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import boardconfig_controller as board
from artie_util import constants

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

class LcdSubmodule:
    def __init__(self) -> None:
        self._current_display = None
        self._lcd_status = constants.SubmoduleStatuses.UNKNOWN

    def _set_status(self, worked: bool):
        if worked:
            self._lcd_status = constants.SubmoduleStatuses.WORKING
        else:
            self._lcd_status = constants.SubmoduleStatuses.NOT_WORKING

    def status(self):
        return {
            "LCD": self._lcd_status
        }

    def self_check(self):
        # Get current value
        prev_state = self._current_display

        # Run test (which will set our status appropriately)
        self.test()

        # Set back to previous value
        if prev_state == "TALKING":
            self.talk()
        elif prev_state is not None:
            self.draw(prev_state)

    def test(self) -> bool:
        alog.test("Received request for mouth LCD -> TEST.", tests=['mouth-driver-unit-tests:lcd-test'])
        lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
        worked = i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_test_bytes)
        self._set_status(worked)
        return worked

    def off(self) -> bool:
        alog.test("Received request for mouth LCD -> OFF.", tests=['mouth-driver-unit-tests:lcd-off'])
        lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
        worked = i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_off_bytes)
        self._set_status(worked)
        return worked

    def draw(self, val: str) -> bool:
        alog.test(f"Received request for mouth LCD -> Draw {val}", tests=['mouth-driver-unit-tests:lcd-draw-*'])
        lcd_draw_bytes = MOUTH_DRAWING_CHOICES.get(val, None)
        if lcd_draw_bytes is None:
            lcd_draw_bytes = MOUTH_DRAWING_CHOICES.get(val.upper(), None)

        if lcd_draw_bytes is None:
            alog.error(f"Cannot draw {val} - choose from: {MOUTH_DRAWING_CHOICES}")
            return False

        worked = i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_draw_bytes)
        self._current_display = val
        self._set_status(worked)
        return worked

    def get(self) -> str:
        alog.test(f"Received request for mouth LCD -> {self._current_display}", tests=['mouth-driver-unit-tests:lcd-get'])
        return self._current_display

    def talk(self) -> bool:
        alog.test("Received request for mouth LCD -> Talking mode.", tests=['mouth-driver-unit-tests:lcd-draw-talk'])
        lcd_talk_bytes = CMD_MODULE_ID_LCD | 0x07
        worked = i2c.write_bytes_to_address(board.I2C_ADDRESS_MOUTH_MCU, lcd_talk_bytes)
        self._current_display = "TALKING"
        self._set_status(worked)
        return worked
