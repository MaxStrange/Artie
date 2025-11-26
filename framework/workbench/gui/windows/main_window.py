"""
Main window for Artie Workbench
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from ..graphics.robot_icon import RobotIcon


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
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Add actions to File menu
        exit_action = QtGui.QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Artie menu
        artie_menu = menubar.addMenu("&Artie")
        
        switch_artie_action = QtGui.QAction("&Switch Artie...", self)
        switch_artie_action.triggered.connect(self._switch_artie)
        artie_menu.addAction(switch_artie_action)
        
        add_artie_action = QtGui.QAction("&Add New Artie...", self)
        add_artie_action.triggered.connect(self._add_artie)
        artie_menu.addAction(add_artie_action)
        
        # Deployment menu
        deployment_menu = menubar.addMenu("&Deployment")
        
        deploy_action = QtGui.QAction("&Deploy Helm Chart...", self)
        deploy_action.triggered.connect(self._deploy_helm_chart)
        deployment_menu.addAction(deploy_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QtGui.QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # Add robot icon to the right side of menu bar
        # Create a spacer widget to push icon to the right
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred
        )
        menubar.setCornerWidget(spacer, QtCore.Qt.Corner.TopLeftCorner)
        
        # Add robot icon
        robot_icon = RobotIcon()
        menubar.setCornerWidget(robot_icon, QtCore.Qt.Corner.TopRightCorner)
    
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
        
        # Add tabs based on ui-flow.md
        self._add_hardware_tab()
        self._add_software_tab()
        self._add_teleop_tab()
        self._add_logging_tab()
        self._add_sensors_tab()
        self._add_experiment_tab()
    
    def _add_hardware_tab(self):
        """Add Hardware tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Single board computers section
        sbc_group = QtWidgets.QGroupBox("Single Board Computers")
        sbc_layout = QtWidgets.QVBoxLayout(sbc_group)
        
        sbc_text = QtWidgets.QTextBrowser()
        sbc_text.setPlaceholderText("K3S node status and Yocto image versions will appear here...")
        sbc_layout.addWidget(sbc_text)
        
        layout.addWidget(sbc_group)
        
        # Microcontrollers section
        mcu_group = QtWidgets.QGroupBox("Microcontrollers")
        mcu_layout = QtWidgets.QVBoxLayout(mcu_group)
        
        mcu_text = QtWidgets.QTextBrowser()
        mcu_text.setPlaceholderText("MCU heartbeat status and firmware versions will appear here...")
        mcu_layout.addWidget(mcu_text)
        
        layout.addWidget(mcu_group)
        
        # Actuators section
        actuator_group = QtWidgets.QGroupBox("Actuators")
        actuator_layout = QtWidgets.QVBoxLayout(actuator_group)
        
        actuator_text = QtWidgets.QTextBrowser()
        actuator_text.setPlaceholderText("Actuator status from CAN bus will appear here...")
        actuator_layout.addWidget(actuator_text)
        
        layout.addWidget(actuator_group)
        
        self.tab_widget.addTab(tab, "Hardware")
    
    def _add_software_tab(self):
        """Add Software tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        k8s_group = QtWidgets.QGroupBox("K3S Pods Status")
        k8s_layout = QtWidgets.QVBoxLayout(k8s_group)
        
        k8s_text = QtWidgets.QTextBrowser()
        k8s_text.setPlaceholderText("K3S pod status will appear here...")
        k8s_layout.addWidget(k8s_text)
        
        layout.addWidget(k8s_group)
        
        self.tab_widget.addTab(tab, "Software")
    
    def _add_teleop_tab(self):
        """Add Teleop tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        control_group = QtWidgets.QGroupBox("Manual Control")
        control_layout = QtWidgets.QVBoxLayout(control_group)
        
        info_label = QtWidgets.QLabel("Manual control interface for Artie")
        control_layout.addWidget(info_label)
        
        # Placeholder for control widgets
        control_text = QtWidgets.QTextEdit()
        control_text.setPlaceholderText("Teleop controls will appear here...")
        control_layout.addWidget(control_text)
        
        layout.addWidget(control_group)
        
        self.tab_widget.addTab(tab, "Teleop")
    
    def _add_logging_tab(self):
        """Add Logging tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Live logging section
        live_group = QtWidgets.QGroupBox("Live Logs")
        live_layout = QtWidgets.QVBoxLayout(live_group)
        
        live_text = QtWidgets.QTextBrowser()
        live_text.setPlaceholderText("Live logs and telemetry will appear here...")
        live_layout.addWidget(live_text)
        
        layout.addWidget(live_group)
        
        # Historical logging section
        history_group = QtWidgets.QGroupBox("Query Logs")
        history_layout = QtWidgets.QVBoxLayout(history_group)
        
        query_layout = QtWidgets.QHBoxLayout()
        query_label = QtWidgets.QLabel("Search:")
        query_input = QtWidgets.QLineEdit()
        query_button = QtWidgets.QPushButton("Query")
        query_layout.addWidget(query_label)
        query_layout.addWidget(query_input)
        query_layout.addWidget(query_button)
        
        history_layout.addLayout(query_layout)
        
        history_text = QtWidgets.QTextBrowser()
        history_text.setPlaceholderText("Query results will appear here...")
        history_layout.addWidget(history_text)
        
        layout.addWidget(history_group)
        
        self.tab_widget.addTab(tab, "Logging")
    
    def _add_sensors_tab(self):
        """Add Sensors tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        sensor_group = QtWidgets.QGroupBox("Sensor Data Stream")
        sensor_layout = QtWidgets.QVBoxLayout(sensor_group)
        
        sensor_text = QtWidgets.QTextBrowser()
        sensor_text.setPlaceholderText("Live sensor data will appear here...")
        sensor_layout.addWidget(sensor_text)
        
        layout.addWidget(sensor_group)
        
        self.tab_widget.addTab(tab, "Sensors")
    
    def _add_experiment_tab(self):
        """Add Experiment Progress tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # Schedule display section
        schedule_group = QtWidgets.QGroupBox("Experiment Schedule")
        schedule_layout = QtWidgets.QVBoxLayout(schedule_group)
        
        schedule_text = QtWidgets.QTextBrowser()
        schedule_text.setPlaceholderText("Current experiment schedule and progress will appear here...")
        schedule_layout.addWidget(schedule_text)
        
        layout.addWidget(schedule_group)
        
        # Manual control section
        control_group = QtWidgets.QGroupBox("Schedule Control")
        control_layout = QtWidgets.QHBoxLayout(control_group)
        
        pause_button = QtWidgets.QPushButton("Pause")
        resume_button = QtWidgets.QPushButton("Resume")
        skip_button = QtWidgets.QPushButton("Skip Step")
        
        control_layout.addWidget(pause_button)
        control_layout.addWidget(resume_button)
        control_layout.addWidget(skip_button)
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        self.tab_widget.addTab(tab, "Experiment")
    
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
        QtWidgets.QMessageBox.information(
            self,
            "Add Artie",
            "New Artie wizard will appear here"
        )
    
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
