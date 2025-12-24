from PyQt6 import QtWidgets, QtCore
from ... import colors

class PowerConnectionPage(QtWidgets.QWizardPage):
    """Page prompting user to connect power cable"""
    
    def __init__(self):
        super().__init__()
        self.setTitle(f"<span style='color:{colors.BasePalette.BLACK};'>Connect Power Cable</span>")
        self.setSubTitle(f"<span style='color:{colors.BasePalette.DARK_GRAY};'>Please connect Artie's power cable before proceeding.</span>")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Add illustration/icon
        icon_label = QtWidgets.QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_label.setMinimumHeight(200)
        icon_label.setText("🔌")
        icon_label.setStyleSheet("font-size: 48px; color: #666;")
        layout.addWidget(icon_label)
        
        # Instructions
        instructions = QtWidgets.QLabel(
            "<ol>"
            "<li>Locate Artie's power cable</li>"
            "<li>Plug the power cable into Artie</li>"
            "<li>Plug the other end into a power outlet</li>"
            "<li>Wait for Artie to power on (indicated by LEDs)</li>"
            "</ol>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addStretch()
