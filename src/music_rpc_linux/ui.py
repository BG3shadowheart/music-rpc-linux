"""Small KDE-friendly system tray interface."""
from __future__ import annotations
import asyncio
import json
import os
import sys
import threading
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFormLayout,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QSystemTrayIcon,
    QVBoxLayout, QWidget, QLabel)
from .config import CONFIG_PATH, save_config, set_autostart
from .runtime import Runtime

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
ICON = ROOT / "assets" / "music-rpc.svg"


class Worker(threading.Thread):
    def __init__(self, config, status_callback):
        super().__init__(daemon=True)
        self.runtime = Runtime(config, status_callback)
        self.loop = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.runtime.run())
        self.loop.close()

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.runtime.stop)

    def update_config(self, config):
        old_id = self.runtime.discord.app_id
        self.runtime.config = config
        self.runtime.art.enabled = config["artwork_lookup"]
        if old_id != config["discord_app_id"]:
            async def reconnect():
                await self.runtime.discord._disconnect()
                self.runtime.discord.app_id = config["discord_app_id"]
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(reconnect(), self.loop)


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Music RPC Settings")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)
        self.app_id = QLineEdit(config["discord_app_id"])
        self.priority = QLineEdit(", ".join(config["player_priority"]))
        self.paused = QCheckBox("Keep a paused track visible")
        self.paused.setChecked(config["show_paused"])
        self.artwork = QCheckBox("Look up cover art online")
        self.artwork.setChecked(config["artwork_lookup"])
        self.enabled = QCheckBox("Enable Discord Rich Presence")
        self.enabled.setChecked(config["enabled"])
        self.autostart = QCheckBox("Start when I sign in")
        self.autostart.setChecked(config["autostart"])
        layout.addRow("Discord application ID", self.app_id)
        layout.addRow("Player priority (comma separated)", self.priority)
        layout.addRow("Playback", self.paused)
        layout.addRow("Artwork", self.artwork)
        layout.addRow("Presence", self.enabled)
        layout.addRow("Startup", self.autostart)
        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        layout.addRow(save)

    def values(self, old):
        value = dict(old)
        value.update(discord_app_id=self.app_id.text().strip(),
                     player_priority=[x.strip() for x in self.priority.text().split(",") if x.strip()],
                     show_paused=self.paused.isChecked(), artwork_lookup=self.artwork.isChecked(),
                     enabled=self.enabled.isChecked(), autostart=self.autostart.isChecked())
        return value


class MainWindow(QMainWindow):
    def __init__(self, config, worker):
        super().__init__()
        self.config, self.worker = config, worker
        self.setWindowTitle("Music RPC for Linux")
        self.setWindowIcon(QIcon(str(ICON)))
        self.status_text = "Starting…"
        self.label = QLabel(self.status_text)
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(360)
        self.label.setContentsMargins(24, 24, 24, 24)
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.addWidget(self.label)
        self.setCentralWidget(widget)
        self.tray = QSystemTrayIcon(QIcon(str(ICON)), self)
        menu = QMenu()
        open_action = QAction("Open", self)
        settings_action = QAction("Settings", self)
        restart_action = QAction("Restart", self)
        quit_action = QAction("Quit", self)
        open_action.triggered.connect(self.showNormal)
        settings_action.triggered.connect(self.open_settings)
        restart_action.triggered.connect(self.restart)
        quit_action.triggered.connect(QApplication.instance().quit)
        for action in (open_action, settings_action, restart_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Music RPC — starting")
        self.tray.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)

    def set_status(self, text):
        self.status_text = text

    def refresh(self):
        self.label.setText(self.status_text)
        self.tray.setToolTip("Music RPC — " + self.status_text[:160])

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = save_config(dialog.values(self.config))
            set_autostart(updated["autostart"], os.environ.get("MUSIC_RPC_LAUNCHER") or sys.argv[0])
            self.worker.update_config(updated)
            self.config = updated
        except Exception as exc:
            QMessageBox.critical(self, "Settings not saved", str(exc))

    def restart(self):
        self.worker.stop()
        self.worker.join(timeout=3)
        os.execv(sys.argv[0], [sys.argv[0], *sys.argv[1:]])


def launch(config):
    app = QApplication(sys.argv)
    app.setApplicationName("Music RPC")
    app.setQuitOnLastWindowClosed(False)
    status = {"value": "Starting…"}
    worker = Worker(config, lambda value: status.__setitem__("value", value))
    window = MainWindow(config, worker)
    worker.start()
    poll = QTimer()
    poll.timeout.connect(lambda: window.set_status(status["value"]))
    poll.start(500)
    window.hide()
    app.aboutToQuit.connect(worker.stop)
    app.aboutToQuit.connect(lambda: worker.join(timeout=4))
    return app.exec()
