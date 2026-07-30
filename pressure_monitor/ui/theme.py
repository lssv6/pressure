"""Dark colour scheme shared by the widgets and the plot."""

from __future__ import annotations

BACKGROUND = "#14161c"
PANEL = "#1b1f27"
PANEL_RAISED = "#232936"
BORDER = "#2c323f"
TEXT = "#e6e9ef"
TEXT_MUTED = "#8b93a7"
ACCENT = "#4cc9f0"
ACCENT_PRESSED = "#33a8cc"
DANGER = "#ef476f"
GRID = "#3a4152"

CHANNEL_COLORS = ("#4cc9f0", "#ffb703")

STYLESHEET = f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-size: 13px;
}}
QGroupBox {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: {TEXT_MUTED};
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 1px;
}}
QLabel[role="caption"] {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}
QLabel[role="reading"] {{
    font-size: 22px;
    font-weight: 600;
}}
QLabel[role="unit"] {{
    color: {TEXT_MUTED};
    font-size: 12px;
    padding-bottom: 4px;
}}
QComboBox, QDoubleSpinBox {{
    background-color: {PANEL_RAISED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 20px;
}}
QComboBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL_RAISED};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: {BACKGROUND};
    outline: none;
}}
QPushButton {{
    background-color: {PANEL_RAISED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 20px;
}}
QPushButton:hover {{
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {BORDER};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
}}
QPushButton[role="primary"] {{
    background-color: {ACCENT};
    border: none;
    color: {BACKGROUND};
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{
    background-color: #6fd6f5;
}}
QPushButton[role="primary"]:pressed {{
    background-color: {ACCENT_PRESSED};
}}
QPushButton[role="danger"] {{
    background-color: transparent;
    border: 1px solid {DANGER};
    color: {DANGER};
    font-weight: 600;
}}
QPushButton[role="danger"]:hover {{
    background-color: rgba(239, 71, 111, 0.12);
}}
QSlider::groove:horizontal {{
    background: {PANEL_RAISED};
    height: 4px;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}
QStatusBar {{
    background-color: {PANEL};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
}}
QStatusBar::item {{
    border: none;
}}
QSplitter::handle {{
    background-color: {BACKGROUND};
}}
"""
