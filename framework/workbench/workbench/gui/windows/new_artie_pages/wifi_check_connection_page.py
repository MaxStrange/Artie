from artie_tooling import artie_profile
from PyQt6 import QtWidgets, QtCore
from comms import artie_serial


class WiFiCheckConnectionPage(QtWidgets.QWizardPage):
    """Page that verifies the WiFi connection"""
    
    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.config = config
        self.setTitle("Verifying WiFi Connection")
        self.setSubTitle("Checking that Artie can connect to the selected network...")
        self.setCommitPage(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Connection status icon
        self.status_label = QtWidgets.QLabel()
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(150)
        self.status_label.setText("📡\n\nConnecting...")
        self.status_label.setStyleSheet("font-size: 48px; color: #666;")
        layout.addWidget(self.status_label)
        
        # Progress indicator
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
        
        # Status text
        self.status_text = QtWidgets.QLabel()
        self.status_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_text.setWordWrap(True)
        self.status_text.setText("Please wait while we verify the WiFi connection...")
        layout.addWidget(self.status_text)
        
        # Output details (collapsible)
        self.details_group = QtWidgets.QGroupBox("Connection Details")
        self.details_group.setCheckable(True)
        self.details_group.setChecked(False)
        details_layout = QtWidgets.QVBoxLayout(self.details_group)
        
        self.details_text = QtWidgets.QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("font-family: monospace;")
        self.details_text.setMaximumHeight(150)
        details_layout.addWidget(self.details_text)
        
        layout.addWidget(self.details_group)
        
        layout.addStretch()
        
        self.connection_verified = False
    
    def initializePage(self):
        """Start the WiFi verification when page is shown"""
        self.connection_verified = False
        self.details_text.clear()
        self.status_label.setText("📡\n\nConnecting...")
        self.status_label.setStyleSheet("font-size: 48px; color: #666;")
        self.status_text.setText("Please wait while we verify the WiFi connection...")
        self.progress.setRange(0, 0)  # Indeterminate
        
        # Log WiFi details
        self.details_text.append(f"Network SSID: {self.config.get('wifi_ssid', 'N/A')}")
        self.details_text.append(f"Artie IP: {self.config.get('artie_ip', 'N/A')}\n")
        
        QtCore.QTimer.singleShot(500, self._verify_connection)
    
    def _verify_connection(self):
        """Verify the WiFi connection"""
        self.details_text.append("Attempting to connect to WiFi network...")
        self.details_text.append("Sending WiFi credentials to Artie...")
        
        with artie_serial.ArtieSerialConnection(port=self.field('serial.port')) as connection:
            err = connection.verify_wifi_connection()
            if err:
                self._connection_failure()
            else:
                self._connection_success()
    
    def _connection_success(self):
        """Successful connection"""
        self.details_text.append("\nConnection established!")
        self.details_text.append("Artie is now connected to the network.")
        
        # Update UI
        self.status_label.setText("✅\n\nConnected!")
        self.status_label.setStyleSheet("font-size: 48px; color: #4CAF50;")
        self.status_text.setText(f"Successfully connected to {self.config.get('wifi_ssid', 'network')}!")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        
        self.connection_verified = True
        self.completeChanged.emit()
    
    def _connection_failure(self):
        """Connection failure"""
        self.details_text.append("\nERROR: Failed to connect to network")
        self.details_text.append("Please check the WiFi password and try again.")
        
        # Update UI
        self.status_label.setText("❌\n\nConnection Failed")
        self.status_label.setStyleSheet("font-size: 48px; color: #f44336;")
        self.status_text.setText("Failed to connect to WiFi. Please go back and check your credentials.")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        
        self.connection_verified = False
        self.completeChanged.emit()
    
    def isComplete(self):
        """Only allow next when connection is verified"""
        return self.connection_verified
