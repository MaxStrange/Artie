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

def _argparse_file_path_type(arg: str) -> str:
    """
    Validates that the given file path exists on disk. To be used as the type argument in argparse.
    """
    if not os.path.exists(arg):
        raise argparse.ArgumentError()
    else:
        return arg

def main():
    """
    Entrypoint for the script.
    """
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s ([help]) [module] [subsystem] [cmd] <args>", add_help=False)
    subparsers = parser.add_subparsers(title="Module", description="Module command", help="The Module to issue a command for")

    option_parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    group = option_parser.add_argument_group("Global", "Global Options")
    group.add_argument("--ipv6", action='store_true', help="If given, we use IPv6 instead of IPv4.")
    group.add_argument("--kube-config", default=None, type=_argparse_file_path_type, help="Path to a Kube Config file if you do not store yours in the default location. If you do not know what this is, you can safely ignore it.")
    group.add_argument("--unit-test", action='store_true', help="If given, we do not access the Artie cluster. Used in unit tests.")
    group.add_argument("--integration-test", action='store_true', help="If given, we do not access the Artie cluster. Used in integration tests.")
    group.add_argument("--artie-id", type=str, default=None, help="If given, we use this for the Artie we wish to communicate with. If not given and we aren't in test mode, we assume there is only one Artie. If there are multiple Arties in the cluster we error out.")
    # TODO: Handle authentication to the K3S cluster (Maybe we should just authenticate only when .kubeconfig is present, and just make use of the .kubeconfig for auth and not worry about it?)

    # Add all the module subparsers
    for module, name in zip(MODULES, MODULE_NAMES):
        module_parser = subparsers.add_parser(name, parents=[option_parser])
        module.fill_subparser(module_parser, option_parser)

    # Add the 'help' command
    parser_help = subparsers.add_parser("help", parents=[option_parser])
    parser_help.set_defaults(cmd=_help, parser=parser)

    # Parse the arguments
    args = parser.parse_args()
    if not hasattr(args, 'kube_config') or args.kube_config is None:
        args.kube_config = os.path.join(os.path.expanduser('~'), ".kube", "config.artie")

    # Run the chosen command
    if not hasattr(args, 'cmd'):
        parser.print_usage()
    else:
        args.cmd(args)

if __name__ == "__main__":
    main()
