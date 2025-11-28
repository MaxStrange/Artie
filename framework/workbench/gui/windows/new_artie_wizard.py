"""
New Artie Wizard for setting up a new Artie robot
"""
from PyQt6 import QtWidgets
from .new_artie_pages import complete_page
from .new_artie_pages import credentials_page
from .new_artie_pages import deploy_page
from .new_artie_pages import install_page
from .new_artie_pages import ip_address_page
from .new_artie_pages import name_page
from .new_artie_pages import power_connection_page
from .new_artie_pages import serial_connection_page
from .new_artie_pages import test_page
from .new_artie_pages import wifi_check_connection_page
from .new_artie_pages import wifi_selection_page
from model import artie_profile
import enum

class PageID(enum.IntEnum):
    POWER = enum.auto()
    SERIAL = enum.auto()
    CREDENTIALS = enum.auto()
    WIFI = enum.auto()
    CHECK_WIFI_CONNECTION = enum.auto()
    IP_ADDRESS = enum.auto()
    NAME = enum.auto()
    INSTALL = enum.auto()
    DEPLOY = enum.auto()
    TEST = enum.auto()
    COMPLETE = enum.auto()

class NewArtieWizard(QtWidgets.QWizard):
    """Wizard for adding and configuring a new Artie robot"""
   
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Artie Setup Wizard")
        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(700, 500)
        
        # Artie configuration data and serial connection
        self.artie_config = artie_profile.ArtieProfile()
        
        # Add wizard pages
        self.setPage(PageID.POWER, power_connection_page.PowerConnectionPage())
        self.setPage(PageID.SERIAL, serial_connection_page.SerialConnectionPage())
        self.setPage(PageID.CREDENTIALS, credentials_page.CredentialsPage(self.artie_config))
        self.setPage(PageID.WIFI, wifi_selection_page.WiFiSelectionPage())
        self.setPage(PageID.CHECK_WIFI_CONNECTION, wifi_check_connection_page.WiFiCheckConnectionPage())
        self.setPage(PageID.IP_ADDRESS, ip_address_page.IPAddressPage(self.artie_config))
        self.setPage(PageID.NAME, name_page.NamePage(self.artie_config))
        self.setPage(PageID.INSTALL, install_page.InstallPage(self.artie_config))
        self.setPage(PageID.DEPLOY, deploy_page.DeployPage(self.artie_config))
        self.setPage(PageID.TEST, test_page.TestPage(self.artie_config))
        self.setPage(PageID.COMPLETE, complete_page.CompletePage())

        self.setStartId(PageID.POWER)

        # Now we have an Artie profile. We need to save it.
        self.artie_config.save()
