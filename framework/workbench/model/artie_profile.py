"""
This module contains the code for keeping track of an Artie Profile.
"""
import dataclasses

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
