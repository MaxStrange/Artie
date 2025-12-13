"""
This module contains the Switch Artie Dialog.
"""
from artie_tooling import artie_profile
from PyQt6 import QtCore
from PyQt6 import QtWidgets
from typing import Optional
from model import settings


class SwitchArtieDialog(QtWidgets.QDialog):
    """Dialog for switching between Artie profiles."""
    
    # Signal emitted when a profile is selected
    profile_selected = QtCore.pyqtSignal(artie_profile.ArtieProfile)
    
    def __init__(self, workbench_settings: settings.WorkbenchSettings, profiles: list[artie_profile.ArtieProfile], current_profile: Optional[artie_profile.ArtieProfile] = None, parent=None):
        """
        Initialize the Switch Artie Dialog.
        
        Args:
            profiles: List of available profiles
            current_profile: Currently active profile
            parent: Parent widget

        """
        super().__init__(parent)
        self.settings = workbench_settings
        self.profiles = profiles
        self.current_profile = current_profile
        self.selected_profile = None
        
        self.setup_ui()
        self.populate_profiles()
        
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Switch Artie Profile")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Label
        label = QtWidgets.QLabel("Select an Artie profile to switch to:")
        layout.addWidget(label)
        
        # Profile list
        self.profile_list = QtWidgets.QListWidget()
        self.profile_list.itemDoubleClicked.connect(self.on_profile_double_clicked)
        self.profile_list.currentItemChanged.connect(self.on_selection_changed)
        layout.addWidget(self.profile_list)
        
        # Button layout
        button_layout = QtWidgets.QHBoxLayout()
        
        self.delete_button = QtWidgets.QPushButton("Delete Artie")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        
        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)
        button_layout.addWidget(self.ok_button)
        
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def populate_profiles(self):
        """Populate the list with available profiles."""
        self.profile_list.clear()
        
        for profile in self.profiles:
            item = QtWidgets.QListWidgetItem(profile.artie_name)
            
            # Highlight current profile
            if profile == self.current_profile:
                item.setData(QtCore.Qt.ItemDataRole.UserRole, "current")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setText(f"{profile.artie_name} (current)")
                
            self.profile_list.addItem(item)
            
        # Select first non-current profile by default
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) != "current":
                self.profile_list.setCurrentItem(item)
                break                    
                    
    def on_selection_changed(self, current: QtWidgets.QListWidgetItem, previous: QtWidgets.QListWidgetItem):
        """Handle profile selection change."""
        if current:
            # Extract profile name (remove " (current)" suffix if present)
            profile_name = current.text().replace(" (current)", "")
            self.selected_profile = artie_profile.ArtieProfile.load(profile_name, path=self.settings.workbench_save_path)
            
            # Enable OK button only if different from current profile
            is_current = current.data(QtCore.Qt.ItemDataRole.UserRole) == "current"
            self.ok_button.setEnabled(not is_current)
            
            # Enable delete button for any selected profile
            self.delete_button.setEnabled(True)
        else:
            self.selected_profile = None
            self.ok_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            
    def on_profile_double_clicked(self, item: QtWidgets.QListWidgetItem):
        """Handle double-click on a profile."""
        if item.data(QtCore.Qt.ItemDataRole.UserRole) != "current":
            self.accept()
            
    def on_delete_clicked(self):
        """Handle delete button click."""
        if not self.selected_profile:
            return
        
        # Show confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Artie Profile",
            f"Are you sure you want to delete the profile '{self.selected_profile.artie_name}'?\n\nThis action cannot be undone.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # Delete the profile
            self.selected_profile.delete(path=self.settings.workbench_save_path)
            
            # Remove from profiles list
            self.profiles = [p for p in self.profiles if p.artie_name != self.selected_profile.artie_name]
            
            # If we deleted the current profile, clear it
            if self.current_profile and self.current_profile.artie_name == self.selected_profile.artie_name:
                self.current_profile = None
            
            # Clear selection
            self.selected_profile = None
            
            # Refresh the list
            self.populate_profiles()
            
            # Show success message
            QtWidgets.QMessageBox.information(self, "Profile Deleted", "The Artie profile has been successfully deleted.")
    
    def accept(self):
        """Handle OK button click."""
        if self.selected_profile and self.selected_profile != self.current_profile:
            self.profile_selected.emit(self.selected_profile)

        super().accept()
        