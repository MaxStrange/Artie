"""
This module enables artie-tool to flash firmware onto devices.
"""
import argparse

FLASH_TASKS = []

def flash(args):
    """
    Top-level flash function.
    """
    raise NotImplementedError()

def fill_subparser(parser_flash: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    group = parser_flash.add_argument_group("Flash", "Flash Options")
    parser_flash.set_defaults(cmd=flash)
