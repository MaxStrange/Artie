"""
Example user-space driver for some sensors.
Mostly used for testing.
"""
from . import datastream
from artie_util import artie_logging as alog
from artie_util import artie_time
from artie_util import constants
from artie_util import util
from artie_service_client import artie_service
from artie_service_client import interfaces
import argparse
import os
import rpyc
import threading

SERVICE_NAME = "example-sensor-service"

@rpyc.service
class ExampleSensorService(
    interfaces.ServiceInterfaceV1,
    interfaces.DriverInterfaceV1,
    interfaces.SensorIMUV1,
    artie_service.ArtieService
    ):
    def __init__(self, port: int, certfpath: str, keyfpath: str, ipv6=False):
        super().__init__(SERVICE_NAME, port)
        self._stop_event = threading.Event()
        self._imu_state = {"imu-1": "off"}
        self._publish_thread: threading.Thread = None
        self._certfpath = certfpath
        self._keyfpath = keyfpath

    @rpyc.exposed
    @alog.function_counter("status", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DriverInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DriverInterfaceV1)
    def status(self) -> dict[str, str]:
        """
        Return the status of this service's submodules.
        """
        status = {
            "example_sensor_driver": constants.SubmoduleStatuses.WORKING,
        }
        alog.info(f"Received request for status. Status: {status}")
        return {k: str(v) for k, v in status.items()}

    @rpyc.exposed
    @alog.function_counter("self_check", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.DriverInterfaceV1.__interface_name__})
    @interfaces.interface_method(interfaces.DriverInterfaceV1)
    def self_check(self):
        """
        Run a self diagnostics check and set our submodule statuses appropriately.
        """
        alog.info("Running self check...")
        return True

    @rpyc.exposed
    @alog.function_counter("imu_list", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_list(self) -> list[str]:
        """
        Return a list of all IMU sensor IDs that this service provides data for.
        """
        return list(self._imu_state.keys())

    @rpyc.exposed
    @alog.function_counter("imu_whoami", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_whoami(self, imu_id: str) -> str:
        """
        Return the name of the IMU sensor with the given ID.
        """
        return "LSM6DSO32"

    @rpyc.exposed
    @alog.function_counter("imu_self_check", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_self_check(self, imu_id: str) -> bool:
        """
        Perform a self-check on the IMU sensor with the given ID and return True if it is functioning properly, and False otherwise.
        """
        return True

    @rpyc.exposed
    @alog.function_counter("imu_on", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_on(self, imu_id: str) -> bool:
        """
        Turn on the IMU sensor with the given ID.
        """
        alog.info(f"Turning on IMU with ID {imu_id}...")
        self._imu_state[imu_id] = "on"
        return True

    @rpyc.exposed
    @alog.function_counter("imu_off", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_off(self, imu_id: str) -> bool:
        """
        Turn off the IMU sensor with the given ID.
        """
        alog.info(f"Turning off IMU with ID {imu_id}...")
        self._stop_stream(imu_id)
        self._imu_state[imu_id] = "off"
        return True

    @rpyc.exposed
    @alog.function_counter("imu_get_data", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_get_data(self, imu_id: str) -> dict:
        """
        Get the latest data from the IMU sensor with the given ID. The returned
        dictionary should have the following format:
        {
            "accelerometer": (x, y, z) (all floating point numbers) or None,
            "gyroscope": (x, y, z) (all floating point numbers) or None,
            "magnetometer": (x, y, z) (all floating point numbers) or None,
            "timestamp": standard (str) Artie time format as a string,
        }
        If a sub-sensor is not present in the IMU, its value should be None.

        It is up to the service implementing this interface to determine whether
        this is a synchronous method that returns the latest data on demand, or an
        asynchronous method that returns the data from the most recent datastream
        publication for the given IMU ID.
        """
        if self._imu_state[imu_id] != "on":
            alog.warning(f"Received request for data from IMU with ID {imu_id}, but it is not on. Returning None.")
            return {
                "accelerometer": None,
                "gyroscope": None,
                "magnetometer": None,
                "timestamp": artie_time.now_str(),
            }

        return {
            "accelerometer": (0.0, 0.0, 9.8),
            "gyroscope": (0.0, 0.0, 0.0),
            "magnetometer": None,
            "timestamp": artie_time.now_str(),
        }

    @rpyc.exposed
    @alog.function_counter("imu_start_stream", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_start_stream(self, imu_id: str, freq_hz=None) -> bool:
        """
        Start streaming data from the IMU sensor with the given ID. The service
        should publish new data to the appropriate datastream at the given
        frequency (in Hz) if possible. It is implementation-dependent whether the service will honor
        this parameter. If called again before imu_stop_stream, the service should update the frequency of the stream if possible
        to the new frequency.

        Returns True if the stream was successfully started (or the frequency was successfully updated), and False otherwise.

        The published data can be found under the name <simple interface name>:sensor-imu-v1:<imu_id>
        (e.g. "my-service:sensor-imu-v1:imu-1") and should be in the same format as described in imu_get_data.
        """
        if self._imu_state[imu_id] != "on":
            alog.warning(f"Received request to start stream for IMU with ID {imu_id}, but it is not on. Cannot start stream.")
            return False

        self._start_stream(imu_id, freq_hz)
        return True

    @rpyc.exposed
    @alog.function_counter("imu_stop_stream", alog.MetricSWCodePathAPIOrder.CALLS, attributes={alog.KnownMetricAttributes.INTERFACE_NAME: interfaces.SensorIMUV1.__interface_name__})
    @interfaces.interface_method(interfaces.SensorIMUV1)
    def imu_stop_stream(self, imu_id: str) -> bool:
        """
        Stop streaming data from the IMU sensor with the given ID.

        Returns True if the stream was successfully stopped, and False otherwise.
        Returns False if the stream was not active in the first place.
        """
        if self._imu_state[imu_id] != "on":
            alog.warning(f"Received request to stop stream for IMU with ID {imu_id}, but it is not on. Cannot stop stream.")
            return False

        self._stop_stream(imu_id)
        return True

    def _start_stream(self, imu_id: str, freq_hz=None):
        alog.info(f"Starting stream for IMU with ID {imu_id} at frequency {freq_hz} Hz...")
        self._stop_event.clear()
        self._publish_thread = threading.Thread(target=datastream.stream, args=(self._stop_event, self._certfpath, self._keyfpath, SERVICE_NAME, imu_id, freq_hz))
        self._publish_thread.start()

    def _stop_stream(self, imu_id: str):
        alog.info(f"Stopping stream for IMU with ID {imu_id}...")
        if self._publish_thread is not None:
            self._stop_event.set()
            self._publish_thread.join()
            self._publish_thread = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
    parser.add_argument("-l", "--loglevel", type=str, default=None, choices=["debug", "info", "warning", "error"], help="The log level.")
    parser.add_argument("-p", "--port", type=int, default=os.environ.get("PORT", 18865), help="The port to bind for the server.")
    args = parser.parse_args()

    # Set up logging
    alog.init(SERVICE_NAME, args)

    # Generate our self-signed certificate (if not already present)
    certfpath = "/etc/cert.pem"
    keyfpath = "/etc/pkey.pem"
    util.generate_self_signed_cert(certfpath, keyfpath, days=None, force=True)

    # Instantiate the single (multi-tenant) server instance and block forever, serving
    server = ExampleSensorService(args.port, certfpath, keyfpath, ipv6=args.ipv6)
    t = util.create_server(server, keyfpath, certfpath, args.port, ipv6=args.ipv6)
    t.start()
