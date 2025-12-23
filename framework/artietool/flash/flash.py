"""
This module enables artie-tool to flash firmware and Yocto images onto devices or SD cards.
"""
from ..build import build 
from .. import common
from ..infrastructure import run
from ..infrastructure import task
from ..infrastructure import task_importer
from collections.abc import Iterable
import argparse
import os

FLASH_TASKS = task_importer.import_tasks(os.path.join(common.repo_root(), "framework", "artietool", "tasks", "flash-tasks"))

def flash(args):
    """
    Top-level flash function.
    """
    flash_task = common.find_task_from_name(args.module, FLASH_TASKS)
    assert flash_task is not None, f"Somehow flash_task is None (args.module: {args.module})"
    results, flash_tasks = run.run_tasks(args, [flash_task], FLASH_TASKS + build.BUILD_TASKS)

    for t in flash_tasks:
        t.clean(args)

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

def list_flash_targets(args):
    """
    List all flash targets.
    """
    for t in FLASH_TASKS:
        print(t.name)

    return 0

def fill_subparser(parser_flash: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser_flash.add_subparsers(title="flash-module", description="Choose what to flash")

    # Args that are useful for all flash tasks
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("Flash", "Flash Options")

    # Add all the flash tasks
    for t in FLASH_TASKS:
        task_parser = subparsers.add_parser(t.name, parents=[option_parser])
        t.fill_subparser(task_parser, parent=option_parser)
        task_parser.set_defaults(cmd=flash, module=t.name)

    # Add the list command
    list_parser = subparsers.add_parser("list", parents=[option_parser], help="List all flash targets")
    list_parser.set_defaults(cmd=list_flash_targets, module="list")
