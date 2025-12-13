from .. import common
from artie_tooling.api_clients import mouth_client
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

def _connect_client(args) -> common._ConnectionWrapper | mouth_client.MouthClient:
    if common.in_test_mode(args):
        ip = "localhost"
        port = 18862
        connection = common.connect(ip, port, ipv6=args.ipv6)
    else:
        connection = mouth_client.MouthClient(profile=args.artie_profile, integration_test=args.integration_test, unit_test=args.unit_test)
    return connection

#########################################################################################
################################# LED Subsystem #########################################
#########################################################################################

def _cmd_led_on(args):
    client = _connect_client(args)
    common.format_print_result(client.led_on(), "mouth", "LED", args.artie_id)

def _cmd_led_off(args):
    client = _connect_client(args)
    common.format_print_result(client.led_off(), "mouth", "LED", args.artie_id)

def _cmd_led_heartbeat(args):
    client = _connect_client(args)
    common.format_print_result(client.led_heartbeat(), "mouth", "LED", args.artie_id)

def _cmd_led_get(args):
    client = _connect_client(args)
    common.format_print_result(client.led_get(), "mouth", "LED", args.artie_id)

#########################################################################################
################################# LCD Subsystem #########################################
#########################################################################################

def _cmd_lcd_get(args):
    client = _connect_client(args)
    common.format_print_result(client.lcd_get(), "mouth", "LCD", args.artie_id)

def _cmd_lcd_draw(args):
    client = _connect_client(args)
    common.format_print_result(client.lcd_draw(args.draw_val), "mouth", "LCD", args.artie_id)

def _cmd_lcd_test(args):
    client = _connect_client(args)
    common.format_print_result(client.lcd_test(), "mouth", "LCD", args.artie_id)

def _cmd_lcd_off(args):
    client = _connect_client(args)
    common.format_print_result(client.lcd_off(), "mouth", "LCD", args.artie_id)

def _cmd_lcd_talk(args):
    client = _connect_client(args)
    common.format_print_result(client.lcd_talk(), "mouth", "LCD", args.artie_id)

#########################################################################################
################################# FW Subsystem ##########################################
#########################################################################################

def _cmd_firmware_load(args):
    client = _connect_client(args)
    common.format_print_result(client.firmware_load(), "mouth", "FW", args.artie_id)

#########################################################################################
################################# Status Commands #######################################
#########################################################################################
def _cmd_status_self_check(args):
    client = _connect_client(args)
    common.format_print_result(client.self_check(), "mouth", "status", args.artie_id)
    common.format_print_status_result(client.status(), "mouth", args.artie_id)

def _cmd_status_get(args):
    client = _connect_client(args)
    common.format_print_status_result(client.status(), "mouth", args.artie_id)

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

    ## Status Check
    status_parser = subparsers.add_parser("status", parents=[option_parser])
    _fill_status_subparser(status_parser, option_parser)
