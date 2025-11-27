from PyQt6 import QtWidgets
from model import artie_profile

class NamePage(QtWidgets.QWizardPage):
    """Page for naming the Artie"""
    
    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.config = config
        self.setTitle("Name Your Artie")
        self.setSubTitle("Give this Artie a unique, memorable name.")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Name input
        form_layout = QtWidgets.QFormLayout()
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("e.g., Artie-Lab-01")
        self.registerField("artie_name*", self.name_input)
        form_layout.addRow("Artie Name:", self.name_input)
        layout.addLayout(form_layout)
        
        # Info
        info_label = QtWidgets.QLabel(
            "<br>This name will be used to identify this Artie in the Workbench.<br>"
            "Choose a name that helps you distinguish between multiple Arties."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        layout.addStretch()
    
    def validatePage(self):
        """Store the name"""
        self.config.artie_name = self.name_input.text()

        return True
