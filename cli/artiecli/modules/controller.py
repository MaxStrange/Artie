import argparse
import dbus
from artie_i2c import i2c

def _connect_to_led_interface():
    bus = dbus.SessionBus()
    led = bus.get_object("com.artie.LedInterface", "/Led")
    return led

def _cmd_led_on(args):
    led = _connect_to_led_interface()
    led.on()

def _cmd_led_off(args):
    led = _connect_to_led_interface()
    led.off()

def _cmd_led_heartbeat(args):
    led = _connect_to_led_interface()
    led.heartbeat()

def _cmd_i2c_list(args):
    for i in i2c.list_all_instances():
        print(i)

def _cmd_i2c_scan(args):
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

def _parse_subsystem_i2c(subparser):
    def _parse_cmd_list(ss):
        p: argparse.ArgumentParser = ss.add_parser("list", help="List all i2c instances")
        p.add_argument("--list", dest="cmd", default=_cmd_i2c_list, help="This command has no args.")
    def _parse_cmd_scan(ss):
        p: argparse.ArgumentParser = ss.add_parser("scan", help="Scan one ore more i2c instances for devices")
        p.add_argument("instance", default="ALL", type=_check_i2c_instance_arg_type, help="Either an integer corresponding to an i2c instance or 'ALL'")
        p.add_argument("--scan", dest="cmd", default=_cmd_i2c_scan, help="Reserved.")
    parser: argparse.ArgumentParser = subparser.add_parser("i2c", help="i2c subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_list(cmd_subparsers)
    _parse_cmd_scan(cmd_subparsers)

def _parse_subsystem_led(subparser):
    def _parse_cmd_on(ss):
        p: argparse.ArgumentParser = ss.add_parser("on", help="Turn LED on.")
        p.add_argument("--on", dest="cmd", default=_cmd_led_on, help="This command has no args.")
    def _parse_cmd_off(ss):
        p = ss.add_parser("off", help="Turn LED off.")
        p.add_argument("--off", dest="cmd", default=_cmd_led_off, help="This command has no args.")
    def _parse_cmd_heartbeat(ss):
        p = ss.add_parser("heartbeat", help="Change eyebrow LED mode to heartbeat.")
        p.add_argument("--heartbeat", dest="cmd", default=_cmd_led_heartbeat, help="This command has no args.")
    parser: argparse.ArgumentParser = subparser.add_parser("led", help="LED subsystem")
    cmd_subparsers = parser.add_subparsers(help="Command")
    _parse_cmd_on(cmd_subparsers)
    _parse_cmd_off(cmd_subparsers)
    _parse_cmd_heartbeat(cmd_subparsers)

def add_subparser(subparsers):
    """
    Add the subargs for the controller module.
    """
    parser: argparse.ArgumentParser = subparsers.add_parser("controller", help="Controller module")
    subsystem_subparsers = parser.add_subparsers(help="Subsystem")
    _parse_subsystem_i2c(subsystem_subparsers)
    _parse_subsystem_led(subsystem_subparsers)
