"""
This module contains the code for communicating with an Artie over serial to its
Controller Node.
"""
import serial
import serial.tools.list_ports

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
            self._serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )

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

    def set_credentials(self, username: str, password: str) -> Exception|None:
        """Set the credentials on the connected Artie."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: On artie-image-dev, we only have a root user, so ignore this for now
        #       Otherwise, we would implement the logic to change the default user's name and password here

    def verify_wifi_connection(self) -> Exception|None:
        """Verify that Artie is connected to the wifi network."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: Implement the actual verification logic
        # TODO: Try pinging 8.8.8.8 or the IP of this development machine
