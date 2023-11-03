"""
All the code pertaining to the LCD submodule.
"""
from . import ebcommon
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import constants
from typing import List, Dict

CMD_MODULE_ID_LCD = 0x40

class LcdSubmodule:
    def __init__(self) -> None:
        self._left_display_state = None
        self._right_display_state = None

        self.left_display_status = constants.SubmoduleStatuses.UNKNOWN
        self.right_display_status = constants.SubmoduleStatuses.UNKNOWN

    def _set_status(self, side: str, status: constants.SubmoduleStatuses):
        if side == 'left':
            self.left_display_status = status
        else:
            self.right_display_status = status

    def self_check(self):
        # Store original values
        left_display = self._left_display_state
        right_display = self._right_display_state

        # Initializing should set our statuses appropriately
        alog.info("Checking LCD subsystem...")
        self.initialize()

        # Set back to originals
        if left_display is not None:
            self.draw('left', left_display)

        if right_display is not None:
            self.draw('right', right_display)

    def status(self) -> Dict[str, str]:
        return {
            "LCD-LEFT": self.left_display_status,
            "LCD-RIGHT": self.right_display_status,
        }

    def test(self, side: str) -> bool:
        alog.test(f"Received request for {side} LCD -> TEST.", tests=['eyebrows-driver-unit-tests:lcd-test'])
        address = ebcommon.get_address(side)
        lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
        wrote = i2c.write_bytes_to_address(address, lcd_test_bytes)
        if side.lower() == 'left':
            self._left_display_state = 'test'
        else:
            self._right_display_state = 'test'
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def off(self, side: str) -> bool:
        alog.test(f"Received request for {side} LCD -> OFF.", tests=['eyebrows-driver-unit-tests:lcd-off'])
        address = ebcommon.get_address(side)
        lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
        wrote = i2c.write_bytes_to_address(address, lcd_off_bytes)
        if side.lower() == 'left':
            self._left_display_state = 'clear'
        else:
            self._right_display_state = 'clear'
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def draw(self, side: str, eyebrow_state: List[str]) -> bool:
        alog.test(f"Received request for {side} LCD -> DRAW.", tests=['eyebrows-driver-unit-tests:lcd-draw'])
        address = ebcommon.get_address(side)
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
        wrote = i2c.write_bytes_to_address(address, lcd_draw_bytes)
        if side.lower() == 'left':
            self._left_display_state = eyebrow_state
        else:
            self._right_display_state = eyebrow_state
        self._set_status(side, constants.SubmoduleStatuses.WORKING if wrote else constants.SubmoduleStatuses.NOT_WORKING)
        return wrote

    def get(self, side: str) -> List[str]|str:
        side = side.lower()
        if side not in ('left', 'right'):
            errmsg = f"Invalid eyebrow side: {side}"
            alog.error(errmsg)
            return "error"
        elif side == 'left':
            state = self._left_display_state
        else:
            state = self._right_display_state
        alog.test(f"Received request for {side} eyebrow LCD -> State: {state}", tests=['eyebrows-driver-unit-tests:lcd-get'])
        return state

    def initialize(self):
        worked = True
        worked &= self.draw('left', ['M', 'H', 'M'])
        worked &= self.draw('right', ['M', 'H', 'M'])
        return worked
