from PyQt6 import QtWidgets, QtCore

class SerialConnectionPage(QtWidgets.QWizardPage):
    """Page prompting user to connect serial USB cable"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Connect Serial Port USB")
        self.setSubTitle("Please connect Artie's serial port USB cable.")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Add illustration/icon
        icon_label = QtWidgets.QLabel()
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_label.setMinimumHeight(200)
        icon_label.setText("🔗")
        icon_label.setStyleSheet("font-size: 48px; color: #666;")
        layout.addWidget(icon_label)
        
        # Instructions
        instructions = QtWidgets.QLabel(
            "<ol>"
            "<li>Locate a USB serial cable</li>"
            "<li>Connect one end to Artie's serial port (on the Controller Node)</li>"
            "<li>Connect the other end to your computer's USB port</li>"
            "</ol>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addStretch()
