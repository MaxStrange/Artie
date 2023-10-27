"""
All the machinery for deploying.
"""
from .. import common
from .. import docker
from ..infrastructure import run
from ..infrastructure import task
from ..infrastructure import task_importer
from collections.abc import Iterable
import argparse
import os

# Populate the DEPLOY_TASKS list by parsing all the 'deploy' config files
DEPLOY_TASKS = task_importer.import_tasks(os.path.join(common.repo_root(), "artietool", "tasks", "deploy-tasks"))

def deploy(args):
    """
    Top-level deploy function.
    """
    deploy_task = common.find_task_from_name(args.module, DEPLOY_TASKS)
    assert deploy_task is not None, f"Somehow deploy_task is None (args.module: {args.module})"
    results, deploy_tasks = run.run_tasks(args, [deploy_task], DEPLOY_TASKS)

    for t in deploy_tasks:
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

def fill_subparser(parser_deploy: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser_deploy.add_subparsers(title="deploy-module", description="Choose what to deploy")

    # Args that are useful for all build tasks
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("Deploy", "Deploy Options")
    group.add_argument("--chart-version", default=None, type=str, help="If given, we override the default version of the deployment with this value.")
    group.add_argument("--artie-name", default=None, type=str, help="If not given, we automatically detect an Artie on the cluster. If you have more than one Artie, you should give the name of the Artie you want to deploy to.")
    group.add_argument("--delete", action='store_true', help="If given, we delete the deployment instead of creating it.")

    # Add all the deploy tasks
    for t in DEPLOY_TASKS:
        task_parser = subparsers.add_parser(t.name, parents=[option_parser])
        t.fill_subparser(task_parser, option_parser)         # Fill argparse with anything that is specific to the task
        task_parser.set_defaults(cmd=deploy, module=t.name)  # Regardless of the task chosen, the command is always 'deploy' from this module
