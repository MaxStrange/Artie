"""
All machinery pertaining to release work.
"""
import argparse

RELEASE_TASKS = []

def release(args):
    """
    Top-level release function.
    """
    raise NotImplementedError()

def fill_subparser(parser_release: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    group = parser_release.add_argument_group("Release", "Release Options")
    parser_release.set_defaults(cmd=release)
