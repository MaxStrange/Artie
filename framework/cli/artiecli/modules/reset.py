from .. import common
from artie_tooling import reset_client
import argparse

def _connect_client(args) -> common._ConnectionWrapper | reset_client.ResetClient:
    if common.in_test_mode(args):
        ip = "localhost"
        port = 18861
        connection = common.connect(ip, port, ipv6=args.ipv6)
    else:
        connection = reset_client.ResetClient(profile=args.artie_profile, integration_test=args.integration_test, unit_test=args.unit_test)
    return connection

def _cmd_reset_target_mcu(args):
    connection = _connect_client(args)
    common.format_print_result(connection.reset_target(args.address), "reset", "MCU", args.artie_id)

def _cmd_reset_target_sbc(args):
    raise NotImplementedError("This functionality is not yet implemented.")

def _cmd_status_self_check(args):
    client = _connect_client(args)
    common.format_print_result(client.self_check(), "reset", "status", args.artie_id)
    common.format_print_status_result(client.status(), "reset", args.artie_id)

def _cmd_status_get(args):
    client = _connect_client(args)
    common.format_print_status_result(client.status(), "reset", args.artie_id)

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

def fill_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="reset", description="The reset module's subsystems")

    # Args that are useful for all reset module commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    #group = option_parser.add_argument_group("Reset Module", "Reset Module Options")

    # Add all the commands for each subystem
    ## MCU
    mcu_parser = subparsers.add_parser("mcu", parents=[option_parser])
    mcu_parser.add_argument("address", type=common.int_or_hex_type, help="The address of the device to reset. Check the various board config files for valid addresses.")
    mcu_parser.set_defaults(cmd=_cmd_reset_target_mcu)

    ## SBC
    sbc_parser = subparsers.add_parser("sbc", parents=[option_parser])
    sbc_parser.add_argument("id", choices=['controller', 'ears', 'eyes'], help="The single board computer to reset.")
    sbc_parser.set_defaults(cmd=_cmd_reset_target_sbc)

    ## Status Check
    status_parser = subparsers.add_parser("status", parents=[option_parser])
    _fill_status_subparser(status_parser, option_parser)
