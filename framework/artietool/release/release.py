"""
All machinery pertaining to release work.
"""
from .. import common
from ..build import build
import argparse
import subprocess

def _fetch(args) -> int:
    if args.remote and not args.skip_checkout:
        p = subprocess.run(["git", "fetch"], capture_output=True)
        retcode = p.returncode
        if retcode:
            common.error(f"Error running git fetch: {p.stdout} ; {p.stderr}")
            return retcode
    return 0

def _checkout(args) -> int:
    if not args.skip_checkout:
        p = subprocess.run(["git", "checkout", args.branch], capture_output=True)
        retcode = p.returncode
        if retcode:
            common.error(f"Error running git checkout: {p.stdout} ; {p.stderr}")
            return retcode
    return 0

def _pull(args) -> int:
    if args.remote and not args.skip_checkout:
        p = subprocess.run(["git", "pull"], capture_output=True)
        retcode = p.returncode
        if retcode:
            common.error(f"Error running git pull: {p.stdout} ; {p.stderr}")
            return retcode
    return 0

def release(args):
    """
    Top-level release function.
    """
    retcode = 0

    # Possibly fetch remote
    if retcode := _fetch(args):
        return retcode

    # Checkout the appropriate branch
    if retcode := _checkout(args):
        return retcode

    # Possibly pull
    if retcode := _pull(args):
        return retcode

    # Get the git tag
    tag = args.docker_tag

    # Determine the repo
    repo = "maxfieldstrange" if args.docker_repo is None else args.docker_repo

    # Build and push all
    # TODO: Handle args here appropriately?
    retcode = build.build(args)
    if retcode:
        common.error(f"Error building the images. See above logs.")
        return retcode

    # Print results for humans
    print(f"Images built and pushed to {repo}/*:{tag}")

    return retcode

def fill_subparser(parser_release: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    parser_release.add_argument("--skip-checkout", action='store_true', help="If given, we skip checking out a branch.")
    parser_release.add_argument("-b", "--branch", default="main", type=str, help="The branch of the repository to release. We will attempt to checkout to this branch.")
    parser_release.add_argument("--remote", action='store_true', help="If given, we attempt to first pull the branch from origin.")
    parser_release.set_defaults(cmd=release, module="release-artie")
