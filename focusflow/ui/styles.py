"""
Modern Linux Desktop Stylesheet and Palettes for FocusFlow.
High-end dark productivity dashboard styling matching Image 4.
"""

from focusflow.config import ASSETS_DIR

_ARROW_UP = (ASSETS_DIR / "arrow_up.svg").as_posix()
_ARROW_DOWN = (ASSETS_DIR / "arrow_down.svg").as_posix()

DARK_THEME = """
QMainWindow, QWidget#CentralWidget, QFrame#ContentPane, QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: #0b0f19;
}

QWidget {
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', 'Noto Sans', 'Cantarell', sans-serif;
    font-size: 13px;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
}

/* Base Dialogs */
QDialog {
    background-color: #0d111d;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #080c16;
    border-right: 1px solid #141b2c;
    min-width: 220px;
    max-width: 220px;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #8b95af;
    text-align: left;
    padding: 10px 14px;
    border-radius: 10px;
    margin: 2px 10px;
    font-size: 13px;
    font-weight: 500;
    border: none;
}

QPushButton#NavButton:hover {
    background-color: #121829;
    color: #ffffff;
}

QPushButton#NavButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e2642, stop:1 #131929);
    color: #ffffff;
    font-weight: bold;
    border-left: 3.5px solid #60a5fa;
    border-top: none;
    border-right: none;
    border-bottom: none;
}

/* Badges inside Sidebar or Cards */
QLabel.Badge {
    background-color: #1a2236;
    color: #a0aec0;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

/* Cards & Elevated Panels */
QFrame#Card, QFrame.Card, QFrame[class="Card"] {
    background-color: #121727;
    border-radius: 16px;
    border: 1px solid #1c2438;
}

QFrame#Card QWidget, QFrame[class="Card"] QWidget {
    background-color: transparent;
}

QFrame.HeroCard, QFrame#HeroCard {
    border-radius: 16px;
    border: 1px solid #232c44;
}

/* Top Navigation Bar Search */
QLineEdit#SearchInput {
    background-color: #121727;
    color: #ffffff;
    border: 1px solid #1f273e;
    border-radius: 18px;
    padding: 7px 16px;
    font-size: 13px;
}

QLineEdit#SearchInput:focus {
    border: 1px solid #6366f1;
    background-color: #151b2e;
}

/* General Buttons */
QPushButton {
    background-color: #161c2e;
    color: #cbd5e1;
    border: 1px solid #222b42;
    border-radius: 10px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #20283f;
    color: #ffffff;
    border-color: #313d5e;
}

QPushButton:pressed {
    background-color: #2a3452;
}

QPushButton:disabled {
    background-color: #0f1422;
    color: #4b5568;
    border-color: #161d2d;
}

/* Gradient Action Buttons */
QPushButton.Primary, QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #3b82f6);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-weight: bold;
}

QPushButton.Primary:hover, QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #2563eb);
}

QPushButton.Success {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-weight: bold;
}

QPushButton.Success:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
}

QPushButton.Danger {
    background-color: #991b1b;
    color: #ffffff;
    border: 1px solid #dc2626;
    border-radius: 10px;
}

QPushButton.Danger:hover {
    background-color: #b91c1c;
}

/* Pills & Segmented Controls */
QPushButton.Pill {
    background-color: #161b2b;
    color: #8a94ac;
    border: 1px solid #222a3f;
    border-radius: 14px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton.Pill:hover {
    background-color: #212940;
    color: #ffffff;
}

QPushButton.Pill:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
    color: #ffffff;
    border: none;
}

/* Inputs & Form Controls */
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {
    background-color: #111625;
    color: #e2e8f0;
    border: 1px solid #1e263d;
    border-radius: 10px;
    padding: 8px 12px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
    border: 1px solid #6366f1;
    background-color: #141a2c;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QSpinBox {
    padding-right: 28px;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    height: 18px;
    border-left: 1px solid #1e263d;
    border-bottom: 1px solid #1e263d;
    border-top-right-radius: 9px;
    background-color: #161c2e;
}

QSpinBox::up-button:hover {
    background-color: #232c45;
}

QSpinBox::up-arrow {
    image: url(__ARROW_UP__);
    width: 9px;
    height: 9px;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    height: 18px;
    border-left: 1px solid #1e263d;
    border-bottom-right-radius: 9px;
    background-color: #161c2e;
}

QSpinBox::down-button:hover {
    background-color: #232c45;
}

QSpinBox::down-arrow {
    image: url(__ARROW_DOWN__);
    width: 9px;
    height: 9px;
}

QComboBox QAbstractItemView {
    background-color: #141a2c;
    color: #e2e8f0;
    border: 1px solid #252f4c;
    border-radius: 8px;
    selection-background-color: #3b4bf6;
    selection-color: #ffffff;
    padding: 4px;
}

/* Modern Checkbox */
QCheckBox {
    spacing: 10px;
    color: #cbd5e1;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 1px solid #2d3856;
    background-color: #121727;
}

QCheckBox::indicator:hover {
    border-color: #4f5f8a;
}

QCheckBox::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #252f4c;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #3b4970;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}
""".replace("__ARROW_UP__", _ARROW_UP).replace("__ARROW_DOWN__", _ARROW_DOWN)

LIGHT_THEME = """
QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Inter', 'Segoe UI', 'Noto Sans', 'Cantarell', sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QFrame#Sidebar {
    background-color: #f1f5f9;
    border-right: 1px solid #e2e8f0;
    min-width: 220px;
    max-width: 220px;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #475569;
    text-align: left;
    padding: 10px 14px;
    border-radius: 10px;
    margin: 2px 10px;
    font-size: 13px;
    font-weight: 500;
    border: none;
}

QPushButton#NavButton:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}

QPushButton#NavButton:checked {
    background-color: #e2e8f0;
    color: #0f172a;
    font-weight: bold;
    border-left: 3.5px solid #2563eb;
    border-top: none;
    border-right: none;
    border-bottom: none;
}

QFrame#ContentPane {
    background-color: #f8fafc;
}

QFrame.Card, QFrame#Card {
    background-color: #ffffff;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    padding: 16px;
}

QPushButton {
    background-color: #f1f5f9;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
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

QLineEdit, QTextEdit, QComboBox {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 8px 12px;
}

QSpinBox {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 8px 12px;
    padding-right: 28px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #2563eb;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    height: 18px;
    border-left: 1px solid #cbd5e1;
    border-bottom: 1px solid #cbd5e1;
    border-top-right-radius: 9px;
    background-color: #f1f5f9;
}

QSpinBox::up-button:hover {
    background-color: #e2e8f0;
}

QSpinBox::up-arrow {
    image: url(__ARROW_UP__);
    width: 9px;
    height: 9px;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    height: 18px;
    border-left: 1px solid #cbd5e1;
    border-bottom-right-radius: 9px;
    background-color: #f1f5f9;
}

QSpinBox::down-button:hover {
    background-color: #e2e8f0;
}

QSpinBox::down-arrow {
    image: url(__ARROW_DOWN__);
    width: 9px;
    height: 9px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
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
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 24px;
    border-radius: 3px;
}
""".replace("__ARROW_UP__", _ARROW_UP).replace("__ARROW_DOWN__", _ARROW_DOWN)
