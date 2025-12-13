"""
Logging tab widget for Artie Workbench

This tab provides live log streaming and historical log querying functionality
by communicating with the Artie API Server, which in turn queries the Fluent Bit
log collector service.
"""
from artie_tooling import artie_profile
from PyQt6 import QtWidgets, QtCore
from model import settings
from comms import api_server


class LoggingTab(QtWidgets.QWidget):
    """Logging tab for live logs and historical queries"""
    
    def __init__(self, parent, current_settings: settings.WorkbenchSettings, profile: artie_profile.ArtieProfile):
        super().__init__(parent)
        self.settings = current_settings
        self.profile = profile
        self.api_client = api_server.ArtieApiClient(profile) if profile else None
        self._setup_ui()

        # Connect to parent signals
        self.parent().profile_switched_signal.connect(self.on_profile_switched)
        self.parent().settings_changed_signal.connect(self.on_settings_changed)
        
        # Set up live log refresh timer
        self.live_timer = QtCore.QTimer(self)
        self.live_timer.timeout.connect(self._refresh_live_logs)
        self.live_timer.start(5000)  # Refresh every 5 seconds

    def on_profile_switched(self, profile: artie_profile.ArtieProfile):
        """Handle profile switch events"""
        self.profile = profile
        self.api_client = api_server.ArtieApiClient(profile) if profile else None
        self.live_text.clear()
        self.history_text.clear()

    def on_settings_changed(self, current_settings: settings.WorkbenchSettings):
        """Handle settings change events"""
        self.settings = current_settings
    
    def _setup_ui(self):
        """Setup the logging tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Live logging section
        live_group = QtWidgets.QGroupBox("Live Logs")
        live_layout = QtWidgets.QVBoxLayout(live_group)
        
        # Live log controls
        live_controls = QtWidgets.QHBoxLayout()
        
        self.live_service_combo = QtWidgets.QComboBox()
        self.live_service_combo.addItem("All Services", None)
        live_controls.addWidget(QtWidgets.QLabel("Service:"))
        live_controls.addWidget(self.live_service_combo)
        
        self.live_level_combo = QtWidgets.QComboBox()
        self.live_level_combo.addItems(["All Levels", "debug", "info", "warning", "error"])
        live_controls.addWidget(QtWidgets.QLabel("Level:"))
        live_controls.addWidget(self.live_level_combo)
        
        self.live_refresh_button = QtWidgets.QPushButton("Refresh Now")
        self.live_refresh_button.clicked.connect(self._refresh_live_logs)
        live_controls.addWidget(self.live_refresh_button)
        
        self.live_clear_button = QtWidgets.QPushButton("Clear")
        self.live_clear_button.clicked.connect(lambda: self.live_text.clear())
        live_controls.addWidget(self.live_clear_button)
        
        live_controls.addStretch()
        live_layout.addLayout(live_controls)
        
        self.live_text = QtWidgets.QTextBrowser()
        self.live_text.setPlaceholderText("Live logs will appear here...")
        live_layout.addWidget(self.live_text)
        
        layout.addWidget(live_group)
        
        # Historical logging section
        history_group = QtWidgets.QGroupBox("Query Logs")
        history_layout = QtWidgets.QVBoxLayout(history_group)
        
        # Query controls
        query_controls = QtWidgets.QFormLayout()
        
        self.query_service_combo = QtWidgets.QComboBox()
        self.query_service_combo.addItem("All Services", None)
        query_controls.addRow("Service:", self.query_service_combo)
        
        self.query_level_combo = QtWidgets.QComboBox()
        self.query_level_combo.addItems(["All Levels", "debug", "info", "warning", "error"])
        query_controls.addRow("Level:", self.query_level_combo)
        
        self.query_message_input = QtWidgets.QLineEdit()
        self.query_message_input.setPlaceholderText("Search in message text...")
        query_controls.addRow("Message Contains:", self.query_message_input)
        
        self.query_limit_spin = QtWidgets.QSpinBox()
        self.query_limit_spin.setRange(10, 10000)
        self.query_limit_spin.setValue(1000)
        self.query_limit_spin.setSuffix(" logs")
        query_controls.addRow("Limit:", self.query_limit_spin)
        
        history_layout.addLayout(query_controls)
        
        query_button_layout = QtWidgets.QHBoxLayout()
        self.query_button = QtWidgets.QPushButton("Query Logs")
        self.query_button.clicked.connect(self._query_logs)
        query_button_layout.addWidget(self.query_button)
        
        self.query_clear_button = QtWidgets.QPushButton("Clear Results")
        self.query_clear_button.clicked.connect(lambda: self.history_text.clear())
        query_button_layout.addWidget(self.query_clear_button)
        
        query_button_layout.addStretch()
        history_layout.addLayout(query_button_layout)
        
        self.history_text = QtWidgets.QTextBrowser()
        self.history_text.setPlaceholderText("Query results will appear here...")
        history_layout.addWidget(self.history_text)
        
        layout.addWidget(history_group)
        
        # Load available services
        self._load_services()
    
    def _load_services(self):
        """Load available services from the API"""
        if not self.api_client:
            return
        
        err, services = self.api_client.get_log_services()
        if err:
            return
        
        # Update both combo boxes
        for combo in [self.live_service_combo, self.query_service_combo]:
            current_text = combo.currentText()
            combo.clear()
            combo.addItem("All Services", None)
            for service in services:
                combo.addItem(service, service)
            
            # Restore previous selection if it exists
            index = combo.findText(current_text)
            if index >= 0:
                combo.setCurrentIndex(index)
    
    def _refresh_live_logs(self):
        """Refresh live logs from the API"""
        if not self.api_client:
            return
        
        # Get selected filters
        service = self.live_service_combo.currentData()
        level_text = self.live_level_combo.currentText()
        level = None if level_text == "All Levels" else level_text
        
        # Query last 60 seconds of logs
        err, data = self.api_client.get_live_logs(seconds=60, level=level, service=service)
        
        if err:
            self.live_text.append(f"<span style='color: red;'>Error: {err}</span>")
            return
        
        if not data.get('success'):
            self.live_text.append(f"<span style='color: red;'>Error: {data.get('error')}</span>")
            return
        
        logs = data.get('logs', [])
        
        # Clear and display logs
        self.live_text.clear()
        for log in logs:
            self._append_log_entry(self.live_text, log)
    
    def _query_logs(self):
        """Query historical logs"""
        if not self.api_client:
            return
        
        # Get query parameters
        service = self.query_service_combo.currentData()
        level_text = self.query_level_combo.currentText()
        level = None if level_text == "All Levels" else level_text
        message_contains = self.query_message_input.text() or None
        limit = self.query_limit_spin.value()
        
        # Query logs (no time filter for now - gets recent logs)
        err, data = self.api_client.query_logs(
            level=level,
            service=service,
            message_contains=message_contains,
            limit=limit
        )
        
        if err:
            self.history_text.append(f"<span style='color: red;'>Error: {err}</span>")
            return
        
        if not data.get('success'):
            self.history_text.append(f"<span style='color: red;'>Error: {data.get('error')}</span>")
            return
        
        logs = data.get('logs', [])
        count = data.get('count', 0)
        truncated = data.get('truncated', False)
        
        # Display results
        self.history_text.clear()
        self.history_text.append(f"<b>Found {count} log entries{' (truncated)' if truncated else ''}</b><br>")
        
        for log in logs:
            self._append_log_entry(self.history_text, log)
    
    def _append_log_entry(self, text_widget: QtWidgets.QTextBrowser, log: dict):
        """Append a formatted log entry to the text widget"""
        timestamp = log.get('timestamp', log.get('date', ''))
        level = log.get('level', 'info')
        service = log.get('service', 'unknown')
        message = log.get('message', '')
        
        # Color code by level
        level_colors = {
            'debug': '#808080',
            'info': '#0000FF',
            'warning': '#FFA500',
            'error': '#FF0000'
        }
        color = level_colors.get(level.lower(), '#000000')
        
        html = f"<span style='color: {color};'>[{timestamp}] [{service}] [{level.upper()}] {message}</span><br>"
        text_widget.append(html)
