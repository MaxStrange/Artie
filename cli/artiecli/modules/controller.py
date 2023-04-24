import argparse
import errno
import platform
import socket

try:
    from artie_i2c import i2c
except ModuleNotFoundError:
    i2c = None

def _send_to_leddaemon(cmd: str):
    if platform.system() != "Linux":
        print("Cannot open a systemd socket when not running on Linux.")
        exit(errno.ENOSYS)

    s = socket.socket(family=socket.AF_UNIX)
    s.connect("/tmp/leddaemonconnection")
    s.send(cmd.encode())
    s.close()

def _cmd_led_on(args):
    _send_to_leddaemon("on")

def _cmd_led_off(args):
    _send_to_leddaemon("off")

def _cmd_led_heartbeat(args):
    _send_to_leddaemon("heartbeat")

def _cmd_i2c_list(args):
    if i2c is None:
        print("No i2c bus available.")
        exit(errno.ENXIO)

    for i in i2c.list_all_instances():
        print(i)

def _cmd_i2c_scan(args):
    if i2c is None:
        print("No i2c bus available.")
        exit(errno.ENXIO)

    instances = i2c.list_all_instances()
    if args.instance == 'ALL':
        for instance in instances:
            for a in i2c.list_all_addresses_on_instance(instance):
                print(a)
    else:
        for a in i2c.list_all_addresses_on_instance(args.instance):
            print(a)

def _check_i2c_instance_arg_type(arg):
    if arg == 'ALL':
        return arg
    else:
        try:
            value = int(arg)
        except ValueError as err:
            raise argparse.ArgumentTypeError(str(err))

        return value

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

def _fill_i2c_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="i2c", description="The i2c subsystem")

    # Args that are useful for all i2c commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("i2c", "i2c Subsystem Options")

    # For each I2C command, add the actual command and any args
    ## List command
    list_parser = subparsers.add_parser("list", help="List all i2c instances on the bus.", parents=[option_parser])
    list_parser.set_defaults(cmd=_cmd_i2c_list)

    ## Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan one or more i2c instances for devices.", parents=[option_parser])
    scan_parser.add_argument("instance", default="ALL", type=_check_i2c_instance_arg_type, help="Either an integer corresponding to an i2c instance or 'ALL'")
    scan_parser.set_defaults(cmd=_cmd_i2c_scan)

def fill_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="controller", description="The controller module's subsystems")

    # Args that are useful for all controller module commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("Controller Module", "Controller Module Options")

    # Add all the commands for each subystem
    ## I2C
    i2c_parser = subparsers.add_parser("i2c", parents=[option_parser])
    _fill_i2c_subparser(i2c_parser, option_parser)

    ## LED
    led_parser = subparsers.add_parser("led", parents=[option_parser])
    _fill_led_subparser(led_parser, option_parser)
