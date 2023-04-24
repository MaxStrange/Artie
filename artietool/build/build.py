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
import logging
import os

# Populate the BUILD_TASKS list by parsing all the 'build' config files
BUILD_TASKS = task_importer.import_tasks(os.path.join(common.repo_root(), "artietool", "tasks", "build-tasks"))

# The available list of task classes/categories
BUILD_CLASSES = [
    "all",
    "all-fw",
    "all-containers",
    "all-yocto",
    "all-base-images",
]

def _build_class_of_items(args):
    """
    Choose between the different categories and run one.
    """
    tasks = []
    match args.module:
        case "all":
            tasks = [t for t in BUILD_TASKS] if args.include_yocto else [t for t in BUILD_TASKS if task.Labels.YOCTO not in t.labels]
        case "all-fw":
            tasks = [t for t in BUILD_TASKS if task.Labels.FIRMWARE in t.labels]
        case "all-containers":
            tasks = [t for t in BUILD_TASKS if task.Labels.DOCKER_IMAGE in t.labels]
        case "all-yocto":
            tasks = [t for t in BUILD_TASKS if task.Labels.YOCTO in t.labels]
        case "all-base-images":
            tasks = [t for t in BUILD_TASKS if task.Labels.BASE_IMAGE in t.labels]
        case _:
            raise ValueError(f"{args.module} is invalid for some reason")

    return run.run_tasks(args, tasks, BUILD_TASKS)

def build(args):
    """
    Top-level build function.
    """
    # Potentially clean first
    if args.clean:
        common.clean()

    if args.module.startswith("all"):
        results, build_tasks = _build_class_of_items(args)
    else:
        build_task = common.find_task_from_name(args.module, BUILD_TASKS)
        assert build_task is not None, f"Somehow build_task is None (args.module: {args.module})"
        results, build_tasks = run.run_tasks(args, [build_task], BUILD_TASKS)

    # Clean up after ourselves
    for t in build_tasks:
        t.clean(args)
    docker.clean_docker_containers()
    docker.clean_build_location(args, common.repo_root())

    # No more logging after this: flush the logger
    logging.shutdown()

    # Print the results for human consumption
    if isinstance(results, Iterable):
        results = sorted(results, key=lambda r: r.name)
        for result in results:
            print(result)
    else:
        print(results)

def fill_subparser(parser_build: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser_build.add_subparsers(title="build-module", description="Choose which module to build")

    # Args that are useful for all build tasks
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("Build", "Build Options")
    group.add_argument("--clean", action='store_true', help="If given, we will run a 'clean' action first, then build.")
    group.add_argument("--include-yocto", action='store_true', help="When building with 'all', we typically exclude Yocto images. Use this flag if you want to include them in 'all'.")

    # Add the all* classes of tasks
    for name in BUILD_CLASSES:
        task_parser = subparsers.add_parser(name, parents=[option_parser])
        task_parser.set_defaults(cmd=build, module=name)

    # Add all the build tasks
    for t in BUILD_TASKS:
        task_parser = subparsers.add_parser(t.name, parents=[option_parser])
        t.fill_subparser(task_parser, option_parser)        # Fill argparse with anything that is specific to the task
        task_parser.set_defaults(cmd=build, module=t.name)  # Regardless of the task chosen, the command is always 'build' from this module
