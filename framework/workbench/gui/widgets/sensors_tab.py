"""
Sensors tab widget for Artie Workbench
"""
from artie_tooling import artie_profile
from PyQt6 import QtWidgets, QtCore
from model import settings
from .status_icon import StatusGrid


class SensorsTab(QtWidgets.QWidget):
    """Sensors tab for displaying live sensor data"""
    
    refresh_status_request_signal = QtCore.pyqtSignal()
    """Requests that we refresh statuses manually."""

    def __init__(self, parent, settings: settings.WorkbenchSettings, profile: artie_profile.ArtieProfile):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        
        self._setup_ui()

        # Connect to parent signals
        self.parent().profile_switched_signal.connect(self.on_profile_switched)
        self.parent().settings_changed_signal.connect(self.on_settings_changed)
        
        # Initial load
        self._refresh_status()

    def on_profile_switched(self, profile: artie_profile.ArtieProfile):
        """Handle profile switch events"""
        self.profile = profile
        self._refresh_status()

    def on_settings_changed(self, settings: settings.WorkbenchSettings):
        """Handle settings change events"""
        self.settings = settings

    def on_sensors_updated(self, sensor_statuses: list):
        """Handle sensors status update"""
        # Clear existing icons
        self.sensor_grid.clear_icons()
        
        # Add status icons for each sensor
        for sensor_status in sensor_statuses:
            name = sensor_status.sensor.name
            details = {
                "type": sensor_status.sensor.type,
                "bus": sensor_status.sensor.bus,
                "message": sensor_status.message
            }
            
            self.sensor_grid.add_status_icon(name, sensor_status.operational_status, details)
    
    def on_error(self, module: str, error: str):
        """Handle status fetch errors"""
        # TODO
        if module == "sensors":
            pass
    
    def _setup_ui(self):
        """Setup the sensors tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Refresh button
        refresh_layout = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh Status")
        refresh_button.clicked.connect(self._refresh_status)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Sensor status section
        status_group = QtWidgets.QGroupBox("Sensor Status")
        status_layout = QtWidgets.QVBoxLayout(status_group)
        
        self.sensor_grid = StatusGrid()
        sensor_scroll = QtWidgets.QScrollArea()
        sensor_scroll.setWidget(self.sensor_grid)
        sensor_scroll.setWidgetResizable(True)
        sensor_scroll.setMinimumHeight(150)
        status_layout.addWidget(sensor_scroll)
        
        layout.addWidget(status_group)
        
        # Live sensor data section
        data_group = QtWidgets.QGroupBox("Live Sensor Data Stream")
        data_layout = QtWidgets.QVBoxLayout(data_group)
        
        sensor_text = QtWidgets.QTextBrowser()
        sensor_text.setPlaceholderText("Live sensor data will appear here...")
        data_layout.addWidget(sensor_text)
        
        layout.addWidget(data_group)
    
    def _refresh_status(self):
        """Force a status update."""
        self.refresh_status_request_signal.emit()
