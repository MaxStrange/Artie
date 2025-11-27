"""
Software tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets


class SoftwareTab(QtWidgets.QWidget):
    """Software monitoring tab showing K3S pod status"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the software tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        k8s_group = QtWidgets.QGroupBox("K3S Pods Status")
        k8s_layout = QtWidgets.QVBoxLayout(k8s_group)
        
        k8s_text = QtWidgets.QTextBrowser()
        k8s_text.setPlaceholderText("K3S pod status will appear here...")
        k8s_layout.addWidget(k8s_text)
        
        layout.addWidget(k8s_group)
