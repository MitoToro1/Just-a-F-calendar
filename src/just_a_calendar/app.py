"""Main application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Just a Calendar")
        self.resize(960, 640)
        self.setCentralWidget(QLabel("Just a Calendar — stage 2 placeholder"))


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()