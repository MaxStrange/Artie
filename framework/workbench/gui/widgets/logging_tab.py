"""
Logging tab widget for Artie Workbench
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
