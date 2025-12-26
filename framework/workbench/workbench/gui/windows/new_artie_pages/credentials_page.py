"""
Module defining the credentials page for the new Artie wizard.
"""
from artie_tooling import artie_profile
from comms import artie_serial
from PyQt6 import QtWidgets
from ... import colors

class CredentialsPage(QtWidgets.QWizardPage):
    """Page for collecting Artie username and password"""

    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.config = config
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Set Artie Credentials</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Create a username and password for this Artie. Credentials will be stored securely.</span>")
        
        layout = QtWidgets.QFormLayout(self)
        
        # Username field
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.registerField("username*", self.username_input)
        layout.addRow("Username:", self.username_input)
        
        # Password field
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        self.registerField("password*", self.password_input)
        layout.addRow("Password:", self.password_input)
        
        # Confirm password field
        self.confirm_password_input = QtWidgets.QLineEdit()
        self.confirm_password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Confirm password")
        layout.addRow("Confirm Password:", self.confirm_password_input)
        
        # Info label
        info_label = QtWidgets.QLabel(
            "<br><i>Note: These credentials will be stored securely using "
            "OS-specific encryption and will not be visible in plaintext.</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {colors.BasePalette.GRAY};")
        layout.addRow(info_label)
    
    def validatePage(self):
        """Validate that passwords match"""
        username = self.username_input.text()
        password = self.password_input.text()
        confirm = self.confirm_password_input.text()
        
        if password != confirm:
            QtWidgets.QMessageBox.warning(self, "Password Mismatch", "The passwords do not match. Please try again.")
            return False

        # Set the credentials on the serial connection
        with artie_serial.ArtieSerialConnection(port=self.field('serial.port')) as connection:
            err = connection.set_credentials(username, password)
            if err:
                QtWidgets.QMessageBox.critical(self, "Error Setting Credentials", f"An error occurred while setting credentials: {err}. Try submitting again.")
                return False
        
        # Store credentials
        self.config.username = username
        self.config.password = password
        return True
