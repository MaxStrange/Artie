"""
Teleop tab widget for Artie Workbench
"""
from artie_tooling import artie_profile
from PyQt6 import QtWidgets
from model import settings


class TeleopTab(QtWidgets.QWidget):
    """Teleoperation tab for manual control of Artie"""
    
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
        """Setup the teleop tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        control_group = QtWidgets.QGroupBox("Manual Control")
        control_layout = QtWidgets.QVBoxLayout(control_group)
        
        info_label = QtWidgets.QLabel("Manual control interface for Artie")
        control_layout.addWidget(info_label)
        
        # Placeholder for control widgets
        control_text = QtWidgets.QTextEdit()
        control_text.setPlaceholderText("Teleop controls will appear here...")
        control_layout.addWidget(control_text)
        
        layout.addWidget(control_group)
