"""
This module contains the code for all the settings in Artie Workbench.
"""
import dataclasses
import enum
import json
import pathlib

# Default save path is in the user's home directory under .artie/workbench/settings
DEFAULT_SAVE_PATH = pathlib.Path.home() / ".artie" / "workbench" / "settings"

class GuiViewOption(enum.StrEnum):
    """Enumeration of GUI view options for settings fields."""
    FILE_PICKER = "file_picker"
    DIRECTORY_PICKER = "directory_picker"
    FLOATING_POINT_INPUT = "floating_point_input"

@dataclasses.dataclass
class WorkbenchSettings:
    """
    An instance of WorkbenchSettings contains all the settings for Artie Workbench.
    """
    last_opened_profile: str = dataclasses.field(default="", metadata={'view': None})
    """The name of the last opened Artie profile."""

    workbench_save_path: str = dataclasses.field(default=str(DEFAULT_SAVE_PATH.parent), metadata={'view': GuiViewOption.DIRECTORY_PICKER})
    """The path where Workbench saves its stuff."""

    status_refresh_rate_s: float = dataclasses.field(default=5.0, metadata={'view': GuiViewOption.FLOATING_POINT_INPUT, 'bottom': 0.0, 'top': None, 'decimals': 2})
    """The refresh rate of all the status information in seconds."""

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

        # Create a WorkbenchSettings object, keeping anything that is not found in the
        # settings file to its default value.
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
