"""
This module contains the code for Artie Workbench,
a graphical user interface for interacting with, setting up, and monitoring Artie robots.
"""
from .model import settings
from .gui import colors
from .util import log
from PyQt6 import QtWidgets
import argparse
import sys
import os

# Add the parent directory to the path to enable imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.windows.main_window import MainWindow

def load_stylesheet(app):
    """Load and apply the Qt Green stylesheet from colors.py"""
    try:
        stylesheet = colors.generate_full_stylesheet()
        app.setStyleSheet(stylesheet)
    except Exception as e:
        print(f"Warning: Could not generate stylesheet: {e}")

def main(loglevel: int = log.logging.INFO, logfpath: str = None):
    """
    Main entry point for Artie Workbench
    """
    # Initialize logging
    log.initialize_logger(loglevel, logfpath)

    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    load_stylesheet(app)

    # Create the main window
    workbench_settings = settings.WorkbenchSettings.load()
    window = MainWindow(workbench_settings)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Artie Workbench - GUI for managing Artie robots")
    parser.add_argument("--loglevel", type=str, default="DEBUG", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level (default: DEBUG)")
    parser.add_argument("--logfile", type=str, default=None, help="Path to log file (default: None)")
    args = parser.parse_args()

    # Get loglevel integer from string
    if not hasattr(log.logging, args.loglevel.upper()):
        print(f"Invalid log level: {args.loglevel}. Using DEBUG level.")
        args.loglevel = "DEBUG"

    loglevel = getattr(log.logging, args.loglevel.upper(), log.logging.DEBUG)

    main(loglevel=loglevel, logfpath=args.logfile)
