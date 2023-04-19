import argparse
import zerorpc

def _connect_client():
    ip = "0.0.0.0"
    port = "4242"
    client = zerorpc.Client()
    client.connect(f"tcp://{ip}:{port}")  # This will change to a K8S service later
    return client

def _cmd_led_on(args):
    client = _connect_client()
    client.led_on(args.side)

def _cmd_led_off(args):
    client = _connect_client()
    client.led_off(args.side)

def _cmd_led_heartbeat(args):
    client = _connect_client()
    client.led_heartbeat(args.side)

def _parse_subsystem_led(subparser):
    def _parse_cmd_on(ss):
        p: argparse.ArgumentParser = ss.add_parser("on", help="Turn LED on.")
        p.add_argument("side", choices=["left", "right"], type=str, help="Which eyebrow?")
        p.set_defaults(cmd=_cmd_led_on)
    def _parse_cmd_off(ss):
        p = ss.add_parser("off", help="Turn LED off.")
        p.add_argument("side", choices=["left", "right"], type=str, help="Which eyebrow?")
        p.set_defaults(cmd=_cmd_led_off)
    def _parse_cmd_heartbeat(ss):
        p = ss.add_parser("heartbeat", help="Change eyebrow LED mode to heartbeat.")
        p.add_argument("side", choices=["left", "right"], type=str, help="Which eyebrow?")
        p.set_defaults(cmd=_cmd_led_heartbeat)
    parser: argparse.ArgumentParser = subparser.add_parser("led", help="LED subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_on(cmd_subparsers)
    _parse_cmd_off(cmd_subparsers)
    _parse_cmd_heartbeat(cmd_subparsers)

def _cmd_lcd_test(args):
    client = _connect_client()
    client.lcd_test(args.side)

def _cmd_lcd_off(args):
    client = _connect_client()
    client.lcd_off(args.side)

def _cmd_lcd_draw(args):
    client = _connect_client()
    client.lcd_draw(args.side, args.draw_val)

def _parse_subsystem_lcd(subparser):
    def _parse_cmd_test(ss):
        p = ss.add_parser("test", help="Draw a test image on the LCD")
        p.add_argument("side", choices=["left", "right"], type=str, help="Which eyebrow?")
        p.set_defaults(cmd=_cmd_lcd_test)
    def _parse_cmd_off(ss):
        p = ss.add_parser("off", help="Clear the LCD")
        p.add_argument("side", choices=["left", "right"], type=str, help="Which eyebrow?")
        p.set_defaults(cmd=_cmd_lcd_off)
    def _parse_cmd_draw(ss):
        p = ss.add_parser("draw", help="Draw the given eyebrow configuration on the LCD.")
        p.add_argument("side", choices=["left", "right"], type=str, help="Which eyebrow?")
        p.add_argument("draw_val", metavar="draw-val", nargs=3, choices=["HIGH", "MIDDLE", "LOW", 'H', 'M', 'L'], help="Need three strings, each 'HIGH' ('H'), 'MIDDLE' ('M'), or 'LOW' ('L').")
        p.set_defaults(cmd=_cmd_lcd_draw)
    parser: argparse.ArgumentParser = subparser.add_parser("lcd", help="LCD subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_test(cmd_subparsers)
    _parse_cmd_off(cmd_subparsers)
    _parse_cmd_draw(cmd_subparsers)

def _cmd_servo_go(args):
    client = _connect_client()
    client.servo_go(args.side, args.go_val)

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
        p.add_argument("side", choices=["left", "right"], type=str, help="Which eyebrow?")
        p.add_argument("go_val", metavar="go-val", type=_check_servo_range, help="Value to drive the servo to. 0 is left. 180 is right. 90 is center.")
        p.set_defaults(cmd=_cmd_servo_go)
    parser: argparse.ArgumentParser = subparsers.add_parser("servo", help="Servo subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_go(cmd_subparsers)

def _cmd_firmware_load(args):
    client = _connect_client()
    client.firmware_load()

def _parse_subsystem_firmware(subparsers):
    def _parse_cmd_load(ss):
        p = ss.add_parser("load", help="(Re)load the firmware. Targets both sides at once.")
        p.set_defaults(cmd=_cmd_firmware_load)
    parser: argparse.ArgumentParser = subparsers.add_parser("firmware", help="Firmware subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_load(cmd_subparsers)

def add_subparser(subparsers):
    """
    Add the subargs for the eyebrows module.
    """
    parser: argparse.ArgumentParser = subparsers.add_parser("eyebrows", help="Eyebrows module")
    subsystem_subparsers = parser.add_subparsers(help="Subsystem")
    _parse_subsystem_led(subsystem_subparsers)
    _parse_subsystem_lcd(subsystem_subparsers)
    _parse_subsystem_servo(subsystem_subparsers)
    _parse_subsystem_firmware(subsystem_subparsers)
