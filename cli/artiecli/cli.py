"""
Command line interface for Artie.
"""
import argparse
import importlib
import os

# Dynamically find and import all modules in the 'modules' directory so we can execute a function in each
_artie_cli_dpath = os.path.dirname(os.path.realpath(__file__))
_module_dpath = os.path.join(_artie_cli_dpath, "modules")
MODULE_NAMES = [os.path.splitext(fname)[0] for fname in os.listdir(_module_dpath) if os.path.splitext(os.path.join(_module_dpath, fname))[-1].lower() == ".py"]
MODULES = [importlib.import_module("." + name, package='artiecli.modules') for name in MODULE_NAMES]

def _help(args):
    """
    Display a helpful message.
    """
    print("Welcome to Artie CLI. Please choose from one of the following modules and run it with --help for more options:")
    print("")
    for name in MODULE_NAMES:
        print(name)

def main():
    """
    Entrypoint for the script.
    """
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s ([help]) [module] [subsystem] [cmd] <args>", add_help=False)
    subparsers = parser.add_subparsers(title="Module", description="Module command", help="The Module to issue a command for")

    option_parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    group = option_parser.add_argument_group("Global", "Global Options")
    group.add_argument("--ipv6", action='store_true', help="If given, we use IPv6 instead of IPv4.")

    # Add all the module subparsers
    for module, name in zip(MODULES, MODULE_NAMES):
        module_parser = subparsers.add_parser(name, parents=[option_parser])
        module.fill_subparser(module_parser, option_parser)

    # Add the 'help' command
    parser_help = subparsers.add_parser("help", parents=[option_parser])
    parser_help.set_defaults(cmd=_help, parser=parser)

    # Parse the arguments
    args = parser.parse_args()

    # Run the chosen command
    if not hasattr(args, 'cmd'):
        parser.print_usage()
    else:
        args.cmd(args)

if __name__ == "__main__":
    main()
