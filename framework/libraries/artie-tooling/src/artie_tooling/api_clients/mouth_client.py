"""
Mouth API client for communicating with the API Server's mouth endpoints.

Each `*Response` object corresponds to the response from a specific API endpoint.

See [API documentation](../../../../../misc-micro-services/artie-api-server/README.md) for more details.
"""
from . import api_client
from .. import errors
import dataclasses
import enum

class LEDState(enum.StrEnum):
    """Enum for LED states."""
    OFF = "off"
    ON = "on"
    HEARTBEAT = "heartbeat"

class MouthDisplay(enum.StrEnum):
    """Enum for Mouth display states."""
    SMILE = "smile"
    FROWN = "frown"
    LINE = "line"
    SMIRK = "smirk"
    OPEN = "open"
    OPEN_SMILE = "open-smile"
    ZIG_ZAG = "zig-zag"
    TALKING = "talking"

    # Special states
    CLEAR = "clear"
    ERROR = "error"
    TEST = "test"

@dataclasses.dataclass
class LEDResponse:
    """Response object for LED state requests."""
    artie_id: str
    """The Artie ID."""

    state: LEDState
    """The LED state."""

@dataclasses.dataclass
class LCDResponse:
    """Response object for LCD state requests."""
    artie_id: str
    """The Artie ID."""

    display: MouthDisplay
    """The mouth display state."""

@dataclasses.dataclass
class StatusResponse:
    """Response object for Mouth status requests."""
    artie_id: str
    """The Artie ID."""

    led_status: api_client.ModuleStatus
    """The LED status."""

    lcd_status: api_client.ModuleStatus
    """The mouth display status."""

class MouthClient(api_client.APIClient):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def led_on(self) -> errors.HTTPError|None:
        response = self.post(f"/mouth/led", params={'artie-id': self.artie.artie_name, 'state': 'on'})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting LED value: {response.content.decode('utf-8')}")
        return None

    def led_off(self) -> errors.HTTPError|None:
        response = self.post(f"/mouth/led", params={'artie-id': self.artie.artie_name, 'state': 'off'})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting LED value: {response.content.decode('utf-8')}")
        return None

    def led_heartbeat(self) -> errors.HTTPError|None:
        response = self.post(f"/mouth/led", params={'artie-id': self.artie.artie_name, 'state': 'heartbeat'})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting LED value: {response.content.decode('utf-8')}")
        return None

    def led_get(self) -> LEDResponse|errors.HTTPError:
        response = self.get(f"/mouth/led", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting LED value: {response.content.decode('utf-8')}")
        return LEDResponse(
            artie_id=response.json().get('artie-id'),
            state=LEDState(response.json().get('state'))
        )

    def lcd_test(self) -> errors.HTTPError|None:
        response = self.post(f"/mouth/lcd/test", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error testing the LCD: {response.content.decode('utf-8')}")
        return None

    def lcd_off(self) -> errors.HTTPError|None:
        response = self.post(f"/mouth/lcd/off", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error clearing the LCD: {response.content.decode('utf-8')}")
        return None

    def lcd_get(self) -> LCDResponse|errors.HTTPError:
        response = self.get(f"/mouth/lcd", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting mouth LCD value: {response.content.decode('utf-8')}")
        return LCDResponse(
            artie_id=response.json().get('artie-id'),
            display=MouthDisplay(response.json().get('display'))
        )

    def lcd_draw(self, draw_val: str) -> errors.HTTPError|None:
        response = self.post(f"/mouth/lcd", params={'artie-id': self.artie.artie_name, 'display': draw_val})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting mouth LCD: {response.content.decode('utf-8')}")
        return None

    def lcd_talk(self) -> errors.HTTPError|None:
        response = self.post(f"/mouth/lcd", params={'artie-id': self.artie.artie_name, 'display': "talking"})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting mouth LCD: {response.content.decode('utf-8')}")
        return None

    def firmware_load(self) -> errors.HTTPError|None:
        response = self.post(f"/mouth/fw", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error reloading mouth FW: {response.content.decode('utf-8')}")
        return None

    def status(self) -> StatusResponse|errors.HTTPError:
        response = self.get("/mouth/status", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting mouth status: {response.content.decode('utf-8')}")
        return StatusResponse(
            artie_id=response.json().get('artie-id'),
            led_status=api_client.ModuleStatus(response.json().get('led-status')),
            lcd_status=api_client.ModuleStatus(response.json().get('lcd-status'))
        )

    def self_check(self) -> errors.HTTPError|None:
        response = self.post("/mouth/self-test", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error running mouth self-check: {response.content.decode('utf-8')}")
        return None
