"""
Base class for the various API clients.
"""
from .. import artie_profile
import enum
import requests
import time

class ModuleStatus(enum.StrEnum):
    """Enum for each module status."""
    WORKING = "working"
    DEGRADED = "degraded"
    NOT_WORKING = "not_working"
    UNKNOWN = "unknown"


class APIClient:
    def __init__(self, profile: artie_profile.ArtieProfile, integration_test=False, unit_test=False) -> None:
        self.artie = profile

        if integration_test or unit_test:
            # Determined by docker compose files
            self.ip_and_port = "artie-api-server:8782"
        else:
            # Determined by Helm chart
            self.ip_and_port = f"artie-api-server-{self.artie.artie_name}:8782"

    def get(self, url: str, params=None, https=True) -> requests.Response:
        """
        Gets the content at the given URL (which should not include the IP or port)
        and returns it.
        """
        scheme = "https" if https else "http"
        uri = f"{scheme}://{self.ip_and_port}{url}"
        ntries = 3
        delay_s = 2
        for i in range(ntries):
            try:
                r = requests.get(uri, params=params, verify=False)
            except Exception as e:
                time.sleep(delay_s)
                if i == ntries - 1:
                    print(f"Error connecting: {e}")
                    raise e
        return r

    def post(self, url: str, body=None, params=None, https=True) -> requests.Response:
        """
        Post the given body to the given url with the given params.
        Does all the appropriate error handling and abstracts away
        boilerplate, which includes adding the appropriate IP and port
        to the URL (which should therefore not include that information).
        """
        scheme = "https" if https else "http"
        uri = f"{scheme}://{self.ip_and_port}{url}"
        ntries = 3
        delay_s = 2
        for i in range(ntries):
            try:
                r = requests.post(uri, json=body, params=params, verify=False)
            except Exception as e:
                time.sleep(delay_s)
                if i == ntries - 1:
                    print(f"Error connecting: {e}")
                    raise e
        return r
