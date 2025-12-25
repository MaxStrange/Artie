"""
This module contains the code for communicating with an Artie over serial to its
Controller Node.
"""
from workbench.util import log
import re
import serial
import serial.tools.list_ports
import time

class ArtieSerialConnection:
    def __init__(self, port: str = None, baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        # The underlying connection
        self._serial_connection = None

    def __enter__(self):
        """Open the serial connection when entering context"""
        self.open()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the serial connection when exiting context"""
        self.close()

        return False

    @staticmethod
    def list_ports() -> list[str]:
        """List all available ports."""
        # TODO: Filter out all ports that can't possibly be an Artie Controller Node
        #       based on VID/PID, etc. See: https://www.pyserial.com/docs/api-reference#listportinfo-properties
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def close(self):
        """Close the connection."""
        if self._serial_connection and self._serial_connection.is_open:
            self._serial_connection.close()

    def open(self):
        """Open the underlying connection."""
        if self.port:
            self._serial_connection = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)

    def reset(self):
        """Close and re-open the connection."""
        self.close()
        self.open()

    def scan_for_wifi_networks(self) -> tuple[Exception, list[str]]:
        """Scan for wifi networks and return a list of them."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: Implement the actual scanning here
        # wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf
        # wpa_cli scan
        # wpa_cli scan_results
        # Report the results
        err = self._write_line("wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf".encode())
        if err:
            return err, []
        
        err = self._write_line("wpa_cli scan".encode())
        if err:
            return err, []

        # Wait a bit for the scan to complete
        time.sleep(0.1)
        
        err = self._write_line("wpa_cli scan_results".encode())
        if err:
            return err, []

        err, lines = self._read_all_lines()
        if err:
            return err, []

        pattern = re.compile(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\s+\d+\s+(-)?\d+\s+.*\s+(?P<ssid>.*)$')  # hex:hex:hex:hex:hex:hex<whitespace>frequency<whitespace>signal_level<whitespace>flags<whitespace>ssid
        networks = []
        for line in lines:
            match = pattern.match(line)
            if match:
                ssid = match.group('ssid')
                networks.append(ssid)
        
        wifi_networks = networks
        return None, wifi_networks

    def select_wifi(self, ssid: str, password: str) -> Exception|None:
        """Select the wifi network and enter its password."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: Implement the wifi network selection logic
        #
        # wpa_cli add_network
        # wpa_cli set_network <id> ssid "<ssid>"
        # wpa_cli set_network <id> psk "<password>"
        # wpa_cli enable_network <id>
        # wpa_cli save_config
        #
        # Update /etc/systemd/network/80-wifi-station.network to replace DHCP with a static IP:
        # [Network]
        # Address=<static_ip>/24
        # Gateway=<gateway_ip>
        # DNS=<dns_ip>
        #
        # Possibly have to reboot Artie
        err = self._write_line(f'wpa_cli add_network'.encode())
        if err:
            return err

        # TODO: Get the network ID from the response of add_network
        network_id = "0"  # Placeholder
        
        err = self._write_line(f'wpa_cli set_network {network_id} ssid "{ssid}"'.encode())
        if err:
            return err

        # TODO: Password needs to be masked or cleared from bash history
        err = self._write_line(f'wpa_cli set_network {network_id} psk "{password}"'.encode())
        if err:
            return err
        
        err = self._write_line(f'wpa_cli enable_network {network_id}'.encode())
        if err:
            return err
        
        err = self._write_line('wpa_cli save_config'.encode())
        if err:
            return err

        # TODO: Restart networking items required to get wifi going again

        return None

    def set_credentials(self, username: str, password: str) -> Exception|None:
        """Set the credentials on the connected Artie."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: On artie-image-dev, we only have a root user, so ignore this for now
        #       Otherwise, we would implement the logic to change the default user's name and password here
        err = self._sign_in(username, password)
        if err:
            return err

    def verify_wifi_connection(self) -> Exception|None:
        """Verify that Artie is connected to the wifi network."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: Implement the actual verification logic
        # TODO: Try pinging 8.8.8.8 or the IP of this development machine

    def _sign_in(self, username: str, password: str) -> Exception|None:
        """Sign in to Artie with the provided credentials."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: Implement the actual sign-in logic for artie-image-release
        self._read_until("login: ".encode())
        self._write_line("root".encode())

    def _write_line(self, data: bytes) -> Exception|None:
        """Write a line to the serial connection."""
        try:
            log.debug(f"Writing to serial: {data.decode()}")
            self._serial_connection.write(data + b'\n')
            return None
        except serial.SerialException as e:
            return e

    def _read_all_lines(self) -> tuple[Exception, list[str]|None]:
        """Read all available lines from the serial connection."""
        lines = []
        while True:
            try:
                line = self._serial_connection.readline()
                log.debug(f"Read from serial: {line.decode().strip()}")
            except serial.SerialException as e:
                return e, None

            if not line:
                break

            lines.append(line.decode().strip())

        return None, lines

    def _read_until(self, terminator: bytes) -> tuple[Exception, bytes|None]:
        """Read from the serial connection until the terminator is found."""
        # TODO: Debug log what we are reading and implement retry and timeout handling?
        try:
            data = self._serial_connection.read_until(terminator)
            log.debug(f"Read from serial until terminator: {data.decode().strip()}")
            return None, data
        except serial.SerialException as e:
            return e, None
