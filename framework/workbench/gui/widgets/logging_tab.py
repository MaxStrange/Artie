"""
Logging tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets


class LoggingTab(QtWidgets.QWidget):
    """Logging tab for live logs and historical queries"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
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
