from .. import apiclient
from .. import common
import argparse

MOUTH_DRAWING_CHOICES = [
    "smile",
    "frown",
    "line",
    "smirk",
    "open",
    "open-smile",
    "zig-zag",
]

class MouthClient(apiclient.APIClient):
    def __init__(self, args) -> None:
        super().__init__(args)

    def led_on(self):
        response = self.post(f"/mouth/led", params={'artie-id': self.artie_id, 'state': 'on'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting LED value: {response}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def led_off(self):
        response = self.post(f"/mouth/led", params={'artie-id': self.artie_id, 'state': 'off'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting LED value: {response}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def led_heartbeat(self):
        response = self.post(f"/mouth/led", params={'artie-id': self.artie_id, 'state': 'heartbeat'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting LED value: {response}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def led_get(self):
        response = self.get(f"/mouth/led", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting LED value: {response}", module='mouth', submodule='LED', artie_id=self.artie_id)
        else:
            common.format_print_result(f"LED value: {response.json().get('state')}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def lcd_test(self):
        response = self.post(f"/mouth/lcd/test", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error testing the LCD: {response}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def lcd_off(self):
        response = self.post(f"/mouth/lcd/off", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error clearing the LCD: {response}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def lcd_get(self):
        response = self.get(f"/mouth/lcd", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting mouth LCD value: {response}", module='mouth', submodule='LCD', artie_id=self.artie_id)
        else:
            common.format_print_result(f"Display value: {response.json().get('display')}", module='mouth', submodule='LCD', artie_id=response.json().get('artie-id'))

    def lcd_draw(self, draw_val: str):
        response = self.post(f"/mouth/lcd", params={'artie-id': self.artie_id, 'display': draw_val})
        if response.status_code != 200:
            common.format_print_result(f"Error setting mouth LCD: {response}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def lcd_talk(self):
        response = self.post(f"/mouth/lcd", params={'artie-id': self.artie_id, 'display': "talking"})
        if response.status_code != 200:
            common.format_print_result(f"Error setting mouth LCD: {response}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def firmware_load(self):
        response = self.post(f"/mouth/fw", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error reloading mouth FW: {response}", module='mouth', submodule='FW', artie_id=self.artie_id)

def _connect_client(args) -> common._ConnectionWrapper | MouthClient:
    if common.in_test_mode(args):
        ip = "localhost"
        port = 18862
        connection = common.connect(ip, port, ipv6=args.ipv6)
    else:
        connection = MouthClient(args)
    return connection

#########################################################################################
################################# LED Subsystem #########################################
#########################################################################################

def _cmd_led_on(args):
    client = _connect_client(args)
    client.led_on()

def _cmd_led_off(args):
    client = _connect_client(args)
    client.led_off()

def _cmd_led_heartbeat(args):
    client = _connect_client(args)
    client.led_heartbeat()

def _cmd_led_get(args):
    client = _connect_client(args)
    client.led_get()

#########################################################################################
################################# LCD Subsystem #########################################
#########################################################################################

def _cmd_lcd_get(args):
    client = _connect_client(args)
    client.lcd_get()

def _cmd_lcd_draw(args):
    client = _connect_client(args)
    client.lcd_draw(args.draw_val)

def _cmd_lcd_test(args):
    client = _connect_client(args)
    client.lcd_test()

def _cmd_lcd_off(args):
    client = _connect_client(args)
    client.lcd_off()

def _cmd_lcd_talk(args):
    client = _connect_client(args)
    client.lcd_talk()

#########################################################################################
################################# FW Subsystem ##########################################
#########################################################################################

def _cmd_firmware_load(args):
    client = _connect_client(args)
    client.firmware_load()

#########################################################################################
################################## PARSERS ##############################################
#########################################################################################
def _fill_fw_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="fw", description="The FW subsystem")

    # Args that are useful for all FW commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("fw", "FW Subsystem Options")

    # Load command
    p = subparsers.add_parser("load", help="(Re)load the firmware. Targets both sides at once.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_firmware_load)

def _fill_lcd_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="lcd", description="The LCD subsystem")

    # Args that are useful for all LCD commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("lcd", "LCD Subsystem Options")

    p = subparsers.add_parser("test", help="Draw a test image on the LCD", parents=[option_parser])
    p.set_defaults(cmd=_cmd_lcd_test)

    p = subparsers.add_parser("off", help="Clear the LCD", parents=[option_parser])
    p.set_defaults(cmd=_cmd_lcd_off)

    p = subparsers.add_parser("get", help="Get the LCD's current display", parents=[option_parser])
    p.set_defaults(cmd=_cmd_lcd_get)

    p = subparsers.add_parser("draw", help="Draw the given eyebrow configuration on the LCD.", parents=[option_parser])
    p.add_argument("draw_val", metavar="draw-val", choices=sorted(MOUTH_DRAWING_CHOICES), help="The mouth configuration to draw.")
    p.set_defaults(cmd=_cmd_lcd_draw)

    p = subparsers.add_parser("talk", help="Set the mouth to talking mode.", parents=[option_parser])
    p.set_defaults(cmd=_cmd_lcd_talk)

def _fill_led_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="led", description="The LED subsystem")

    # Args that are useful for all LED commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("led", "LED Subsystem Options")

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

    ## FW
    fw_parser = subparsers.add_parser("fw", parents=[option_parser])
    _fill_fw_subparser(fw_parser, option_parser)
