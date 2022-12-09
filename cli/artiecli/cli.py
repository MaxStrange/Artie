"""
Command line interface for Artie.
"""
import argparse
from .modules import controller
from .modules import eyebrows
from .modules import mouth
from .modules.hardware import util

MODULES = [
    controller,
    eyebrows,
    mouth,
]

def main():
    """
    Entrypoint for the script.
    """
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s [--help] [module] [subsystem] [cmd]")
    subparsers = parser.add_subparsers(help="Module command")
    for module in MODULES:
        module.add_subparser(subparsers)
    args = parser.parse_args()

    if not hasattr(args, 'cmd'):
        parser.print_usage()
    else:
        args.cmd(args)

    # Cleanup
    if util.on_linux():
        import RPi.GPIO as GPIO
        GPIO.setwarnings(False)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
