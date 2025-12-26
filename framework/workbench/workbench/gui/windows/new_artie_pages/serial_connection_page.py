from PyQt6 import QtWidgets, QtCore
from comms import artie_serial
from ... import colors

class SerialConnectionPage(QtWidgets.QWizardPage):
    """Page prompting user to connect serial USB cable"""

    _NO_PORTS_FOUND_TEXT = "No ports found"
    """The text we display when there are no ports found."""
    
    def __init__(self):
        super().__init__()
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Connect Serial Port USB</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Please connect Artie's serial port USB cable and select the port.</span>")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Add illustration/icon
        icon_label = QtWidgets.QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_label.setMinimumHeight(200)
        icon_label.setText("🔗")
        icon_label.setStyleSheet(f"font-size: 48px; color: {colors.BasePalette.GRAY};")
        layout.addWidget(icon_label)
        
        # Instructions
        instructions = QtWidgets.QLabel(
            "<ol>"
            "<li>Locate a USB serial cable</li>"
            "<li>Connect one end to Artie's serial port (on the Controller Node)</li>"
            "<li>Connect the other end to your computer's USB port</li>"
            "<li>Select the serial port from the dropdown below</li>"
            "</ol>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Serial port selection
        port_group = QtWidgets.QGroupBox("Serial Port")
        port_layout = QtWidgets.QHBoxLayout(port_group)
        
        port_label = QtWidgets.QLabel("Port:")
        port_layout.addWidget(port_label)
        
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(200)
        port_layout.addWidget(self.port_combo)
        
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.refresh_button)
        
        port_layout.addStretch()
        
        layout.addWidget(port_group)
        
        layout.addStretch()

        # We are not complete until a valid port is selected
        self._complete = False

        # If the selected port changes, inform the wizard to re-check completeness
        self.port_combo.currentIndexChanged.connect(self.isComplete)
        
        # Populate ports on initialization
        self._refresh_ports()

        # Set the chosen port as a QWizard 'field', which allows other pages
        # in the wizard access to its value.
        self.registerField('serial.port', self.port_combo, 'currentText')
        self.isComplete()
    
    def _refresh_ports(self):
        """Refresh the list of available serial ports"""
        self.port_combo.clear()
        ports = artie_serial.ArtieSerialConnection.list_ports()
        
        if ports:
            self.port_combo.addItems(ports)
            self.port_combo.setEnabled(True)
            self.isComplete()
        else:
            self.port_combo.addItem(self._NO_PORTS_FOUND_TEXT)
            self.port_combo.setEnabled(False)
            self.isComplete()

    def isComplete(self):
        """Check if a valid port is selected to enable Next button"""
        # If there are no ports, we are not complete
        if self.port_combo.count() == 0 or not self.port_combo.isEnabled():
            if self._complete:
                self._complete = False
                self.completeChanged.emit()
            return False
        
        # If the "No ports found" text is selected, we are not complete
        selected_port = self.port_combo.currentText()
        if selected_port == self._NO_PORTS_FOUND_TEXT:
            if self._complete:
                self._complete = False
                self.completeChanged.emit()
            return False
        
        # Otherwise, we are complete
        if not self._complete:
            self._complete = True
            self.completeChanged.emit()
        return True
    
    def validatePage(self):
        """Validate that a port is selected"""
        if self.port_combo.count() == 0 or not self.port_combo.isEnabled():
            QtWidgets.QMessageBox.warning(self, "No Port Selected", "No serial ports detected. Please connect the USB cable and click Refresh.")
            return False
        
        selected_port = self.port_combo.currentText()
        if selected_port == self._NO_PORTS_FOUND_TEXT:
            QtWidgets.QMessageBox.warning(self, "No Port Selected", "No serial ports detected. Please connect the USB cable and click Refresh.")
            return False
        
        return True
    