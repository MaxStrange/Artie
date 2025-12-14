"""
This module contains the code for keeping track of an Artie Profile.
"""
from artie_tooling import artie_secrets
import dataclasses
import pathlib
import json

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

    api_server_host: str = None
    """The hostname or IP address of the API server."""

    api_server_port: int = 8782
    """The port for the API server."""

    api_server_cert_path: str = str(pathlib.Path.home() / ".artie" / "controller-node-CA" / "controller-node-ca.crt")
    """The controller node's root certificate. This is the CA bundle we use for authenticating the API server is who it says it is."""

    api_server_bearer_token: str = None
    """An optional bearer token for the API server."""

    @staticmethod
    def load(artie_name=None, path=None) -> 'ArtieProfile':
        """
        Load an Artie profile from disk.

        If both `artie_name` and `path` are given, we assume `path` is a directory
        and try to load a file named `'<artie_name>.json'` from `path` directory.

        If `artie_name` is given but `path` is not, we assume `path` is the default directory
        and attempt to load a file named `'<artie_name>.json'` from that directory.

        If `artie_name` is not given but `path` is, `path` should be a path to the *file*.

        If neither `artie_name` nor `path` are given, we attempt to load `'unnamed_artie.json'`
        from the default directory. This will likely fail, resulting in a FileNotFound exception.
        """
        if artie_name is not None and path is not None:
            path = pathlib.Path(path) / f"{artie_name}.json"
        elif artie_name is not None and path is None:
            path = DEFAULT_SAVE_PATH / f"{artie_name}.json"
        elif artie_name is None and path is not None:
            path = pathlib.Path(path)
        else:
            path = DEFAULT_SAVE_PATH / "unnamed_artie.json"

        with open(path, 'r') as f:
            data = json.load(f)

        profile = ArtieProfile(**data)

        # Load the secrets
        profile.password = artie_secrets.retrieve_secret(f"artie_{profile.artie_name}_password")
        profile.token = artie_secrets.retrieve_secret(f"artie_{profile.artie_name}_token")
        profile.api_server_bearer_token = artie_secrets.retrieve_secret(f"artie_{profile.artie_name}_bearer_token")
        profile.api_server_cert_path = artie_secrets.retrieve_api_server_cert()

        return profile

    def save(self, path=None):
        """
        Save the Artie profile to disk. If `path` is not given, we save to the default location.

        `path` should be a directory; the filename will be derived from the Artie name.
        """
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
        data.pop("api_server_cert_path", None)
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

        # Save the password and token in an OS-dependent manner
        artie_secrets.store_secret(f"artie_{self.artie_name}_password", self.password)
        artie_secrets.store_secret(f"artie_{self.artie_name}_token", self.token)
        artie_secrets.store_secret(f"artie_{self.artie_name}_api_server_bearer_token", self.api_server_bearer_token)
        artie_secrets.store_api_server_cert(self.api_server_cert_path)

    def delete(self, path=None):
        """
        Delete the Artie profile from disk and remove associated secrets.

        `path` should be a directory; the filename will be derived from the Artie name.
        """
        if path is None:
            name = self.artie_name or "unnamed_artie"
            path = DEFAULT_SAVE_PATH / f"{name}.json"
        else:
            path = pathlib.Path(path) / f"{self.artie_name}.json"

        path = pathlib.Path(path)
        
        # Delete the JSON file
        if path.exists():
            path.unlink()
        
        # Delete the associated secrets
        artie_secrets.delete_secret(f"artie_{self.artie_name}_password")
        artie_secrets.delete_secret(f"artie_{self.artie_name}_token")

def list_profiles(path=None) -> list[ArtieProfile]:
    """
    List all saved Artie profiles in the given path.
    If `path` is not given, we look in the default location.

    `path` should be a directory.
    """
    if path is None:
        path = DEFAULT_SAVE_PATH
    else:
        path = pathlib.Path(path)

    profiles = []
    if path.exists() and path.is_dir():
        for file in path.glob("*.json"):
            profiles.append(ArtieProfile.load(file.stem, path=path))

    return profiles
