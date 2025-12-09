"""
All the machinery for the status command.
"""
from .. import common
from .. import kube
from artie_tooling import hw_config
import argparse

def _get_hw_config(args: argparse.Namespace) -> int:
    """Get the HW configuration from K3S."""
    try:
        # After this call, `args` will have `artie_name` populated
        artie_hw_config = kube.get_artie_hw_config(args)
    except ValueError as e:
        common.error(f"Cannot get Artie's HW configuration: {str(e)}")
        return 1
    except KeyError as e:
        common.error(f"Cannot get Artie's HW configuration: {str(e)}")
        return 1

    # We have a HW configuration. Format it according to args.
    if args.json:
        s = artie_hw_config.to_json_str()
        print(s)
    elif args.yaml:
        s = artie_hw_config.to_yaml_str()
        print(s)
    else:
        common.info(f"HW Configuration for {args.artie_name}:")
        common.info(str(artie_hw_config))

    return 0

def get(args: argparse.Namespace):
    """
    Top-level get function.
    """
    retcode = 0

    match args.module:
        case "hw_config":
            retcode = _get_hw_config(args)
        case _:
            common.error(f"Unknown get module: {args.module}")
            retcode = 1

    return retcode

def fill_subparser(parser_get: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser_get.add_subparsers(title="get-module", description="Choose what to get")

    # Args that are useful for all get commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("Get", "Get Options")
    group.add_argument("--json", action='store_true', help="If given, we format the output in JSON according to `get-command-api.md`")
    group.add_argument("--yaml", action='store_true', help="If given, we format the output in YAML according to `get-command-api.md`")

    # Add all the get subcommands
    hw_config_parser = subparsers.add_parser("hw-config", parents=[option_parser])
    hw_config_parser.set_defaults(cmd=get, module="hw_config")
