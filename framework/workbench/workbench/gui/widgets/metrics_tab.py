"""
Metrics tab widget for Artie Workbench

This tab provides Prometheus metrics querying and visualization functionality
by communicating with the Artie API Server, which in turn queries Prometheus.
"""
from artie_tooling import artie_profile
from PyQt6 import QtWidgets, QtCore
from model import settings
from datetime import datetime, timedelta


class MetricsTab(QtWidgets.QWidget):
    """Metrics tab for querying and displaying Prometheus metrics"""
    
    def __init__(self, parent, current_settings: settings.WorkbenchSettings, profile: artie_profile.ArtieProfile):
        super().__init__(parent)
        self.settings = current_settings
        self.profile = profile

        # TODO: This GUI does not currently do anything. It is just a demo placeholder.
        self.api_client = None

        self._setup_ui()

        # Connect to parent signals
        self.parent().profile_switched_signal.connect(self.on_profile_switched)
        self.parent().settings_changed_signal.connect(self.on_settings_changed)

    def on_profile_switched(self, profile: artie_profile.ArtieProfile):
        """Handle profile switch events"""
        self.profile = profile
        # TODO: This is a demo
        self.api_client = None
        self.results_text.clear()

    def on_settings_changed(self, current_settings: settings.WorkbenchSettings):
        """Handle settings change events"""
        self.settings = current_settings
    
    def _setup_ui(self):
        """Setup the metrics tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Query section
        query_group = QtWidgets.QGroupBox("Query Metrics")
        query_layout = QtWidgets.QVBoxLayout(query_group)
        
        # Query type selection
        query_type_layout = QtWidgets.QHBoxLayout()
        query_type_layout.addWidget(QtWidgets.QLabel("Query Type:"))
        
        self.instant_radio = QtWidgets.QRadioButton("Instant Query")
        self.instant_radio.setChecked(True)
        self.instant_radio.toggled.connect(self._on_query_type_changed)
        query_type_layout.addWidget(self.instant_radio)
        
        self.range_radio = QtWidgets.QRadioButton("Range Query")
        self.range_radio.toggled.connect(self._on_query_type_changed)
        query_type_layout.addWidget(self.range_radio)
        
        query_type_layout.addStretch()
        query_layout.addLayout(query_type_layout)
        
        # PromQL query input
        query_input_layout = QtWidgets.QHBoxLayout()
        query_input_layout.addWidget(QtWidgets.QLabel("PromQL Query:"))
        self.query_input = QtWidgets.QLineEdit()
        self.query_input.setPlaceholderText("e.g., up or rate(http_requests_total[5m])")
        query_input_layout.addWidget(self.query_input)
        query_layout.addLayout(query_input_layout)
        
        # Range query controls (hidden by default)
        self.range_controls = QtWidgets.QWidget()
        range_controls_layout = QtWidgets.QFormLayout(self.range_controls)
        
        self.range_duration_spin = QtWidgets.QSpinBox()
        self.range_duration_spin.setRange(1, 1440)
        self.range_duration_spin.setValue(60)
        self.range_duration_spin.setSuffix(" minutes")
        range_controls_layout.addRow("Time Range:", self.range_duration_spin)
        
        self.range_step_input = QtWidgets.QLineEdit("15s")
        self.range_step_input.setPlaceholderText("e.g., 15s, 1m, 5m")
        range_controls_layout.addRow("Step:", self.range_step_input)
        
        self.range_controls.setVisible(False)
        query_layout.addWidget(self.range_controls)
        
        # Query button
        query_button_layout = QtWidgets.QHBoxLayout()
        self.query_button = QtWidgets.QPushButton("Execute Query")
        self.query_button.clicked.connect(self._execute_query)
        query_button_layout.addWidget(self.query_button)
        
        self.clear_button = QtWidgets.QPushButton("Clear Results")
        self.clear_button.clicked.connect(lambda: self.results_text.clear())
        query_button_layout.addWidget(self.clear_button)
        
        query_button_layout.addStretch()
        query_layout.addLayout(query_button_layout)
        
        layout.addWidget(query_group)
        
        # Common queries section
        common_group = QtWidgets.QGroupBox("Common Queries")
        common_layout = QtWidgets.QVBoxLayout(common_group)
        
        common_queries_layout = QtWidgets.QGridLayout()
        
        common_queries = [
            ("System Up", "up"),
            ("CPU Usage", "rate(process_cpu_seconds_total[5m])"),
            ("Memory Usage", "process_resident_memory_bytes"),
            ("HTTP Request Rate", "rate(http_requests_total[5m])"),
            ("Error Rate", "rate(http_requests_total{status=~\"5..\"}[5m])"),
            ("Scrape Duration", "scrape_duration_seconds"),
        ]
        
        for i, (label, query) in enumerate(common_queries):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda checked, q=query: self._set_query(q))
            common_queries_layout.addWidget(button, i // 3, i % 3)
        
        common_layout.addLayout(common_queries_layout)
        layout.addWidget(common_group)
        
        # Results section
        results_group = QtWidgets.QGroupBox("Results")
        results_layout = QtWidgets.QVBoxLayout(results_group)
        
        self.results_text = QtWidgets.QTextBrowser()
        self.results_text.setPlaceholderText("Query results will appear here...")
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        # Set stretch factors
        layout.setStretch(0, 0)  # Query section - fixed
        layout.setStretch(1, 0)  # Common queries - fixed
        layout.setStretch(2, 1)  # Results - expandable
    
    def _on_query_type_changed(self):
        """Handle query type radio button changes"""
        self.range_controls.setVisible(self.range_radio.isChecked())
    
    def _set_query(self, query: str):
        """Set the query input to a predefined query"""
        self.query_input.setText(query)
    
    def _execute_query(self):
        """Execute the metrics query"""
        if not self.api_client:
            self.results_text.append("<span style='color: red;'>Error: No API client available</span>")
            return
    