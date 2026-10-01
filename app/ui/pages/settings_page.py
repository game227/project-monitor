from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.settings import Settings


class SettingsPage(QWidget):
    settings_changed = Signal()

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSpacing(16)
        scroll.setWidget(body)

        layout.addWidget(self._build_roots_group())
        layout.addWidget(self._build_ignore_group())
        layout.addWidget(self._build_toggles_group())
        layout.addWidget(self._build_intervals_group())

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._on_save)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)
        layout.addStretch(1)

    def _build_roots_group(self) -> QGroupBox:
        group = QGroupBox("Project roots")
        layout = QVBoxLayout(group)

        self._roots_list = QListWidget()
        self._roots_list.addItems(self._settings.project_roots)
        layout.addWidget(self._roots_list)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Add folder...")
        remove_btn = QPushButton("Remove selected")
        add_btn.clicked.connect(self._on_add_root)
        remove_btn.clicked.connect(self._on_remove_root)
        buttons.addWidget(add_btn)
        buttons.addWidget(remove_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return group

    def _on_add_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose a project root")
        if path:
            self._roots_list.addItem(path)

    def _on_remove_root(self) -> None:
        for item in self._roots_list.selectedItems():
            self._roots_list.takeItem(self._roots_list.row(item))

    def _build_ignore_group(self) -> QGroupBox:
        group = QGroupBox("Ignore patterns")
        layout = QVBoxLayout(group)

        self._ignore_list = QListWidget()
        self._ignore_list.addItems(self._settings.ignore_patterns)
        layout.addWidget(self._ignore_list)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Add pattern...")
        remove_btn = QPushButton("Remove selected")
        add_btn.clicked.connect(self._on_add_ignore)
        remove_btn.clicked.connect(self._on_remove_ignore)
        buttons.addWidget(add_btn)
        buttons.addWidget(remove_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return group

    def _on_add_ignore(self) -> None:
        text, ok = QInputDialog.getText(self, "Add ignore pattern", "Pattern (e.g. *.log):")
        if ok and text.strip():
            self._ignore_list.addItem(text.strip())

    def _on_remove_ignore(self) -> None:
        for item in self._ignore_list.selectedItems():
            self._ignore_list.takeItem(self._ignore_list.row(item))

    def _build_toggles_group(self) -> QGroupBox:
        group = QGroupBox("Startup behavior")
        layout = QVBoxLayout(group)

        self._cb_scan_on_startup = QCheckBox("Scan projects on startup")
        self._cb_monitor_new = QCheckBox("Monitor new projects automatically")
        self._cb_auto_detect = QCheckBox("Auto detect project type")
        self._cb_notifications = QCheckBox("Show desktop notifications")
        self._cb_auto_monitor_start = QCheckBox("Start monitoring automatically")
        self._cb_auto_add = QCheckBox("Automatically add future projects (skip the ADD/IGNORE prompt)")

        checkboxes = [
            (self._cb_scan_on_startup, self._settings.scan_on_startup),
            (self._cb_monitor_new, self._settings.monitor_new_projects_automatically),
            (self._cb_auto_detect, self._settings.auto_detect_project_type),
            (self._cb_notifications, self._settings.show_desktop_notifications),
            (self._cb_auto_monitor_start, self._settings.start_monitoring_automatically),
            (self._cb_auto_add, self._settings.auto_add_future_projects),
        ]
        for checkbox, value in checkboxes:
            checkbox.setChecked(value)
            layout.addWidget(checkbox)

        return group

    def _build_intervals_group(self) -> QGroupBox:
        group = QGroupBox("Polling intervals")
        layout = QVBoxLayout(group)

        cpu_row = QHBoxLayout()
        cpu_row.addWidget(QLabel("CPU/RAM poll interval (seconds)"))
        self._cpu_interval = QDoubleSpinBox()
        self._cpu_interval.setRange(1.0, 60.0)
        self._cpu_interval.setValue(self._settings.cpu_ram_poll_interval_seconds)
        cpu_row.addStretch(1)
        cpu_row.addWidget(self._cpu_interval)
        layout.addLayout(cpu_row)

        git_row = QHBoxLayout()
        git_row.addWidget(QLabel("Git scan interval (seconds)"))
        self._git_interval = QDoubleSpinBox()
        self._git_interval.setRange(2.0, 120.0)
        self._git_interval.setValue(self._settings.git_scan_interval_seconds)
        git_row.addStretch(1)
        git_row.addWidget(self._git_interval)
        layout.addLayout(git_row)

        note = QLabel("Changes to project roots and intervals take effect after restarting Project Monitor.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _on_save(self) -> None:
        self._settings.project_roots = [
            self._roots_list.item(i).text() for i in range(self._roots_list.count())
        ]
        self._settings.ignore_patterns = [
            self._ignore_list.item(i).text() for i in range(self._ignore_list.count())
        ]
        self._settings.scan_on_startup = self._cb_scan_on_startup.isChecked()
        self._settings.monitor_new_projects_automatically = self._cb_monitor_new.isChecked()
        self._settings.auto_detect_project_type = self._cb_auto_detect.isChecked()
        self._settings.show_desktop_notifications = self._cb_notifications.isChecked()
        self._settings.start_monitoring_automatically = self._cb_auto_monitor_start.isChecked()
        self._settings.auto_add_future_projects = self._cb_auto_add.isChecked()
        self._settings.cpu_ram_poll_interval_seconds = self._cpu_interval.value()
        self._settings.git_scan_interval_seconds = self._git_interval.value()

        self._settings.save()
        self.settings_changed.emit()
