"""
This module contains the code for the settings dialog.
"""
import dataclasses
from PyQt6 import QtWidgets, QtCore, QtGui
from model import settings

class _SettingsWidgetWrapper:
    """Wrapper for a single settings field widget"""

    def __init__(self, settings_field_name: str, get_value_callback, widget: QtWidgets.QWidget):
        self._get_value_callback = get_value_callback
        self._settings_field_name = settings_field_name
        self._widget = widget

    @property
    def widget(self):
        """Get the underlying widget"""
        return self._widget

    def get_settings_value(self):
        """Get the current value from the widget"""
        return self._get_value_callback()

    def get_field_name(self):
        """Get the name of the settings field this widget represents"""
        return self._settings_field_name


class SettingsDialog(QtWidgets.QDialog):
    """Dialog for modifying Workbench settings"""

    def __init__(self, current_settings: settings.WorkbenchSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.current_settings = current_settings
        self.updated_settings = None
        self._settings_widgets = []

        # Layout
        layout = QtWidgets.QVBoxLayout()

        for field in dataclasses.fields(settings.WorkbenchSettings):
            view_option = field.metadata.get('view', None)
            widget = self._create_widget_for_field(field, view_option)
            if widget is not None:
                layout.addWidget(widget.widget)
                self._settings_widgets.append(widget)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._apply_settings)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)
        self.setLayout(layout)

    def _apply_settings(self):
        """Apply the settings and emit the signal"""
        kwargs = dataclasses.asdict(self.current_settings)
        new_settings = settings.WorkbenchSettings(**kwargs)
        for widget in self._settings_widgets:
            updated_value = widget.get_settings_value()
            field_name = widget.get_field_name()
            setattr(new_settings, field_name, updated_value)

        self.updated_settings = new_settings
        self.accept()

    def _create_widget_for_field(self, field: dataclasses.Field, view_option: settings.GuiViewOption|None) -> _SettingsWidgetWrapper|None:
        """Create a widget for a given settings field based on its view option"""
        match view_option:
            case None:
                return None
            case settings.GuiViewOption.DIRECTORY_PICKER:
                return self._create_directory_picker(field)
            case settings.GuiViewOption.FLOATING_POINT_INPUT:
                return self._create_floating_point_input_widget(field)
            case settings.GuiViewOption.INTEGER_INPUT:
                return self._create_integer_input_widget(field)
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

        return _SettingsWidgetWrapper(field.name, lambda: line_edit.text(), container)

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

        return _SettingsWidgetWrapper(field.name, lambda: line_edit.text(), container)

    def _create_floating_point_input_widget(self, field: dataclasses.Field):
        """Create a widget for inputting a floating point value."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)

        label = QtWidgets.QLabel(field.name.replace('_', ' ').capitalize())
        line_edit = QtWidgets.QLineEdit(str(getattr(self.current_settings, field.name)))

        if 'bottom' in field.metadata or 'top' in field.metadata or 'decimals' in field.metadata:
            validator = QtGui.QDoubleValidator()
            if 'bottom' in field.metadata and field.metadata['bottom'] is not None:
                validator.setBottom(field.metadata['bottom'])
            if 'top' in field.metadata and field.metadata['top'] is not None:
                validator.setTop(field.metadata['top'])
            if 'decimals' in field.metadata and field.metadata['decimals'] is not None:
                validator.setDecimals(field.metadata['decimals'])
            line_edit.setValidator(validator)

        layout.addWidget(label)
        layout.addWidget(line_edit)

        return _SettingsWidgetWrapper(field.name, lambda: float(line_edit.text()), container)

    def _create_integer_input_widget(self, field: dataclasses.Field):
        """Create a widget for inputting an integer value."""
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)

        label = QtWidgets.QLabel(field.name.replace('_', ' ').capitalize())
        line_edit = QtWidgets.QLineEdit(str(getattr(self.current_settings, field.name)))

        if 'bottom' in field.metadata or 'top' in field.metadata:
            validator = QtGui.QIntValidator()
            if 'bottom' in field.metadata and field.metadata['bottom'] is not None:
                validator.setBottom(field.metadata['bottom'])
            if 'top' in field.metadata and field.metadata['top'] is not None:
                validator.setTop(field.metadata['top'])
            line_edit.setValidator(validator)

        layout.addWidget(label)
        layout.addWidget(line_edit)

        return _SettingsWidgetWrapper(field.name, lambda: int(line_edit.text()), container)

    def get_updated_settings(self) -> settings.WorkbenchSettings:
        """Retrieve the updated settings from the dialog"""
        return self.updated_settings
