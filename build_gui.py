from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    import PySide6
    from PySide6.QtCore import QObject, QThread, Signal, Slot
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:
    # pythonw hides tracebacks, so show a native Windows dialog if the GUI
    # dependency is missing or fails to load during startup.
    import ctypes
    import traceback

    ctypes.windll.user32.MessageBoxW(
        None,
        f"Не удалось запустить интерфейс сборщика.\n\n{exc}\n\n{traceback.format_exc()}",
        "Grom Builder — ошибка запуска",
        0x10,
    )
    raise


ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = ROOT / "grom_browser.py"
APP_VERSION = "1.1.1"
VERSION_FILE = ROOT / "version_info.txt"
APP_ICON = ROOT / "browser_icon.ico"


def build_command() -> list[str]:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        "Grom",
        "--version-file",
        str(VERSION_FILE),
        "--icon",
        str(APP_ICON),
        "--contents-directory",
        ".",
        "--hidden-import",
        "PySide6.QtWebView",
        "--hidden-import",
        "shiboken6",
    ]
    for asset in sorted(ROOT.glob("*.png")):
        command.extend(("--add-data", f"{asset};."))
    translations = ROOT / "ui_translations_en.json"
    if translations.is_file():
        command.extend(("--add-data", f"{translations};."))
    webview_plugins = Path(PySide6.__file__).resolve().parent / "plugins" / "webview"
    for plugin in sorted(webview_plugins.glob("*.dll")):
        command.extend(("--add-binary", f"{plugin};PySide6/plugins/webview"))
    menu_icons = ROOT / "menu_icons"
    if menu_icons.is_dir():
        command.extend(("--add-data", f"{menu_icons};menu_icons"))
    command.append(str(MAIN_SCRIPT))
    return command


class BuildWorker(QObject):
    output = Signal(str)
    finished = Signal(int)

    @Slot()
    def run(self) -> None:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        try:
            process = subprocess.Popen(
                build_command(),
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            assert process.stdout is not None
            for line in process.stdout:
                self.output.emit(line.rstrip())
            self.finished.emit(process.wait())
        except Exception as exc:
            self.output.emit(f"Ошибка запуска сборки: {exc}")
            self.finished.emit(1)


class BuilderWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Grom — сборка приложения")
        self.setMinimumSize(760, 520)
        self.thread: QThread | None = None
        self.worker: BuildWorker | None = None

        title = QLabel(f"Сборка Grom Browser {APP_VERSION}")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        subtitle = QLabel(
            "Соберите готовую папку приложения для Windows. Консольное окно не откроется."
        )
        subtitle.setWordWrap(True)
        self.status = QLabel("Готово к сборке")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Здесь появится ход сборки PyInstaller.")
        self.build_button = QPushButton("Собрать приложение")
        self.build_button.setMinimumHeight(42)
        self.build_button.clicked.connect(self.start_build)
        self.open_button = QPushButton("Открыть папку dist")
        self.open_button.clicked.connect(self.open_dist)
        buttons = QHBoxLayout()
        buttons.addWidget(self.build_button)
        buttons.addWidget(self.open_button)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(self.log, 1)
        layout.addLayout(buttons)
        self.setCentralWidget(content)
        self.setStyleSheet(
            "QMainWindow{background:#f4f6fa} QLabel{color:#202633} "
            "QTextEdit{background:white;border:1px solid #d8deea;border-radius:8px;"
            "font-family:Consolas;font-size:10pt} QPushButton{padding:8px 14px;"
            "border:1px solid #ccd4e1;border-radius:7px;background:white} "
            "QPushButton:hover{background:#e9efff} QProgressBar{height:12px;"
            "border:0;border-radius:6px;background:#e1e6ef} "
            "QProgressBar::chunk{border-radius:6px;background:#426fe8}"
        )

    def start_build(self) -> None:
        if self.thread and self.thread.isRunning():
            return
        if not MAIN_SCRIPT.is_file():
            QMessageBox.critical(self, "Нет исходников", f"Не найден файл:\n{MAIN_SCRIPT}")
            return
        self.log.clear()
        self.status.setText("Идёт сборка…")
        self.progress.setRange(0, 0)
        self.build_button.setEnabled(False)
        self.thread = QThread(self)
        self.worker = BuildWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.output.connect(self.log.append)
        self.worker.finished.connect(self.finish_build)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    @Slot(int)
    def finish_build(self, code: int) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if code == 0 else 0)
        self.build_button.setEnabled(True)
        if code == 0:
            self.status.setText(f"Сборка {APP_VERSION} завершена: {ROOT / 'dist' / 'Grom'}")
            self.log.append("\nГотово. Запускаемый файл: dist/Grom/Grom.exe")
        else:
            self.status.setText("Сборка завершилась с ошибкой. Подробности выше.")

    def open_dist(self) -> None:
        dist = ROOT / "dist"
        dist.mkdir(exist_ok=True)
        os.startfile(dist)


def main() -> int:
    app = QApplication(sys.argv)
    window = BuilderWindow()
    window.show()
    if "--build" in sys.argv:
        window.start_build()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
