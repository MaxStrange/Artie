"""
Main window for Artie Workbench
"""
from PyQt6 import QtWidgets, QtCore, QtGui

from ..utils import status_fetcher
from ..widgets.menubar import ArtieMenuBar
from ..widgets.hardware_tab import HardwareTab
from ..widgets.software_tab import SoftwareTab
from ..widgets.teleop_tab import TeleopTab
from ..widgets.logging_tab import LoggingTab
from ..widgets.sensors_tab import SensorsTab
from ..widgets.experiment_tab import ExperimentTab
from . import new_artie_wizard
from . import settings_dialog
from . import switch_artie_dialog
from . import deploy_chart_dialog
from model import artie_profile
from model import settings


class MainWindow(QtWidgets.QMainWindow):
    """Main window for the Artie Workbench application"""

    # Signal for profile switch
    profile_switched_signal = QtCore.pyqtSignal(artie_profile.ArtieProfile)

    # Signal for settings change
    settings_changed_signal = QtCore.pyqtSignal(settings.WorkbenchSettings)

    def __init__(self, workbench_settings: settings.WorkbenchSettings = None):
        super().__init__()
        self.settings = workbench_settings
        self.current_profile = self.settings.last_opened_profile

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
        menubar.about_requested.connect(self._show_about)
        menubar.add_artie_requested.connect(self._add_artie)
        menubar.exit_requested.connect(self.close)
        menubar.deploy_helm_requested.connect(self._deploy_helm_chart)
        menubar.settings_requested.connect(self._show_settings)
        menubar.switch_artie_requested.connect(self._switch_artie)
    
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
        self.hardware_tab = HardwareTab(self, self.settings, self.current_profile)
        self.software_tab = SoftwareTab(self, self.settings, self.current_profile)
        self.teleop_tab = TeleopTab(self, self.settings, self.current_profile)
        self.logging_tab = LoggingTab(self, self.settings, self.current_profile)
        self.sensors_tab = SensorsTab(self, self.settings, self.current_profile)
        self.experiment_tab = ExperimentTab(self, self.settings, self.current_profile)
        self.tab_widget.addTab(self.hardware_tab, "Hardware")
        self.tab_widget.addTab(self.software_tab, "Software")
        self.tab_widget.addTab(self.teleop_tab, "Teleop")
        self.tab_widget.addTab(self.logging_tab, "Logging")
        self.tab_widget.addTab(self.sensors_tab, "Sensors")
        self.tab_widget.addTab(self.experiment_tab, "Experiment")

        # Add status fetcher to get status periodically
        ## HW Tab
        self.status_fetcher = status_fetcher.StatusFetcher(self, self.current_profile, self.settings)
        self.status_fetcher.nodes_updated_signal.connect(self.hardware_tab.on_nodes_updated)
        self.status_fetcher.mcus_updated_signal.connect(self.hardware_tab.on_mcus_updated)
        self.status_fetcher.actuators_updated_signal.connect(self.hardware_tab.on_actuators_updated)
        ## SW Tab
        self.status_fetcher.pods_updated_signal.connect(self.software_tab.on_pods_updated)
        ## Sensors Tab
        self.status_fetcher.sensors_updated_signal.connect(self.sensors_tab.on_sensors_updated)
        ## Error signal
        self.status_fetcher.error_occurred_signal.connect(self.hardware_tab.on_error)
        self.status_fetcher.error_occurred_signal.connect(self.software_tab.on_error)
        self.status_fetcher.error_occurred_signal.connect(self.sensors_tab.on_error)
        ## Connect refresh signals
        self.software_tab.refresh_status_request_signal.connect(self.status_fetcher.fetch_pods_status)
        self.hardware_tab.refresh_status_request_signal.connect(self.status_fetcher.fetch_mcus_status)
        self.hardware_tab.refresh_status_request_signal.connect(self.status_fetcher.fetch_actuators_status)
        self.hardware_tab.refresh_status_request_signal.connect(self.status_fetcher.fetch_nodes_status)
        self.sensors_tab.refresh_status_request_signal.connect(self.status_fetcher.fetch_sensors_status)

    def closeEvent(self, a0):
        self.status_fetcher.close()
        super().closeEvent(a0)

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
        profiles = artie_profile.list_profiles()

        dialog = switch_artie_dialog.SwitchArtieDialog(self.settings, profiles, self.current_profile, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_profile = dialog.selected_profile
            if selected_profile:
                self.current_profile = selected_profile
                self.profile_switched_signal.emit(self.current_profile)
    
    def _add_artie(self):
        """Handle adding a new Artie"""
        wizard = new_artie_wizard.NewArtieWizard(self)
        wizard.show()
    
    def _deploy_helm_chart(self):
        """Handle deploying a Helm chart"""
        dialog = deploy_chart_dialog.DeployChartDialog(self.settings, self.current_profile, self)
        dialog.exec()

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

    def _show_settings(self):
        """Show settings dialog"""
        dialog = settings_dialog.SettingsDialog(self.settings, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            new_settings = dialog.get_updated_settings()
            self.settings = new_settings
            self.settings_changed_signal.emit(self.settings)
