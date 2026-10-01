"""A single QSS stylesheet for the whole app: light, spacious, low on
color and decoration. Kept as one string so every page/widget stays
consistent without importing colors piecemeal.

Direct feedback that shaped this: the earlier dark/neon-green theme was
uncomfortable to read (dark background, cramped spacing, too much color
and status decoration, too many buttons per card). This version:
- light background, dark text -- no dark mode
- generous padding/spacing and a bigger base font size
- ONE accent color, used only for the primary action and active nav;
  status color is the only other color, and only on the status word
- plain sans-serif everywhere (monospace only for logs/paths/tables,
  where it genuinely helps reading columns of data)
"""

FONT_STACK = '"Ubuntu", "Segoe UI", "Noto Sans", system-ui, sans-serif'
FONT_MONO = '"Ubuntu Mono", "JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", monospace'

BG = "#ffffff"
BG_ELEVATED = "#f7f7f8"
BG_CARD = "#ffffff"
BG_INPUT = "#ffffff"
BORDER = "#e2e4e8"
BORDER_STRONG = "#c9cdd3"
TEXT = "#1c1f23"
TEXT_MUTED = "#6b7280"
ACCENT = "#2563eb"
ACCENT_STRONG = "#1d4ed8"
ACCENT_TEXT_ON = "#ffffff"
GREEN = "#15803d"
RED = "#dc2626"
YELLOW = "#b45309"
GRAY = "#8a8f98"

DARK_STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: {FONT_STACK};
    font-size: 14px;
}}

QMainWindow {{
    background-color: {BG};
}}

#Sidebar {{
    background-color: {BG_ELEVATED};
    border-right: 1px solid {BORDER};
}}

#Sidebar QPushButton {{
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    background-color: transparent;
    color: {TEXT_MUTED};
    font-family: {FONT_STACK};
    font-size: 14px;
}}

#Sidebar QPushButton:hover {{
    background-color: #eef0f2;
    color: {TEXT};
}}

#Sidebar QPushButton:checked {{
    background-color: #e8f0fe;
    border-left: 3px solid {ACCENT};
    color: {ACCENT};
    font-weight: 600;
}}

#SidebarTitle {{
    color: {TEXT};
    font-size: 17px;
    font-weight: 700;
    padding: 24px 20px 10px 20px;
}}

QFrame#Card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#StatTile {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QLabel#StatValue {{
    font-size: 28px;
    font-weight: 700;
    color: {TEXT};
}}

QLabel#StatLabel {{
    color: {TEXT_MUTED};
    font-size: 12px;
    letter-spacing: 0.5px;
}}

QLabel#ProjectName {{
    font-size: 16px;
    font-weight: 700;
    color: {TEXT};
}}

QLabel#Muted {{
    color: {TEXT_MUTED};
}}

QLabel#Mono {{
    font-family: {FONT_MONO};
    color: {TEXT_MUTED};
}}

QPushButton {{
    background-color: {BG};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 9px 18px;
    color: {TEXT};
    font-family: {FONT_STACK};
}}

QPushButton:hover {{
    background-color: {BG_ELEVATED};
    border: 1px solid #9aa0a8;
}}

QPushButton:disabled {{
    color: #b5b9c0;
    border: 1px solid {BORDER};
    background-color: transparent;
}}

QPushButton#Primary {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
    color: {ACCENT_TEXT_ON};
    font-weight: 600;
}}

QPushButton#Primary:hover {{
    background-color: {ACCENT_STRONG};
    border: 1px solid {ACCENT_STRONG};
    color: {ACCENT_TEXT_ON};
}}

QPushButton#Primary:disabled {{
    background-color: transparent;
    border: 1px solid {BORDER};
    color: #b5b9c0;
}}

QPushButton#Danger {{
    background-color: transparent;
    border: 1px solid #f3c2c2;
    color: {RED};
}}

QPushButton#Danger:hover {{
    background-color: #fdf1f1;
    border: 1px solid {RED};
}}

QPushButton#Danger:disabled {{
    background-color: transparent;
    border: 1px solid {BORDER};
    color: #b5b9c0;
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit, QListWidget, QTableWidget {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_TEXT_ON};
    font-family: {FONT_STACK};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {ACCENT};
}}

QPlainTextEdit, QTextEdit, QListWidget, QTableWidget {{
    font-family: {FONT_MONO};
}}

QTableWidget {{
    gridline-color: {BORDER};
}}

QHeaderView::section {{
    background-color: {BG_ELEVATED};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px;
    font-family: {FONT_STACK};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 10px 20px;
    font-family: {FONT_STACK};
}}

QTabBar::tab:selected {{
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}

QTabBar::tab:hover {{
    color: {TEXT};
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 14px;
    color: {TEXT_MUTED};
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {TEXT};
}}

QCheckBox {{
    color: {TEXT};
    spacing: 10px;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 11px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: #9aa0a8;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #9aa0a8;
}}

QToolTip {{
    background-color: {TEXT};
    color: {BG};
    border: none;
    padding: 6px 8px;
    font-family: {FONT_STACK};
}}
"""


def status_color(status: str) -> str:
    return {
        "RUNNING": GREEN,
        "STARTING": YELLOW,
        "STOPPING": YELLOW,
        "STOPPED": GRAY,
        "DISCOVERED": TEXT_MUTED,
        "CRASHED": RED,
        "ERROR": RED,
        "UNKNOWN": GRAY,
    }.get(status, GRAY)
