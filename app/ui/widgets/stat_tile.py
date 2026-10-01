from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatTile(QFrame):
    def __init__(self, label: str, value: str = "0") -> None:
        super().__init__()
        self.setObjectName("StatTile")
        self.setMinimumHeight(84)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("StatValue")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        caption = QLabel(label.upper())
        caption.setObjectName("StatLabel")

        layout.addWidget(self._value_label)
        layout.addWidget(caption)
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)
