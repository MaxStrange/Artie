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
    """Base class for API clients."""
    def __init__(self, profile: artie_profile.ArtieProfile, integration_test=False, unit_test=False, nretries=3) -> None:
        self.artie = profile
        self.nretries = nretries

        # Set up requests session
        self.session = requests.Session()

        # Set up authentication TO the server
        if profile.username and profile.password:
            self.session.auth = (profile.username, profile.password)
        elif profile.api_server_bearer_token:
            self.session.headers.update({'Authorization': f'Bearer {profile.api_server_bearer_token}'})

        # Set up authentication OF the server
        if profile.api_server_cert_path:
            self.session.verify = profile.api_server_cert_path

        # Determine IP and port based on whether we're in test mode
        # Also, if we are in test mode, we do not need verification
        if integration_test or unit_test:
            # Determined by docker compose files
            self.ip_and_port = f"{profile.api_server_host}:{profile.api_server_port}"
            self.session.verify = False
        else:
            # Determined by Helm chart
            self.ip_and_port = f"{profile.api_server_host}-{self.artie.artie_name}:{self.artie.api_server_port}"

    def get(self, endpoint: str, params=None, https=True) -> requests.Response:
        """
        Gets the content at the given endpoint (which should not include the IP or port)
        and returns it.

        Args:

        * `endpoint`: The URL not including the "http(s)://" portion.
        * `params`: Dictionary, list of tuples or bytes to send in the query string.
        * `https`: If `True` (the default), we use HTTPS. Otherwise we use HTTP.

        """
        scheme = "https" if https else "http"
        uri = f"{scheme}://{self.ip_and_port}{endpoint}"
        delay_s = 2
        for i in range(self.nretries):
            try:
                r = self.session.get(uri, params=params)
            except requests.RequestException as e:
                time.sleep(delay_s)
                if i == self.nretries - 1:
                    print(f"Error connecting: {e}")
                    raise e
        return r

    def post(self, endpoint: str, body=None, params=None, https=True) -> requests.Response:
        """
        Post the given body to the given endpoint with the given params.
        Does all the appropriate error handling and abstracts away
        boilerplate, which includes adding the appropriate IP and port
        to the URL (which should therefore not include that information).

        Args:

        * `endpoint`: The URL not including the "http(s)://" portion.
        * `body`: A JSON-serializable Python object (probably a dict) to send as the body.
        * `params`: Dictionary, list of tuples or bytes to send in the query string.
        * `https`: If `True` (the default), we use HTTPS. Otherwise we use HTTP.

        """
        scheme = "https" if https else "http"
        uri = f"{scheme}://{self.ip_and_port}{endpoint}"
        delay_s = 2
        for i in range(self.nretries):
            try:
                r = requests.post(uri, json=body, params=params, verify=False)
            except Exception as e:
                time.sleep(delay_s)
                if i == self.nretries - 1:
                    print(f"Error connecting: {e}")
                    raise e
        return r
