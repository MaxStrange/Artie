"""
All machinery pertaining to release work.
"""
import argparse

def release(args):
    """
    Top-level release function.
    """
    raise NotImplementedError()

def fill_subparser(parser_release: argparse.ArgumentParser):
    parser_release.set_defaults(cmd=release)
