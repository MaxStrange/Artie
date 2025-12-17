"""
A wrapper/shim to decouple our choice of logging/telemetry library/SDK
from the programming interface.
"""
from . import constants
from logging import handlers as loghandlers
from socket import socket
from typing import Dict
from opentelemetry import metrics
from opentelemetry.exporter import prometheus
import opentelemetry.sdk.metrics as otelmetrics
import opentelemetry.sdk.metrics.view as metview
import opentelemetry.sdk.resources as otelresource
import datetime
import enum
import functools
import inspect
import io
import json
import logging
import multiprocessing
import os
import prometheus_client as promc
import queue
import random
import ssl
import string
import traceback

GLOBAL_METER_NAME = "artie.global.meter"
ARTIE_ID = os.environ.get(constants.ArtieEnvVariables.ARTIE_ID, 'UNSET')
SERVICE_NAME = ""  # Set when initialized
HISTOGRAM_SUFFIX_SECONDS = "duration-seconds"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# A cache of metrics (name: meter)
_metrics = {}

# If we fail to configure metrics, we cannot use them at all
METRICS_CONFIGURED = True


def _emit_records_to_remote(socket_handler):
    """
    Helper for multi-processing the remote transmission of logs.
    """
    while True:
        record = socket_handler.queue.get()
        if record == socket_handler.QUIT_SIGNAL:
            return
        try:
            s = socket_handler.makeJson(record)
            socket_handler.send(s.encode('utf-8'))
        except Exception:
            socket_handler.handleError(record)

class ArtieLogSocketHandler(loghandlers.SocketHandler):
    """
    Subclass of SocketHandler to:

    1) Use TLS
    2) Be conformant to the FluentBit collector.
    3) Be asynchronous when emitting the logs or when trying to connect to remote.
    """
    def __init__(self, host: str, port: int | None) -> None:
        super().__init__(host, port)
        self.sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.sslcontext.check_hostname = False
        self.sslcontext.verify_mode = ssl.CERT_NONE
        self.QUIT_SIGNAL = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        self.queue = multiprocessing.Queue(maxsize=1000)
        self.emitter_proc = multiprocessing.Process(target=_emit_records_to_remote, args=(self,), daemon=True)
        self.emitter_proc.start()

    def emit(self, record):
        """
        Emit a record.

        JSON-ifies the record and writes it to the socket.
        If there is an error with the socket, silently drop the packet.
        If there was a problem with the socket, re-establishes the
        socket.
        """
        try:
            self.queue.put_nowait(record)
        except queue.Full as e:
            print(f"Cannot send log message to remote endpoint. Queue is full.")

    def makeJson(self, record) -> str:
        """
        Returns the given `record` as a JSON version of the form:

        {
            'level': <level>,
            'message': <the log message>,
            'processname': <the name of the process>,
            'threadname': <the name of the thread>,
            'timestamp': <timestamp in asctime format from Python logging library>,
            'servicename': <the name of the service>,
            'artieID': <the ID of the Artie that is logging>
        }
        """
        msg_dict = {
            'level': record.levelname if hasattr(record, 'levelname') else 'UNKNOWN',
            'message': record.getMessage() if hasattr(record, 'getMessage') else '',
            'processname': record.processName if hasattr(record, 'processName') else 'Unknown',
            'threadname': record.threadName if hasattr(record, 'threadName') else 'Unknown',
            'timestamp': record.asctime if hasattr(record, 'asctime') else datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'servicename': SERVICE_NAME,
            'artieid': ARTIE_ID,
        }
        return json.dumps(msg_dict, default=str)

    def makeSocket(self, timeout: float = 1) -> socket:
        sock = super().makeSocket(timeout)
        if self.port is None:
            # Unix socket
            return sock

        return self.sslcontext.wrap_socket(sock, server_hostname=self.host)

    def close(self):
        self.queue.put(self.QUIT_SIGNAL, timeout=2.0)
        self.emitter_proc.join(timeout=5.0)
        super().close()

def init(service_name, args=None):
    """
    Initialize the telemetry stack.
    """
    if args is not None and hasattr(args, 'loglevel') and args.loglevel is not None:
        loglevel = args.loglevel.upper()
    else:
        loglevel = "INFO"

    # Set the service name globally
    global SERVICE_NAME
    SERVICE_NAME = service_name

    resource = otelresource.Resource.create({
        otelresource.SERVICE_NAME: SERVICE_NAME,
        otelresource.SERVICE_NAMESPACE: "artie",
        otelresource.SERVICE_INSTANCE_ID: os.environ.get("HOSTNAME", ''.join(random.choices(string.ascii_letters, k=10))),
        otelresource.SERVICE_VERSION: os.environ.get(constants.ArtieEnvVariables.ARTIE_GIT_TAG, 'unversioned'),
        otelresource.CONTAINER_NAME: os.environ.get("HOSTNAME", SERVICE_NAME),
        otelresource.CONTAINER_IMAGE_TAG: os.environ.get(constants.ArtieEnvVariables.ARTIE_GIT_TAG, 'unversioned'),
    })

    # Check if we are running in test mode
    test_mode = os.environ.get(constants.ArtieEnvVariables.ARTIE_RUN_MODE, constants.ArtieRunModes.PRODUCTION) in (constants.ArtieRunModes.SANITY_TESTING, constants.ArtieRunModes.UNIT_TESTING)

    # Set up logging
    fluent_bit_collector_hostname = os.environ.get(constants.ArtieEnvVariables.LOG_COLLECTOR_HOSTNAME, None)
    fluent_bit_collector_port = os.environ.get(constants.ArtieEnvVariables.LOG_COLLECTOR_PORT, None)
    socket_handler = ArtieLogSocketHandler(fluent_bit_collector_hostname, fluent_bit_collector_port)
    stream_handler = logging.StreamHandler()
    handlers = None if test_mode else [socket_handler, stream_handler]
    format = "%(asctime)s %(threadName)s %(levelname)s: %(message)s"
    logging.basicConfig(format=format, level=getattr(logging, loglevel), force=True, handlers=handlers, datefmt=DATE_FORMAT)

    # Set up metrics
    prometheus_server_port = os.environ.get(constants.ArtieEnvVariables.METRICS_SERVER_PORT, None)
    if not prometheus_server_port:
        global METRICS_CONFIGURED
        logging.error("No 'METRICS_SERVER_PORT' in environment. Cannot send metrics.")
        METRICS_CONFIGURED = False
        return
    promc.start_http_server(int(prometheus_server_port))
    histogram_view = metview.View(instrument_name=f"*-{HISTOGRAM_SUFFIX_SECONDS}", aggregation=metview.ExplicitBucketHistogramAggregation([1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]))
    metric_reader = prometheus.PrometheusMetricReader(prefix=SERVICE_NAME.replace(' ', '_').replace('-', '_'))
    provider = otelmetrics.MeterProvider(metric_readers=[metric_reader], resource=resource, views=[histogram_view])
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(GLOBAL_METER_NAME)

################################################################################
############################### Logging API ####################################
################################################################################

def exception(msg, e, stack_trace=False):
    """
    Logs the given `msg` at ERROR level, formats the exception `e`
    into a nice message, and if `stack_trace` is `True`, also
    logs a stack trace.
    """
    logging.error(f"{msg}; Exception information: {e}")
    if stack_trace:
        log = io.StringIO()
        traceback.print_exception(e, file=log)
        traceback_msg = log.getvalue()
        log.close()
        logging.error(traceback_msg)

def error(msg):
    """
    Logs at the ERROR level.
    """
    logging.error(msg)

def warning(msg):
    """
    Logs at the WARNING level.
    """
    logging.warning(msg)

def info(msg):
    """
    Logs at the INFO level.
    """
    logging.info(msg)

def debug(msg):
    """
    Logs at the DEBUG level.
    """
    logging.debug(msg)

def test(msg, tests):
    """
    Print `msg` to stdout via INFO logging. The variable `tests` is a list of
    the names of the tests that use this test point. It is
    not used in this function. It's simply a way to document
    which tests are using a test point so you know what will
    be affected if you change the msg string.
    """
    logging.info(msg)

################################################################################
############################### Metrics API ####################################
################################################################################
class MetricUnits(enum.StrEnum):
    SECONDS = "seconds"
    DEGREES_C = "celsius"
    METERS = "meters"
    BYTES = "bytes"
    PERCENT = "ratio"
    VOLTS = "volts"
    AMPS = "amperes"
    JOULES = "joules"
    GRAMS = "grams"
    CALLS = "calls"

class KnownMetricAttributes(enum.StrEnum):
    ARTIE_ID = "artie.id"
    """The Artie ID."""

    SERVICE_NAME = "artie.service_name"
    """The service name."""

    SUBMODULE = "submodule"
    """The submodule of the driver or service."""

    FUNCTION_NAME = "function-name"
    """The name of the function being measured."""

class _MetricEnumMixin:
    """
    When mixed in with an Enum, this class takes care of the __new__ method
    so that each member value is the appropriate series of 'kingdom.phylum.etc.'.

    Just make sure that all non-top-level (i.e., non-kingdom-level) enums
    have a `_parent` member that points to the correct parent enum.
    """
    def __init__(self, *args):
        if len(args) != 2:
            # All enum members (including _parent need to have a '_value_')
            self._value_ = args[0]
        else:
            # If we are a normal member with a _parent, the _parent should
            # be an Enum member, so get its 'value' and prepend it to the normal value.
            self._value_ = f"{args[1].value}.{args[0]}"

################################ Metric Taxonomy ####################################

################################## Kingdoms #################################################

class MetricKingdom(enum.StrEnum):
    """Metrics come in two main branches: hardware and software."""
    HARDWARE = "hw"
    SOFTWARE = "sw"

############################### Phyla #######################################################

class MetricHWPhylum(_MetricEnumMixin, enum.Enum):
    """hw.X: HW branch of metrics taxonomy comes in several phyla."""
    _parent = MetricKingdom.HARDWARE

    SYSTEM = "system", _parent
    """System-level metrics, such as CPU, memory, disk, temperature."""

    BUSES = "buses", _parent
    """Metrics related to hardware buses, such as I2C, SPI, UART."""

    ACTUATORS = "actuators", _parent
    """Metrics related to 'actuators', such as displays, servos, etc."""

    SENSORS = "sensors", _parent
    """Metrics related to sensors, such as distance sensors, IMUs, etc."""



class MetricSWPhylum(_MetricEnumMixin, enum.Enum):
    """sw.X: SW branch of metrics taxonomy comes in several phyla."""
    _parent = MetricKingdom.SOFTWARE
    
    CODE_PATHS = "code_paths", _parent
    """Metrics related to code paths, such as function call counts and latencies."""

    RESOURCE_USAGE = "resource_usage", _parent
    """Metrics related to resource usage, such as process/thread count or availability."""

################################ Classes #######################################################

class MetricHWSystemClass(_MetricEnumMixin, enum.Enum):
    """hw.system.X: System-level metrics classes."""
    _parent = MetricHWPhylum.SYSTEM

    CPU = "cpu", _parent
    """CPU-related metrics."""

    MEMORY = "memory", _parent
    """Memory-related metrics."""

    DISK = "disk", _parent
    """Disk-related metrics."""

    TEMPERATURE = "temperature", _parent
    """Temperature-related metrics."""

class MetricHWBusClass(_MetricEnumMixin, enum.Enum):
    """hw.buses.X: Bus-related metrics classes."""
    _parent = MetricHWPhylum.BUSES

    I2C = "i2c", _parent
    """I2C bus metrics."""

    SPI = "spi", _parent
    """SPI bus metrics."""

    UART = "uart", _parent
    """UART bus metrics."""

    CAN = "can", _parent
    """CAN bus metrics."""

    GPIO = "gpio", _parent
    """GPIO metrics."""

class MetricHWActuatorClass(_MetricEnumMixin, enum.Enum):
    """hw.actuators.X: 'Actuator'-related metrics classes."""
    _parent = MetricHWPhylum.ACTUATORS

    DISPLAY = "display", _parent
    """Display actuator metrics."""

    SERVO = "servo", _parent
    """Servo actuator metrics."""

    SPEAKER = "speaker", _parent
    """Speaker metrics."""

class MetricHWSensorClass(_MetricEnumMixin, enum.Enum):
    """hw.sensors.X: Sensor-related metrics classes."""
    _parent = MetricHWPhylum.SENSORS

    DISTANCE = "distance", _parent
    """Distance sensor metrics."""

    IMU = "imu", _parent
    """IMU sensor metrics."""

    TEMPERATURE = "temperature", _parent
    """Temperature sensor metrics."""

    AUDIO = "audio", _parent
    """Audio sensor metrics."""

    VISUAL = "visual", _parent
    """Visual sensor metrics."""



class MetricSWCodePathsClass(_MetricEnumMixin, enum.Enum):
    """sw.code_paths.X: Code-path-related metrics classes."""
    _parent = MetricSWPhylum.CODE_PATHS
    
    API = "api", _parent
    """API-related metrics."""

    SUBMODULE = "submodule", _parent
    """Submodule-related metrics."""

class MetricSWResourceUsageClass(_MetricEnumMixin, enum.Enum):
    """sw.resource_usage.X: Resource-usage-related metrics classes."""
    _parent = MetricSWPhylum.RESOURCE_USAGE

    PROCESS = "process", _parent
    """Process-related metrics."""

    THREAD = "thread", _parent
    """Thread-related metrics."""

    APPLICATION = "application", _parent
    """Whole-application-related metrics."""

############################### Orders #######################################################

class MetricHWSystemCPUOrder(_MetricEnumMixin, enum.Enum):
    """hw.system.cpu.X: CPU-related metrics orders."""
    _parent = MetricHWSystemClass.CPU

    USAGE = "usage", _parent
    """CPU usage metrics."""

class MetricHWSystemMemoryOrder(_MetricEnumMixin, enum.Enum):
    """hw.system.memory.X: Memory-related metrics orders."""
    _parent = MetricHWSystemClass.MEMORY

    USAGE = "usage", _parent
    """Memory usage metrics."""

class MetricHWSystemDiskOrder(_MetricEnumMixin, enum.Enum):
    """hw.system.disk.X: Disk-related metrics orders."""
    _parent = MetricHWSystemClass.DISK

    USAGE = "usage", _parent
    """Disk usage metrics."""

class MetricHWSystemTemperatureOrder(_MetricEnumMixin, enum.Enum):
    """hw.system.temperature.X: Temperature-related metrics orders."""
    _parent = MetricHWSystemClass.TEMPERATURE

    TEMPERATURE = "temperature", _parent
    """Temperature metrics."""

class MetricHWBusI2COrder(_MetricEnumMixin, enum.Enum):
    """hw.buses.i2c.X: I2C bus-related metrics orders."""
    _parent = MetricHWBusClass.I2C

    TRAFFIC = "traffic", _parent
    """I2C bus traffic metrics."""

class MetricHWBusSPIOrder(_MetricEnumMixin, enum.Enum):
    """hw.buses.spi.X: SPI bus-related metrics orders."""
    _parent = MetricHWBusClass.SPI

    TRAFFIC = "traffic", _parent
    """SPI bus traffic metrics."""

class MetricHWBusUARTOrder(_MetricEnumMixin, enum.Enum):
    """hw.buses.uart.X: UART bus-related metrics orders."""
    _parent = MetricHWBusClass.UART

    TRAFFIC = "traffic", _parent
    """UART bus traffic metrics."""

class MetricHWBusCANOrder(_MetricEnumMixin, enum.Enum):
    """hw.buses.can.X: CAN bus-related metrics orders."""
    _parent = MetricHWBusClass.CAN

    TRAFFIC = "traffic", _parent
    """CAN bus traffic metrics."""

class MetricHWBusGPIOOrder(_MetricEnumMixin, enum.Enum):
    """hw.buses.gpio.X: GPIO-related metrics orders."""
    _parent = MetricHWBusClass.GPIO

    PIN_INPUT = "pin-input", _parent
    """GPIO pin input metrics."""

    PIN_OUTPUT = "pin-output", _parent
    """GPIO pin output metrics."""

class MetricHWActuatorDisplayOrder(_MetricEnumMixin, enum.Enum):
    """hw.actuators.display.X: Display actuator-related metrics orders."""
    _parent = MetricHWActuatorClass.DISPLAY

    BRIGHTNESS = "brightness", _parent
    """Display brightness metrics."""

class MetricHWActuatorServoOrder(_MetricEnumMixin, enum.Enum):
    """hw.actuators.servo.X: Servo actuator-related metrics orders."""
    _parent = MetricHWActuatorClass.SERVO

    POSITION = "position", _parent
    """Servo position metrics."""

class MetricHWActuatorSpeakerOrder(_MetricEnumMixin, enum.Enum):
    """hw.actuators.speaker.X: Speaker actuator-related metrics orders."""
    _parent = MetricHWActuatorClass.SPEAKER

    VOLUME = "volume", _parent
    """Speaker volume metrics."""

class MetricHWSensorDistanceOrder(_MetricEnumMixin, enum.Enum):
    """hw.sensors.distance.X: Distance sensor-related metrics orders."""
    _parent = MetricHWSensorClass.DISTANCE

    DISTANCE = "distance", _parent
    """Distance sensor metrics."""

class MetricHWSensorIMUOrder(_MetricEnumMixin, enum.Enum):
    """hw.sensors.imu.X: IMU sensor-related metrics orders."""
    _parent = MetricHWSensorClass.IMU

    ORIENTATION = "orientation", _parent
    """IMU orientation metrics."""

class MetricHWSensorTemperatureOrder(_MetricEnumMixin, enum.Enum):
    """hw.sensors.temperature.X: Temperature sensor-related metrics orders."""
    _parent = MetricHWSensorClass.TEMPERATURE

    TEMPERATURE = "temperature", _parent
    """Temperature sensor metrics."""

class MetricHWSensorAudioOrder(_MetricEnumMixin, enum.Enum):
    """hw.sensors.audio.X: Audio sensor-related metrics orders."""
    _parent = MetricHWSensorClass.AUDIO

    LEVEL = "level", _parent
    """Audio level metrics."""

class MetricHWSensorVisualOrder(_MetricEnumMixin, enum.Enum):
    """hw.sensors.visual.X: Visual sensor-related metrics orders."""
    _parent = MetricHWSensorClass.VISUAL

    IMAGE = "image", _parent
    """Visual image metrics."""



class MetricSWCodePathAPIOrder(_MetricEnumMixin,enum.Enum):
    """sw.code_paths.api.X: API-related metrics orders."""
    _parent = MetricSWCodePathsClass.API

    CALLS = "calls", _parent
    """API call count metrics."""

    LATENCY = "latency", _parent
    """API call latency metrics."""

class MetricSWCodePathSubmoduleOrder(_MetricEnumMixin,enum.Enum):
    """sw.code_paths.submodule.X: Submodule-related metrics orders."""
    _parent = MetricSWCodePathsClass.SUBMODULE

    CALLS = "calls", _parent
    """Submodule call count metrics."""

    LATENCY = "latency", _parent
    """Submodule call latency metrics."""

    COMMANDS_PROCESSED = "commands-processed", _parent
    """Submodule commands processed metrics."""

class MetricSWResourceUsageProcessOrder(_MetricEnumMixin, enum.Enum):
    """sw.resource_usage.process.X: Process-related metrics orders."""
    _parent = MetricSWResourceUsageClass.PROCESS

    CPU_USAGE = "cpu-usage", _parent
    """Process CPU usage metrics."""

    MEMORY_USAGE = "memory-usage", _parent
    """Process memory usage metrics."""

    UPTIME = "uptime", _parent
    """Process uptime metrics."""

class MetricSWResourceUsageThreadOrder(_MetricEnumMixin, enum.Enum):
    """sw.resource_usage.thread.X: Thread-related metrics orders."""
    _parent = MetricSWResourceUsageClass.THREAD

    CPU_USAGE = "cpu-usage", _parent
    """Thread CPU usage metrics."""

    MEMORY_USAGE = "memory-usage", _parent
    """Thread memory usage metrics."""

    UPTIME = "uptime", _parent
    """Thread uptime metrics."""

class MetricSWResourceUsageApplicationOrder(_MetricEnumMixin, enum.Enum):
    """sw.resource_usage.application.X: Application-related metrics orders."""
    _parent = MetricSWResourceUsageClass.APPLICATION

    CPU_USAGE = "cpu-usage", _parent
    """Application CPU usage metrics."""

    MEMORY_USAGE = "memory-usage", _parent
    """Application memory usage metrics."""

    UPTIME = "uptime", _parent
    """Application uptime metrics."""

################################ Metric Families #######################################

class MetricSWCodePathAPICallFamily(enum.StrEnum):
    """sw.code_paths.api.calls: API call count metric family."""
    SUCCESS = "success"
    """API call succeeded."""

    FAILURE = "failure"
    """API call failed."""



def _add_attributes(obs):
    if obs.attributes is None:
        obs.attributes = {}
    obs.attributes[KnownMetricAttributes.ARTIE_ID] = ARTIE_ID
    obs.attributes[KnownMetricAttributes.SERVICE_NAME] = SERVICE_NAME

def _callback_wrapper(callback, *args, **kwargs):
    if inspect.isgeneratorfunction(callback):
        for obs in callback(*args, **kwargs):
            _add_attributes(obs)
            yield obs
    else:
        observations = [_add_attributes(obs) for obs in callback(*args, **kwargs)]
        return observations

def create_async_counter(callback, name: str, taxonomy, unit: MetricUnits, description: str):
    """
    Create an asynchronous counter which will increment by the value given by `callback`'s return value
    every time the metrics are scraped by the endpoint.

    If this is called more than once for a given `name`/`taxonomy` combination, we remove the old metric and
    replace it with the new one.

    `callback` must take an opentelemetry.metrics.CallbackOptions argument and
    return a sequence of opentelemetry.metrics.Observation objects.

    `callback` can be a generator which yields one Observation object at a time.

    `callback` should make use of the `timeout_millis` property on the `CallbackOptions` object passed to it.

    Any Observations returned by `callback` will automatically have 'artie.id' and 'artie.service_name' appended to their attributes.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)
    derived_name = f"{SERVICE_NAME}.{taxonomy.value}.{name}"

    global _metrics
    if derived_name in _metrics:
        del _metrics[derived_name]
        _metrics[derived_name] = None

    async_counter = meter.create_observable_counter(derived_name, [functools.partial(_callback_wrapper, callback)], unit, description)
    _metrics[derived_name] = async_counter

def create_async_gauge(callback, name: str, taxonomy, unit: MetricUnits, description: str):
    """
    Same as `create_async_counter`, except we create a gauge, which simply returns its
    value at the time of reading. For example, you might have a 'fuel' metric,
    which returns the amount of fuel currently in the tank whenever the callback is called.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)
    derived_name = f"{SERVICE_NAME}.{taxonomy.value}.{name}"

    global _metrics
    if derived_name in _metrics:
        del _metrics[derived_name]
        _metrics[derived_name] = None

    gauge = meter.create_observable_gauge(derived_name, [functools.partial(_callback_wrapper, callback)], unit, description)
    _metrics[derived_name] = gauge

def create_async_updown_counter(callback, name: str, taxonomy, unit: MetricUnits, description: str):
    """
    Same as `create_async_counter`, but for an up-down counter.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)
    derived_name = f"{SERVICE_NAME}.{taxonomy.value}.{name}"

    global _metrics
    if derived_name in _metrics:
        del _metrics[derived_name]
        _metrics[derived_name] = None

    updown = meter.create_observable_up_down_counter(derived_name, [functools.partial(_callback_wrapper, callback)], unit, description)
    _metrics[derived_name] = updown

def update_counter(increment: int | float, name: str, taxonomy, unit:MetricUnits=None, description:str=None, attributes: Dict[str, str]=None):
    """
    Create a counter if it doesn't already exist, otherwise get the counter with the name derived
    from the given `name` and `taxonomy`, then increment (or initialize) by `increment`.

    Args
    ----
    - increment: The value to initialize the counter to if it is new, otherwise the value by which we increment.
    - name: The name of the counter.
    - taxonomy: The taxonomy of the metric. Should be one of the enums defined in this module for that purpose.
    - unit: The measurement unit. Only used if we create a new counter.
    - description: A description of the counter. Only used if we create a new counter.
    - attributes: A dict of {str: str} to add as metadata to the metric when updating it.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)
    derived_name = f"{SERVICE_NAME}.{taxonomy.value}.{name}"

    global _metrics
    if derived_name in _metrics:
        counter = _metrics[derived_name]
    else:
        counter = meter.create_counter(derived_name, unit, description)
        _metrics[derived_name] = counter

    attributes = {} if not attributes else attributes
    attributes[KnownMetricAttributes.ARTIE_ID] = ARTIE_ID
    attributes[KnownMetricAttributes.SERVICE_NAME] = SERVICE_NAME
    counter.add(increment, attributes=attributes)

def update_histogram(amount: int | float, name: str, taxonomy, unit:MetricUnits=None, description:str=None, attributes: Dict[str, str]=None, bins=None):
    """
    Same as `update_counter`, but a histogram instead.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)
    derived_name = f"{SERVICE_NAME}.{taxonomy.value}.{name}"

    global _metrics
    if derived_name in _metrics:
        histogram = _metrics[derived_name]
    else:
        histogram = meter.create_histogram(derived_name, unit, description)
        _metrics[derived_name] = histogram

    attributes = {} if not attributes else attributes
    attributes[KnownMetricAttributes.ARTIE_ID] = ARTIE_ID
    attributes[KnownMetricAttributes.SERVICE_NAME] = SERVICE_NAME
    histogram.record(amount, attributes=attributes)

def update_updown_counter(amount: int | float, name: str, taxonomy,unit:MetricUnits=None, description:str=None, attributes: Dict[str, str]=None):
    """
    Same as `update_counter`, but an up-down counter instead.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)
    derived_name = f"{SERVICE_NAME}.{taxonomy.value}.{name}"

    global _metrics
    if derived_name in _metrics:
        updown = _metrics[derived_name]
    else:
        updown = meter.create_up_down_counter(derived_name, unit, description)
        _metrics[derived_name] = updown

    attributes = {} if not attributes else attributes
    attributes[KnownMetricAttributes.ARTIE_ID] = ARTIE_ID
    attributes[KnownMetricAttributes.SERVICE_NAME] = SERVICE_NAME
    updown.add(amount, attributes=attributes)

def function_counter(name: str, taxonomy, attributes=None):
    """
    A decorator for creating a function call counter. It increments
    every time the decorated function is called.

    The `taxonomy` argument is used to specify the taxonomy of the metric and should
    be one of the enums defined in this module for that purpose.
    """
    def function_decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            nonlocal attributes
            attributes = attributes if attributes is not None else {}
            attributes[KnownMetricAttributes.FUNCTION_NAME] = f.__name__ if hasattr(f, '__name__') else name
            fname = attributes[KnownMetricAttributes.FUNCTION_NAME]
            update_counter(1, name, taxonomy, unit=MetricUnits.CALLS, description=f"Number of times {fname} is called.", attributes=attributes)
            return f(*args, **kwargs)
        return wrapper
    return function_decorator
