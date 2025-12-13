"""
Reset API client for communicating with the API Server's reset endpoints.

See [API documentation](../../../../../misc-micro-services/artie-api-server/README.md) for more details.
"""
from . import api_client

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

    def reset_target(self, address: int):
        mcu = self._convert_address_to_mcu(address)
        self.post(f"/reset/mcu", params={'artie-id': self.artie_id, 'id': mcu})

    def status(self):
        response = self.get("/reset/status", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_status_result(f"Error getting reset status: {response.content.decode('utf-8')}", module='reset', artie_id=self.artie_id)
        else:
            common.format_print_status_result(response.json(), module='reset', artie_id=self.artie_id)

    def self_check(self):
        response = self.post("/reset/self-test", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error running reset self-check: {response.content.decode('utf-8')}", module='reset', submodule='status', artie_id=self.artie_id)
