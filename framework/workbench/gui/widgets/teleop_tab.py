"""
Teleop tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets


class TeleopTab(QtWidgets.QWidget):
    """Teleoperation tab for manual control of Artie"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
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
