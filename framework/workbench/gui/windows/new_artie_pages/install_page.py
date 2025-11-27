from PyQt6 import QtWidgets, QtCore

class InstallPage(QtWidgets.QWizardPage):
    """Page that runs the artie-tool.py install command"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setTitle("Installing Artie")
        self.setSubTitle("Running installation script...")
        self.setCommitPage(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Progress indicator
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
        
        # Output text
        self.output_text = QtWidgets.QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.output_text)
        
        self.install_complete = False
    
    def initializePage(self):
        """Start the installation when page is shown"""
        self.install_complete = False
        self.output_text.clear()
        QtCore.QTimer.singleShot(500, self._run_install)
    
    def _run_install(self):
        """Run the artie-tool.py install command"""
        cmd = [
            "python",
            "artie-tool.py",
            "install",
            "--username", self.config['username'],
            "--artie-ip", self.config['artie_ip'],
            "--admin-ip", self.config['admin_ip'],
            "--artie-name", self.config['artie_name']
        ]
        
        self.output_text.append(f"Running: {' '.join(cmd)}\n")
        
        # TODO: Implement actual subprocess execution
        # For now, simulate with timer
        QtCore.QTimer.singleShot(2000, self._simulate_install_complete)
    
    def _simulate_install_complete(self):
        """Simulate installation completion"""
        self.output_text.append("\nInstallation complete!")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.install_complete = True
        self.completeChanged.emit()
    
    def isComplete(self):
        """Only allow next when installation is complete"""
        return self.install_complete
