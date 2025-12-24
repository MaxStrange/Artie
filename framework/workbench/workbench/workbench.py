"""
This module contains the code for Artie Workbench,
a graphical user interface for interacting with, setting up, and monitoring Artie robots.
"""
from .model import settings
from .gui import colors
from PyQt6 import QtWidgets
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

def main():
    """
    Main entry point for Artie Workbench
    """
    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    load_stylesheet(app)

    # Create the main window
    workbench_settings = settings.WorkbenchSettings.load()
    window = MainWindow(workbench_settings)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
