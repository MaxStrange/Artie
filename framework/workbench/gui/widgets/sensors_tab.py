"""
Sensors tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets
from model import artie_profile
from model import settings


class SensorsTab(QtWidgets.QWidget):
    """Sensors tab for displaying live sensor data"""
    
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
        """Setup the sensors tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        sensor_group = QtWidgets.QGroupBox("Sensor Data Stream")
        sensor_layout = QtWidgets.QVBoxLayout(sensor_group)
        
        sensor_text = QtWidgets.QTextBrowser()
        sensor_text.setPlaceholderText("Live sensor data will appear here...")
        sensor_layout.addWidget(sensor_text)
        
        layout.addWidget(sensor_group)
