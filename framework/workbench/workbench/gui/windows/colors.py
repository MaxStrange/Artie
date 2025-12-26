"""
This module contains color definitions for the workbench GUI windows.
Please try to only use these colors to ensure a consistent look and feel.
"""
import enum


class BasePalette(enum.StrEnum):
    """Base colors used in workbench windows."""
    
    # Dark backgrounds
    DARKEST = "#1e1e1e"
    """Very dark background color."""
    
    DARK = "#2b2b2b"
    """Dark background color."""
    
    DARK_ACCENT = "#3c3c3c"
    """Lighter dark background color."""
    
    MEDIUM_DARK = "#4a4a4a"
    """Medium dark background/hover color."""
    
    # Grays
    GRAY = "#555555"
    """Medium gray for borders and handles."""
    
    GRAY_DISABLED = "#777777"
    """Gray for disabled text."""
    
    GRAY_LIGHT = "#999999"
    """Light gray for disabled elements."""
    
    # Light colors
    LIGHT = "#e0e0e0"
    """Light gray text color."""
    
    WHITE = "#ffffff"
    """Pure white color."""
    
    # Green accents
    GREEN_DARK = "#2da042"
    """Dark green for pressed state."""
    
    GREEN = "#41cd52"
    """Primary green accent color."""
    
    GREEN_LIGHT = "#4ee75e"
    """Light green for hover state."""
    
    # Red
    RED = "#f44336"
    """Red color for errors and warnings."""
    
    # Special
    TRANSPARENT = "transparent"
    """Transparent color."""
    
    BLACK = "#000000"
    """Pure black color."""
    
    DARK_GRAY = "#333333"
    """Dark gray color."""


class QMainWindowStyle(enum.StrEnum):
    """Colors for QMainWindow styling."""
    BACKGROUND = BasePalette.DARK
    COLOR = BasePalette.LIGHT
    
    @property
    def stylesheet(self) -> str:
        """Generate QMainWindow stylesheet."""
        return f"""
QMainWindow {{
    background-color: {QMainWindowStyle.BACKGROUND};
    color: {QMainWindowStyle.COLOR};
}}
"""


class QMenuBarStyle(enum.StrEnum):
    """Colors for QMenuBar styling."""
    BACKGROUND = BasePalette.DARK_ACCENT
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GREEN
    ITEM_SELECTED_BG = BasePalette.GREEN
    ITEM_SELECTED_COLOR = BasePalette.WHITE
    ITEM_PRESSED_BG = BasePalette.GREEN_DARK
    
    @property
    def stylesheet(self) -> str:
        """Generate QMenuBar stylesheet."""
        return f"""
QMenuBar {{
    background-color: {QMenuBarStyle.BACKGROUND};
    color: {QMenuBarStyle.COLOR};
    border-bottom: 2px solid {QMenuBarStyle.BORDER};
    padding: 4px;
}}

QMenuBar::item {{
    background-color: {BasePalette.TRANSPARENT};
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {QMenuBarStyle.ITEM_SELECTED_BG};
    color: {QMenuBarStyle.ITEM_SELECTED_COLOR};
}}

QMenuBar::item:pressed {{
    background-color: {QMenuBarStyle.ITEM_PRESSED_BG};
}}
"""


class QMenuStyle(enum.StrEnum):
    """Colors for QMenu styling."""
    BACKGROUND = BasePalette.DARK_ACCENT
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GREEN
    ITEM_SELECTED_BG = BasePalette.GREEN
    ITEM_SELECTED_COLOR = BasePalette.WHITE
    SEPARATOR = BasePalette.GRAY
    
    @property
    def stylesheet(self) -> str:
        """Generate QMenu stylesheet."""
        return f"""
QMenu {{
    background-color: {QMenuStyle.BACKGROUND};
    color: {QMenuStyle.COLOR};
    border: 1px solid {QMenuStyle.BORDER};
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {QMenuStyle.ITEM_SELECTED_BG};
    color: {QMenuStyle.ITEM_SELECTED_COLOR};
}}

QMenu::separator {{
    height: 1px;
    background-color: {QMenuStyle.SEPARATOR};
    margin: 4px 8px;
}}
"""


class QPushButtonStyle(enum.StrEnum):
    """Colors for QPushButton styling."""
    BACKGROUND = BasePalette.GREEN
    COLOR = BasePalette.WHITE
    HOVER_BG = BasePalette.GREEN_LIGHT
    PRESSED_BG = BasePalette.GREEN_DARK
    DISABLED_BG = BasePalette.GRAY
    DISABLED_COLOR = BasePalette.GRAY_LIGHT
    
    @property
    def stylesheet(self) -> str:
        """Generate QPushButton stylesheet."""
        return f"""
QPushButton {{
    background-color: {QPushButtonStyle.BACKGROUND};
    color: {QPushButtonStyle.COLOR};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {QPushButtonStyle.HOVER_BG};
}}

QPushButton:pressed {{
    background-color: {QPushButtonStyle.PRESSED_BG};
}}

QPushButton:disabled {{
    background-color: {QPushButtonStyle.DISABLED_BG};
    color: {QPushButtonStyle.DISABLED_COLOR};
}}
"""


class QTabWidgetStyle(enum.StrEnum):
    """Colors for QTabWidget styling."""
    PANE_BORDER = BasePalette.GRAY
    PANE_BG = BasePalette.DARK
    TAB_BG = BasePalette.DARK_ACCENT
    TAB_COLOR = BasePalette.LIGHT
    TAB_BORDER = BasePalette.GRAY
    TAB_SELECTED_BG = BasePalette.GREEN
    TAB_SELECTED_COLOR = BasePalette.WHITE
    TAB_HOVER_BG = BasePalette.MEDIUM_DARK
    
    @property
    def stylesheet(self) -> str:
        """Generate QTabWidget stylesheet."""
        return f"""
QTabWidget::pane {{
    border: 1px solid {QTabWidgetStyle.PANE_BORDER};
    background-color: {QTabWidgetStyle.PANE_BG};
    border-radius: 4px;
}}

QTabBar::tab {{
    background-color: {QTabWidgetStyle.TAB_BG};
    color: {QTabWidgetStyle.TAB_COLOR};
    border: 1px solid {QTabWidgetStyle.TAB_BORDER};
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background-color: {QTabWidgetStyle.TAB_SELECTED_BG};
    color: {QTabWidgetStyle.TAB_SELECTED_COLOR};
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background-color: {QTabWidgetStyle.TAB_HOVER_BG};
}}
"""


class QTextEditStyle(enum.StrEnum):
    """Colors for QTextEdit and QTextBrowser styling."""
    BACKGROUND = BasePalette.DARKEST
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GRAY
    SELECTION_BG = BasePalette.GREEN
    SELECTION_COLOR = BasePalette.WHITE
    
    @property
    def stylesheet(self) -> str:
        """Generate QTextEdit stylesheet."""
        return f"""
QTextEdit, QTextBrowser {{
    background-color: {QTextEditStyle.BACKGROUND};
    color: {QTextEditStyle.COLOR};
    border: 1px solid {QTextEditStyle.BORDER};
    border-radius: 4px;
    padding: 4px;
    selection-background-color: {QTextEditStyle.SELECTION_BG};
    selection-color: {QTextEditStyle.SELECTION_COLOR};
}}
"""


class QLineEditStyle(enum.StrEnum):
    """Colors for QLineEdit styling."""
    BACKGROUND = BasePalette.DARK_ACCENT
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GRAY
    FOCUS_BORDER = BasePalette.GREEN
    DISABLED_BG = BasePalette.DARK
    DISABLED_COLOR = BasePalette.GRAY_DISABLED
    SELECTION_BG = BasePalette.GREEN
    SELECTION_COLOR = BasePalette.WHITE
    
    @property
    def stylesheet(self) -> str:
        """Generate QLineEdit stylesheet."""
        return f"""
QLineEdit {{
    background-color: {QLineEditStyle.BACKGROUND};
    color: {QLineEditStyle.COLOR};
    border: 1px solid {QLineEditStyle.BORDER};
    border-radius: 4px;
    padding: 6px;
    selection-background-color: {QLineEditStyle.SELECTION_BG};
    selection-color: {QLineEditStyle.SELECTION_COLOR};
}}

QLineEdit:focus {{
    border: 1px solid {QLineEditStyle.FOCUS_BORDER};
}}

QLineEdit:disabled {{
    background-color: {QLineEditStyle.DISABLED_BG};
    color: {QLineEditStyle.DISABLED_COLOR};
}}
"""


class QComboBoxStyle(enum.StrEnum):
    """Colors for QComboBox styling."""
    BACKGROUND = BasePalette.DARK_ACCENT
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GRAY
    HOVER_BORDER = BasePalette.GREEN
    FOCUS_BORDER = BasePalette.GREEN
    ARROW_COLOR = BasePalette.LIGHT
    VIEW_BG = BasePalette.DARK_ACCENT
    VIEW_COLOR = BasePalette.LIGHT
    VIEW_BORDER = BasePalette.GREEN
    SELECTION_BG = BasePalette.GREEN
    SELECTION_COLOR = BasePalette.WHITE
    
    @property
    def stylesheet(self) -> str:
        """Generate QComboBox stylesheet."""
        return f"""
QComboBox {{
    background-color: {QComboBoxStyle.BACKGROUND};
    color: {QComboBoxStyle.COLOR};
    border: 1px solid {QComboBoxStyle.BORDER};
    border-radius: 4px;
    padding: 6px;
    min-width: 100px;
}}

QComboBox:hover {{
    border: 1px solid {QComboBoxStyle.HOVER_BORDER};
}}

QComboBox:focus {{
    border: 1px solid {QComboBoxStyle.FOCUS_BORDER};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid {BasePalette.TRANSPARENT};
    border-right: 4px solid {BasePalette.TRANSPARENT};
    border-top: 6px solid {QComboBoxStyle.ARROW_COLOR};
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {QComboBoxStyle.VIEW_BG};
    color: {QComboBoxStyle.VIEW_COLOR};
    border: 1px solid {QComboBoxStyle.VIEW_BORDER};
    selection-background-color: {QComboBoxStyle.SELECTION_BG};
    selection-color: {QComboBoxStyle.SELECTION_COLOR};
    padding: 4px;
}}
"""


class QCheckBoxStyle(enum.StrEnum):
    """Colors for QCheckBox styling."""
    COLOR = BasePalette.LIGHT
    INDICATOR_BORDER = BasePalette.GRAY
    INDICATOR_BG = BasePalette.DARK_ACCENT
    HOVER_BORDER = BasePalette.GREEN
    CHECKED_BG = BasePalette.GREEN
    CHECKED_BORDER = BasePalette.GREEN
    CHECKED_HOVER_BG = BasePalette.GREEN_LIGHT
    
    @property
    def stylesheet(self) -> str:
        """Generate QCheckBox stylesheet."""
        return f"""
QCheckBox {{
    color: {QCheckBoxStyle.COLOR};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {QCheckBoxStyle.INDICATOR_BORDER};
    border-radius: 4px;
    background-color: {QCheckBoxStyle.INDICATOR_BG};
}}

QCheckBox::indicator:hover {{
    border: 2px solid {QCheckBoxStyle.HOVER_BORDER};
}}

QCheckBox::indicator:checked {{
    background-color: {QCheckBoxStyle.CHECKED_BG};
    border: 2px solid {QCheckBoxStyle.CHECKED_BORDER};
    image: none;
}}

QCheckBox::indicator:checked:hover {{
    background-color: {QCheckBoxStyle.CHECKED_HOVER_BG};
}}
"""


class QSpinBoxStyle(enum.StrEnum):
    """Colors for QSpinBox styling."""
    BACKGROUND = BasePalette.DARK_ACCENT
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GRAY
    FOCUS_BORDER = BasePalette.GREEN
    BUTTON_BG = BasePalette.MEDIUM_DARK
    BUTTON_HOVER_BG = BasePalette.GREEN
    
    @property
    def stylesheet(self) -> str:
        """Generate QSpinBox stylesheet."""
        return f"""
QSpinBox {{
    background-color: {QSpinBoxStyle.BACKGROUND};
    color: {QSpinBoxStyle.COLOR};
    border: 1px solid {QSpinBoxStyle.BORDER};
    border-radius: 4px;
    padding: 4px;
}}

QSpinBox:focus {{
    border: 1px solid {QSpinBoxStyle.FOCUS_BORDER};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {QSpinBoxStyle.BUTTON_BG};
    border: none;
    width: 16px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {QSpinBoxStyle.BUTTON_HOVER_BG};
}}
"""


class QLabelStyle(enum.StrEnum):
    """Colors for QLabel styling."""
    COLOR = BasePalette.LIGHT
    
    @property
    def stylesheet(self) -> str:
        """Generate QLabel stylesheet."""
        return f"""
QLabel {{
    color: {QLabelStyle.COLOR};
}}
"""


class QGroupBoxStyle(enum.StrEnum):
    """Colors for QGroupBox styling."""
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GRAY
    TITLE_COLOR = BasePalette.GREEN
    
    @property
    def stylesheet(self) -> str:
        """Generate QGroupBox stylesheet."""
        return f"""
QGroupBox {{
    color: {QGroupBoxStyle.COLOR};
    border: 2px solid {QGroupBoxStyle.BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {QGroupBoxStyle.TITLE_COLOR};
}}
"""


class QStatusBarStyle(enum.StrEnum):
    """Colors for QStatusBar styling."""
    BACKGROUND = BasePalette.DARK_ACCENT
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GRAY
    
    @property
    def stylesheet(self) -> str:
        """Generate QStatusBar stylesheet."""
        return f"""
QStatusBar {{
    background-color: {QStatusBarStyle.BACKGROUND};
    color: {QStatusBarStyle.COLOR};
    border-top: 1px solid {QStatusBarStyle.BORDER};
}}

QStatusBar::item {{
    border: none;
}}
"""


class QScrollBarStyle(enum.StrEnum):
    """Colors for QScrollBar styling."""
    BACKGROUND = BasePalette.DARK
    HANDLE = BasePalette.GRAY
    HANDLE_HOVER = BasePalette.GREEN
    
    @property
    def stylesheet(self) -> str:
        """Generate QScrollBar stylesheet."""
        return f"""
QScrollBar:vertical {{
    background-color: {QScrollBarStyle.BACKGROUND};
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {QScrollBarStyle.HANDLE};
    min-height: 20px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {QScrollBarStyle.HANDLE_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {QScrollBarStyle.BACKGROUND};
    height: 12px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {QScrollBarStyle.HANDLE};
    min-width: 20px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {QScrollBarStyle.HANDLE_HOVER};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
"""


class QDialogStyle(enum.StrEnum):
    """Colors for QDialog styling."""
    BACKGROUND = BasePalette.DARK
    COLOR = BasePalette.LIGHT
    
    @property
    def stylesheet(self) -> str:
        """Generate QDialog stylesheet."""
        return f"""
QDialog {{
    background-color: {QDialogStyle.BACKGROUND};
    color: {QDialogStyle.COLOR};
}}
"""


class QMessageBoxStyle(enum.StrEnum):
    """Colors for QMessageBox styling."""
    BACKGROUND = BasePalette.DARK
    LABEL_COLOR = BasePalette.LIGHT
    
    @property
    def stylesheet(self) -> str:
        """Generate QMessageBox stylesheet."""
        return f"""
QMessageBox {{
    background-color: {QMessageBoxStyle.BACKGROUND};
}}

QMessageBox QLabel {{
    color: {QMessageBoxStyle.LABEL_COLOR};
}}

QMessageBox QPushButton {{
    min-width: 70px;
}}
"""


class QToolTipStyle(enum.StrEnum):
    """Colors for QToolTip styling."""
    BACKGROUND = BasePalette.DARK_ACCENT
    COLOR = BasePalette.LIGHT
    BORDER = BasePalette.GREEN
    
    @property
    def stylesheet(self) -> str:
        """Generate QToolTip stylesheet."""
        return f"""
QToolTip {{
    background-color: {QToolTipStyle.BACKGROUND};
    color: {QToolTipStyle.COLOR};
    border: 1px solid {QToolTipStyle.BORDER};
    padding: 4px;
    border-radius: 4px;
}}
"""


class QWizardStyle(enum.StrEnum):
    """Colors for QWizard styling."""
    BACKGROUND = BasePalette.WHITE
    PAGE_BACKGROUND = BasePalette.WHITE
    TITLE_COLOR = BasePalette.BLACK
    SUBTITLE_COLOR = BasePalette.DARK_GRAY
    
    @property
    def stylesheet(self) -> str:
        """Generate QWizard stylesheet."""
        return f"""
QWizard {{
    background-color: {QWizardStyle.BACKGROUND};
}}

QWizardPage {{
    background-color: {QWizardStyle.PAGE_BACKGROUND};
}}

QWizard QLabel {{
    color: {BasePalette.BLACK};
}}

QLabel#qt_wizard_title {{
    color: {QWizardStyle.TITLE_COLOR};
    font-weight: bold;
    font-size: 14pt;
}}

QLabel#qt_wizard_subtitle {{
    color: {QWizardStyle.SUBTITLE_COLOR};
    font-size: 10pt;
}}
"""


def generate_full_stylesheet() -> str:
    """
    Generate the complete application stylesheet by combining all component stylesheets.
    
    Returns:
        Complete Qt stylesheet string for the application.
    """
    styles = [
        QMainWindowStyle.BACKGROUND.stylesheet,
        QMenuBarStyle.BACKGROUND.stylesheet,
        QMenuStyle.BACKGROUND.stylesheet,
        QPushButtonStyle.BACKGROUND.stylesheet,
        QTabWidgetStyle.PANE_BG.stylesheet,
        QTextEditStyle.BACKGROUND.stylesheet,
        QLineEditStyle.BACKGROUND.stylesheet,
        QComboBoxStyle.BACKGROUND.stylesheet,
        QCheckBoxStyle.COLOR.stylesheet,
        QSpinBoxStyle.BACKGROUND.stylesheet,
        QLabelStyle.COLOR.stylesheet,
        QGroupBoxStyle.COLOR.stylesheet,
        QStatusBarStyle.BACKGROUND.stylesheet,
        QScrollBarStyle.BACKGROUND.stylesheet,
        QDialogStyle.BACKGROUND.stylesheet,
        QMessageBoxStyle.BACKGROUND.stylesheet,
        QToolTipStyle.BACKGROUND.stylesheet,
        QWizardStyle.BACKGROUND.stylesheet,
    ]
    
    return "/* Qt Green Theme - Generated from colors.py */\n" + "\n".join(styles)
