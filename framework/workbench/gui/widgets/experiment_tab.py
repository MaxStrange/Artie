"""
Experiment tab widget for Artie Workbench
"""
from PyQt6 import QtWidgets


class ExperimentTab(QtWidgets.QWidget):
    """Experiment progress tab showing schedule and controls"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the experiment tab UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
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
