"""
Software tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets
from model import artie_profile
from model import settings


class SoftwareTab(QtWidgets.QWidget):
    """Software monitoring tab showing K3S pod status"""
    
    def __init__(self, parent, settings: settings.WorkbenchSettings, profile: artie_profile.ArtieProfile):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        self._setup_ui()

        # Connect to parent signals
        self.parent().profile_switched_signal.connect(self.on_profile_switched)
        self.parent().settings_changed_signal.connect(self.on_settings_changed)

    def on_profile_switched(self, profile: artie_profile.ArtieProfile):
        """Handle profile switch events"""
        self.profile = profile

    def on_settings_changed(self, settings: settings.WorkbenchSettings):
        """Handle settings change events"""
        self.settings = settings
    
    def _setup_ui(self):
        """Setup the software tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        k8s_group = QtWidgets.QGroupBox("K3S Pods Status")
        k8s_layout = QtWidgets.QVBoxLayout(k8s_group)
        
        k8s_text = QtWidgets.QTextBrowser()
        k8s_text.setPlaceholderText("K3S pod status will appear here...")
        k8s_layout.addWidget(k8s_text)
        
        layout.addWidget(k8s_group)
