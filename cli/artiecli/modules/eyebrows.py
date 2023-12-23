from .. import apiclient
from .. import common
from typing import List
import argparse

class EyebrowClient(apiclient.APIClient):
    def __init__(self, args) -> None:
        super().__init__(args)

    def led_on(self, side: str):
        response = self.post(f"/eyebrows/led/{side}", params={'artie-id': self.artie_id, 'state': 'on'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting {side} LED value: {response.content.decode('utf-8')}", module='eyebrows', submodule='LED', artie_id=self.artie_id)

    def led_off(self, side: str):
        response = self.post(f"/eyebrows/led/{side}", params={'artie-id': self.artie_id, 'state': 'off'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting {side} LED value: {response.content.decode('utf-8')}", module='eyebrows', submodule='LED', artie_id=self.artie_id)

    def led_heartbeat(self, side: str):
        response = self.post(f"/eyebrows/led/{side}", params={'artie-id': self.artie_id, 'state': 'heartbeat'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting {side} LED value: {response.content.decode('utf-8')}", module='eyebrows', submodule='LED', artie_id=self.artie_id)

    def led_get(self, side: str):
        response = self.get(f"/eyebrows/led/{side}", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting {side} LED value: {response.content.decode('utf-8')}", module='eyebrows', submodule='LED', artie_id=self.artie_id)
        else:
            common.format_print_result(f"{side} LED value: {response.json().get('state')}", module='eyebrows', submodule='LED', artie_id=response.json().get('artie-id'))

    def lcd_test(self, side: str):
        response = self.post(f"/eyebrows/lcd/{side}/test", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error testing {side} LCD: {response.content.decode('utf-8')}", module='eyebrows', submodule='LCD', artie_id=self.artie_id)

    def lcd_off(self, side: str):
        response = self.post(f"/eyebrows/lcd/{side}/off", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error clearing {side} LCD: {response.content.decode('utf-8')}", module='eyebrows', submodule='LCD', artie_id=self.artie_id)

    def lcd_draw(self, side: str, draw_val: List[str]):
        body = {
            "vertices": [arg[0] for arg in draw_val]
        }
        response = self.post(f"/eyebrows/lcd/{side}", body=body, params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error setting {side} LCD: {response.content.decode('utf-8')}", module='eyebrows', submodule='LCD', artie_id=self.artie_id)

    def lcd_get(self, side: str):
        response = self.get(f"/eyebrows/lcd/{side}", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting {side} LCD value: {response.content.decode('utf-8')}", module='eyebrows', submodule='LCD', artie_id=self.artie_id)
        else:
            common.format_print_result(f"Display value: {response.json().get('vertices')}", module='eyebrows', submodule='LCD', artie_id=response.json().get('artie-id'))

    def servo_go(self, side: str, go_val: float):
        response = self.post(f"/eyebrows/servo/{side}", params={'artie-id': self.artie_id, 'degrees': f"{go_val:0.2f}"})
        if response.status_code != 200:
            common.format_print_result(f"Error setting {side} Servo: {response.content.decode('utf-8')}", module='eyebrows', submodule='servo', artie_id=self.artie_id)

    def servo_get(self, side: str):
        response = self.get(f"/eyebrows/servo/{side}", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting {side} Servo: {response.content.decode('utf-8')}", module='eyebrows', submodule='servo', artie_id=self.artie_id)
        else:
            common.format_print_result(f"{side} servo position in degrees: {response.json().get('degrees')}", module='eyebrows', submodule='servo', artie_id=response.json().get('artie-id'))

    def firmware_load(self):
        response = self.post(f"/eyebrows/fw", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error reloading eyebrow FW: {response.content.decode('utf-8')}", module='eyebrows', submodule='FW', artie_id=self.artie_id)

    def status(self):
        response = self.get("/eyebrows/status", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_status_result(f"Error getting eyebrow status: {response.content.decode('utf-8')}", module='eyebrows', artie_id=self.artie_id)
        else:
            common.format_print_status_result(response.json(), module='eyebrows', artie_id=self.artie_id)

    def self_check(self):
        response = self.post("/eyebrows/self-test", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error running eyebrow self-check: {response.content.decode('utf-8')}", module='eyebrows', submodule='status', artie_id=self.artie_id)

def _connect_client(args) -> common._ConnectionWrapper | EyebrowClient:
    if common.in_test_mode(args):
        ip = "localhost"
        port = 18863
        connection = common.connect(ip, port, ipv6=args.ipv6)
    else:
        connection = EyebrowClient(args)
    return connection

#########################################################################################
################################# LED Subsystem #########################################
#########################################################################################

def _cmd_led_on(args):
    client = _connect_client(args)
    if args.side == "both":
        client.led_on("left")
        client.led_on("right")
    else:
        client.led_on(args.side)

def _cmd_led_off(args):
    client = _connect_client(args)
    if args.side == "both":
        client.led_off("left")
        client.led_off("right")
    else:
        client.led_off(args.side)

def _cmd_led_heartbeat(args):
    client = _connect_client(args)
    if args.side == "both":
        client.led_heartbeat("left")
        client.led_heartbeat("right")
    else:
        client.led_heartbeat(args.side)

def _cmd_led_get(args):
    client = _connect_client(args)
    if args.side == "both":
        client.led_get("left")
        client.led_get("right")
    else:
        client.led_get(args.side)

#########################################################################################
################################# LCD Subsystem #########################################
#########################################################################################
def _cmd_lcd_get(args):
    client = _connect_client(args)
    if args.side == "both":
        client.lcd_get("left")
        client.lcd_get("right")
    else:
        client.lcd_get(args.side)

def _cmd_lcd_test(args):
    client = _connect_client(args)
    if args.side == "both":
        client.lcd_test("left")
        client.lcd_test("right")
    else:
        client.lcd_test(args.side)

def _cmd_lcd_off(args):
    client = _connect_client(args)
    if args.side == "both":
        client.lcd_off("left")
        client.lcd_off("right")
    else:
        client.lcd_off(args.side)

def _cmd_lcd_draw(args):
    client = _connect_client(args)
    if args.side == "both":
        client.lcd_draw("left", args.draw_val)
        client.lcd_draw("right", args.draw_val)
    else:
        client.lcd_draw(args.side, args.draw_val)


#########################################################################################
################################# Servo Subsystem #######################################
#########################################################################################
def _cmd_servo_get(args):
    client = _connect_client(args)
    if args.side == "both":
        client.servo_get("left")
        client.servo_get("right")
    else:
        client.servo_get(args.side)

def _cmd_servo_go(args):
    client = _connect_client(args)
    if args.side == "both":
        client.servo_go("left", args.go_val)
        client.servo_go("right", args.go_val)
    else:
        client.servo_go(args.side, args.go_val)

def _check_servo_range(arg):
    try:
        value = int(arg)
    except ValueError as err:
       raise argparse.ArgumentTypeError(str(err))

    if value < 0 or value > 180:
        raise argparse.ArgumentTypeError(f"Need a servo value in range [0, 180] but got {arg}")

    return value

#########################################################################################
################################# FW Subsystem ##########################################
#########################################################################################
def _cmd_firmware_load(args):
    client = _connect_client(args)
    client.firmware_load()

#########################################################################################
################################# Status Commands #######################################
#########################################################################################
def _cmd_status_self_check(args):
    client = _connect_client(args)
    client.self_check()
    client.status()

def _cmd_status_get(args):
    client = _connect_client(args)
    client.status()

#########################################################################################
################################## PARSERS ##############################################
#########################################################################################
def _fill_status_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="status", description="The status subsystem")

    # Args that are useful for all status commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("status", "Status Subsystem Options")

    # Self-Check command
    p = subparsers.add_parser("self-check", help="Run a self-diagnostics check and print the results.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_status_self_check)

    p = subparsers.add_parser("get", help="Get the eyebrow module's subsystems' statuses.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_status_get)

def _fill_fw_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="fw", description="The FW subsystem")

    # Args that are useful for all FW commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("fw", "FW Subsystem Options")

    # Load command
    p = subparsers.add_parser("load", help="(Re)load the firmware. Targets both sides at once.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_firmware_load)

def _fill_servo_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="servo", description="The Servo subsystem")

    # Args that are useful for all servo commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("servo", "Servo Subsystem Options")
    group.add_argument("--side", choices=["left", "right", "both"], type=str, default="both", help="Which eye?")

    # 'go' command
    p = subparsers.add_parser("go", help="Drive servo to given value", parents=[option_parser])
    p.add_argument("go_val", metavar="go-val", type=_check_servo_range, help="Value to drive the servo to. 0 is left. 180 is right. 90 is center.")
    p.set_defaults(cmd=_cmd_servo_go)

    # 'get' command
    p = subparsers.add_parser("get", help="Get a best estimate of the servo's position in degrees", parents=[option_parser])
    p.set_defaults(cmd=_cmd_servo_get)

def _fill_lcd_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="lcd", description="The LCD subsystem")

    # Args that are useful for all LCD commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("lcd", "LCD Subsystem Options")
    group.add_argument("--side", choices=["left", "right", "both"], type=str, default="both", help="Which eyebrow?")

    p = subparsers.add_parser("test", help="Draw a test image on the LCD", parents=[option_parser])
    p.set_defaults(cmd=_cmd_lcd_test)

    p = subparsers.add_parser("off", help="Clear the LCD", parents=[option_parser])
    p.set_defaults(cmd=_cmd_lcd_off)

    p = subparsers.add_parser("draw", help="Draw the given eyebrow configuration on the LCD.", parents=[option_parser])
    p.add_argument("draw_val", metavar="draw-val", nargs=3, choices=["HIGH", "MIDDLE", "LOW", 'H', 'M', 'L'], help="Need three strings, each 'HIGH' ('H'), 'MIDDLE' ('M'), or 'LOW' ('L').")
    p.set_defaults(cmd=_cmd_lcd_draw)

    p = subparsers.add_parser("get", help="Get the LCD's current display", parents=[option_parser])
    p.set_defaults(cmd=_cmd_lcd_get)

def _fill_led_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="led", description="The LED subsystem")

    # Args that are useful for all LED commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("led", "LED Subsystem Options")
    group.add_argument("--side", choices=["left", "right", "both"], type=str, default="both", help="Which eyebrow?")

    # For each LED command, add the actual command and any args
    ## 'on' command
    p = subparsers.add_parser("on", help="Turn LED on.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_led_on)

    ## 'off' command
    p = subparsers.add_parser("off", help="Turn LED off.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_led_off)

    ## 'heartbeat' command
    p = subparsers.add_parser("heartbeat", help="Turn LED to heartbeat mode.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_led_heartbeat)

    ## 'get' command
    p = subparsers.add_parser("get", help="Get the current LED state.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_led_get)

def fill_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="eyebrows", description="The eyebrow module's subsystems")

    # Args that are useful for all eyebrow module commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("Eyebrows Module", "Eyebrows Module Options")

    # Add all the commands for each subystem
    ## LED
    led_parser = subparsers.add_parser("led", parents=[option_parser])
    _fill_led_subparser(led_parser, option_parser)

    ## LCD
    lcd_parser = subparsers.add_parser("lcd", parents=[option_parser])
    _fill_lcd_subparser(lcd_parser, option_parser)

    ## Servo
    servo_parser = subparsers.add_parser("servo", parents=[option_parser])
    _fill_servo_subparser(servo_parser, option_parser)

    ## FW
    fw_parser = subparsers.add_parser("fw", parents=[option_parser])
    _fill_fw_subparser(fw_parser, option_parser)

    ## Status Check
    status_parser = subparsers.add_parser("status", parents=[option_parser])
    _fill_status_subparser(status_parser, option_parser)
