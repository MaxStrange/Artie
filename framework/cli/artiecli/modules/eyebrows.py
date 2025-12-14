from .. import common
from artie_tooling.api_clients import eyebrow_client
from artie_tooling import errors
import argparse

def _connect_client(args) -> common._ConnectionWrapper | eyebrow_client.EyebrowClient:
    if common.in_test_mode(args):
        ip = "localhost"
        port = 18863
        connection = common.connect(ip, port, ipv6=args.ipv6)
    else:
        connection = eyebrow_client.EyebrowClient(profile=args.artie_profile, integration_test=args.integration_test, unit_test=args.unit_test)
    return connection

#########################################################################################
################################# LED Subsystem #########################################
#########################################################################################

def _cmd_led_on(args):
    client = _connect_client(args)
    if args.side == "both":
        common.format_print_result(client.led_on("left"), "eyebrows", "LED", args.artie_id)
        common.format_print_result(client.led_on("right"), "eyebrows", "LED", args.artie_id)
    else:
        common.format_print_result(client.led_on(args.side), "eyebrows", "LED", args.artie_id)

def _cmd_led_off(args):
    client = _connect_client(args)
    if args.side == "both":
        common.format_print_result(client.led_off("left"), "eyebrows", "LED", args.artie_id)
        common.format_print_result(client.led_off("right"), "eyebrows", "LED", args.artie_id)
    else:
        common.format_print_result(client.led_off(args.side), "eyebrows", "LED", args.artie_id)

def _cmd_led_heartbeat(args):
    client = _connect_client(args)
    if args.side == "both":
        common.format_print_result(client.led_heartbeat("left"), "eyebrows", "LED", args.artie_id)
        common.format_print_result(client.led_heartbeat("right"), "eyebrows", "LED", args.artie_id)
    else:
        common.format_print_result(client.led_heartbeat(args.side), "eyebrows", "LED", args.artie_id)

def _cmd_led_get(args):
    client = _connect_client(args)
    if args.side == "both":
        # Left
        result = client.led_get("left")
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "LED", args.artie_id)
        else:
            common.format_print_result(f"left LED value: {result.state if hasattr(result, 'state') else str(result)}", "eyebrows", "LED", args.artie_id)

        # Right
        result = client.led_get("right")
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "LED", args.artie_id)
        else:
            common.format_print_result(f"right LED value: {result.state if hasattr(result, 'state') else str(result)}", "eyebrows", "LED", args.artie_id)
    else:
        result = client.led_get(args.side)
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "LED", args.artie_id)
        else:
            common.format_print_result(f"{args.side} LED value: {result.state if hasattr(result, 'state') else str(result)}", "eyebrows", "LED", args.artie_id)

#########################################################################################
################################# LCD Subsystem #########################################
#########################################################################################
def _cmd_lcd_get(args):
    client = _connect_client(args)
    if args.side == "both":
        # Left
        result = client.lcd_get("left")
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "LCD", args.artie_id)
        else:
            common.format_print_result(f"left Display value: {result.vertices if hasattr(result, 'vertices') else str(result)}", "eyebrows", "LCD", args.artie_id)

        # Right
        result = client.lcd_get("right")
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "LCD", args.artie_id)
        else:
            common.format_print_result(f"right Display value: {result.vertices if hasattr(result, 'vertices') else str(result)}", "eyebrows", "LCD", args.artie_id)
    else:
        result = client.lcd_get(args.side)
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "LCD", args.artie_id)
        else:
            common.format_print_result(f"{args.side} Display value: {result.vertices if hasattr(result, 'vertices') else str(result)}", "eyebrows", "LCD", args.artie_id)

def _cmd_lcd_test(args):
    client = _connect_client(args)
    if args.side == "both":
        common.format_print_result(client.lcd_test("left"), "eyebrows", "LCD", args.artie_id)
        common.format_print_result(client.lcd_test("right"), "eyebrows", "LCD", args.artie_id)
    else:
        common.format_print_result(client.lcd_test(args.side), "eyebrows", "LCD", args.artie_id)

def _cmd_lcd_off(args):
    client = _connect_client(args)
    if args.side == "both":
        common.format_print_result(client.lcd_off("left"), "eyebrows", "LCD", args.artie_id)
        common.format_print_result(client.lcd_off("right"), "eyebrows", "LCD", args.artie_id)
    else:
        common.format_print_result(client.lcd_off(args.side), "eyebrows", "LCD", args.artie_id)

def _cmd_lcd_draw(args):
    client = _connect_client(args)
    if args.side == "both":
        common.format_print_result(client.lcd_draw("left", args.draw_val), "eyebrows", "LCD", args.artie_id)
        common.format_print_result(client.lcd_draw("right", args.draw_val), "eyebrows", "LCD", args.artie_id)
    else:
        common.format_print_result(client.lcd_draw(args.side, args.draw_val), "eyebrows", "LCD", args.artie_id)


#########################################################################################
################################# Servo Subsystem #######################################
#########################################################################################
def _cmd_servo_get(args):
    client = _connect_client(args)
    if args.side == "both":
        # Left
        result = client.servo_get("left")
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "servo", args.artie_id)
        else:
            common.format_print_result(f"left servo position in degrees: {result.degrees if hasattr(result, 'degrees') else str(result)}", "eyebrows", "servo", args.artie_id)

        # Right
        result = client.servo_get("right")
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "servo", args.artie_id)
        else:
            common.format_print_result(f"right servo position in degrees: {result.degrees if hasattr(result, 'degrees') else str(result)}", "eyebrows", "servo", args.artie_id)
    else:
        result = client.servo_get(args.side)
        if issubclass(type(result), errors.HTTPError):
            common.format_print_result(result, "eyebrows", "servo", args.artie_id)
        else:
            common.format_print_result(f"{args.side} servo position in degrees: {result.degrees if hasattr(result, 'degrees') else str(result)}", "eyebrows", "servo", args.artie_id)

def _cmd_servo_go(args):
    client = _connect_client(args)
    if args.side == "both":
        common.format_print_result(client.servo_go("left", args.go_val), "eyebrows", "servo", args.artie_id)
        common.format_print_result(client.servo_go("right", args.go_val), "eyebrows", "servo", args.artie_id)
    else:
        common.format_print_result(client.servo_go(args.side, args.go_val), "eyebrows", "servo", args.artie_id)

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
    common.format_print_result(client.firmware_load(), "eyebrows", "FW", args.artie_id)

#########################################################################################
################################# Status Commands #######################################
#########################################################################################
def _cmd_status_self_check(args):
    client = _connect_client(args)
    common.format_print_result(client.self_check(), "eyebrows", "status", args.artie_id)
    common.format_print_status_result(client.status(), "eyebrows", args.artie_id)

def _cmd_status_get(args):
    client = _connect_client(args)
    result = client.status()
    if issubclass(type(result), dict) and 'submodule-statuses' in result:
        common.format_print_status_result(result, "eyebrows", args.artie_id)
    else:
        common.format_print_result({'submodule-statuses': result}, "eyebrows", "status", args.artie_id)

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
