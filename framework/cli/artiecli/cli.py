"""
Command line interface for Artie.

Typically, Artie is accessed through Workbench. But there are two cases where a CLI
makes more sense: 1) automated testing and 2) development.

As for (1), Artie CLI is used extensively in the automated testing of the various micro services.
As for (2), when SSH'd into a controller node, a developer can run Artie CLI locally to access
all kinds of things that are not exposed by Artie's high level API server. This makes it easier
to debug issues with things like Artie's LED or the CAN bus.
"""
from artie_tooling import artie_profile
import argparse
import importlib
import os
import urllib3

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
    group.add_argument("--artie-id", type=str, default=None, help="If given, we use this for the Artie we wish to communicate with. This is used to derive the Artie profile to use if the --artie-profile argument is not given. If the --artie-profile argument is given, we use the artie specified by that profile instead and this argument is ignored.")
    group.add_argument("--artie-profile", type=_argparse_file_path_type, default=None, help=f"If given, we use this Artie profile. If not given, and --artie-id is given, we attempt to use the profile corresponding to that Artie at {artie_profile.DEFAULT_SAVE_PATH}. If neither argument is given, we use only profile found at {artie_profile.DEFAULT_SAVE_PATH}; if more than one profile is found, we error out.")
    group.add_argument("--integration-test", action='store_true', help="If given, we do not access the Artie cluster. Used in integration tests.")
    group.add_argument("--ipv6", action='store_true', help="If given, we use IPv6 instead of IPv4.")
    group.add_argument("--unit-test", action='store_true', help="If given, we do not access the Artie cluster. Used in unit tests.")
    # TODO: For authenticating TO the Artie API server, we should make use of the Artie profile + username/password mechanism that workbench uses
    # TODO: For authenticating the Artie API server itself, we should make use of the CA bundle in the Artie profile
    # TODO: Refactor Artie CLI so that workbench and Artie CLI both use the same library for REST API calls into the API server

    # Disable the urllib3 warnings
    urllib3.disable_warnings()

    # Add all the module subparsers
    for module, name in zip(MODULES, MODULE_NAMES):
        module_parser = subparsers.add_parser(name, parents=[option_parser])
        module.fill_subparser(module_parser, option_parser)

    # Add the 'help' command
    parser_help = subparsers.add_parser("help", parents=[option_parser])
    parser_help.set_defaults(cmd=_help, parser=parser)

    # Parse the arguments
    args = parser.parse_args()
    if args.artie_profile is not None:
        # Use the given profile
        pass
    elif args.artie_profile is None and args.artie_id is not None:
        # Derive the profile path from the given Artie ID
        args.artie_profile = os.path.join(artie_profile.DEFAULT_SAVE_PATH, f"{args.artie_id}.json")
    elif args.artie_id is None and args.artie_profile is None:
        # Attempt to find a single profile in the default location
        profiles = [f for f in os.listdir(artie_profile.DEFAULT_SAVE_PATH) if f.endswith(".json")]
        if len(profiles) == 0:
            print(f"Error: No Artie profile found at {artie_profile.DEFAULT_SAVE_PATH}. Please specify a profile path or make sure you have installed an Artie.")
            exit(1)
        elif len(profiles) > 1:
            print(f"Error: Multiple Artie profiles found at {artie_profile.DEFAULT_SAVE_PATH}. Please specify an Artie ID or profile path.")
            exit(1)
        else:
            args.artie_profile = os.path.join(artie_profile.DEFAULT_SAVE_PATH, profiles[0])

    # Now check that artie_profile path exists
    if not os.path.exists(args.artie_profile):
        print(f"Error: Artie profile not found at {args.artie_profile}. Please specify a valid profile path or Artie ID.")
        exit(1)

    # Load the Artie profile
    args.artie_profile = artie_profile.ArtieProfile.load(path=args.artie_profile)
    args.artie_id = args.artie_profile.artie_name

    # Run the chosen command
    if not hasattr(args, 'cmd'):
        parser.print_usage()
    else:
        args.cmd(args)

if __name__ == "__main__":
    main()
