from PyQt6 import QtWidgets, QtCore
from model import artie_profile

class CompletePage(QtWidgets.QWizardPage):
    """Final completion page"""
    
    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.setTitle("Setup Complete!")
        self.setSubTitle("Your Artie has been successfully configured and is ready to use.")

        layout = QtWidgets.QVBoxLayout(self)

        # Success icon
        icon_label = QtWidgets.QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_label.setMinimumHeight(200)
        icon_label.setText("✅\n\nSetup Successful!")
        icon_label.setStyleSheet("font-size: 48px; color: #4CAF50;")
        layout.addWidget(icon_label)

        # Summary
        summary_label = QtWidgets.QLabel(
            "Your Artie has been:<br>"
            "<ul>"
            "<li>Installed with the base configuration</li>"
            "<li>Deployed to the K3S cluster</li>"
            "<li>Tested and verified</li>"
            "</ul>"
            f"<br>Click Finish to save {config.artie_name} to the path below."
        )
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # File path selection
        path_label = QtWidgets.QLabel("Save to Folder:")
        layout.addWidget(path_label)

        path_edit = QtWidgets.QLineEdit()
        path_edit.setText(str(artie_profile.DEFAULT_SAVE_PATH))
        self.registerField("complete.savepath*", path_edit)
        layout.addWidget(path_edit)

        layout.addStretch()
