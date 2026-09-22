"""
Modern Linux Desktop Stylesheet and Palettes for FocusFlow.
Adwaita / Breeze inspired calm, distraction-free dark and light themes.
"""

DARK_THEME = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Cantarell', 'Inter', 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #181825;
    border-right: 1px solid #313244;
    min-width: 210px;
    max-width: 210px;
}

QLabel#SidebarTitle {
    font-size: 17px;
    font-weight: bold;
    color: #ffffff;
    padding: 18px 12px 12px 16px;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #a6adc8;
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    margin: 3px 10px;
    font-size: 13px;
    font-weight: 500;
    border: none;
}

QPushButton#NavButton:hover {
    background-color: #313244;
    color: #ffffff;
}

QPushButton#NavButton:checked {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
}

/* Content Container */
QFrame#ContentPane {
    background-color: #1e1e2e;
}

/* Cards */
QFrame.Card {
    background-color: #24273a;
    border-radius: 12px;
    border: 1px solid #363a4f;
    padding: 16px;
}

/* Buttons */
QPushButton {
    background-color: #363a4f;
    color: #cdd6f4;
    border: 1px solid #494d64;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #494d64;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #5b6078;
}

QPushButton:disabled {
    background-color: #1e1e2e;
    color: #6c7086;
    border-color: #313244;
}

QPushButton.Primary {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
}

QPushButton.Primary:hover {
    background-color: #2563eb;
}

QPushButton.Success {
    background-color: #10b981;
    color: #ffffff;
    border: none;
}

QPushButton.Success:hover {
    background-color: #059669;
}

QPushButton.Danger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
}

QPushButton.Danger:hover {
    background-color: #dc2626;
}

/* Inputs & Form Controls */
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #363a4f;
    border-radius: 8px;
    padding: 8px 12px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3b82f6;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #494d64;
    background-color: #181825;
}

QCheckBox::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #181825;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #494d64;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #5b6078;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_THEME = """
QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Cantarell', 'Inter', 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QFrame#Sidebar {
    background-color: #f1f5f9;
    border-right: 1px solid #e2e8f0;
    min-width: 210px;
    max-width: 210px;
}

QLabel#SidebarTitle {
    font-size: 17px;
    font-weight: bold;
    color: #0f172a;
    padding: 18px 12px 12px 16px;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #475569;
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    margin: 3px 10px;
    font-size: 13px;
    font-weight: 500;
    border: none;
}

QPushButton#NavButton:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}

QPushButton#NavButton:checked {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: bold;
}

QFrame#ContentPane {
    background-color: #f8fafc;
}

QFrame.Card {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 16px;
}

QPushButton {
    background-color: #f1f5f9;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #e2e8f0;
}

QPushButton.Primary {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
}

QPushButton.Primary:hover {
    background-color: #1d4ed8;
}

QPushButton.Success {
    background-color: #10b981;
    color: #ffffff;
    border: none;
}

QPushButton.Danger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
}

QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #2563eb;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
}

QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 4px;
}
"""
