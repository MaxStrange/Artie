from artie_tooling import artie_profile
from PyQt6 import QtWidgets, QtCore
from comms import artie_serial
from ... import colors


class WiFiCheckConnectionPage(QtWidgets.QWizardPage):
    """Page that verifies the WiFi connection"""
    
    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.config = config
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Verifying WiFi Connection</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Checking that Artie can connect to the selected network...</span>")
        self.setCommitPage(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Connection status icon
        self.status_label = QtWidgets.QLabel()
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(80)
        self.status_label.setText("📡\n\nConnecting...")
        self.status_label.setStyleSheet(f"font-size: 24px; color: {colors.BasePalette.GRAY};")
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
        self.details_text.setStyleSheet(f"font-family: monospace; background-color: {colors.BasePalette.WHITE}; color: {colors.BasePalette.BLACK};")
        self.details_text.setMaximumHeight(150)
        details_layout.addWidget(self.details_text)
        
        # Connect checkbox to toggle visibility
        self.details_group.toggled.connect(self.details_text.setVisible)
        self.details_text.setVisible(False)
        
        layout.addWidget(self.details_group)
        
        layout.addStretch()
        
        self.connection_verified = False
    
    def initializePage(self):
        """Start the WiFi verification when page is shown"""
        self.connection_verified = False
        self.details_text.clear()
        self.status_label.setText("📡\n\nConnecting...")
        self.status_label.setStyleSheet(f"font-size: 24px; color: {colors.BasePalette.GRAY};")
        self.status_text.setText("Please wait while we verify the WiFi connection...")
        self.progress.setRange(0, 0)  # Indeterminate
        
        # Log WiFi details
        self.details_text.append(f"Network SSID: {self.field('wifi.ssid')}\n")
        self.details_text.append(f"Artie IP: {self.config.controller_node_ip}\n")
        
        QtCore.QTimer.singleShot(500, self._verify_connection)
    
    def _verify_connection(self):
        """Verify the WiFi connection"""
        self.details_text.append("Attempting to connect to WiFi network...")
        self.details_text.append("Sending WiFi credentials to Artie...")

        ###################### DEBUG TODO ############################
        self._connection_success()
        return
        ##############################################################
        
        with artie_serial.ArtieSerialConnection(port=self.field('serial.port')) as connection:
            err = connection.verify_wifi_connection()
            if err:
                self._connection_failure(err)
            else:
                self._connection_success()
    
    def _connection_success(self):
        """Successful connection"""
        self.details_text.append("\nConnection established!")
        self.details_text.append("Artie is now connected to the network.")
        
        # Update UI
        self.status_label.setText("✅\n\nConnected!")
        self.status_label.setStyleSheet(f"font-size: 24px; color: {colors.BasePalette.GREEN};")
        self.status_text.setText(f"Successfully connected to {self.field('wifi.ssid')}.")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        
        self.connection_verified = True
        self.completeChanged.emit()
    
    def _connection_failure(self, err: Exception):
        """Connection failure"""
        self.details_text.append(f"\nERROR: Failed to connect to network: {err}")
        self.details_text.append("Please check the WiFi password and try again.")
        
        # Update UI
        self.status_label.setText("❌\n\nConnection Failed")
        self.status_label.setStyleSheet(f"font-size: 24px; color: {colors.BasePalette.RED};")
        self.status_text.setText("Failed to connect to WiFi. Please go back and check your credentials.")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        
        self.connection_verified = False
        self.completeChanged.emit()
    
    def isComplete(self):
        """Only allow next when connection is verified"""
        return self.connection_verified
