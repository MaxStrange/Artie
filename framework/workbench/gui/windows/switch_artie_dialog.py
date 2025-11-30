"""
This module contains the Switch Artie Dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QLabel, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional
from model import artie_profile
from model import settings


class SwitchArtieDialog(QDialog):
    """Dialog for switching between Artie profiles."""
    
    # Signal emitted when a profile is selected
    profile_selected = pyqtSignal(artie_profile.ArtieProfile)
    
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
        layout = QVBoxLayout(self)
        
        # Label
        label = QLabel("Select an Artie profile to switch to:")
        layout.addWidget(label)
        
        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.itemDoubleClicked.connect(self.on_profile_double_clicked)
        self.profile_list.currentItemChanged.connect(self.on_selection_changed)
        layout.addWidget(self.profile_list)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)
        button_layout.addWidget(self.ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def populate_profiles(self):
        """Populate the list with available profiles."""
        self.profile_list.clear()
        
        for profile in self.profiles:
            item = QListWidgetItem(profile.artie_name)
            
            # Highlight current profile
            if profile == self.current_profile:
                item.setData(Qt.UserRole, "current")
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setText(f"{profile.artie_name} (current)")
                
            self.profile_list.addItem(item)
            
        # Select first non-current profile by default
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.data(Qt.UserRole) != "current":
                self.profile_list.setCurrentItem(item)
                break                    
                    
    def on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle profile selection change."""
        if current:
            # Extract profile name (remove " (current)" suffix if present)
            profile_name = current.text().replace(" (current)", "")
            self.selected_profile = artie_profile.ArtieProfile.load(profile_name, path=self.settings.workbench_save_path)
            
            # Enable OK button only if different from current profile
            is_current = current.data(Qt.UserRole) == "current"
            self.ok_button.setEnabled(not is_current)
        else:
            self.selected_profile = None
            self.ok_button.setEnabled(False)
            
    def on_profile_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on a profile."""
        if item.data(Qt.UserRole) != "current":
            self.accept()
            
    def accept(self):
        """Handle OK button click."""
        if self.selected_profile and self.selected_profile != self.current_profile:
            self.profile_selected.emit(self.selected_profile)

        super().accept()
        