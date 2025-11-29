"""
This module contains the code for all the settings in Artie Workbench.
"""
import dataclasses
import json
import pathlib

# Default save path is in the user's home directory under .artie/workbench/settings
DEFAULT_SAVE_PATH = pathlib.Path.home() / ".artie" / "workbench" / "settings"

@dataclasses.dataclass
class WorkbenchSettings:
    """
    An instance of WorkbenchSettings contains all the settings for Artie Workbench.
    """
    last_opened_profile: str = None
    """The name of the last opened Artie profile."""

    workbench_save_path: str = str(DEFAULT_SAVE_PATH.parent)
    """The path where Workbench saves its stuff."""

    @staticmethod
    def load(path=None) -> 'WorkbenchSettings':
        """Load the Workbench settings from disk."""
        if path is None:
            path = DEFAULT_SAVE_PATH / "settings.json"
        else:
            path = pathlib.Path(path) / "settings.json"

        path = pathlib.Path(path)
        if not path.exists():
            return WorkbenchSettings()  # Return default settings if file does not exist

        with open(path, 'r') as f:
            data = json.load(f)

        return WorkbenchSettings(**data)

    def save(self, path=None):
        """
        Save the Workbench settings to disk. If `path` is not given, we save to the default location.

        `path` should be a directory; the filename will be "settings.json".
        """
        if path is None:
            path = DEFAULT_SAVE_PATH / "settings.json"
        else:
            path = pathlib.Path(path) / "settings.json"

        path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

        with open(path, 'w') as f:
            json.dump(dataclasses.asdict(self), f, indent=4)
