"""
Status fetcher for querying Artie Tool status command
"""
from artie_tooling import artie_profile
from artie_tooling import hw_config
from util import qutil
from PyQt6 import QtCore
from model import settings
from comms import tool
import queue
import time


class NodeStatus:
    """Status information for a single node"""
    def __init__(self, sbc: hw_config.SBC, status: str, role: str = "unknown", artie: str = "unknown", labels: dict = None, error: str = None):
        self.sbc = sbc
        self.status = status
        self.role = role
        self.artie = artie
        self.labels = labels or {}
        self.error = error


class MCUStatus:
    """Status information for a single MCU"""
    def __init__(self, mcu: hw_config.MCU, heartbeat_status: str = "unknown", heartbeat_message: str = ""):
        self.mcu = mcu
        self.heartbeat_status = heartbeat_status
        self.heartbeat_message = heartbeat_message


class ActuatorStatus:
    """Status information for a single actuator"""
    def __init__(self, actuator: hw_config.Actuator, status: str = "unknown", message: str = ""):
        self.actuator = actuator
        self.status = status
        self.message = message


class SensorStatus:
    """Status information for a single sensor"""
    def __init__(self, sensor: hw_config.Sensor, operational_status: str = "unknown", message: str = ""):
        self.sensor = sensor
        self.operational_status = operational_status
        self.message = message


class StatusFetcher(QtCore.QObject):
    """Fetches status information from Artie Tool periodically, emitting its information on various signals."""
    
    # Signals for status updates
    nodes_updated_signal = QtCore.pyqtSignal(list)  # list[NodeStatus]
    pods_updated_signal = QtCore.pyqtSignal(dict)  # Raw pod data for now
    mcus_updated_signal = QtCore.pyqtSignal(list)  # list[MCUStatus]
    actuators_updated_signal = QtCore.pyqtSignal(list)  # list[ActuatorStatus]
    sensors_updated_signal = QtCore.pyqtSignal(list)  # list[SensorStatus]
    error_occurred_signal = QtCore.pyqtSignal(str, str)
    hw_config_updated_signal = QtCore.pyqtSignal(hw_config.HWConfig)

    # Signal to alert main window (and whoever else) that we are closing
    closed_signal = QtCore.pyqtSignal()
    
    def __init__(self, parent, profile: artie_profile.ArtieProfile, current_settings: settings.WorkbenchSettings):
        super().__init__(parent)
        self.profile = profile
        self.settings = current_settings
        self.tool_invoker = tool.ArtieToolInvoker(profile) if profile else None
        self.hw_config_cache = None

        # Add the global profile and settings signals
        self.parent().profile_switched_signal.connect(self.set_profile)
        self.parent().settings_changed_signal.connect(self.on_settings_changed)

        # Create job queues for each thread
        self.hw_config_q = queue.Queue()
        self.nodes_q = queue.Queue()
        self.pods_q = queue.Queue()
        self.mcus_q = queue.Queue()
        self.actuators_q = queue.Queue()
        self.sensors_q = queue.Queue()

        # Create dedicated threads for each status type
        self.hw_config_thread = HWConfigThread(self, self.hw_config_q, self.tool_invoker)
        self.nodes_thread = NodesStatusThread(self, self.nodes_q, self.tool_invoker)
        self.pods_thread = PodsStatusThread(self, self.pods_q, self.tool_invoker)
        self.mcus_thread = MCUsStatusThread(self, self.mcus_q, self.tool_invoker)
        self.actuators_thread = ActuatorsStatusThread(self, self.actuators_q, self.tool_invoker)
        self.sensors_thread = SensorsStatusThread(self, self.sensors_q, self.tool_invoker)
        self.threads = [
            self.hw_config_thread,
            self.nodes_thread,
            self.pods_thread,
            self.mcus_thread,
            self.actuators_thread,
            self.sensors_thread,
        ]
        self.queues = [
            self.hw_config_q,
            self.nodes_q,
            self.pods_q,
            self.mcus_q,
            self.actuators_q,
            self.sensors_q,
        ]
        self.received_stopped_signals = []

        # Connect thread signals
        self.hw_config_thread.finished_signal.connect(self._on_hw_config_fetched)
        self.hw_config_thread.error_signal.connect(lambda err: self.error_occurred_signal.emit("hw_config", err))
        self.hw_config_thread.stopped_signal.connect(self.handle_thread_exited)
        
        self.nodes_thread.finished_signal.connect(lambda statuses: self.nodes_updated_signal.emit(statuses))
        self.nodes_thread.error_signal.connect(lambda err: self.error_occurred_signal.emit("nodes", err))
        self.nodes_thread.stopped_signal.connect(self.handle_thread_exited)
        
        self.pods_thread.finished_signal.connect(lambda data: self.pods_updated_signal.emit(data))
        self.pods_thread.error_signal.connect(lambda err: self.error_occurred_signal.emit("pods", err))
        self.pods_thread.stopped_signal.connect(self.handle_thread_exited)

        self.mcus_thread.finished_signal.connect(lambda statuses: self.mcus_updated_signal.emit(statuses))
        self.mcus_thread.error_signal.connect(lambda err: self.error_occurred_signal.emit("mcus", err))
        self.mcus_thread.stopped_signal.connect(self.handle_thread_exited)
        
        self.actuators_thread.finished_signal.connect(lambda statuses: self.actuators_updated_signal.emit(statuses))
        self.actuators_thread.error_signal.connect(lambda err: self.error_occurred_signal.emit("actuators", err))
        self.actuators_thread.stopped_signal.connect(self.handle_thread_exited)

        self.sensors_thread.finished_signal.connect(lambda statuses: self.sensors_updated_signal.emit(statuses))
        self.sensors_thread.error_signal.connect(lambda err: self.error_occurred_signal.emit("sensors", err))
        self.sensors_thread.stopped_signal.connect(self.handle_thread_exited)
        
        # Start all threads
        for t in self.threads:
            t.start()

    def close(self):
        """Close this object and stop all threads."""
        for t in self.threads:
            t.stop()

    def handle_thread_exited(self, name):
        """Handle thread exiting."""
        self.received_stopped_signals.append(name)
        if len(set(self.received_stopped_signals)) == len(self.threads):
            # Everyone has stopped. Join all the threads.
            for t in self.threads:
                t.wait()

            # Alert main window that we are closing
            self.closed_signal.emit()

    def fetch_nodes_status(self):
        """Manually initiate a node status fetch instead of waiting for the next one."""
        self.nodes_q.put("get")

    def fetch_mcus_status(self):
        """Manually initiate an MCU status fetch instead of waiting for the next one."""
        self.mcus_q.put("get")

    def fetch_actuators_status(self):
        """Manually initiate an actuator status fetch instead of waiting for the next one."""
        self.actuators_q.put("get")

    def fetch_pods_status(self):
        """Manually initiate a pod status fetch instead of waiting for the next one."""
        self.pods_q.put("get")

    def fetch_sensors_status(self):
        """Manually initiate a sensor status fetch instead of waiting for the next one."""
        self.sensors_q.put("get")

    def on_settings_changed(self, new_settings: settings.WorkbenchSettings):
        """Handle settings changes"""
        self.settings = new_settings
        self.tool_invoker = tool.ArtieToolInvoker(self.profile)
        self.hw_config_cache = None
        
        # Update refresh rate for all threads
        for t in self.threads:
            t.set_refresh_rate(new_settings.status_refresh_rate_s)

    def set_profile(self, profile: artie_profile.ArtieProfile):
        """Update the Artie profile"""
        self.profile = profile
        self.tool_invoker = tool.ArtieToolInvoker(profile)
        self.hw_config_cache = None
        for t in self.threads:
            t.set_tool_invoker(self.tool_invoker)

    def _on_hw_config_fetched(self, config: hw_config.HWConfig):
        """Handle fetched hardware configuration"""
        self.hw_config_cache = config
        self.hw_config_updated_signal.emit(config)
    

class _StatusThread(QtCore.QThread):
    """Base class for all the status thread workers."""
    error_signal = QtCore.pyqtSignal(str)
    """Emitted when there is an error fetching status."""

    stopped_signal = QtCore.pyqtSignal(str)
    """Emitted when the thread is stopped."""

    def __init__(self, parent: StatusFetcher, q: queue.Queue, tool_invoker: tool.ArtieToolInvoker|None):
        super().__init__(parent)
        self.job_queue = q
        self.status_fetcher = parent
        self.tool_invoker = tool_invoker
        self._running = True
        self._refresh_rate = parent.settings.status_refresh_rate_s

    def set_refresh_rate(self, rate_s: float):
        """Update the refresh rate"""
        self._refresh_rate = rate_s

    def set_tool_invoker(self, invoker: tool.ArtieToolInvoker):
        """Set self.tool_invoker."""
        self.tool_invoker = invoker
    
    def stop(self):
        """Stop the thread"""
        self._running = False
    
    def run(self):
        """Run the thread."""
        while self._running:
            # If something comes in on the queue, it just means that we want
            # to do our only job (the refresh job) sooner instead of later.
            qutil.get(self.job_queue, timeout_s=self._refresh_rate)
            if self.tool_invoker is not None:
                self._fetch_status()

        # Tell anyone who cares that the thread has exited
        self.stopped_signal.emit(type(self).__name__)

    def _fetch_status(self):
        raise NotImplementedError()

class HWConfigThread(_StatusThread):
    """Dedicated thread for periodically fetching hardware configuration"""

    finished_signal = QtCore.pyqtSignal(hw_config.HWConfig)

    def __init__(self, parent: StatusFetcher, q: queue.Queue, tool_invoker: tool.ArtieToolInvoker|None):
        super().__init__(parent, q, tool_invoker)

    def _fetch_status(self):
        """Fetch hardware configuration."""
        err, artie_hw_config = self.status_fetcher.tool_invoker.get_hw_config()
        if err:
            self.error_signal.emit(str(err))
            return

        self.finished_signal.emit(artie_hw_config)
        

class NodesStatusThread(_StatusThread):
    """Dedicated thread for periodically fetching nodes status"""

    finished_signal = QtCore.pyqtSignal(list)  # list[NodeStatus]

    def __init__(self, parent: StatusFetcher, q: queue.Queue, tool_invoker: tool.ArtieToolInvoker|None):
        super().__init__(parent, q, tool_invoker)

    def _fetch_status(self):
        """Fetch nodes status."""
        if not self.status_fetcher.hw_config_cache:
            return

        err, data = self.status_fetcher.tool_invoker.status_nodes()
        if err:
            self.error_signal.emit(str(err))
            return

        if not data.get("success", False):
            self.error_signal.emit(data.get("error", "Unknown error"))
            return

        try:
            nodes_data = data.get("data", {}).get("nodes", [])
            statuses = []
            
            # Match nodes data with SBC objects from hw_config
            for node_data in nodes_data:
                node_name = node_data.get("name", "")
                # Find matching SBC by comparing node name format: "<sbc-name>-<artie-name>"
                sbc = None
                for s in self.status_fetcher.hw_config_cache.sbcs:
                    if node_name.startswith(s.name):
                        sbc = s
                        break
                
                if sbc:
                    status = NodeStatus(
                        sbc=sbc,
                        status=node_data.get("status", "unknown"),
                        role=node_data.get("role", "unknown"),
                        artie=node_data.get("artie", "unknown"),
                        labels=node_data.get("labels", {}),
                        error=node_data.get("error")
                    )
                    statuses.append(status)
            
            self.finished_signal.emit(statuses)
        except Exception as e:
            self.error_signal.emit(f"Failed to parse nodes status: {e}")


class PodsStatusThread(_StatusThread):
    """Dedicated thread for periodically fetching pods status"""

    finished_signal = QtCore.pyqtSignal(dict)  # Raw pod data

    def __init__(self, parent: StatusFetcher, q: queue.Queue, tool_invoker: tool.ArtieToolInvoker|None):
        super().__init__(parent, q, tool_invoker)

    def _fetch_status(self):
        """Fetch pods status"""
        err, data = self.status_fetcher.tool_invoker.status_pods()
        if err:
            self.error_signal.emit(str(err))
            return

        if not data.get("success", False):
            self.error_signal.emit(data.get("error", "Unknown error"))
            return

        self.finished_signal.emit(data)


class MCUsStatusThread(_StatusThread):
    """Dedicated thread for periodically fetching MCUs status"""

    finished_signal = QtCore.pyqtSignal(list)

    def __init__(self, parent: StatusFetcher, q: queue.Queue, tool_invoker: tool.ArtieToolInvoker|None):
        super().__init__(parent, q, tool_invoker)

    def _fetch_status(self):
        """Fetch MCUs status"""
        if not self.status_fetcher.hw_config_cache:
            return

        err, data = self.status_fetcher.tool_invoker.status_mcus()
        if err:
            self.error_signal.emit(str(err))
            return

        if not data.get("success", False):
            self.error_signal.emit(data.get("error", "Unknown error"))
            return

        try:
            mcus_data = data.get("data", {}).get("mcus", [])
            statuses = []
            
            # Match MCU data with MCU objects from hw_config
            for mcu_data in mcus_data:
                mcu_name = mcu_data.get("name", "")
                mcu_obj = next((m for m in self.status_fetcher.hw_config_cache.mcus if m.name == mcu_name), None)
                
                if mcu_obj:
                    heartbeat = mcu_data.get("heartbeat", {})
                    status = MCUStatus(
                        mcu=mcu_obj,
                        heartbeat_status=heartbeat.get("status", "unknown"),
                        heartbeat_message=heartbeat.get("message", "")
                    )
                    statuses.append(status)
            
            self.finished_signal.emit(statuses)
        except Exception as e:
            self.error_signal.emit(f"Failed to parse MCUs status: {e}")


class ActuatorsStatusThread(_StatusThread):
    """Dedicated thread for periodically fetching actuators status"""

    finished_signal = QtCore.pyqtSignal(list)  # list[ActuatorStatus]

    def __init__(self, parent: StatusFetcher, q: queue.Queue, tool_invoker: tool.ArtieToolInvoker|None):
        super().__init__(parent, q, tool_invoker)

    def _fetch_status(self):
        """Fetch actuators status"""
        if not self.status_fetcher.hw_config_cache:
            return

        err, data = self.status_fetcher.tool_invoker.status_actuators()
        if err:
            self.error_signal.emit(str(err))
            return

        if not data.get("success", False):
            self.error_signal.emit(data.get("error", "Unknown error"))
            return

        try:
            actuators_data = data.get("data", {}).get("actuators", [])
            statuses = []
            
            # Match actuator data with Actuator objects from hw_config
            for actuator_data in actuators_data:
                actuator_name = actuator_data.get("name", "")
                actuator_obj = next((a for a in self.status_fetcher.hw_config_cache.actuators if a.name == actuator_name), None)
                
                if actuator_obj:
                    actuator_status = actuator_data.get("status", {})
                    status = ActuatorStatus(
                        actuator=actuator_obj,
                        status=actuator_status.get("status", "unknown"),
                        message=actuator_status.get("message", "")
                    )
                    statuses.append(status)
            
            self.finished_signal.emit(statuses)
        except Exception as e:
            self.error_signal.emit(f"Failed to parse actuators status: {e}")


class SensorsStatusThread(_StatusThread):
    """Dedicated thread for periodically fetching sensors status"""

    finished_signal = QtCore.pyqtSignal(list)  # list[SensorStatus]

    def __init__(self, parent: StatusFetcher, q: queue.Queue, tool_invoker: tool.ArtieToolInvoker|None):
        super().__init__(parent, q, tool_invoker)
    
    def _fetch_status(self):
        """Fetch sensors status"""
        if not self.status_fetcher.hw_config_cache:
            return

        err, data = self.status_fetcher.tool_invoker.status_sensors()
        if err:
            self.error_signal.emit(str(err))
            return

        if not data.get("success", False):
            self.error_signal.emit(data.get("error", "Unknown error"))
            return

        try:
            sensors_data = data.get("data", {}).get("sensors", [])
            statuses = []
            
            # Match sensor data with Sensor objects from hw_config
            for sensor_data in sensors_data:
                sensor_name = sensor_data.get("name", "")
                sensor_obj = next((s for s in self.status_fetcher.hw_config_cache.sensors if s.name == sensor_name), None)
                
                if sensor_obj:
                    sensor_status = sensor_data.get("status", {})
                    status = SensorStatus(
                        sensor=sensor_obj,
                        operational_status=sensor_status.get("operational", "unknown"),
                        message=sensor_status.get("message", "")
                    )
                    statuses.append(status)
            
            self.finished_signal.emit(statuses)
        except Exception as e:
            self.error_signal.emit(f"Failed to parse sensors status: {e}")
