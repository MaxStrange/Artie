from artie_tooling import artie_profile
from PyQt6 import QtWidgets
from ... import colors

class NamePage(QtWidgets.QWizardPage):
    """Page for naming the Artie"""
    
    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.config = config
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Name Your Artie</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Give this Artie a unique, memorable name.</span>")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Name input
        form_layout = QtWidgets.QFormLayout()
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("e.g., Artie-Lab-01")
        form_layout.addRow("Artie Name:", self.name_input)
        layout.addLayout(form_layout)
        
        # Info
        info_label = QtWidgets.QLabel(
            "<br>This name will be used to identify this Artie in the Workbench.<br>"
            "Choose a name that helps you distinguish between multiple Arties."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {colors.BasePalette.GRAY};")
        layout.addWidget(info_label)
        
        layout.addStretch()
    
    def validatePage(self):
        """Store the name"""
        self.config.artie_name = self.name_input.text()

        return True
