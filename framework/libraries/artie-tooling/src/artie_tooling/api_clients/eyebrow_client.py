"""
Eyebrow API client for communicating with the API Server's eyebrow endpoints.

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

class EyebrowSide(enum.StrEnum):
    """Enum for Eyebrow sides."""
    LEFT = "left"
    RIGHT = "right"

class VertexPosition(enum.StrEnum):
    """Enum for LCD vertex positions."""
    HIGH = "H"
    MEDIUM = "M"
    LOW = "L"

class LCDStatus(enum.StrEnum):
    """Enum for LCD statuses."""
    CLEAR = "clear"
    ERROR = "error"
    TEST = "test"

@dataclasses.dataclass
class LEDResponse:
    """Response object for LED state requests."""
    artie_id: str
    """The Artie ID."""

    side: EyebrowSide
    """Which eyebrow side."""

    state: LEDState
    """The LED state."""

@dataclasses.dataclass
class LCDResponse:
    """Response object for LCD state requests."""
    artie_id: str
    """The Artie ID."""

    side: EyebrowSide
    """Which eyebrow side."""

    vertices: list[VertexPosition]|LCDStatus
    """List of vertex positions ('H', 'M', 'L') or 'clear' or 'error' or 'test'."""

@dataclasses.dataclass
class ServoResponse:
    """Response object for Servo state requests."""
    artie_id: str
    """The Artie ID."""

    side: EyebrowSide
    """Which eyebrow side."""

    degrees: float
    """The servo position in degrees."""

@dataclasses.dataclass
class StatusResponse:
    """Response object for Eyebrow status requests."""
    artie_id: str
    """The Artie ID."""

    fw_status: api_client.ModuleStatus
    """Firmware submodule status."""

    led_left_status: api_client.ModuleStatus
    """Left LED submodule status."""

    led_right_status: api_client.ModuleStatus
    """Right LED submodule status."""

    lcd_left_status: api_client.ModuleStatus
    """Left LCD submodule status."""

    lcd_right_status: api_client.ModuleStatus
    """Right LCD submodule status."""

    servo_left_status: api_client.ModuleStatus
    """Left Servo submodule status."""

    servo_right_status: api_client.ModuleStatus
    """Right Servo submodule status."""


class EyebrowClient(api_client.APIClient):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def led_on(self, side: str) -> errors.HTTPError|None:
        response = self.post(f"/eyebrows/led/{side}", params={'artie-id': self.artie.artie_name, 'state': 'on'})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting {side} LED value: {response.content.decode('utf-8')}")
        return None

    def led_off(self, side: str) -> errors.HTTPError|None:
        response = self.post(f"/eyebrows/led/{side}", params={'artie-id': self.artie.artie_name, 'state': 'off'})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting {side} LED value: {response.content.decode('utf-8')}")
        return None

    def led_heartbeat(self, side: str) -> errors.HTTPError|None:
        response = self.post(f"/eyebrows/led/{side}", params={'artie-id': self.artie.artie_name, 'state': 'heartbeat'})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting {side} LED value: {response.content.decode('utf-8')}")
        return None

    def led_get(self, side: str) -> errors.HTTPError|LEDResponse:
        response = self.get(f"/eyebrows/led/{side}", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting {side} LED value: {response.content.decode('utf-8')}")
        return LEDResponse(
            artie_id=response.json().get('artie-id'),
            side=EyebrowSide(response.json().get('side')),
            state=LEDState(response.json().get('state'))
        )

    def lcd_test(self, side: str) -> errors.HTTPError|None:
        response = self.post(f"/eyebrows/lcd/{side}/test", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error testing {side} LCD: {response.content.decode('utf-8')}")
        return None

    def lcd_off(self, side: str) -> errors.HTTPError|None:
        response = self.post(f"/eyebrows/lcd/{side}/off", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error clearing {side} LCD: {response.content.decode('utf-8')}")
        return None

    def lcd_draw(self, side: str, draw_val: list[str]) -> errors.HTTPError|None:
        body = {
            "vertices": [arg[0] for arg in draw_val]
        }
        response = self.post(f"/eyebrows/lcd/{side}", body=body, params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting {side} LCD: {response.content.decode('utf-8')}")
        return None

    def lcd_get(self, side: str) -> errors.HTTPError|LCDResponse:
        response = self.get(f"/eyebrows/lcd/{side}", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting {side} LCD value: {response.content.decode('utf-8')}")
        return LCDResponse(
            artie_id=response.json().get('artie-id'),
            side=EyebrowSide(response.json().get('side')),
            vertices=response.json().get('vertices')
        )

    def servo_go(self, side: str, go_val: float) -> errors.HTTPError|None:
        response = self.post(f"/eyebrows/servo/{side}", params={'artie-id': self.artie.artie_name, 'degrees': f"{go_val:0.2f}"})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error setting {side} Servo: {response.content.decode('utf-8')}")
        return None

    def servo_get(self, side: str) -> errors.HTTPError|ServoResponse:
        response = self.get(f"/eyebrows/servo/{side}", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting {side} Servo: {response.content.decode('utf-8')}")
        return ServoResponse(
            artie_id=response.json().get('artie-id'),
            side=EyebrowSide(response.json().get('side')),
            degrees=response.json().get('degrees')
        )

    def firmware_load(self) -> errors.HTTPError|None:
        response = self.post(f"/eyebrows/fw", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error reloading eyebrow FW: {response.content.decode('utf-8')}")
        return None

    def status(self) -> errors.HTTPError|StatusResponse:
        response = self.get("/eyebrows/status", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error getting eyebrow status: {response.content.decode('utf-8')}")
        return StatusResponse(
            artie_id=response.json().get('artie-id'),
            fw_status=api_client.ModuleStatus(response.json().get('fw-status')),
            led_left_status=api_client.ModuleStatus(response.json().get('led-left-status')),
            led_right_status=api_client.ModuleStatus(response.json().get('led-right-status')),
            lcd_left_status=api_client.ModuleStatus(response.json().get('lcd-left-status')),
            lcd_right_status=api_client.ModuleStatus(response.json().get('lcd-right-status')),
            servo_left_status=api_client.ModuleStatus(response.json().get('servo-left-status')),
            servo_right_status=api_client.ModuleStatus(response.json().get('servo-right-status')),
        )

    def self_check(self):
        response = self.post("/eyebrows/self-test", params={'artie-id': self.artie.artie_name})
        if response.status_code != 200:
            return errors.HTTPError(response.status_code, f"Error running eyebrow self-check: {response.content.decode('utf-8')}")
        return None
