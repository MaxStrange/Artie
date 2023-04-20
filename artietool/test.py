"""
All machinery releated to unit testing and whatnot.
"""
import argparse

def test(args):
    """
    Top-level test function.
    """
    raise NotImplementedError()

def fill_subparser(parser_test: argparse.ArgumentParser):
    parser_test.set_defaults(cmd=test)
