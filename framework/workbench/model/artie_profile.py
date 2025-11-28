"""
This module contains the code for keeping track of an Artie Profile.
"""
import dataclasses
import pathlib
import json
import secrets

# Default save path is in the user's home directory under .artie/workbench/profiles
DEFAULT_SAVE_PATH = pathlib.Path.home() / ".artie" / "workbench" / "profiles"

@dataclasses.dataclass
class ArtieProfile:
    """
    An ArtieProfile instance contains all the information pertaining
    to a particular Artie that we might need in order to access or install it.
    """
    admin_node_ip: str = None
    """The IP address of the admin node."""

    artie_name: str = None
    """The name of this Artie."""

    controller_node_ip: str = None
    """The IP address of Artie's controller node."""

    password: str = None
    """The password for this Artie."""

    token: str = None
    """The K3S token for this Artie."""

    username: str = None
    """The username for this Artie."""

    @staticmethod
    def load(artie_name: str, path=None) -> 'ArtieProfile':
        """Load an Artie profile from disk."""
        if path is None:
            path = DEFAULT_SAVE_PATH / f"{artie_name}.json"
        else:
            path = pathlib.Path(path) / f"{artie_name}.json"

        path = pathlib.Path(path)
        with open(path, 'r') as f:
            data = json.load(f)

        profile = ArtieProfile(**data)

        # Load the password and token in an OS-dependent manner
        profile.password = secrets.get_secret(f"artie_{profile.artie_name}_password")
        profile.token = secrets.get_secret(f"artie_{profile.artie_name}_token")

        return profile

    def save(self, path=None):
        """Save the Artie profile to disk. If `path` is not given, we save to the default location."""
        if path is None:
            name = self.artie_name or "unnamed_artie"
            path = DEFAULT_SAVE_PATH / f"{name}.json"
        else:
            path = pathlib.Path(path)

        # Ensure the parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to JSON and write to file, but not including the password and token for security reasons
        data = dataclasses.asdict(self)
        data.pop("password", None)
        data.pop("token", None)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

        # Save the password and token in an OS-dependent manner
        secrets.store_secret(f"artie_{self.artie_name}_password", self.password)
        secrets.store_secret(f"artie_{self.artie_name}_token", self.token)
