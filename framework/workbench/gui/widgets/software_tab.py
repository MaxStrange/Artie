"""
Software tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets, QtCore
from model import artie_profile
from model import settings
from .status_icon import StatusGrid
from ..utils.status_fetcher import StatusFetcher


class SoftwareTab(QtWidgets.QWidget):
    """Software monitoring tab showing K3S pod status"""

    refresh_status_request_signal = QtCore.pyqtSignal()
    """Requests that we refresh statuses manually."""
    
    def __init__(self, parent, settings: settings.WorkbenchSettings, profile: artie_profile.ArtieProfile):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        
        self._setup_ui()

        # Connect to parent signals
        self.parent().profile_switched_signal.connect(self.on_profile_switched)
        self.parent().settings_changed_signal.connect(self.on_settings_changed)
        
        # Initial load
        self._refresh_status()

    def on_profile_switched(self, profile: artie_profile.ArtieProfile):
        """Handle profile switch events"""
        self.profile = profile
        self._refresh_status()

    def on_settings_changed(self, settings: settings.WorkbenchSettings):
        """Handle settings change events"""
        self.settings = settings

    def on_pods_updated(self, data: dict):
        """Handle pods status update"""
        if not data.get("success", False):
            return
        
        pods = data.get("data", {}).get("pods", [])
        
        # Clear existing icons
        self.pod_grid.clear_icons()
        
        # Add status icons for each pod
        for pod in pods:
            name = pod.get("name", "Unknown")
            status = pod.get("status", "unknown").lower()
            details = {
                "node": pod.get("node", "unknown"),
                "containers": pod.get("containers", [])
            }
            
            self.pod_grid.add_status_icon(name, status, details)
    
    def on_error(self, module: str, error: str):
        """Handle status fetch errors"""
        # TODO
        if module == "pods":
            pass

    def _refresh_status(self):
        """Force a status update."""
        self.refresh_status_request_signal.emit()
    
    def _setup_ui(self):
        """Setup the software tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Refresh button
        refresh_layout = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh Status")
        refresh_button.clicked.connect(self._refresh_status)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # K3S pods section
        k8s_group = QtWidgets.QGroupBox("K3S Pods Status")
        k8s_layout = QtWidgets.QVBoxLayout(k8s_group)
        
        self.pod_grid = StatusGrid()
        pod_scroll = QtWidgets.QScrollArea()
        pod_scroll.setWidget(self.pod_grid)
        pod_scroll.setWidgetResizable(True)
        pod_scroll.setMinimumHeight(200)
        k8s_layout.addWidget(pod_scroll)
        
        layout.addWidget(k8s_group)
    