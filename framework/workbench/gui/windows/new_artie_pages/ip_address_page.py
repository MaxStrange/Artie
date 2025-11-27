from PyQt6 import QtWidgets
from comms import artie_serial
import re

class IPAddressPage(QtWidgets.QWizardPage):
    """Page for collecting the IP address"""
    
    def __init__(self, config: artie_serial.ArtieSerialConnection):
        super().__init__()
        self.config = config
        self.setTitle("Network Configuration")
        self.setSubTitle("Enter the IP addresses for Artie and the admin server.")
        
        layout = QtWidgets.QFormLayout(self)
        
        # Artie IP
        self.artie_ip_input = QtWidgets.QLineEdit()
        self.artie_ip_input.setPlaceholderText("e.g., 192.168.1.100")
        self.registerField("artie_ip*", self.artie_ip_input)
        layout.addRow("Artie IP Address:", self.artie_ip_input)
        
        # Admin IP
        self.admin_ip_input = QtWidgets.QLineEdit()
        self.admin_ip_input.setPlaceholderText("e.g., 192.168.1.10")
        self.registerField("admin_ip*", self.admin_ip_input)
        layout.addRow("Admin Server IP:", self.admin_ip_input)
        
        # Admin token
        self.admin_token_input = QtWidgets.QLineEdit()
        self.admin_token_input.setPlaceholderText("Token from /var/lib/rancher/k3s/server/node-token")
        self.registerField("admin_token*", self.admin_token_input)
        layout.addRow("Admin Token:", self.admin_token_input)
        
        # Info label
        info_label = QtWidgets.QLabel(
            "<br><i>The admin token can be found on the admin server at:<br>"
            "/var/lib/rancher/k3s/server/node-token</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666;")
        layout.addRow(info_label)
    
    def validatePage(self):
        """Validate IP addresses"""
        artie_ip = self.artie_ip_input.text()
        admin_ip = self.admin_ip_input.text()
        admin_token = self.admin_token_input.text()
        
        # Simple IP validation
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        
        if not ip_pattern.match(artie_ip):
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid IP",
                "Please enter a valid IP address for Artie."
            )
            return False
        
        if not ip_pattern.match(admin_ip):
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid IP",
                "Please enter a valid IP address for the admin server."
            )
            return False
        
        # Store IP addresses
        self.config['artie_ip'] = artie_ip
        self.config['admin_ip'] = admin_ip
        self.config['admin_token'] = admin_token
        return True
