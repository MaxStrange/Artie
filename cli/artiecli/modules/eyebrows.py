from .hardware import i2c
import argparse
import numpy as np

EYEBROWS_ADDRESS_LEFT = 0x17
EYEBROWS_ADDRESS_RIGHT = 0x18
CMD_MODULE_ID_LEDS = 0x00
CMD_MODULE_ID_LCD = 0x40
CMD_MODULE_ID_SERVO = 0x80

def _cmd_led_on(args):
    address = EYEBROWS_ADDRESS_LEFT if args.side == "LEFT" else EYEBROWS_ADDRESS_RIGHT
    led_on_bytes = CMD_MODULE_ID_LEDS | 0x00
    i2c.write_bytes_to_address(address, led_on_bytes)

def _cmd_led_off(args):
    address = EYEBROWS_ADDRESS_LEFT if args.side == "LEFT" else EYEBROWS_ADDRESS_RIGHT
    led_off_bytes = CMD_MODULE_ID_LEDS | 0x01
    i2c.write_bytes_to_address(address, led_off_bytes)

def _cmd_led_heartbeat(args):
    address = EYEBROWS_ADDRESS_LEFT if args.side == "LEFT" else EYEBROWS_ADDRESS_RIGHT
    led_heartbeat_bytes = CMD_MODULE_ID_LEDS | 0x02
    i2c.write_bytes_to_address(address, led_heartbeat_bytes)

def _parse_subsystem_led(subparser):
    def _parse_cmd_on(ss):
        p: argparse.ArgumentParser = ss.add_parser("on", help="Turn LED on.")
        p.add_argument("side", choices=["LEFT", "RIGHT"], type=str, help="Which eyebrow?")
        p.add_argument("--on", dest="cmd", default=_cmd_led_on, help="This command has no args.")
    def _parse_cmd_off(ss):
        p = ss.add_parser("off", help="Turn LED off.")
        p.add_argument("side", choices=["LEFT", "RIGHT"], type=str, help="Which eyebrow?")
        p.add_argument("--off", dest="cmd", default=_cmd_led_off, help="This command has no args.")
    def _parse_cmd_heartbeat(ss):
        p = ss.add_parser("heartbeat", help="Change eyebrow LED mode to heartbeat.")
        p.add_argument("side", choices=["LEFT", "RIGHT"], type=str, help="Which eyebrow?")
        p.add_argument("--heartbeat", dest="cmd", default=_cmd_led_heartbeat, help="This command has no args.")
    parser: argparse.ArgumentParser = subparser.add_parser("led", help="LED subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_on(cmd_subparsers)
    _parse_cmd_off(cmd_subparsers)
    _parse_cmd_heartbeat(cmd_subparsers)

def _cmd_lcd_test(args):
    address = EYEBROWS_ADDRESS_LEFT if args.side == "LEFT" else EYEBROWS_ADDRESS_RIGHT
    lcd_test_bytes = CMD_MODULE_ID_LCD | 0x11
    i2c.write_bytes_to_address(address, lcd_test_bytes)

def _cmd_lcd_off(args):
    address = EYEBROWS_ADDRESS_LEFT if args.side == "LEFT" else EYEBROWS_ADDRESS_RIGHT
    lcd_off_bytes = CMD_MODULE_ID_LCD | 0x22
    i2c.write_bytes_to_address(address, lcd_off_bytes)

def _cmd_lcd_draw(args):
    address = EYEBROWS_ADDRESS_LEFT if args.side == "LEFT" else EYEBROWS_ADDRESS_RIGHT
    eyebrow_state = args.draw_val
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
    i2c.write_bytes_to_address(address, lcd_draw_bytes)

def _parse_subsystem_lcd(subparser):
    def _parse_cmd_test(ss):
        p = ss.add_parser("test", help="Draw a test image on the LCD")
        p.add_argument("side", choices=["LEFT", "RIGHT"], type=str, help="Which eyebrow?")
        p.add_argument("--test", dest="cmd", default=_cmd_lcd_test, help="This command has no args.")
    def _parse_cmd_off(ss):
        p = ss.add_parser("off", help="Clear the LCD")
        p.add_argument("side", choices=["LEFT", "RIGHT"], type=str, help="Which eyebrow?")
        p.add_argument("--off", dest="cmd", default=_cmd_lcd_off, help="This command has no args.")
    def _parse_cmd_draw(ss):
        p = ss.add_parser("draw", help="Draw the given eyebrow configuration on the LCD.")
        p.add_argument("side", choices=["LEFT", "RIGHT"], type=str, help="Which eyebrow?")
        p.add_argument("draw_val", metavar="draw-val", nargs=3, choices=["HIGH", "MIDDLE", "LOW", 'H', 'M', 'L'], help="Need three strings, each 'HIGH' ('H'), 'MIDDLE' ('M'), or 'LOW' ('L').")
        p.add_argument("--draw", dest="cmd", default=_cmd_lcd_draw, help="Reserved.")
    parser: argparse.ArgumentParser = subparser.add_parser("lcd", help="LCD subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_test(cmd_subparsers)
    _parse_cmd_off(cmd_subparsers)
    _parse_cmd_draw(cmd_subparsers)

def _cmd_servo_go(args):
    address = EYEBROWS_ADDRESS_LEFT if args.side == "LEFT" else EYEBROWS_ADDRESS_RIGHT
    servo_degrees = args.go_val
    go_val_bytes = int(round(np.interp(servo_degrees, [0, 180], [0, 63]))) # map 0 to 180 into 0 to 63
    go_val_bytes = 0b00000000 if go_val_bytes < 0b00000000 else go_val_bytes
    go_val_bytes = 0b00111111 if go_val_bytes > 0b00111111 else go_val_bytes
    servo_go_bytes = CMD_MODULE_ID_SERVO | go_val_bytes
    i2c.write_bytes_to_address(address, servo_go_bytes)

def _check_servo_range(arg):
    try:
        value = int(arg)
    except ValueError as err:
       raise argparse.ArgumentTypeError(str(err))

    if value < 0 or value > 180:
        raise argparse.ArgumentTypeError(f"Need a servo value in range [0, 180] but got {arg}")

    return value

def _parse_subsystem_servo(subparsers):
    def _parse_cmd_go(ss):
        p = ss.add_parser("go", help="Drive servo to given value.")
        p.add_argument("side", choices=["LEFT", "RIGHT"], type=str, help="Which eyebrow?")
        p.add_argument("go_val", metavar="go-val", type=_check_servo_range, help="Value to drive the servo to. 0 is left. 180 is right. 90 is center.")
        p.add_argument("--go", dest="cmd", default=_cmd_servo_go, help="Reserved.")
    parser: argparse.ArgumentParser = subparsers.add_parser("servo", help="Servo subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_go(cmd_subparsers)

def add_subparser(subparsers):
    """
    Add the subargs for the eyebrows module.
    """
    parser: argparse.ArgumentParser = subparsers.add_parser("eyebrows", help="Eyebrows module")
    subsystem_subparsers = parser.add_subparsers(help="Subsystem")
    _parse_subsystem_led(subsystem_subparsers)
    _parse_subsystem_lcd(subsystem_subparsers)
    _parse_subsystem_servo(subsystem_subparsers)
