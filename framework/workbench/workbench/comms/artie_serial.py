"""
This module contains the code for communicating with an Artie over serial to its
Controller Node.
"""
from workbench.util import log
import dataclasses
import re
import serial
import serial.tools.list_ports
import time

@dataclasses.dataclass
class WifiNetwork:
    """Represents a WiFi network with its details."""
    bssid: str
    frequency: int
    signal_level: int
    flags: str
    ssid: str

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

    def scan_for_wifi_networks(self) -> tuple[Exception, list[WifiNetwork]]:
        """Scan for wifi networks and return a list of them."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # First, stop any existing wpa_cli instances
        err = self._write_line("wpa_cli terminate".encode(), check_return_code=False)
        if err:
            return err, []

        # Remove any existing wpa_supplicant PID files
        err = self._write_line("rm -f /var/run/wpa_supplicant/wlan0".encode(), check_return_code=False)
        if err:
            return err, []

        # Now start a new wpa_supplicant instance in the background
        err = self._write_line("wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf".encode())
        if err:
            return err, []
        
        # Initiate a scan
        err = self._write_line("wpa_cli scan".encode(), check_return_code=False)
        if err:
            return err, []

        # Wait a bit for the scan to complete
        time.sleep(0.1)

        # Retrieve the scan results
        err = self._write_line("wpa_cli scan_results".encode(), check_return_code=False)
        if err:
            return err, []

        err, lines = self._read_all_lines()
        if err:
            return err, []

        pattern = re.compile(r'^(?P<bssid>([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})\s+(?P<frequency>\d+)\s+(?P<signal_level>(-)?\d+)\s+(?P<flags>.*)\s+(?P<ssid>.*)$')  # hex:hex:hex:hex:hex:hex<whitespace>frequency<whitespace>signal_level<whitespace>flags<whitespace>ssid
        networks = []
        for line in lines:
            log.debug(f"Scan result line: {line}")
            match = pattern.match(line)
            if match:
                network = WifiNetwork(
                    bssid=match.group('bssid'),
                    frequency=int(match.group('frequency')),
                    signal_level=int(match.group('signal_level')),
                    flags=match.group('flags'),
                    ssid=match.group('ssid')
                )
                networks.append(network)
        
        return None, networks

    def select_wifi(self, ssid: str, password: str, static_ip: str = None) -> Exception|None:
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

        # Get an IP address via DHCP
        err = self._write_line("dhcpcd wlan0".encode())
        if err:
            return err

        # TODO: Restart networking items required to get wifi going again

        # If static IP is provided, configure it
        if static_ip:
            # Get the DNS IP
            err = self._write_line("resolvectl status | grep 'DNS'".encode())
            if err:
                return err
            
            # TODO
            err, dns_ip = self._read_until("DNS=".encode())
            if err:
                return err

            # Get the Gateway IP
            err = self._write_line("ip route | grep default".encode())
            if err:
                return err
            
            # TODO
            err, gateway_ip = self._read_until("via ".encode())
            if err:
                return err

            # Update the network configuration
            err = self._write_line(f'echo -e "[Match]\\nName=wlan0\\n[Network]\\nAddress={static_ip}/24\\nGateway={gateway_ip.decode().strip()}\\nDNS={dns_ip.decode().strip()}" > /etc/systemd/network/80-wifi-station.network'.encode())
            if err:
                return err

        # Now set wpa_supplicant in systemd
        err = self._write_line("systemctl enable wpa_supplicant@wlan0".encode())
        if err:
            return err

        err = self._write_line("systemctl start wpa_supplicant@wlan0".encode())
        if err:
            return err

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

    def verify_wifi_connection(self) -> tuple[Exception|None, str|None]:
        """Verify that Artie is connected to the wifi network and return the IP address."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open."), None

        # Verify connection by checking that we can ping this machine or 8.8.8.8
        err = self._write_line("ping -c 3 8.8.8.8".encode())
        if err:
            return err, None
        
        err, data = self._read_until("3 packets transmitted".encode())
        if err:
            return err, None
        
        if '0 received' in data.encode():
            return Exception("Test packets not received. WiFi connection may have failed."), None

        # Return the IP address of Artie
        err = self._write_line("ip addr show wlan0 | grep 'inet '".encode())
        if err:
            return err, None
        
        err, data = self._read_until("inet ".encode())
        if err:
            return err, None
        
        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', data.decode())
        if not ip_match:
            return Exception("Could not find IP address."), None
        
        ip_address = ip_match.group(1)
        return None, ip_address

    def _sign_in(self, username: str, password: str) -> Exception|None:
        """Sign in to Artie with the provided credentials."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: Implement the actual sign-in logic for artie-image-release
        self._read_until("login: ".encode())
        self._write_line("root".encode(), check_return_code=False)

    def _write_line(self, data: bytes, check_return_code=True) -> Exception|None:
        """Write a line to the serial connection."""
        try:
            log.debug(f"Writing to serial: ".encode() + data)
            self._serial_connection.write(data + b'\n')
            self._read_until(data)  # Read out the echo

            if check_return_code:
                self._serial_connection.write(b'echo $?\n')
                err, ret_code_lines = self._read_all_lines()
                if err:
                    return err

                if not any([line.strip() == '0' for line in ret_code_lines]):
                    ret_code_str = ", ".join(ret_code_lines)
                    log.error(f"Command returned non-zero exit code: {ret_code_str}")
                    return Exception(f"Command returned non-zero exit code: {ret_code_str}")

            return None

        except serial.SerialException as e:
            return e

    def _read_all_lines(self) -> tuple[Exception, list[str]|None]:
        """Read all available lines from the serial connection."""
        lines = []
        while True:
            try:
                line = self._serial_connection.readline()
                log.debug(f"Read from serial: ".encode() + line)
            except serial.SerialException as e:
                return e, None

            if not line:
                break

            lines.append(line.decode().strip())

        return None, lines

    def _read_until(self, terminator: bytes) -> tuple[Exception, bytes|None]:
        """Read from the serial connection until the terminator is found."""
        try:
            data = self._serial_connection.read_until(terminator)
            log.debug(f"Read from serial: ".encode() + data)
            return None, data
        except serial.SerialException as e:
            return e, None
