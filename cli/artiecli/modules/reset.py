from .. import apiclient
from .. import common
import argparse
import errno

class ResetClient(apiclient.APIClient):
    def __init__(self, args) -> None:
        super().__init__(args)

    def _convert_address_to_mcu(self, address: int) -> str:
        match address:
            case 0x00:
                return 'eyebrows'
            case 0x01:
                return 'mouth'
            case 0x02:
                return 'sensors-head'
            case 0x03:
                return 'pump-control'
            case 0xFF:
                return 'all'
            case _:
                print(f"Invalid argument given for MCU address: {address}")
                exit(errno.EINVAL)

    def reset_target(self, address: int):
        mcu = self._convert_address_to_mcu(address)
        self.post(f"/reset/mcu", params={'artie-id': self.artie_id, 'id': mcu})

    def status(self):
        response = self.get("/reset/status", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting reset status: {response}", module='reset', submodule='status', artie_id=self.artie_id)
        else:
            common.format_print_status_result(response.json(), module='reset', artie_id=self.artie_id)

    def self_check(self):
        response = self.post("/reset/self-test", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error running reset self-check: {response}", module='reset', submodule='status', artie_id=self.artie_id)
            return
        else:
            # Print the status now that the self-check has completed
            self.status()


def _connect_client(args) -> common._ConnectionWrapper | ResetClient:
    if common.in_test_mode(args):
        ip = "localhost"
        port = 18861
        connection = common.connect(ip, port, ipv6=args.ipv6)
    else:
        connection = ResetClient(args)
    return connection

def _cmd_reset_target_mcu(args):
    connection = _connect_client(args)
    connection.reset_target(args.address)

def _cmd_reset_target_sbc(args):
    raise NotImplementedError("This functionality is not yet implemented.")

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
