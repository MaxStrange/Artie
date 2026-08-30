"""
All the machinery for building.
"""
from .. import common
from .. import docker
from ..infrastructure import run
from ..infrastructure import task
from ..infrastructure import task_importer
from collections.abc import Iterable
import argparse
import os

# Build tasks come from every component in the workspace - see build_tasks().
_BUILD_TASKS = None

def build_tasks():
    """
    Every build task in the workspace, discovered once per process.

    Each component owns the definitions of its own tasks, so this looks across every
    checkout rather than reading one directory. Deferred until first use so that a
    malformed task definition in any component cannot break `--help` at import time.
    """
    global _BUILD_TASKS
    if _BUILD_TASKS is None:
        _BUILD_TASKS = task_importer.discover_tasks("build")
    return _BUILD_TASKS

# The available list of task classes/categories
BUILD_CLASSES = [
    "all",
    "all-fw",
    "all-containers",
    "all-yocto",
    "all-base-images",
    "all-driver"
]

def _build_class_of_items(args):
    """
    Choose between the different categories and run one.
    """
    tasks = []
    match args.module:
        case "all":
            tasks = [t for t in build_tasks()] if args.include_yocto else [t for t in build_tasks() if task.Labels.YOCTO not in t.labels]
        case "all-fw":
            tasks = [t for t in build_tasks() if task.Labels.FIRMWARE in t.labels]
        case "all-containers":
            tasks = [t for t in build_tasks() if task.Labels.DOCKER_IMAGE in t.labels]
        case "all-yocto":
            tasks = [t for t in build_tasks() if task.Labels.YOCTO in t.labels]
        case "all-base-images":
            tasks = [t for t in build_tasks() if task.Labels.BASE_IMAGE in t.labels]
        case "all-driver":
            tasks = [t for t in build_tasks() if task.Labels.DRIVER in t.labels]
        case _:
            raise ValueError(f"{args.module} is invalid for some reason")

    return run.run_tasks(args, tasks, build_tasks())

def build(args):
    """
    Top-level build function.
    """
    # Potentially clean first
    if args.clean:
        common.clean()

    if args.module.startswith("all"):
        results, ran_tasks = _build_class_of_items(args)
    else:
        build_task = common.find_task_from_name(args.module, build_tasks())
        assert build_task is not None, f"Somehow build_task is None (args.module: {args.module})"
        results, ran_tasks = run.run_tasks(args, [build_task], build_tasks())

    # Clean up after ourselves
    for t in ran_tasks:
        t.clean(args)
    docker.clean_docker_containers()
    docker.clean_build_location(args, common.repo_root())

    # Print the results for human consumption
    retcode = 0
    if isinstance(results, Iterable):
        results = sorted(results, key=lambda r: r.name)
        for result in results:
            print(result)
            if not result.success:
                retcode = 1
    else:
        print(results)
        if not results.success:
            retcode = 1

    return retcode

def fill_subparser(parser_build: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser_build.add_subparsers(title="build-module", description="Choose which module to build")

    # Args that are useful for all build tasks
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("Build", "Build Options")
    group.add_argument("--clean", action='store_true', help="If given, we will run a 'clean' action first, then build.")
    group.add_argument("--include-yocto", action='store_true', help="When building with 'all', we typically exclude Yocto images. Use this flag if you want to include them in 'all'.")
    group.add_argument("--platforms", nargs='+', default=None, metavar="PLATFORM", help="If given (e.g. 'linux/arm64'), only Docker build steps targeting one of these platforms will run; steps for other platforms are skipped and assumed to have been built elsewhere. Manifest assembly is skipped while this filter is active - run again with --manifests-only to assemble manifests.")
    group.add_argument("--manifests-only", action='store_true', help="If given, we skip all Docker image builds (assuming they have already been built and pushed) and only assemble/push the multi-arch manifests. Use this after per-platform builds done with --platforms.")

    # Add the all* classes of tasks
    for name in BUILD_CLASSES:
        task_parser = subparsers.add_parser(name, parents=[option_parser])
        task_parser.set_defaults(cmd=build, module=name)

    # Add all the build tasks
    for t in build_tasks():
        task_parser = subparsers.add_parser(t.name, parents=[option_parser])
        t.fill_subparser(task_parser, option_parser)        # Fill argparse with anything that is specific to the task
        task_parser.set_defaults(cmd=build, module=t.name)  # Regardless of the task chosen, the command is always 'build' from this module
