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

    def set_credentials(self, username: str, password: str) -> Exception|None:
        """Set the credentials on the connected Artie."""
        if not self._serial_connection or not self._serial_connection.is_open:
            return serial.SerialException("Connection not open.")

        # TODO: Implement the actual protocol for setting credentials over serial
