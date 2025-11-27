"""
Main window for Artie Workbench
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from ..widgets.menubar import ArtieMenuBar
from ..widgets.hardware_tab import HardwareTab
from ..widgets.software_tab import SoftwareTab
from ..widgets.teleop_tab import TeleopTab
from ..widgets.logging_tab import LoggingTab
from ..widgets.sensors_tab import SensorsTab
from ..widgets.experiment_tab import ExperimentTab
from . import new_artie_wizard


class MainWindow(QtWidgets.QMainWindow):
    """Main window for the Artie Workbench application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Artie Workbench")
        self.setMinimumSize(1000, 700)
        
        # Setup UI components
        self._setup_menubar()
        self._setup_central_widget()
        self._setup_statusbar()
        
        # Center window on screen
        self._center_on_screen()
    
    def _setup_menubar(self):
        """Create the menu bar with robot icon in top right"""
        menubar = ArtieMenuBar(self)
        self.setMenuBar(menubar)
        
        # Connect menu signals to handlers
        menubar.exit_requested.connect(self.close)
        menubar.switch_artie_requested.connect(self._switch_artie)
        menubar.add_artie_requested.connect(self._add_artie)
        menubar.deploy_helm_requested.connect(self._deploy_helm_chart)
        menubar.about_requested.connect(self._show_about)
    
    def _setup_central_widget(self):
        """Create the central widget with tabs"""
        # Create central widget container
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Add tabs using custom widgets
        self.tab_widget.addTab(HardwareTab(), "Hardware")
        self.tab_widget.addTab(SoftwareTab(), "Software")
        self.tab_widget.addTab(TeleopTab(), "Teleop")
        self.tab_widget.addTab(LoggingTab(), "Logging")
        self.tab_widget.addTab(SensorsTab(), "Sensors")
        self.tab_widget.addTab(ExperimentTab(), "Experiment")
    
    def _setup_statusbar(self):
        """Create the status bar"""
        statusbar = self.statusBar()
        statusbar.showMessage("Ready")
    
    def _center_on_screen(self):
        """Center the window on the screen"""
        frame_geometry = self.frameGeometry()
        screen_center = QtGui.QGuiApplication.primaryScreen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())
    
    # Menu action handlers
    def _switch_artie(self):
        """Handle switching to a different Artie"""
        QtWidgets.QMessageBox.information(
            self,
            "Switch Artie",
            "Artie selection dialog will appear here"
        )
    
    def _add_artie(self):
        """Handle adding a new Artie"""
        wizard = new_artie_wizard.NewArtieWizard(self)
        wizard.show()
    
    def _deploy_helm_chart(self):
        """Handle deploying a Helm chart"""
        QtWidgets.QMessageBox.information(
            self,
            "Deploy",
            "Helm chart deployment dialog will appear here"
        )
    
    def _show_about(self):
        """Show about dialog"""
        QtWidgets.QMessageBox.about(
            self,
            "About Artie Workbench",
            "<h3>Artie Workbench</h3>"
            "<p>A graphical user interface for interacting with, setting up, "
            "and monitoring Artie robots.</p>"
            "<p>© 2025</p>"
        )
