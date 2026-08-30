"""
This module contains the code for the datastream published by the example sensor driver service.
"""
from artie_util import constants
from artie_util import artie_logging as alog
from artie_util import artie_time
from artie_service_client import pubsub
import os
import threading
import time

def stream(stop_event: threading.Event, certfpath: str, keyfpath: str, service_simple_name: str, imu_id: str, freq_hz=1.0):
    use_ssl = os.getenv(constants.ArtieEnvVariables.ARTIE_PUBSUB_USE_SSL, 'false').lower() == 'true'
    topic_name = f"{service_simple_name}.sensor-imu-v1.{imu_id}"
    alog.info(f"Starting datastream for topic {topic_name} with frequency {freq_hz} Hz")
    with pubsub.ArtieStreamPublisher(topic_name, service_simple_name, encrypt=use_ssl, certfpath=certfpath, keyfpath=keyfpath) as publisher:
        while True:
            # Publish dummy data
            data = {
                "accelerometer": (0.0, 0.0, 9.8),
                "gyroscope": (0.0, 0.0, 0.0),
                "magnetometer": None,
                "timestamp": artie_time.now_str(),
            }
            publisher.publish(data)

            # Wait for stop signal or timeout
            if stop_event.wait(timeout=1.0 / freq_hz):
                alog.info(f"Stopping datastream for topic {topic_name}")
                break
