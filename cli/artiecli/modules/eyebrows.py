from .. import common
import argparse

def _connect_client(args):
    ip = "localhost"
    port = 18863
    connection = common.connect(ip, port, ipv6=args.ipv6)
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

#########################################################################################
################################# LCD Subsystem #########################################
#########################################################################################
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
