"""
User-space driver for Artie's mouth MCU.

This driver is responsible for:

* Loading mouth MCU firmware
* Animating the mouth

This driver accepts RPC requests and controls the
MCU over the Controller Node's I2C bus. It is therefore
meant to be run on the Controller Node, and it needs to
be run inside a container that has access to CAN
on the Controller Node.
"""
from artie_i2c import i2c
from artie_util import boardconfig_controller as board
from artie_util import artie_logging as alog
from artie_service_client import artie_service
from artie_service_client import interfaces
from artie_util import util
from . import fw
from . import lcd
from . import led
from . import metrics
import argparse
import base64
import rpyc

SERVICE_NAME = "mouth-driver"

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
        self._fw_submodule = fw.FirmwareSubmodule(fw_fpath, ipv6=ipv6)
        self._led_submodule = led.LedSubmodule()
        self._lcd_submodule = lcd.LcdSubmodule()

        # Load the FW file
        self._fw_submodule.load()

        # Set up the starting display
        self._lcd_submodule.draw("SMILE")

        # Set up the LED
        self._led_submodule.heartbeat()

    @rpyc.exposed
    @alog.function_counter("status", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DriverInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DriverInterfaceV1)
    def status(self) -> dict[str, str]:
        """
        Return the status of this service's submodules.
        """
        status = self._fw_submodule.status() | self._led_submodule.status() | self._lcd_submodule.status()
        alog.info(f"Received request for status: {status}")
        return {k: str(v) for k, v in status.items()}

    @rpyc.exposed
    @alog.function_counter("self_check", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DriverInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DriverInterfaceV1)
    def self_check(self):
        """
        Run a self diagnostics check and set our submodule statuses appropriately.
        """
        alog.info("Running self check...")
        self._fw_submodule.self_check()
        self._led_submodule.self_check()
        self._lcd_submodule.self_check()

    @rpyc.exposed
    @alog.function_counter("led_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LED, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.StatusLEDInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.StatusLEDInterfaceV1)
    def led_list(self) -> list[str]:
        """
        RPC method to list all available status LEDs.

        Returns
        -------
        list[str]: A list of all available status LED names.
        """
        return self._led_submodule.list()

    @rpyc.exposed
    @alog.function_counter("led_set", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LED, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.StatusLEDInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.StatusLEDInterfaceV1)
    def led_set(self, which: str, state: str) -> bool:
        """
        RPC method to turn led on.

        Args
        ----
        - which: Which LED to set to on. Ignored in mouth driver since there is only one LED.
        - state: The state to set the LED to. Must be one of 'on', 'off', or 'heartbeat'.

        Returns
        ----
        True if it worked. False otherwise.
        """
        if state == 'on':
            return self._led_submodule.on()
        elif state == 'off':
            return self._led_submodule.off()
        elif state == 'heartbeat':
            return self._led_submodule.heartbeat()
        else:
            alog.error(f"Invalid LED state: {state}")
            return False

    @rpyc.exposed
    @alog.function_counter("led_get", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LED, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.StatusLEDInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.StatusLEDInterfaceV1)
    def led_get(self, which: str) -> str:
        """
        RPC method to get the LED state.

        Args
        ----
        - which: Which LED to get the state of. Ignored in mouth driver since there is only one LED.

        Returns
        ----
        str: The current state of the LED.
        """
        return self._led_submodule.get()

    @rpyc.exposed
    @alog.function_counter("display_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DisplayInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DisplayInterfaceV1)
    def display_list(self) -> list[str]:
        """
        RPC method to list all available displays.

        Returns
        -------
        list[str]: A list of all available display IDs.
        """
        return self._lcd_submodule.list()

    @rpyc.exposed
    @alog.function_counter("display_set", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    @interfaces.interface_method(interfaces.DisplayInterfaceV1)
    def display_set(self, which: str, val: str):
        """
        RPC method to draw the given configuration on the mouth LCD.

        Args
        ----
        - which: The display ID to draw on. Ignored in mouth driver since there is only one display.
        - val: One of the available MOUTH_DRAWING_CHOICES (a base64-encoded string thereof).

        Returns
        ----
        True if it worked. False otherwise.
        """
        decoded_val = base64.b64decode(val).decode('utf-8')
        return self._lcd_submodule.draw(decoded_val)

    @rpyc.exposed
    @alog.function_counter("display_get", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    @interfaces.interface_method(interfaces.DisplayInterfaceV1)
    def display_get(self, which: str) -> str:
        """
        RPC method to get the current value (base64-encoded string) we think we are drawing.
        """
        current_val = self._lcd_submodule.get()

        if current_val is None:
            return None

        return base64.b64encode(current_val.encode('utf-8')).decode('utf-8')

    @rpyc.exposed
    @alog.function_counter("display_test", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    @interfaces.interface_method(interfaces.DisplayInterfaceV1)
    def display_test(self, which: str) -> bool:
        """
        RPC method to test the LCD.

        Returns
        ----
        True if it worked. False otherwise.
        """
        return self._lcd_submodule.test()

    @rpyc.exposed
    @alog.function_counter("display_clear", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.LCD})
    def display_clear(self, which: str):
        """
        RPC method to turn the LCD off.

        Returns
        ----
        True if it worked. False otherwise.
        """
        return self._lcd_submodule.off()

    @rpyc.exposed
    @alog.function_counter("mcu_fw_load", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_fw_load(self, mcu_id=fw.MOUTH_MCU_NAME) -> bool:
        """
        RPC method to (re)load the FW on the mouth MCU.
        This will also reinitialize the LED and LCD.

        Returns
        ----
        True if it worked. False otherwise.

        """
        worked = self._fw_submodule.load()

        # Set up the starting display
        self._lcd_submodule.draw("SMILE")

        # Set up the LED
        self._led_submodule.heartbeat()

        return worked

    @rpyc.exposed
    @alog.function_counter("mcu_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_list(self) -> list[str]:
        """
        Return a list of MCU IDs that this service is responsible for.
        """
        mcus = [fw.MOUTH_MCU_NAME]
        alog.test(f"MCU IDs: {mcus}", tests=["mouth-driver-integration-tests:mcu-list"])
        return mcus

    @rpyc.exposed
    @alog.function_counter("mcu_reset", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_reset(self, mcu_id=fw.MOUTH_MCU_NAME) -> bool:
        """
        Reset the given MCU ID.

        * *Parameters*:
            * `mcu_id`: The ID of the MCU to reset.

        *Returns*: `True` if the reset was successful, `False` otherwise.
        """
        if mcu_id != fw.MOUTH_MCU_NAME:
            raise ValueError(f"Invalid MCU ID: {mcu_id}")

        return self._fw_submodule.reset()

    @rpyc.exposed
    @alog.function_counter("mcu_self_check", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_self_check(self, mcu_id=fw.MOUTH_MCU_NAME):
        """
        Run a self diagnostics check and set our submodule statuses appropriately.
        """
        if mcu_id != fw.MOUTH_MCU_NAME:
            raise ValueError(f"Invalid MCU ID: {mcu_id}")

        self._fw_submodule.self_check()

    @rpyc.exposed
    @alog.function_counter("mcu_status", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_status(self, mcu_id=fw.MOUTH_MCU_NAME) -> str:
        """
        Return the status of the given MCU ID.

        * *Parameters*:
            * `mcu_id`: The ID of the MCU to get status for.

        *Returns*: A string representing the status of the MCU. This string
        should be one of the enum values of `artie_util.constants.SubmoduleStatuses`.
        """
        if mcu_id != fw.MOUTH_MCU_NAME:
            raise ValueError(f"Invalid MCU ID: {mcu_id}")

        status = self._fw_submodule.status()
        return status["FW"]

    @rpyc.exposed
    @alog.function_counter("mcu_version", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.SUBMODULE: metrics.SubmoduleNames.FIRMWARE, alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.MCUInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.MCUInterfaceV1)
    def mcu_version(self, mcu_id=fw.MOUTH_MCU_NAME) -> str:
        """
        Return the firmware version information for the given MCU ID.

        * *Parameters*:
            * `mcu_id`: The ID of the MCU to get version information for.

        *Returns*: A string representing the firmware version of the MCU.
        """
        if mcu_id != fw.MOUTH_MCU_NAME:
            raise ValueError(f"Invalid MCU ID: {mcu_id}")

        return self._fw_submodule.version()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fw_fpath", metavar="fw-fpath", type=str, help="The path to the FW file. It must be an .elf file.")
    parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
    parser.add_argument("-l", "--loglevel", type=str, default=None, choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=18862, help="The port to bind for the server.")
    args = parser.parse_args()

    # Set up logging
    alog.init(SERVICE_NAME, args)

    # Generate our self-signed certificate (if not already present)
    certfpath = "/etc/cert.pem"
    keyfpath = "/etc/pkey.pem"
    util.generate_self_signed_cert(certfpath, keyfpath, days=None, force=True)

    # If we are in testing mode, we need to manually initialize some stuff
    if util.in_test_mode():
        i2c.manually_initialize(i2c_instances=[0], instance_to_address_map={0: [board.I2C_ADDRESS_MOUTH_MCU]})

    # Instantiate the single (multi-tenant) server instance and block forever, serving
    server = DriverServer(args.port, args.fw_fpath, ipv6=args.ipv6)
    t = util.create_server(server, keyfpath, certfpath, args.port, ipv6=args.ipv6)
    t.start()
