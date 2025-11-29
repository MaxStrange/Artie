"""
Custom menu bar for Artie Workbench
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from ..graphics.robot_icon import RobotIcon


class ArtieMenuBar(QtWidgets.QMenuBar):
    """Custom menu bar for Artie Workbench with robot icon"""
    
    # Signals for menu actions
    switch_artie_requested = QtCore.pyqtSignal()
    add_artie_requested = QtCore.pyqtSignal()
    deploy_helm_requested = QtCore.pyqtSignal()
    about_requested = QtCore.pyqtSignal()
    exit_requested = QtCore.pyqtSignal()
    settings_requested = QtCore.pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_menus()
        self._setup_robot_icon()
    
    def _setup_menus(self):
        """Create all menu items"""
        # File menu
        file_menu = self.addMenu("&File")
        
        exit_action = QtGui.QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.exit_requested.emit)
        file_menu.addAction(exit_action)

        settings_action = QtGui.QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+S")
        settings_action.triggered.connect(self.settings_requested.emit)
        file_menu.addAction(settings_action)
        
        # Artie menu
        artie_menu = self.addMenu("&Artie")
        
        switch_artie_action = QtGui.QAction("&Switch Artie...", self)
        switch_artie_action.triggered.connect(self.switch_artie_requested.emit)
        artie_menu.addAction(switch_artie_action)
        
        add_artie_action = QtGui.QAction("&Add New Artie...", self)
        add_artie_action.triggered.connect(self.add_artie_requested.emit)
        artie_menu.addAction(add_artie_action)
        
        # Deployment menu
        deployment_menu = self.addMenu("&Deployment")
        
        deploy_action = QtGui.QAction("&Deploy Helm Chart...", self)
        deploy_action.triggered.connect(self.deploy_helm_requested.emit)
        deployment_menu.addAction(deploy_action)
        
        # Help menu
        help_menu = self.addMenu("&Help")
        
        about_action = QtGui.QAction("&About", self)
        about_action.triggered.connect(self.about_requested.emit)
        help_menu.addAction(about_action)
    
    def _setup_robot_icon(self):
        """Add robot icon to the right side of menu bar"""
        # Create a spacer widget to push icon to the right
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred
        )
        self.setCornerWidget(spacer, QtCore.Qt.Corner.TopLeftCorner)
        
        # Add robot icon
        robot_icon = RobotIcon()
        self.setCornerWidget(robot_icon, QtCore.Qt.Corner.TopRightCorner)
