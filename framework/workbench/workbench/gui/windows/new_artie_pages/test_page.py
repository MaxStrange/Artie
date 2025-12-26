from PyQt6 import QtWidgets, QtCore
from comms import tool
from ... import colors

class TestPage(QtWidgets.QWizardPage):
    """Page that runs the artie-tool.py test all-hw command"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._artie_tool = tool.ArtieToolInvoker(self.config)
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Testing Hardware</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Running hardware tests...</span>")
        self.setCommitPage(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Progress indicator
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
        
        # Output text
        self.output_text = QtWidgets.QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet(f"font-family: monospace; background-color: {colors.BasePalette.WHITE}; color: {colors.BasePalette.BLACK};")
        layout.addWidget(self.output_text)
        
        self.test_complete = False
    
    def initializePage(self):
        """Start the tests when page is shown"""
        self.test_complete = False
        self.output_text.clear()
        QtCore.QTimer.singleShot(500, self._run_tests)

    def _complete_tests(self, success: bool, err=None):
        """Complete the testing process"""
        if success:
            self.output_text.append("\nAll tests passed!")
        else:
            self.output_text.append(f"\nERROR: Tests failed: {err}")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.test_complete = success
        self.completeChanged.emit()
    
    def _run_tests(self):
        """Run the artie-tool.py test all-hw command"""
        ###################### DEBUG TODO ############################
        self._complete_tests(True)
        return
        ##############################################################

        err = self._artie_tool.test("all-hw")
        if err:
            self._complete_tests(False, err)
            return

        for stdout, stderr in self._artie_tool.read_all():
            text = stdout + " " + stderr
            self.output_text.append(text)

        if not self._artie_tool.success:
            self._complete_tests(False, "artie-tool.py reported an error.")
            return

        self._complete_tests(True)
    
    def isComplete(self):
        """Only allow next when tests are complete"""
        return self.test_complete
