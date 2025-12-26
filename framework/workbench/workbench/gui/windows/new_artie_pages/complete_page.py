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

        text_frame = QtWidgets.QFrame()
        text_layout = QtWidgets.QVBoxLayout(text_frame)

        # Success icon
        icon_label = QtWidgets.QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_label.setText("✅\n\nSetup Successful!")
        icon_label.setStyleSheet(f"font-size: 48px; color: {colors.BasePalette.GREEN};")
        text_layout.addWidget(icon_label)

        # Summary
        summary_label = QtWidgets.QLabel(
            "Your Artie has been:<br><br>"
            "<span style='display: inline-block; margin: 0 10px;'>✓ Installed with the base configuration </span>"
            "<span style='display: inline-block; margin: 0 10px;'>✓ Deployed to the K3S cluster </span>"
            "<span style='display: inline-block; margin: 0 10px;'>✓ Tested and verified</span>"
            f"<br><br>Click Finish to save {config.artie_name} to the path below."
        )
        summary_label.setWordWrap(True)
        summary_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        text_layout.addWidget(summary_label)

        text_frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        layout.addWidget(text_frame)

        # File path selection
        path_label = QtWidgets.QLabel("Save to Folder:")
        layout.addWidget(path_label)

        # Create a horizontal layout for path selection
        path_layout = QtWidgets.QHBoxLayout()
        
        # Line edit for folder path
        self.folder_line_edit = QtWidgets.QLineEdit()
        self.folder_line_edit.setText(str(artie_profile.DEFAULT_SAVE_PATH))
        self.folder_line_edit.setPlaceholderText("Select a folder to save the Artie profile")
        path_layout.addWidget(self.folder_line_edit)
        
        # Browse button
        browse_button = QtWidgets.QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_folder)
        path_layout.addWidget(browse_button)
        
        layout.addLayout(path_layout)
        self.registerField("complete.savefolder", self.folder_line_edit)
        
        layout.addStretch()

    def _browse_folder(self):
        """Open folder dialog and update line edit"""
        default = self.folder_line_edit.text() or str(artie_profile.DEFAULT_SAVE_PATH)
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder", default, QtWidgets.QFileDialog.Option.ShowDirsOnly)
        if folder:
            self.folder_line_edit.setText(folder)

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
