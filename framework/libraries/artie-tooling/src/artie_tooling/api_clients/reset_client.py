"""
Reset API client for communicating with the API Server's reset endpoints.

Each `*Response` object corresponds to the response from a specific API endpoint.

See [API documentation](../../../../../misc-micro-services/artie-api-server/README.md) for more details.
"""
from . import api_client
from .. import errors
import dataclasses
import enum

@dataclasses.dataclass
class StatusResponse:
    """Response object for status request."""
    artie_id: str
    """The Artie ID."""

    mcu_status: api_client.ModuleStatus
    """The reset status."""

class ResetClient(api_client.APIClient):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _convert_address_to_mcu(self, address: int) -> str:
        match address:
            case 0x00:
                return 'eyebrows'
            case 0x01:
                return 'mouth'
            case 0x02:
                return 'sensors-head'
            case 0x03:
                return 'pump-control'
            case 0xFF:
                return 'all'
            case _:
                raise ValueError(f"Invalid argument given for MCU address: {address}")

    def reset_target(self, address: int) -> errors.HTTPError|None:
        mcu = self._convert_address_to_mcu(address)
        response = self.post(f"/reset/mcu", params={'artie-id': self.artie.artie_name, 'id': mcu})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error resetting target: {response.content.decode('utf-8')}")
        return None

    def status(self) -> StatusResponse|errors.HTTPError:
        response = self.get("/reset/status", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting reset status: {response.content.decode('utf-8')}")
        return StatusResponse(
            artie_id=response.json().get('artie-id'),
            mcu_status=api_client.ModuleStatus(response.json().get('submodule-statuses').get('MCU'))
        )

    def self_check(self) -> errors.HTTPError|None:
        response = self.post("/reset/self-test", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error running reset self-check: {response.content.decode('utf-8')}")
        return None
