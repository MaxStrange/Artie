"""
Logging tab widget for Artie Workbench

TODO:

* The logging mechanics in Artie work like this:
    - There is a Fluent Bit pod, which collects logs and currently just pushes them to stdout.
      The fluent bit pod accepts logs pushed to it from each other pod via Artie logging library.
    - There is a Prometheus pod, which collects metrics and currently stores them in /data inside
      the Docker container (we need to update the Helm chart to actually map a physical drive to this directory).
      Prometheus reaches out to each pod, which expose their metrics via a server thread, and scrapes them
      periodically. Prometheus has a very nice metrics viewer API for collecting and displaying the information.
* TODO: Update fluent bit configuration to store logs to disk
* TODO: Update fluent bit configuration to allow API server to query the logs
* TODO: Update pod configuration for fluent bit pod to mount a directory
* TODO: Update pod configuration for prometheus pod to mount a directory
* TODO: Require a compute node for at least log storing purposes
* TODO: Update Artie API Server to include an API for retrieving all logs from within the past X seconds
* TODO: Update Artie API Server to include an API for querying logs
* TODO: Update Artie API Server to include a set of HTTP methods for querying metrics (see the Prometheus documentation for examples)
* TODO: Update this file to make use of Artie API Server for log querying and "live" streaming.
        The interface to the API server might make sense as a separate file in the comms directory, but not sure.
* TODO: Add another widget to the main window, similar to this tab, but instead it should be for metrics.

"""
from PyQt6 import QtWidgets
from model import artie_profile
from model import settings


class LoggingTab(QtWidgets.QWidget):
    """Logging tab for live logs and historical queries"""
    
    def __init__(self, parent, settings: settings.WorkbenchSettings, profile: artie_profile.ArtieProfile):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        self._setup_ui()

        # Connect to parent signals
        self.parent().profile_switched_signal.connect(self.on_profile_switched)
        self.parent().settings_changed_signal.connect(self.on_settings_changed)

    def on_profile_switched(self, profile: artie_profile.ArtieProfile):
        """Handle profile switch events"""
        self.profile = profile

    def on_settings_changed(self, settings: settings.WorkbenchSettings):
        """Handle settings change events"""
        self.settings = settings
    
    def _setup_ui(self):
        """Setup the logging tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Live logging section
        live_group = QtWidgets.QGroupBox("Live Logs")
        live_layout = QtWidgets.QVBoxLayout(live_group)
        
        live_text = QtWidgets.QTextBrowser()
        live_text.setPlaceholderText("Live logs and telemetry will appear here...")
        live_layout.addWidget(live_text)
        
        layout.addWidget(live_group)
        
        # Historical logging section
        history_group = QtWidgets.QGroupBox("Query Logs")
        history_layout = QtWidgets.QVBoxLayout(history_group)
        
        query_layout = QtWidgets.QHBoxLayout()
        query_label = QtWidgets.QLabel("Search:")
        query_input = QtWidgets.QLineEdit()
        query_button = QtWidgets.QPushButton("Query")
        query_layout.addWidget(query_label)
        query_layout.addWidget(query_input)
        query_layout.addWidget(query_button)
        
        history_layout.addLayout(query_layout)
        
        history_text = QtWidgets.QTextBrowser()
        history_text.setPlaceholderText("Query results will appear here...")
        history_layout.addWidget(history_text)
        
        layout.addWidget(history_group)
