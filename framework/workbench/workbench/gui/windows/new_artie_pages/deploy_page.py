from PyQt6 import QtWidgets, QtCore
from comms import tool
from ... import colors

class DeployPage(QtWidgets.QWizardPage):
    """Page that runs the artie-tool.py deploy base command"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._artie_tool = tool.ArtieToolInvoker(self.config)
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Deploying Base Configuration</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Running deployment script...</span>")
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
        
        self.deploy_complete = False
    
    def initializePage(self):
        """Start the deployment when page is shown"""
        self.deploy_complete = False
        self.output_text.clear()
        QtCore.QTimer.singleShot(500, self._run_deploy)

    def _complete_deployment(self, success: bool, err=None):
        """Complete the deployment process"""
        if success:
            self.output_text.append("\nDeployment complete!")
        else:
            self.output_text.append(f"\nERROR: Deployment failed: {err}")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.deploy_complete = success
        self.completeChanged.emit()
    
    def _run_deploy(self):
        """Run the artie-tool.py deploy base command"""
        ###################### DEBUG TODO ############################
        self._complete_deployment(True)
        return
        ##############################################################

        err = self._artie_tool.deploy("base")
        if err:
            self._complete_deployment(False, err)
            return

        for stdout, stderr in self._artie_tool.read_all():
            text = stdout + " " + stderr
            self.output_text.append(text)

        if not self._artie_tool.success:
            self._complete_deployment(False, "artie-tool.py reported an error.")
            return

        self._complete_deployment(True)

    def isComplete(self):
        """Only allow next when deployment is complete"""
        return self.deploy_complete
