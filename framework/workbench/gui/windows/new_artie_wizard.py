"""
New Artie Wizard for setting up a new Artie robot
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from .new_artie_pages import complete_page
from .new_artie_pages import credentials_page
from .new_artie_pages import deploy_page
from .new_artie_pages import install_page
from .new_artie_pages import ip_address_page
from .new_artie_pages import name_page
from .new_artie_pages import power_connection_page
from .new_artie_pages import serial_connection_page
from .new_artie_pages import test_page
from .new_artie_pages import wifi_selection_page
import subprocess
import re


class NewArtieWizard(QtWidgets.QWizard):
    """Wizard for adding and configuring a new Artie robot"""
    
    # Page IDs
    PAGE_POWER = 0
    PAGE_SERIAL = 1
    PAGE_CREDENTIALS = 2
    PAGE_WIFI = 3
    PAGE_IP_ADDRESS = 4
    PAGE_NAME = 5
    PAGE_INSTALL = 6
    PAGE_DEPLOY = 7
    PAGE_TEST = 8
    PAGE_COMPLETE = 9
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Artie Setup Wizard")
        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(700, 500)
        
        # Artie configuration data
        self.artie_config = {
            'username': '',
            'password': '',
            'wifi_ssid': '',
            'wifi_password': '',
            'artie_ip': '',
            'admin_ip': '',
            'artie_name': '',
            'admin_token': ''
        }
        
        # Add wizard pages
        self.setPage(self.PAGE_POWER, power_connection_page.PowerConnectionPage())
        self.setPage(self.PAGE_SERIAL, serial_connection_page.SerialConnectionPage())
        self.setPage(self.PAGE_CREDENTIALS, credentials_page.CredentialsPage(self.artie_config))
        self.setPage(self.PAGE_WIFI, wifi_selection_page.WiFiSelectionPage(self.artie_config))
        self.setPage(self.PAGE_IP_ADDRESS, ip_address_page.IPAddressPage(self.artie_config))
        self.setPage(self.PAGE_NAME, name_page.NamePage(self.artie_config))
        self.setPage(self.PAGE_INSTALL, install_page.InstallPage(self.artie_config))
        self.setPage(self.PAGE_DEPLOY, deploy_page.DeployPage(self.artie_config))
        self.setPage(self.PAGE_TEST, test_page.TestPage(self.artie_config))
        self.setPage(self.PAGE_COMPLETE, complete_page.CompletePage())

        self.setStartId(self.PAGE_POWER)
