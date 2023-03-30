import argparse
import zerorpc

MOUTH_DRAWING_CHOICES = [
    "smile",
    "frown",
    "line",
    "smirk",
    "open",
    "open-smile",
    "zig-zag",
]

def _connect_client():
    ip = "0.0.0.0"
    port = "4243"
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

def _cmd_lcd_draw(args):
    client = _connect_client()
    client.lcd_draw(args.draw_val)

def _cmd_lcd_test(args):
    client = _connect_client()
    client.lcd_test(args.side)

def _cmd_lcd_off(args):
    client = _connect_client()
    client.lcd_off(args.side)

def _cmd_lcd_draw(args):
    client = _connect_client()
    client.lcd_draw(args.side, args.draw_val)

def _cmd_lcd_talk(args):
    client = _connect_client()
    client.lcd_talk()

def _parse_subsystem_lcd(subparser):
    def _parse_cmd_test(ss):
        p = ss.add_parser("test", help="Draw a test image on the LCD")
        p.add_argument("--test", dest="cmd", default=_cmd_lcd_test, help="This command has no args.")
    def _parse_cmd_off(ss):
        p = ss.add_parser("off", help="Clear the LCD")
        p.add_argument("--off", dest="cmd", default=_cmd_lcd_off, help="This command has no args.")
    def _parse_cmd_draw(ss):
        p = ss.add_parser("draw", help="Draw the given mouth configuration on the LCD.")
        p.add_argument("draw_val", metavar="draw-val", choices=sorted(MOUTH_DRAWING_CHOICES), help="The mouth configuration to draw.")
        p.add_argument("--draw", dest="cmd", default=_cmd_lcd_draw, help="Reserved.")
    def _parse_cmd_talk(ss):
        p = ss.add_parser("talk", help="Set the mouth to talking mode.")
        p.add_argument("--talk", dest="cmd", default=_cmd_lcd_talk, help="Reserved.")
    parser: argparse.ArgumentParser = subparser.add_parser("lcd", help="LCD subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_test(cmd_subparsers)
    _parse_cmd_off(cmd_subparsers)
    _parse_cmd_draw(cmd_subparsers)
    _parse_cmd_talk(cmd_subparsers)

def _cmd_firmware_load(args):
    client = _connect_client()
    client.firmware_load()

def _parse_subsystem_firmware(subparsers):
    def _parse_cmd_load(ss):
        p = ss.add_parser("load", help="(Re)load the firmware. Targets both sides at once.")
        p.add_argument("--load", dest="cmd", default=_cmd_firmware_load, help="Reserved.")
    parser: argparse.ArgumentParser = subparsers.add_parser("firmware", help="Firmware subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_load(cmd_subparsers)

def add_subparser(subparsers):
    """
    Add the subargs for the mouth module.
    """
    parser: argparse.ArgumentParser = subparsers.add_parser("eyebrows", help="Eyebrows module")
    subsystem_subparsers = parser.add_subparsers(help="Subsystem")
    _parse_subsystem_led(subsystem_subparsers)
    _parse_subsystem_lcd(subsystem_subparsers)
    _parse_subsystem_firmware(subsystem_subparsers)
