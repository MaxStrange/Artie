"""
Artie Tool is the build system for all the Artie software components.
"""
from artietool import build
from artietool import common
from artietool import release
from artietool import test
import argparse
import logging

def _clean(args):
    """
    Clean up after anything artie-tool may have done (to an extent).
    """
    common.clean()


if __name__ == "__main__":
    # Set up parser
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    subparsers = parser.add_subparsers(help="Command")

    # Parser for build command
    parser_build = subparsers.add_parser("build")
    build.fill_subparser(parser_build)

    # Parser for release command
    parser_release = subparsers.add_parser("release")
    release.fill_subparser(parser_release)

    # Parser for test command
    parser_test = subparsers.add_parser("test")
    test.fill_subparser(parser_test)

    # Parser for clean command
    parser_clean = subparsers.add_parser("clean")
    parser_clean.set_defaults(cmd=_clean)

    args = parser.parse_args()
    # Set up logging
    common.set_up_logging(args)

    # Run the chosen command
    if not hasattr(args, "cmd"):
        parser.print_usage()
    else:
        args.cmd(args)
