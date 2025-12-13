"""
Hardware tab widget for Artie Workbench
"""
from artie_tooling import artie_profile
from PyQt6 import QtWidgets, QtCore
from model import settings
from . import status_icon


class HardwareTab(QtWidgets.QWidget):
    """Hardware monitoring tab showing SBCs, MCUs, and actuators"""

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
        
    def on_profile_switched(self, profile: artie_profile.ArtieProfile):
        """Handle profile switch events"""
        self.profile = profile
        self._refresh_status()

    def on_settings_changed(self, settings: settings.WorkbenchSettings):
        """Handle settings change events"""
        self.settings = settings

    def on_nodes_updated(self, node_statuses: list):
        """Handle nodes status update"""
        # Clear existing icons
        self.sbc_grid.clear_icons()
        
        # Add status icons for each node
        for node_status in node_statuses:
            name = f"{node_status.sbc.name} ({node_status.role})"
            details = {
                "role": node_status.role,
                "artie": node_status.artie,
                "architecture": node_status.sbc.architecture,
                "buses": node_status.sbc.buses
            }
            if node_status.error:
                details["error"] = node_status.error
            
            self.sbc_grid.add_status_icon(name, node_status.status, details)
    
    def on_mcus_updated(self, mcu_statuses: list):
        """Handle MCUs status update"""
        # Clear existing icons
        self.mcu_grid.clear_icons()
        
        # Add status icons for each MCU
        for mcu_status in mcu_statuses:
            name = mcu_status.mcu.name
            details = {
                "buses": mcu_status.mcu.buses,
                "message": mcu_status.heartbeat_message
            }
            
            self.mcu_grid.add_status_icon(name, mcu_status.heartbeat_status, details)
    
    def on_actuators_updated(self, actuator_statuses: list):
        """Handle actuators status update"""
        # Clear existing icons
        self.actuator_grid.clear_icons()
        
        # Add status icons for each actuator
        for actuator_status in actuator_statuses:
            name = actuator_status.actuator.name
            details = {
                "type": actuator_status.actuator.type,
                "bus": actuator_status.actuator.bus,
                "message": actuator_status.message
            }
            
            self.actuator_grid.add_status_icon(name, actuator_status.status, details)
    
    def on_error(self, module: str, error: str):
        """Handle status fetch errors"""
        # TODO
        match module:
            case "nodes":
                pass
            case "mcus":
                pass
            case "actuators":
                pass

    def _refresh_status(self):
        """Force a status update."""
        self.refresh_status_request_signal.emit()
    
    def _setup_ui(self):
        """Setup the hardware tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Refresh button
        refresh_layout = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh Status")
        refresh_button.clicked.connect(self._refresh_status)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Single board computers section
        sbc_group = QtWidgets.QGroupBox("Single Board Computers (K3S Nodes)")
        sbc_layout = QtWidgets.QVBoxLayout(sbc_group)
        
        self.sbc_grid = status_icon.StatusGrid()
        sbc_scroll = QtWidgets.QScrollArea()
        sbc_scroll.setWidget(self.sbc_grid)
        sbc_scroll.setWidgetResizable(True)
        sbc_scroll.setMinimumHeight(120)
        sbc_layout.addWidget(sbc_scroll)
        
        layout.addWidget(sbc_group)
        
        # Microcontrollers section
        mcu_group = QtWidgets.QGroupBox("Microcontrollers")
        mcu_layout = QtWidgets.QVBoxLayout(mcu_group)
        
        self.mcu_grid = status_icon.StatusGrid()
        mcu_scroll = QtWidgets.QScrollArea()
        mcu_scroll.setWidget(self.mcu_grid)
        mcu_scroll.setWidgetResizable(True)
        mcu_scroll.setMinimumHeight(120)
        mcu_layout.addWidget(mcu_scroll)
        
        layout.addWidget(mcu_group)
        
        # Actuators section
        actuator_group = QtWidgets.QGroupBox("Actuators")
        actuator_layout = QtWidgets.QVBoxLayout(actuator_group)
        
        self.actuator_grid = status_icon.StatusGrid()
        actuator_scroll = QtWidgets.QScrollArea()
        actuator_scroll.setWidget(self.actuator_grid)
        actuator_scroll.setWidgetResizable(True)
        actuator_scroll.setMinimumHeight(120)
        actuator_layout.addWidget(actuator_scroll)
        
        layout.addWidget(actuator_group)
    