"""
This module contains the code for the settings dialog.
"""
import dataclasses
from PyQt6 import QtWidgets, QtCore
from model import settings

class SettingsDialog(QtWidgets.QDialog):
    """Dialog for modifying Workbench settings"""

    settings_changed_signal = QtCore.pyqtSignal(settings.WorkbenchSettings)

    def __init__(self, current_settings: settings.WorkbenchSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.current_settings = current_settings

        # Layout
        layout = QtWidgets.QVBoxLayout()

        for field in dataclasses.fields(settings.WorkbenchSettings):
            view_option = field.metadata.get('view', None)
            widget = self._create_widget_for_field(field, view_option)
            if widget is not None:
                layout.addWidget(widget)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._apply_settings)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)
        self.setLayout(layout)

    def _apply_settings(self):
        """Apply the settings and emit the signal"""
        # TODO: In case there are any settings that need special handling, do it here
        self.accept()

    def _create_widget_for_field(self, field: dataclasses.Field, view_option: settings.GuiViewOption|None):
        """Create a widget for a given settings field based on its view option"""
        match view_option:
            case None:
                return None
            case settings.GuiViewOption.DIRECTORY_PICKER:
                return self._create_directory_picker(field)
            case _:
                return self._create_default_field_widget(field)

    def _create_default_field_widget(self, field: dataclasses.Field):
        """Create a default widget for a settings field (QLineEdit)"""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)

        label = QtWidgets.QLabel(field.name.replace('_', ' ').capitalize())
        line_edit = QtWidgets.QLineEdit(str(getattr(self.current_settings, field.name)))

        layout.addWidget(label)
        layout.addWidget(line_edit)

        return container

    def _create_directory_picker(self, field: dataclasses.Field):
        """Create a directory picker widget for a settings field"""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)

        label = QtWidgets.QLabel(field.name.replace('_', ' ').capitalize())
        line_edit = QtWidgets.QLineEdit(getattr(self.current_settings, field.name))
        browse_button = QtWidgets.QPushButton("Browse...")

        def on_browse():
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, f"Select {field.name.replace('_', ' ')}")
            if directory:
                line_edit.setText(directory)

        browse_button.clicked.connect(on_browse)

        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(browse_button)

        return container
