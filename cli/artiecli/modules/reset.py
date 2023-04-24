from .. import common
import argparse

def _cmd_reset_target_mcu(args):
    ip = "localhost"
    port = 18861
    connection = common.connect(ip, port, ipv6=args.ipv6)
    connection.reset_target(args.address)

def _cmd_reset_target_sbc(args):
    raise NotImplementedError("This functionality is not yet implemented.")

#########################################################################################
################################## PARSERS ##############################################
#########################################################################################
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
