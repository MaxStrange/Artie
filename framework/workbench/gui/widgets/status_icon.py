"""
Status icon widget for displaying hardware/software component status
"""
from PyQt6 import QtWidgets, QtCore, QtGui


class StatusIcon(QtWidgets.QWidget):
    """A status icon with tooltip showing component health"""
    
    # Status colors
    STATUS_COLORS = {
        "online": "#4CAF50",      # Green
        "offline": "#F44336",     # Red
        "running": "#4CAF50",     # Green
        "waiting": "#FFC107",     # Amber
        "terminated": "#F44336",  # Red
        "unknown": "#9E9E9E",     # Gray
        "error": "#F44336",       # Red
        "not_implemented": "#2196F3"  # Blue
    }
    
    def __init__(self, name: str, status: str = "unknown", details: dict = None, parent=None):
        super().__init__(parent)
        self.name = name
        self.status = status
        self.details = details or {}
        
        self.setFixedSize(100, 80)
        self._setup_tooltip()
    
    def _setup_tooltip(self):
        """Setup the tooltip with detailed information"""
        tooltip_lines = [f"<b>{self.name}</b>", f"Status: {self.status}"]
        
        # Add details based on what's available
        if "role" in self.details:
            tooltip_lines.append(f"Role: {self.details['role']}")
        
        if "node" in self.details:
            tooltip_lines.append(f"Node: {self.details['node']}")
        
        if "containers" in self.details:
            tooltip_lines.append(f"Containers: {len(self.details['containers'])}")
            for container in self.details['containers']:
                tooltip_lines.append(f"  • {container['name']}: {container['state']}")
        
        if "buses" in self.details:
            tooltip_lines.append(f"Buses: {', '.join(self.details['buses'])}")
        
        if "type" in self.details:
            tooltip_lines.append(f"Type: {self.details['type']}")
        
        if "bus" in self.details:
            tooltip_lines.append(f"Bus: {self.details['bus']}")
        
        if "message" in self.details:
            tooltip_lines.append(f"Message: {self.details['message']}")
        
        if "error" in self.details:
            tooltip_lines.append(f"<font color='red'>Error: {self.details['error']}</font>")
        
        self.setToolTip("<br>".join(tooltip_lines))
    
    def update_status(self, status: str, details: dict = None):
        """Update the status and details"""
        self.status = status
        if details:
            self.details = details
        self._setup_tooltip()
        self.update()
    
    def paintEvent(self, event):
        """Paint the status icon"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # Draw background rectangle
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#F5F5F5")))
        painter.setPen(QtGui.QPen(QtGui.QColor("#E0E0E0"), 1))
        painter.drawRoundedRect(rect, 5, 5)
        
        # Draw status indicator circle
        status_color = self.STATUS_COLORS.get(self.status, self.STATUS_COLORS["unknown"])
        painter.setBrush(QtGui.QBrush(QtGui.QColor(status_color)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        
        circle_rect = QtCore.QRect(rect.center().x() - 12, rect.top() + 10, 24, 24)
        painter.drawEllipse(circle_rect)
        
        # Draw component name
        painter.setPen(QtGui.QColor("#333333"))
        font = painter.font()
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        text_rect = QtCore.QRect(rect.left(), circle_rect.bottom() + 5, rect.width(), 20)
        painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignCenter, self.name)


class StatusGrid(QtWidgets.QWidget):
    """A grid layout of status icons"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.status_icons = {}
    
    def add_status_icon(self, name: str, status: str = "unknown", details: dict = None, row: int = None, col: int = None):
        """Add a status icon to the grid"""
        icon = StatusIcon(name, status, details, self)
        self.status_icons[name] = icon
        
        if row is not None and col is not None:
            self.layout.addWidget(icon, row, col)
        else:
            # Auto-arrange in grid
            count = len(self.status_icons) - 1
            cols = 5  # 5 items per row
            self.layout.addWidget(icon, count // cols, count % cols)
        
        return icon
    
    def update_status_icon(self, name: str, status: str, details: dict = None):
        """Update an existing status icon"""
        if name in self.status_icons:
            self.status_icons[name].update_status(status, details)
    
    def clear_icons(self):
        """Remove all status icons"""
        for icon in self.status_icons.values():
            self.layout.removeWidget(icon)
            icon.deleteLater()
        self.status_icons.clear()
