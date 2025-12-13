"""
Mouth API client for communicating with the API Server's mouth endpoints.

See [API documentation](../../../../../misc-micro-services/artie-api-server/README.md) for more details.
"""
from . import api_client

class MouthClient(api_client.APIClient):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def led_on(self):
        response = self.post(f"/mouth/led", params={'artie-id': self.artie_id, 'state': 'on'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting LED value: {response.content.decode('utf-8')}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def led_off(self):
        response = self.post(f"/mouth/led", params={'artie-id': self.artie_id, 'state': 'off'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting LED value: {response.content.decode('utf-8')}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def led_heartbeat(self):
        response = self.post(f"/mouth/led", params={'artie-id': self.artie_id, 'state': 'heartbeat'})
        if response.status_code != 200:
            common.format_print_result(f"Error setting LED value: {response.content.decode('utf-8')}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def led_get(self):
        response = self.get(f"/mouth/led", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting LED value: {response.content.decode('utf-8')}", module='mouth', submodule='LED', artie_id=self.artie_id)
        else:
            common.format_print_result(f"LED value: {response.json().get('state')}", module='mouth', submodule='LED', artie_id=self.artie_id)

    def lcd_test(self):
        response = self.post(f"/mouth/lcd/test", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error testing the LCD: {response.content.decode('utf-8')}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def lcd_off(self):
        response = self.post(f"/mouth/lcd/off", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error clearing the LCD: {response.content.decode('utf-8')}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def lcd_get(self):
        response = self.get(f"/mouth/lcd", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error getting mouth LCD value: {response.content.decode('utf-8')}", module='mouth', submodule='LCD', artie_id=self.artie_id)
        else:
            common.format_print_result(f"Display value: {response.json().get('display')}", module='mouth', submodule='LCD', artie_id=response.json().get('artie-id'))

    def lcd_draw(self, draw_val: str):
        response = self.post(f"/mouth/lcd", params={'artie-id': self.artie_id, 'display': draw_val})
        if response.status_code != 200:
            common.format_print_result(f"Error setting mouth LCD: {response.content.decode('utf-8')}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def lcd_talk(self):
        response = self.post(f"/mouth/lcd", params={'artie-id': self.artie_id, 'display': "talking"})
        if response.status_code != 200:
            common.format_print_result(f"Error setting mouth LCD: {response.content.decode('utf-8')}", module='mouth', submodule='LCD', artie_id=self.artie_id)

    def firmware_load(self):
        response = self.post(f"/mouth/fw", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error reloading mouth FW: {response.content.decode('utf-8')}", module='mouth', submodule='FW', artie_id=self.artie_id)

    def status(self):
        response = self.get("/mouth/status", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_status_result(f"Error getting mouth status: {response.content.decode('utf-8')}", module='mouth', artie_id=self.artie_id)
        else:
            common.format_print_status_result(response.json(), module='mouth', artie_id=self.artie_id)

    def self_check(self):
        response = self.post("/mouth/self-test", params={'artie-id': self.artie_id})
        if response.status_code != 200:
            common.format_print_result(f"Error running mouth self-check: {response.content.decode('utf-8')}", module='mouth', submodule='status', artie_id=self.artie_id)
