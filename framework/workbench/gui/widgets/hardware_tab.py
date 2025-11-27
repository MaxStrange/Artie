"""
Hardware tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets


class HardwareTab(QtWidgets.QWidget):
    """Hardware monitoring tab showing SBCs, MCUs, and actuators"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the hardware tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Single board computers section
        sbc_group = QtWidgets.QGroupBox("Single Board Computers")
        sbc_layout = QtWidgets.QVBoxLayout(sbc_group)
        
        sbc_text = QtWidgets.QTextBrowser()
        sbc_text.setPlaceholderText("K3S node status and Yocto image versions will appear here...")
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
