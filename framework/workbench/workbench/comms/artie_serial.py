"""
This module contains the code for communicating with an Artie over serial to its
Controller Node.
"""
from workbench.util import error
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
            return error.SerialConnectionError("Connection not open."), []

        # First, stop any existing wpa_cli instances
        err, _ = self._run_cmd("wpa_cli terminate".encode())
        if err:
            return err, []

        # Remove any existing wpa_supplicant PID files
        err, _ = self._run_cmd("rm -f /var/run/wpa_supplicant/wlan0".encode(), check_return_code=True)
        if err:
            return err, []

        # Now start a new wpa_supplicant instance in the background
        err, _ = self._run_cmd("wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf".encode(), check_return_code=True)
        if err:
            return err, []
        
        # Initiate a scan
        err, _ = self._run_cmd("wpa_cli scan".encode(), check_return_code=True)
        if err:
            return err, []

        # Wait a bit for the scan to complete
        time.sleep(0.1)

        # Retrieve the scan results
        err, lines = self._run_cmd("wpa_cli scan_results".encode())
        if err:
            return err, []

        # Parse the scan results into WifiNetwork objects
        # A typical line looks like this:
        # bssid              frequency signal_level flags                   ssid
        # But there are plenty of lines that do not conform to this format,
        # so we use a regex to extract the fields.
        pattern = re.compile(r'^(?P<bssid>([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})\s+(?P<frequency>\d+)\s+(?P<signal_level>(-)?\d+)\s+(?P<flags>.*)\s+(?P<ssid>.*)$')  # hex:hex:hex:hex:hex:hex<whitespace>frequency<whitespace>signal_level<whitespace>flags<whitespace>ssid
        networks = []
        for line in lines:
            log.debug(f"Scan result line: {line}")
            match = pattern.match(line)
            if match:
                log.info(f"Found a network: SSID={match.group('ssid')}, BSSID={match.group('bssid')}, Signal Level={match.group('signal_level')}, Frequency={match.group('frequency')}, Flags={match.group('flags')}")
                network = WifiNetwork(
                    bssid=match.group('bssid'),
                    frequency=int(match.group('frequency')),
                    signal_level=int(match.group('signal_level')),
                    flags=match.group('flags'),
                    ssid=match.group('ssid')
                )
                networks.append(network)
        
        log.info(f"Total networks found: {len(networks)}")
        return None, networks

    def select_wifi(self, bssid: str, ssid: str, password: str, static_ip: str = None) -> Exception|None:
        """Select the wifi network and enter its password."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return error.SerialConnectionError("Connection not open.")

        # Check if there is already a network
        err, response_lines = self._run_cmd('wpa_cli list_networks'.encode())
        if err:
            return err
        
        if len(response_lines) > 1:
            # How many networks are there?
            pattern = re.compile(r'^(?P<id>\d+)\s+$')
            network_ids = []
            for line in response_lines[1:]:
                match = pattern.match(line)
                if match:
                    network_ids.append(match.group('id'))
            log.debug(f"Existing network IDs: {network_ids}")

            # Remove existing networks
            for network_id in network_ids:
                err, _ = self._run_cmd(f'wpa_cli remove_network {network_id}'.encode(), check_return_code=True)
                if err:
                    return err

        # Add a new network
        err, response_lines = self._run_cmd(f'wpa_cli add_network'.encode(), check_return_code=True)
        if err:
            return err

        # The network ID is the first line that just has a single integer
        network_id = None
        for line in response_lines:
            line = line.strip()
            if line.isdigit():
                network_id = line
                break

        if network_id is None:
            return error.SerialConnectionError("Could not determine network ID from wpa_cli add_network response.")

        # Set the SSID and password
        err, _ = self._run_cmd(f'wpa_cli set_network {network_id} bssid "{bssid}"'.encode(), check_return_code=True)
        if err:
            return err

        err, _ = self._run_cmd(f'wpa_cli set_network {network_id} ssid \'"{ssid}"\''.encode(), check_return_code=True)
        if err:
            return err

        # TODO: Password needs to be masked or cleared from bash history
        err, _ = self._run_cmd(f'wpa_cli set_network {network_id} psk \'"{password}"\''.encode(), check_return_code=True)
        if err:
            return err
        
        err, _ = self._run_cmd(f'wpa_cli enable_network {network_id}'.encode(), check_return_code=True)
        if err:
            return err
        
        err, _ = self._run_cmd('wpa_cli save_config'.encode(), check_return_code=True)
        if err:
            return err

        # If static IP is provided, configure it
        if static_ip:
            # Get the DNS IP
            err, ip_lines = self._run_cmd("cat /etc/resolv.conf | grep nameserver".encode(), check_return_code=True)
            if err:
                return err

            dns_ip = None
            for line in ip_lines.splitlines():
                match = re.match(r'nameserver (\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    dns_ip = match.group(1)
                    break

            if not dns_ip:
                return error.SerialConnectionError("Could not determine DNS IP from /etc/resolv.conf.")

            # Get the Gateway IP
            err, route_lines = self._run_cmd("ip route | grep default".encode(), check_return_code=True)
            if err:
                return err

            gateway_ip = None
            for line in route_lines.splitlines():
                match = re.match(r'default via (\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    gateway_ip = match.group(1)
                    break

            if not gateway_ip:
                return error.SerialConnectionError("Could not determine Gateway IP from ip route.")

            # Update the network configuration
            err = self._write_line(f'echo -e "[Match]\\nName=wlan0\\n\\n[Network]\\nAddress={static_ip}/24\\nGateway={gateway_ip.decode().strip()}\\nDNS={dns_ip.decode().strip()}" > /etc/systemd/network/80-wifi-station.network'.encode())
            if err:
                return err

        # Now set wpa_supplicant in systemd
        # TODO: Need to start wpa_supplicant on startup via systemd
        #err, _ = self._run_cmd("wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf".encode(), check_return_code=True)

        return None

    def set_credentials(self, username: str, password: str) -> Exception|None:
        """Set the credentials on the connected Artie."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return error.SerialConnectionError("Connection not open.")

        # TODO: On artie-image-dev, we only have a root user, so ignore this for now
        #       Otherwise, we would implement the logic to change the default user's name and password here
        err = self._sign_in(username, password)
        if err:
            return err

    def verify_wifi_connection(self) -> tuple[Exception|None, str|None]:
        """Verify that Artie is connected to the wifi network and return the IP address."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return error.SerialConnectionError("Connection not open."), None

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

    def _read_all_lines(self) -> tuple[Exception, list[str]|None]:
        """Read all available lines from the serial connection."""
        lines = []
        while True:
            try:
                line = self._serial_connection.readline()
                log.debug(f"Read from serial: ".encode() + line)
            except serial.SerialException as e:
                return error.SerialConnectionError(str(e)), None

            if not line:
                break

            lines.append(line.decode().strip())

        return None, lines

    def _read_until(self, terminator_or_regex: bytes|re.Pattern) -> tuple[Exception, bytes|None]:
        """
        Read from the serial connection until the terminator is found or
        until the regular expression pattern is matched.
        """
        # Determine if we have a terminator or a regex pattern
        pattern = None
        is_regex = False
        if issubclass(type(terminator_or_regex), re.Pattern):
            pattern = terminator_or_regex
            is_regex = True
        else:
            terminator = terminator_or_regex

        # Read out bytes until we find the terminator or match the regex
        # (or we timeout)
        buffer = b''
        while True:
            try:
                byte = self._serial_connection.read(1)
            except serial.SerialException as e:
                return error.SerialConnectionError(str(e)), None

            if not byte:
                # Timeout reached
                log.warning(f"Read {buffer} from serial but did not find terminator or match regex ({terminator_or_regex}) before timeout.")
                return error.SerialConnectionError(f"Read timeout while looking for {terminator_or_regex}."), None

            buffer += byte

            if is_regex:
                if pattern.search(buffer.decode(errors='ignore')):
                    log.write(f"Matched regex pattern {pattern.pattern} in buffer: {buffer}")
                    return None, buffer
            else:
                if buffer.endswith(terminator):
                    log.write(f"Found terminator {terminator} in buffer: {buffer}")
                    return None, buffer

    def _run_cmd(self, command: bytes, check_return_code=False) -> tuple[Exception, str|None]:
        """Run a command on the serial connection and return its output."""
        err = self._write_line(command)
        if err:
            return err, None

        # username@host:path#
        pattern = re.compile(r"^(?P<user>[\w\-]+)@(?P<host>[\w\-]+):(?P<path>.+)#$")
        err, data = self._read_until(pattern)
        if err:
            return err, None

        # Extract just the command output (everything except the last line)
        lines = data.decode().splitlines()

        # Check return code
        if check_return_code:
            self._serial_connection.write(b'echo $?\n')
            err, ret_code_lines = self._read_all_lines()
            if err:
                return err

            if not any([line.strip() == '0' for line in ret_code_lines]):
                ret_code_str = ", ".join(ret_code_lines)
                log.error(f"Command returned non-zero exit code: {ret_code_str}")
                return error.SerialConnectionError(f"Command returned non-zero exit code: {ret_code_str}")

        return None, "\n".join(lines[:-1])

    def _sign_in(self, username: str, password: str) -> Exception|None:
        """Sign in to Artie with the provided credentials."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        try:
            self._read_until("login: ".encode())
        except error.SerialConnectionError:
            pass  # Possibly already logged in

        # TODO: Implement the actual sign-in and username/password change logic for artie-image-release
        self._write_line("root".encode())

    def _write_line(self, data: bytes) -> Exception|None:
        """Write a line to the serial connection."""
        try:
            log.debug(f"Writing to serial: ".encode() + data)
            self._serial_connection.write(data + b'\n')
            self._read_until(data)  # Read out the echo
            return None
        except serial.SerialException as e:
            return error.SerialConnectionError(str(e))
