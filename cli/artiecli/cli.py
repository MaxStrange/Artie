"""
Command line interface for Artie.
"""
from .modules import controller
from .modules import eyebrows
from .modules import mouth
import argparse

MODULES = [
    controller,
    eyebrows,
    mouth,
]

def main():
    """
    Entrypoint for the script.
    """
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s [--help] [module] [subsystem] [cmd] <args>")
    subparsers = parser.add_subparsers(help="Module command")
    for module in MODULES:
        module.add_subparser(subparsers)
    args = parser.parse_args()

    if not hasattr(args, 'cmd'):
        parser.print_usage()
    else:
        args.cmd(args)

if __name__ == "__main__":
    main()
