"""
Hardware tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets
from model import artie_profile
from model import settings


class HardwareTab(QtWidgets.QWidget):
    """Hardware monitoring tab showing SBCs, MCUs, and actuators"""
    
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
        """Setup the hardware tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Single board computers section
        sbc_group = QtWidgets.QGroupBox("Single Board Computers")
        sbc_layout = QtWidgets.QVBoxLayout(sbc_group)
        
        sbc_text = QtWidgets.QTextBrowser()
        sbc_text.setPlaceholderText("K3S node status will appear here...")
        sbc_layout.addWidget(sbc_text)
        
        layout.addWidget(sbc_group)
        
        # Microcontrollers section
        mcu_group = QtWidgets.QGroupBox("Microcontrollers")
        mcu_layout = QtWidgets.QVBoxLayout(mcu_group)
        
        mcu_text = QtWidgets.QTextBrowser()
        mcu_text.setPlaceholderText("MCU heartbeat status and firmware versions will appear here...")
        mcu_layout.addWidget(mcu_text)
        
        layout.addWidget(mcu_group)
        
        # Actuators section
        actuator_group = QtWidgets.QGroupBox("Actuators")
        actuator_layout = QtWidgets.QVBoxLayout(actuator_group)
        
        actuator_text = QtWidgets.QTextBrowser()
        actuator_text.setPlaceholderText("Actuator status from CAN bus will appear here...")
        actuator_layout.addWidget(actuator_text)
        
        layout.addWidget(actuator_group)
