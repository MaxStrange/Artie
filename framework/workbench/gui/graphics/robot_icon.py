from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QPainter
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QPen
from PyQt6.QtWidgets import QLabel

class RobotIcon(QLabel):
    """Custom widget to draw a simple robot icon"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.create_robot_pixmap()
    
    def create_robot_pixmap(self):
        """Create a simple robot icon using QPainter"""
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Robot head (rectangle)
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(8, 10, 24, 20)
        
        # Antenna
        painter.drawLine(20, 10, 20, 5)
        painter.drawEllipse(18, 3, 4, 4)
        
        # Eyes
        painter.setBrush(QColor(50, 50, 50))
        painter.drawEllipse(13, 16, 4, 4)
        painter.drawEllipse(23, 16, 4, 4)
        
        # Mouth
        painter.drawLine(15, 24, 25, 24)
        
        painter.end()
        self.setPixmap(pixmap)
