"""
User-space driver for Artie's eyebrows MCUs.

This driver is responsible for:

* Loading eyebrow MCU firmware
* Animating eyebrows
* Moving eyes

This driver accepts RPC requests and controls the
MCUs over the Controller Node's CAN bus. It is
therefore meant to be run on the Controller Node,
and it needs to be run inside a container that
has access to CAN on the Controller Node.
"""
from artie_i2c import i2c
from artie_util import artie_logging as alog
from artie_util import constants
from artie_util import util
from artie_service_client import artie_service
from artie_service_client import interfaces
from . import ebcommon
from . import fw
from . import lcd
from . import led
from . import metrics
from . import servo
import argparse
import base64
import binascii
import rpyc

SERVICE_NAME = "eyebrows-driver"

@rpyc.service
class DriverServer(
    interfaces.ServiceInterfaceV1,
    interfaces.DriverInterfaceV1,
    interfaces.DisplayInterfaceV1,
    interfaces.MCUInterfaceV1,
    interfaces.StatusLEDInterfaceV1,
    artie_service.ArtieService
    ):
    def __init__(self, port: int, fw_fpath: str, ipv6=False):
        super().__init__(SERVICE_NAME, port)
        self._servo_submodule = servo.ServoSubmodule()
        self._led_submodule = led.LedSubmodule()
        self._lcd_submodule = lcd.LcdSubmodule()
        self._fw_submodule = fw.FirmwareSubmodule(fw_fpath, ipv6=ipv6)

        # Load FW
        self._fw_submodule.initialize_mcus()

        # Initialize
        self._led_submodule.initialize()
        self._lcd_submodule.initialize()

    @rpyc.exposed
    @alog.function_counter("status", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DriverInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DriverInterfaceV1)
    def status(self) -> dict[str, str]:
        """
        Return the status of this service's submodules.
        """
        status = self._fw_submodule.status() | self._led_submodule.status() | self._lcd_submodule.status() | self._servo_submodule.status()
        alog.test(f"Received request for status. Status: {status}", tests=['logging-integration-tests:status'])
        return {k: str(v) for k, v in status.items()}

    @rpyc.exposed
    @alog.function_counter("self_check", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DriverInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DriverInterfaceV1)
    def self_check(self):
        """
        Run a self diagnostics check and set our submodule statuses appropriately.
        """
        alog.info("Running self check...")
        self._fw_submodule.self_check_all()
        self._led_submodule.self_check()
        self._lcd_submodule.self_check()
        self._servo_submodule.self_check()

    @rpyc.exposed
    @alog.function_counter("led_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LED, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.StatusLEDInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.StatusLEDInterfaceV1)
    def led_list(self) -> list[str]:
        """
        RPC method to list all LEDs.
        """
        leds = [e.value for e in self._led_submodule.list()]
        alog.test(f"LEDs: {leds}", tests=['eyebrows-driver-integration-tests:led-list'])
        return leds

    @rpyc.exposed
    @alog.function_counter("led_set", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LED, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.StatusLEDInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.StatusLEDInterfaceV1)
    def led_set(self, side: str, state: str) -> bool:
        """
        RPC method to turn led on.

        Args
        ----
        - side: One of 'eyebrow-left' or 'eyebrow-right'
        - state: The state to set the LED to. Must be one of 'on', 'off', or 'heartbeat'.

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        if state == 'on':
            return self._led_submodule.on(side)
        elif state == 'off':
            return self._led_submodule.off(side)
        elif state == 'heartbeat':
            return self._led_submodule.heartbeat(side)
        else:
            alog.error(f"Invalid LED state: {state}")
            return False

    @rpyc.exposed
    @alog.function_counter("led_get", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LED, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.StatusLEDInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.StatusLEDInterfaceV1)
    def led_get(self, side: str) -> str:
        """
        RPC method to get the state of the given LED.
        """
        return self._led_submodule.get(side)

    @rpyc.exposed
    @alog.function_counter("display_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DisplayInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DisplayInterfaceV1)
    def display_list(self) -> list[str]:
        """
        RPC method to list all displays.
        """
        displays = [e.value for e in self._lcd_submodule.list()]
        alog.test(f"Displays: {displays}", tests=['eyebrows-driver-integration-tests:display-list'])
        return displays

    @rpyc.exposed
    @alog.function_counter("display_set", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    def display_set(self, side: str, eyebrow_state: str) -> bool:
        """
        RPC method to draw a specified eyebrow state to the LCD.

        Args
        ----
        - side: One of 'eyebrow-left' or 'eyebrow-right'
        - eyebrow_state: A base64-encoded string representing the eyebrow state to draw.
          Must be a string of three 'H', 'L', and 'M' characters representing High, Low, and Medium vertices.

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        # Decode from base64
        try:
            decoded_state = base64.b64decode(eyebrow_state).decode('utf-8')
        except binascii.Error as e:
            alog.error(f"Failed to decode eyebrow state from base64: {e}")
            return False
        except Exception as e:
            alog.error(f"Failed to decode eyebrow state from base64: {e}")
            return False

        if not all(c in 'HLM' for c in decoded_state):
            alog.error(f"Invalid eyebrow state after decoding: {decoded_state}. Must only contain 'H', 'L', and 'M' characters.")
            return False

        return self._lcd_submodule.draw(side, decoded_state)

    @rpyc.exposed
    @alog.function_counter("display_get", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    def display_get(self, side: str) -> str:
        """
        RPC method to get the LCD value that we think
        we are displaying on the given side. Will return either
        a list of vertices, 'test', 'clear', or 'error', any of which
        is base64-encoded.
        """
        return base64.b64encode(self._lcd_submodule.get(side).encode('utf-8')).decode('utf-8')

    @rpyc.exposed
    @alog.function_counter("display_test", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    def display_test(self, side: str) -> bool:
        """
        RPC method to test the LCD.

        Args
        ----
        - side: One of 'eyebrow-left' or 'eyebrow-right'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._lcd_submodule.test(side)

    @rpyc.exposed
    @alog.function_counter("display_clear", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    def display_clear(self, side: str) -> bool:
        """
        RPC method to turn the LCD off.

        Args
        ----
        - side: One of 'eyebrow-left' or 'eyebrow-right'

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._lcd_submodule.off(side)

    @rpyc.exposed
    @alog.function_counter("mcu_fw_load", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_fw_load(self, mcu_id: str) -> bool:
        """
        Load firmware onto the given MCU ID.

        * *Parameters*:
            * `mcu_id`: The ID of the MCU to load firmware onto.
        *Returns*: `True` if the firmware load was successful, `False` otherwise.
        """
        alog.info("Reloading FW...")
        worked = self._fw_submodule.initialize_mcus()

        # Initialize
        worked &= self._led_submodule.initialize()
        worked &= self._lcd_submodule.initialize()

        return worked

    @rpyc.exposed
    @alog.function_counter("mcu_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_list(self) -> list[str]:
        """
        Return a list of MCU IDs that this service is responsible for.
        """
        mcu_ids = list([str(k) for k in ebcommon.MCU_ADDRESS_MAP.keys()])
        alog.test(f"MCU IDs: {mcu_ids}", tests=['eyebrows-driver-integration-tests:mcu-list'])
        return mcu_ids

    @rpyc.exposed
    @alog.function_counter("mcu_reset", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_reset(self, mcu_id):
        """
        Reset the given MCU ID.

        * *Parameters*:
            * `mcu_id`: The ID of the MCU to reset.
        """
        return self._fw_submodule.reset(mcu_id)

    @rpyc.exposed
    @alog.function_counter("mcu_self_check", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_self_check(self, mcu_id: str):
        """
        Run a self diagnostics check on the given MCU and set our submodule statuses appropriately.
        """
        alog.test(f"Running self check on MCU {mcu_id}...", tests=[f'eyebrows-driver-integration-tests:mcu-self-check'])
        return self._fw_submodule.self_check(mcu_id)

    @rpyc.exposed
    @alog.function_counter("mcu_status", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_status(self, mcu_id: str) -> str:
        """
        Return the status of the given MCU ID.

        * *Parameters*:
            * `mcu_id`: The ID of the MCU to get status for.
        *Returns*: A string representing the status of the MCU. This string
        should be one of the enum values of `artie_util.constants.SubmoduleStatuses`.
        """
        alog.test(f"Checking status of MCU {mcu_id}...", tests=[f'eyebrows-driver-integration-tests:mcu-status'])
        if mcu_id == ebcommon.EyebrowSides.LEFT:
            return self._fw_submodule.left_status
        elif mcu_id == ebcommon.EyebrowSides.RIGHT:
            return self._fw_submodule.right_status
        else:
            alog.error(f"Requested status for invalid MCU ID {mcu_id}.")
            return constants.SubmoduleStatuses.UNKNOWN

    @rpyc.exposed
    @alog.function_counter("mcu_version", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_version(self, mcu_id: str) -> str:
        """
        Return the firmware version information for the given MCU ID.

        * *Parameters*:
            * `mcu_id`: The ID of the MCU to get version information for.
        *Returns*: A string representing the firmware version of the MCU.
        """
        return self._fw_submodule.version(mcu_id)

    @rpyc.exposed
    @alog.function_counter("mcu_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.ServoInterfaceV1)
    def servo_list(self) -> list[str]:
        """
        Return a list of servo IDs that this service is responsible for.
        """
        servo_ids = [ebcommon.EyebrowSides.LEFT.value, ebcommon.EyebrowSides.RIGHT.value]
        alog.test(f"Servo IDs: {servo_ids}", tests=['eyebrows-driver-integration-tests:servo-list'])
        return servo_ids

    @rpyc.exposed
    @alog.function_counter("servo_get", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.SERVO})
    @interfaces.interface_method(interfaces.ServoInterfaceV1)
    def servo_get(self, side: str) -> float:
        """
        RPC method to get the servo's degrees. This could be off
        due to inaccuracies of the servo, but also due to limiting on the left
        and right extreme ends as found during servo calibration.

        Returns
        -------
        Degrees (float).
        """
        return self._servo_submodule.get(side)

    @rpyc.exposed
    @alog.function_counter("servo_set", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.SERVO})
    @interfaces.interface_method(interfaces.ServoInterfaceV1)
    def servo_set(self, side: str, servo_degrees: float) -> bool:
        """
        RPC method to move the servo to the given location.

        Args
        ----
        - side: One of 'eyebrow-left' or 'eyebrow-right'
        - servo_degrees: Any value in the interval [0, 180]

        Returns
        -------
        bool: True if we do not detect an error. False otherwise.
        """
        return self._servo_submodule.go(side, servo_degrees)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fw_fpath", metavar="fw-fpath", type=str, help="The path to the FW file. It must be an .elf file.")
    parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
    parser.add_argument("-l", "--loglevel", type=str, default=None, choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=18863, help="The port to bind for the server.")
    args = parser.parse_args()

    # Set up logging
    alog.init(SERVICE_NAME, args)

    # Generate our self-signed certificate (if not already present)
    certfpath = "/etc/cert.pem"
    keyfpath = "/etc/pkey.pem"
    util.generate_self_signed_cert(certfpath, keyfpath, days=None, force=True)

    # If we are in testing mode, we need to manually initialize some stuff
    if util.in_test_mode():
        i2c.manually_initialize(i2c_instances=[0], instance_to_address_map={0: [ebcommon.MCU_ADDRESS_MAP['eyebrow-left'], ebcommon.MCU_ADDRESS_MAP['eyebrow-right']]})

    # Instantiate the single (multi-tenant) server instance and block forever, serving
    server = DriverServer(args.port, args.fw_fpath, ipv6=args.ipv6)
    t = util.create_server(server, keyfpath, certfpath, args.port, ipv6=args.ipv6)
    t.start()
