"""
Artie Tool is the build system, test harness, and release pipeline
for all the Artie software components.

Choose from one of the commands and try --help,
as in `python artie-tool.py test --help`
"""
from artietool import common
from artietool import docker
from artietool.build import build
from artietool.flash import flash
from artietool.release import release
from artietool.test import test
import argparse
import multiprocessing
import signal

def handle_sigint(sig, stack_frame):
    """
    Handle shutting down all the remaining Docker containers, if any.
    """
    docker.clean_docker_containers()
    common.clean_build_stuff()
    exit(130)

def _clean(args):
    """
    Clean up after anything artie-tool may have done.
    """
    if args.all:
        common.clean()
    else:
        common.clean_build_stuff()

    # Now call 'clean()' on all possible tasks
    all_tasks = []
    all_tasks.extend(build.BUILD_TASKS)
    all_tasks.extend(test.TEST_TASKS)
    all_tasks.extend(flash.FLASH_TASKS)
    all_tasks.extend(release.RELEASE_TASKS)
    for t in all_tasks:
        t.clean(args)

def _help(args):
    """
    Print the help message.
    """
    args.parser.print_help()

if __name__ == "__main__":
    # Set up parser
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    subparsers = parser.add_subparsers(title="Command", description="Artie Tool Command", help="The top-level command to invoke with Artie Tool")

    # Global arguments useful for at least two commands
    ## Have to create a second argparser that does NOT have all the subparsers. This one just has options.
    ## All [parents] should be derived from this one, while all subparsers get derived down the other chain.
    ## It's gross, but seems to be how argparse works with subcommands and global options.
    option_parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    group = option_parser.add_argument_group("Global", "Global Options")
    group.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
    group.add_argument("-e", "--enable-error-tracing", action='store_true', help="If given, error messages will include stack traces when possible.")
    group.add_argument("--artifact-folder", default=common.default_build_location())
    group.add_argument("--force-build", action='store_true', help="If given, build tasks will run even if they already have their artifacts built.")
    group.add_argument("--docker-logs", action='store_true', help="If given, we print Docker logs as we receive them (normally they are hidden).")
    group.add_argument("--docker-no-cache", action='store_true', help="If given, we pass --no-cache to Docker builds.")
    group.add_argument("--docker-repo", default=None, type=str, help="Docker repository for pushing/pulling.")
    group.add_argument("--docker-tag", default=common.git_tag(), type=str, help="The tag (not name) of the Docker images we build (if any). If not given, we use the git hash.")
    group.add_argument("--nprocs", default=multiprocessing.cpu_count(), type=int, help="If given, we will use at most this many processes to parallelize the command.")

    # Parser for build command
    parser_build = subparsers.add_parser("build", parents=[option_parser])
    build.fill_subparser(parser_build, option_parser)

    # Parser for release command
    parser_release = subparsers.add_parser("release", parents=[option_parser])
    release.fill_subparser(parser_release, option_parser)

    # Parser for test command
    parser_test = subparsers.add_parser("test", parents=[option_parser])
    test.fill_subparser(parser_test, option_parser)

    # Parser for the flash command
    parser_flash = subparsers.add_parser("flash", parents=[option_parser])
    flash.fill_subparser(parser_flash, option_parser)

    # Parser for clean command
    parser_clean = subparsers.add_parser("clean", parents=[option_parser])
    parser_clean.add_argument("--all", action='store_true', help="If given, we will also remove everything in build-artifacts/")
    parser_clean.set_defaults(cmd=_clean)

    # Parser for the help command
    parser_help = subparsers.add_parser("help", parents=[option_parser])
    parser_help.set_defaults(cmd=_help, parser=parser)

    # Parse the args
    args = parser.parse_args()

    # Set up logging
    common.set_up_logging(args)

    # Try to close gracefully with CTRL-C
    signal.signal(signal.SIGINT, handle_sigint)

    # Run the chosen command
    if not hasattr(args, "cmd"):
        parser.print_usage()
    else:
        args.cmd(args)
