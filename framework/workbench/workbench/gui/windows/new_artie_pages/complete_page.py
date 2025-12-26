from artie_tooling import artie_profile
from PyQt6 import QtWidgets, QtCore
from ... import colors
import pathlib

class CompletePage(QtWidgets.QWizardPage):
    """Final completion page"""
    
    def __init__(self, config: artie_profile.ArtieProfile):
        super().__init__()
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Setup Complete!</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Your Artie has been successfully configured and is ready to use.</span>")
        self.artie_config = config

        layout = QtWidgets.QVBoxLayout(self)

        # Success icon
        icon_label = QtWidgets.QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_label.setMinimumHeight(200)
        icon_label.setText("✅\n\nSetup Successful!")
        icon_label.setStyleSheet(f"font-size: 48px; color: {colors.BasePalette.GREEN};")
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
        summary_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(summary_label)

        # File path selection
        path_label = QtWidgets.QLabel("Save to Folder:")
        layout.addWidget(path_label)

        # Create a folder picker dialog
        folder_picker = QtWidgets.QFileDialog(self)
        folder_picker.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        folder_picker.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, True)
        folder_picker.setLabelText(QtWidgets.QFileDialog.DialogLabel.Accept, "Select Folder")
        folder_picker.setLabelText(QtWidgets.QFileDialog.DialogLabel.Reject, "Cancel")
        folder_picker.setDirectory(str(artie_profile.DEFAULT_SAVE_PATH.parent))
        self.registerField("complete.savefolder", folder_picker)
        layout.addWidget(folder_picker)

        layout.addStretch()

    def validatePage(self) -> bool:
        """Called when Finish is clicked"""
        if not self.field('complete.savefolder'):
            QtWidgets.QMessageBox.warning(self, "Save Path Required", "Please specify a valid save path for the Artie profile.")
            return False
        elif not pathlib.Path(self.field('complete.savefolder')).exists():
            QtWidgets.QMessageBox.warning(self, "Invalid Save Path", "The specified save directory does not exist. Please choose a valid path.")
            return False

        # Now we have an Artie profile. We need to save it.
        self.artie_config.save(self.field('complete.savefolder'))
        return True
