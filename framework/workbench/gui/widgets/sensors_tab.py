"""
Sensors tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets


class SensorsTab(QtWidgets.QWidget):
    """Sensors tab for displaying live sensor data"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the sensors tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        sensor_group = QtWidgets.QGroupBox("Sensor Data Stream")
        sensor_layout = QtWidgets.QVBoxLayout(sensor_group)
        
        sensor_text = QtWidgets.QTextBrowser()
        sensor_text.setPlaceholderText("Live sensor data will appear here...")
        sensor_layout.addWidget(sensor_text)
        
        layout.addWidget(sensor_group)
