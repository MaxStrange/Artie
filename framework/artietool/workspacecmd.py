"""
The `artie-tool workspace` command: inspect and populate the set of repositories that
Artie Tool builds from.

The resolution logic itself lives in `workspace`, which deliberately has no dependency on
`common` so that `common` can use it. This module is the command line surface over it.
"""
from . import common
from . import workspace
import argparse


def _cmd_status(args) -> int:
    """
    Print where each Artie component resolves to and what state it is in.
    """
    cfg = workspace.config(args)

    print(f"Workspace: {cfg.workspace}")
    print(f"Channel:   {cfg.channel}")
    print()

    header = f"{'REPO':<16} {'STATE':<10} {'REF':<10} {'SOURCE':<12} PATH"
    print(header)
    print("-" * len(header))

    for name in workspace.known_repo_names():
        info = workspace.repo_status(name, cfg)

        if not info["exists"]:
            state = "missing"
        elif info["dirty"]:
            state = "dirty"
        elif info["git"]:
            state = "clean"
        else:
            state = "present"

        source = "dev-override" if info["dev_override"] else ("git" if info["git"] else "in-repo")
        ref = info["head"] or info["ref"] or "-"

        print(f"{name:<16} {state:<10} {ref:<10} {source:<12} {info['path']}")

    return 0


def _cmd_sync(args) -> int:
    """
    Make sure every configured repository is present at its configured ref.
    """
    cfg = workspace.config(args)

    names = args.repos if args.repos else workspace.known_repo_names()
    failed = []
    for name in names:
        try:
            if not workspace.sync_repo(name, cfg, dry_run=args.dry_run):
                failed.append(name)
        except KeyError as e:
            common.error(str(e))
            failed.append(name)

    if failed:
        common.error(f"Could not sync: {', '.join(failed)}")
        return 1

    return 0


def fill_subparser(parser_workspace: argparse.ArgumentParser, option_parser: argparse.ArgumentParser):
    """
    Add the workspace subcommands to the given parser.
    """
    subparsers = parser_workspace.add_subparsers(title="Workspace Command", description="Workspace subcommand", help="What to do with the workspace")

    parser_status = subparsers.add_parser("status", parents=[option_parser], help="Show where each Artie component resolves to.")
    parser_status.set_defaults(cmd=_cmd_status)

    parser_sync = subparsers.add_parser("sync", parents=[option_parser], help="Clone or fetch each Artie component at its configured ref.")
    parser_sync.add_argument("repos", nargs="*", default=[], help="Only sync these repositories. Defaults to all of them.")
    parser_sync.add_argument("--dry-run", action="store_true", help="Report what would be cloned or fetched without touching anything.")
    parser_sync.set_defaults(cmd=_cmd_sync)
