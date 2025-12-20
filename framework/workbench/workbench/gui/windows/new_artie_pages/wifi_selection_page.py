from PyQt6 import QtWidgets, QtCore
from comms import artie_serial
import threading

class WiFiSelectionPage(QtWidgets.QWizardPage):
    """Page for selecting WiFi network and entering credentials"""
    
    def __init__(self):
        super().__init__()
        self._scanning_thread = threading.Thread(target=self._get_networks, name='scanning thread', daemon=True)
        self.setTitle("Configure WiFi")
        self.setSubTitle("Select a WiFi network for Artie to connect to.")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # WiFi network list
        network_label = QtWidgets.QLabel("Available Networks:")
        layout.addWidget(network_label)
        
        self.network_list = QtWidgets.QListWidget()
        self.network_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.network_list)
        
        # Scan button
        scan_layout = QtWidgets.QHBoxLayout()
        self.scan_button = QtWidgets.QPushButton("Scan for Networks")
        self.scan_button.clicked.connect(self._scan_networks)
        scan_layout.addWidget(self.scan_button)
        scan_layout.addStretch()
        layout.addLayout(scan_layout)
        
        # WiFi credentials
        credentials_group = QtWidgets.QGroupBox("Network Credentials")
        credentials_layout = QtWidgets.QFormLayout(credentials_group)
        
        self.ssid_input = QtWidgets.QLineEdit()
        self.ssid_input.setPlaceholderText("Selected network SSID")
        self.ssid_input.setReadOnly(True)
        credentials_layout.addRow("SSID:", self.ssid_input)
        
        self.wifi_password_input = QtWidgets.QLineEdit()
        self.wifi_password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.wifi_password_input.setPlaceholderText("Enter WiFi password")
        credentials_layout.addRow("Password:", self.wifi_password_input)
        
        layout.addWidget(credentials_group)
        
        # Connect list selection to SSID field
        self.network_list.itemSelectionChanged.connect(self._on_network_selected)
        
        # Note
        note_label = QtWidgets.QLabel(
            "<i>Note: WiFi credentials are stored on Artie's OS, not in the Workbench.</i>"
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666;")
        layout.addWidget(note_label)
    
    def _scan_networks(self):
        """Scan for available WiFi networks"""
        self.network_list.clear()
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning...")

        # Start the scanning thread. This will do its best to asyncronously
        # find the Wifi networks that Artie has access to and populate
        # them in the network list.
        self._scanning_thread.start()
        
        # TODO: Implement actual network scanning via serial connection
        # TODO: Scan and set using nmcli on the target
        # For now, add some dummy networks
        QtCore.QTimer.singleShot(1000, self._populate_dummy_networks)

    def _get_networks(self):
        """This is the thread target for the scanning button."""
        with artie_serial.ArtieSerialConnection(port=self.field('serial.port')) as connection:
            err, wifi_networks = connection.scan_for_wifi_networks()
            if err:
                QtWidgets.QMessageBox.critical(self, "Error Setting Credentials", f"An error occurred while setting credentials: {err}. Try submitting again.")
                return

        for network in wifi_networks:
            self.network_list.addItem(network)

        self.scan_button.setEnabled(True)
        self.scan_button.setText("Scan for Networks")
    
    def _on_network_selected(self):
        """Update SSID field when network is selected"""
        selected_items = self.network_list.selectedItems()
        if selected_items:
            self.ssid_input.setText(selected_items[0].text())
    
    def validatePage(self):
        """Validate WiFi selection"""
        ssid = self.ssid_input.text()
        password = self.wifi_password_input.text()
        
        if not ssid:
            QtWidgets.QMessageBox.warning(self, "No Network Selected", "Please select a WiFi network.")
            return False
        
        if not password:
            QtWidgets.QMessageBox.warning(self, "No Password", "Please enter the WiFi password.")
            return False
        
        # Store WiFi credentials on Artie
        with artie_serial.ArtieSerialConnection(port=self.field('serial.port')) as connection:
            err = connection.select_wifi(ssid, password)
            if err:
                QtWidgets.QMessageBox.critical(self, "Error Selecting Wifi Network", f"An error occurred while selecting the wifi network: {err}.")
                return False

        return True
