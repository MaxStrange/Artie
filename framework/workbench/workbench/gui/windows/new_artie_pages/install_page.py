from PyQt6 import QtWidgets, QtCore
from comms import tool
from ... import colors

class InstallPage(QtWidgets.QWizardPage):
    """Page that runs the artie-tool.py install command"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._artie_tool = tool.ArtieToolInvoker(self.config)
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Installing Artie</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Running installation script...</span>")
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
    
    def _complete_install(self, success: bool, err=None):
        """Complete the installation process"""
        if success:
            self.output_text.append("\nInstallation complete!")
        else:
            self.output_text.append(f"\nERROR: Installation failed: {err}")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.install_complete = success
        self.completeChanged.emit()
    
    def _run_install(self):
        """Run the artie-tool.py install command"""
        err = self._artie_tool.install()
        if err:
            self._complete_install(False, err)
            return

        for stdout, stderr in self._artie_tool.read_all():
            text = stdout + " " + stderr
            self.output_text.append(text)

        if not self._artie_tool.success:
            self._complete_install(False, "artie-tool.py reported an error.")
            return

        self._complete_install(True)
    
    def isComplete(self):
        """Only allow next when installation is complete"""
        return self.install_complete
