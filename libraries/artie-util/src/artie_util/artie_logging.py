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

# A cache of metrics (name: meter)
_metrics = {}

# If we fail to configure metrics, we cannot use them at all
METRICS_CONFIGURED = True

@enum.unique
class Units(enum.StrEnum):
    """
    The various units for metrics.
    """
    BYTES = "bytes"
    SECONDS = "s"
    TIMES = "times"

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
            'processName': <the name of the process>,
            'threadName': <the name of the thread>,
            'timestamp': <timestamp in asctime format from Python logging library>,
            'serviceName': <the name of the service>,
            'artieID': <the ID of the Artie that is logging>
        }
        """
        msg_dict = {
            'level': record.levelname if hasattr(record, 'levelname') else 'UNKNOWN',
            'message': record.getMessage() if hasattr(record, 'getMessage') else '',
            'processName': record.processName if hasattr(record, 'processName') else 'Unknown',
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
    logging.basicConfig(format=format, level=getattr(logging, loglevel), force=True, handlers=handlers)

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

def _add_artie_id_attribute(obs):
    if obs.attributes is None:
        obs.attributes = {}
    obs.attributes['artie.id'] = ARTIE_ID

def _callback_wrapper(callback, *args, **kwargs):
    if inspect.isgeneratorfunction(callback):
        for obs in callback(*args, **kwargs):
            _add_artie_id_attribute(obs)
            yield obs
    else:
        observations = [_add_artie_id_attribute(obs) for obs in callback(*args, **kwargs)]
        return observations

def create_async_counter(callback, name: str, unit: MetricUnits, description: str):
    """
    Create an asynchronous counter which will increment by the value given by `callback`'s return value
    every time the metrics are scraped by the endpoint.

    If this is called more than once for a given `name`, we remove the old metric and
    replace it with the new one.

    `callback` must take an opentelemetry.metrics.CallbackOptions argument and
    return a sequence of opentelemetry.metrics.Observation objects.

    `callback` can be a generator which yields one Observation object at a time.

    `callback` should make use of the `timeout_millis` property on the `CallbackOptions` object passed to it.

    Any Observations returned by `callback` will automatically have 'artie.id' appended to their attributes.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)

    global _metrics
    if name in _metrics:
        del _metrics[name]
        _metrics[name] = None

    async_counter = meter.create_observable_counter(name, [functools.partial(_callback_wrapper, callback)], unit, description)
    _metrics[name] = async_counter

def create_async_gauge(callback, name: str, unit: MetricUnits, description: str):
    """
    Same as `create_async_counter`, except we create a gauge, which simply returns its
    value at the time of reading. For example, you might have a 'fuel' metric,
    which returns the amount of fuel currently in the tank whenever the callback is called.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)

    global _metrics
    if name in _metrics:
        del _metrics[name]
        _metrics[name] = None

    gauge = meter.create_observable_gauge(name, [functools.partial(_callback_wrapper, callback)], unit, description)
    _metrics[name] = gauge

def create_async_updown_counter(callback, name: str, unit: MetricUnits, description: str):
    """
    Same as `create_async_counter`, but for an up-down counter.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)

    global _metrics
    if name in _metrics:
        del _metrics[name]
        _metrics[name] = None

    updown = meter.create_observable_up_down_counter(name, [functools.partial(_callback_wrapper, callback)], unit, description)
    _metrics[name] = updown

def update_counter(increment: int | float, name: str, unit:MetricUnits=None, description:str=None, attributes: Dict[str, str]=None):
    """
    Create a counter if it doesn't already exist, otherwise get the counter with the given `name`,
    then increment (or initialize) by `increment`.

    Args
    ----
    - increment: The value to initialize the counter to if it is new, otherwise the value by which we increment.
    - name: The name of the counter.
    - unit: The measurement unit. Only used if we create a new counter.
    - description: A description of the counter. Only used if we create a new counter.
    - attributes: A dict of {str: str} to add as metadata to the metric when updating it.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)

    global _metrics
    if name in _metrics:
        counter = _metrics[name]
    else:
        counter = meter.create_counter(name, unit, description)
        _metrics[name] = counter

    attributes = {} if not attributes else attributes
    attributes['artie.id'] = ARTIE_ID
    counter.add(increment, attributes=attributes)

def update_histogram(amount: int | float, name: str, unit:MetricUnits=None, description:str=None, attributes: Dict[str, str]=None, bins=None):
    """
    Same as `update_counter`, but a histogram instead.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)

    global _metrics
    if name in _metrics:
        histogram = _metrics[name]
    else:
        histogram = meter.create_histogram(name, unit, description)
        _metrics[name] = histogram

    attributes = {} if not attributes else attributes
    attributes['artie.id'] = ARTIE_ID
    histogram.record(amount, attributes=attributes)

def update_updown_counter(amount: int | float, name: str, unit:MetricUnits=None, description:str=None, attributes: Dict[str, str]=None):
    """
    Same as `update_counter`, but an up-down counter instead.
    """
    if not METRICS_CONFIGURED:
        return

    meter = metrics.get_meter(GLOBAL_METER_NAME)

    global _metrics
    if name in _metrics:
        updown = _metrics[name]
    else:
        updown = meter.create_up_down_counter(name, unit, description)
        _metrics[name] = updown

    attributes = {} if not attributes else attributes
    attributes['artie.id'] = ARTIE_ID
    updown.add(amount, attributes=attributes)

def function_counter(name: str, attributes=None):
    """
    A decorator for creating a function call counter. It increments
    every time the decorated function is called.
    """
    def function_decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            nonlocal attributes
            attributes = attributes if attributes is not None else {}
            attributes['function-name'] = f.__name__ if hasattr(f, '__name__') else name
            update_counter(1, f"{SERVICE_NAME}.functions.{name}", unit="calls", description=f"Number of times {name} is called.", attributes=attributes)
            return f(*args, **kwargs)
        return wrapper
    return function_decorator
