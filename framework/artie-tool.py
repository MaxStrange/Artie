"""
Artie Tool is the build system, test harness, and release pipeline
for all the Artie software components.

Choose from one of the commands and try --help,
as in `python artie-tool.py test --help`
"""
from artietool import common
from artietool import docker
from artietool.build import build
from artietool.deploy import deploy
from artietool.flash import flash
from artietool.install import install
from artietool.install import uninstall
from artietool.release import release
from artietool.status import status
from artietool.test import test
import argparse
import multiprocessing
import os
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
    group.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level. Default: %(default)s")
    group.add_argument("-e", "--enable-error-tracing", action='store_true', help="If given, error messages will include stack traces when possible.")
    group.add_argument("-o", "--output", type=str, default=None, help="If given, should be a path to a file we will create and log to.")
    group.add_argument("--artie-name", default=None, type=str, help="[Deployment, HW testing, and Status] If not given, we automatically detect an Artie on the cluster. If you have more than one Artie, you should give the name of the Artie you want to interact with.")
    group.add_argument("--artifact-folder", default=common.default_build_location(), help="Where to store the output artifacts. Default: %(default)s")
    group.add_argument("--fail-fast", action='store_true', help="If given, we will stop the procedure on the first failure.")
    group.add_argument("--force-build", action='store_true', help="If given, build tasks will run even if they already have their artifacts built.")
    group.add_argument("--docker-logs", action='store_true', help="If given, we print Docker logs as we receive them (normally they are hidden).")
    group.add_argument("--docker-no-cache", action='store_true', help="If given, we pass --no-cache to Docker builds.")
    group.add_argument("--docker-repo", default=None, type=str, help="Docker repository for pushing/pulling.")
    group.add_argument("--docker-tag", default=common.git_tag(), type=str, help="The tag (not name) of the Docker images we build (if any). If not given, we use the git hash.")
    group.add_argument("--docker-password", default=None, type=str, help="The password to use for docker login. For CI, please use the environment variable ARTIE_TOOL_DOCKER_PASSWORD. If both are given, we use this arg instead of the env variable.")
    group.add_argument("--docker-username", default=None, type=str, help="The username for docker login. If not given, we do not attempt to login before pushing images.")
    group.add_argument("--insecure-docker-repo", action='store_true', help="(Experimental) If you are pushing a multiarch image to an insecure repo, you will need this flag.")
    group.add_argument("--kube-config", default=None, type=common.argparse_file_path_type, help="Path to a Kube Config file if you do not store yours in the default location. If you do not know what this is, you can safely ignore it.")
    group.add_argument("--kube-timeout-s", default=180, type=int, help="Timeout (s) for commands that deal with the K8S cluster. Default: %(default)s")
    group.add_argument("--nprocs", default=multiprocessing.cpu_count(), type=int, help="If given, we will use at most this many processes to parallelize the command. Default: %(default)s")

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

    # Parser for the install command
    parser_install = subparsers.add_parser("install", parents=[option_parser])
    install.fill_subparser(parser_install, option_parser)

    # Parser for the uninstall command
    parser_uninstall = subparsers.add_parser("uninstall", parents=[option_parser])
    uninstall.fill_subparser(parser_uninstall, option_parser)

    # Parser for the deploy command
    parser_deploy = subparsers.add_parser("deploy", parents=[option_parser])
    deploy.fill_subparser(parser_deploy, option_parser)

    # Parser for the status command
    parser_status = subparsers.add_parser("status", parents=[option_parser])
    status.fill_subparser(parser_status, option_parser)

    # Parser for clean command
    parser_clean = subparsers.add_parser("clean", parents=[option_parser])
    parser_clean.add_argument("--all", action='store_true', help="If given, we will also remove everything in build-artifacts/")
    parser_clean.set_defaults(cmd=_clean)

    # Parser for the help command
    parser_help = subparsers.add_parser("help", parents=[option_parser])
    parser_help.set_defaults(cmd=_help, parser=parser)

    # Parse the args
    args = parser.parse_args()
    if not hasattr(args, 'kube_config') or args.kube_config is None:
        args.kube_config = os.path.join(os.path.expanduser('~'), ".kube", "config.artie")

    # Set up logging
    common.set_up_logging(args)

    # Try to close gracefully with CTRL-C
    signal.signal(signal.SIGINT, handle_sigint)

    # Run the chosen command
    if not hasattr(args, "cmd"):
        parser.print_usage()
    else:
        retcode = args.cmd(args)

        if not retcode:
            # Note! CI depends on this log string to determine if all tests passed.
            common.info("All tasks succeeded")
        else:
            common.error("At least one task did not succeed")

        # No more logging after this: flush the logger
        common.shutdown_logging()

        if retcode is not None:
            exit(retcode)
