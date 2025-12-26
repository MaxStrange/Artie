from PyQt6 import QtWidgets, QtCore
from artie_tooling import artie_profile
from comms import artie_serial
from util import log
import threading
from ... import colors

class WiFiSelectionPage(QtWidgets.QWizardPage):
    """Page for selecting WiFi network and entering credentials"""
    
    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.config = config

        self._scanning_thread = threading.Thread(target=self._get_networks, name='scanning thread', daemon=True)
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Configure WiFi</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Select a WiFi network for Artie to connect to.</span>")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # WiFi network list
        network_label = QtWidgets.QLabel("Available Networks:")
        layout.addWidget(network_label)
        
        self.network_table = QtWidgets.QTableWidget()
        self.network_table.setColumnCount(3)
        self.network_table.setHorizontalHeaderLabels(["SSID", "Signal Level", "BSSID"])
        self.network_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.network_table)
        
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
        self.registerField('wifi.ssid*', self.ssid_input)
        credentials_layout.addRow("SSID:", self.ssid_input)
        
        self.wifi_password_input = QtWidgets.QLineEdit()
        self.wifi_password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.wifi_password_input.setPlaceholderText("Enter WiFi password")
        credentials_layout.addRow("Password:", self.wifi_password_input)
        
        layout.addWidget(credentials_group)
        
        # Connect list selection to SSID field
        self.network_table.itemSelectionChanged.connect(self._on_network_selected)
        
        # Note
        note_label = QtWidgets.QLabel("<i>Note: WiFi credentials are stored on Artie's OS, not in the Workbench.</i>")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666;")
        layout.addWidget(note_label)
    
    def _scan_networks(self):
        """Scan for available WiFi networks"""
        if self._scanning_thread.is_alive():
            # Shouldn't be possible due to button disabling, but just in case
            return

        self._scanning_thread = threading.Thread(target=self._get_networks, name='scanning thread', daemon=True)
        self.network_table.clearContents()
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning...")

        # Start the scanning thread. This will do its best to asyncronously
        # find the Wifi networks that Artie has access to and populate
        # them in the network list.
        self._scanning_thread.start()

    def _get_networks(self):
        """This is the thread target for the scanning button."""
        ###################### DEBUG TODO ############################
        row_position = 0
        for network in [artie_serial.WifiNetwork("1e:9d:72:32:45:72", 5785, -74, "", "skynet5")]:
            # If this index does not exist, add a new row
            if row_position >= self.network_table.rowCount():
                self.network_table.insertRow(row_position)
            self.network_table.setItem(row_position, 0, QtWidgets.QTableWidgetItem(network.ssid))
            self.network_table.setItem(row_position, 1, QtWidgets.QTableWidgetItem(str(network.signal_level)))
            self.network_table.setItem(row_position, 2, QtWidgets.QTableWidgetItem(network.bssid))
            row_position += 1

        self.scan_button.setEnabled(True)
        self.scan_button.setText("Scan for Networks")
        return
        ##############################################################

        with artie_serial.ArtieSerialConnection(port=self.field('serial.port')) as connection:
            err, wifi_networks = connection.scan_for_wifi_networks()
            if err:
                # TODO: Can't do this from another thread. Need the parent thread to actually do this.
                QtWidgets.QMessageBox.critical(self, "Error Scanning Networks", f"An error occurred while scanning for networks: {err}. Try scanning again.")
                return

        log.debug(f"Found {len(wifi_networks)} WiFi networks.")
        row_position = 0
        for network in wifi_networks:
            # If this index does not exist, add a new row
            if row_position >= self.network_table.rowCount():
                self.network_table.insertRow(row_position)
            self.network_table.setItem(row_position, 0, QtWidgets.QTableWidgetItem(network.ssid))
            self.network_table.setItem(row_position, 1, QtWidgets.QTableWidgetItem(str(network.signal_level)))
            self.network_table.setItem(row_position, 2, QtWidgets.QTableWidgetItem(network.bssid))
            row_position += 1

        self.scan_button.setEnabled(True)
        self.scan_button.setText("Scan for Networks")
    
    def _on_network_selected(self):
        """Update SSID field when network is selected"""
        # First, select the entire row when an item is clicked
        selected_ranges = self.network_table.selectedRanges()
        for selected_range in selected_ranges:
            for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                self.network_table.selectRow(row)

        # Now determine the SSID of the selected row
        selected_items = self.network_table.selectedItems()
        if selected_items:
            ssid = selected_items[0].text()
            self.ssid_input.setText(ssid)
    
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

        ###################### DEBUG TODO ############################
        return True
        ##############################################################
        
        # Store WiFi credentials on Artie
        # TODO: Add option for static IP to the GUI, then pass the settings here
        with artie_serial.ArtieSerialConnection(port=self.field('serial.port')) as connection:
            err = connection.select_wifi(ssid, password)
            if err:
                QtWidgets.QMessageBox.critical(self, "Error Selecting Wifi Network", f"An error occurred while selecting the wifi network: {err}.")
                return False

        return True
