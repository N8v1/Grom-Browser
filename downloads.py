from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import time
import uuid
from datetime import datetime

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest


class DownloadsMixin:
    DANGEROUS_DOWNLOAD_EXTENSIONS = {
        ".exe", ".msi", ".msix", ".bat", ".cmd", ".com", ".scr",
        ".ps1", ".vbs", ".js", ".jar", ".reg", ".lnk", ".iso",
    }

    def download_category(self, name):
        extension = os.path.splitext(str(name or ""))[1].lower()
        categories = {
            "PDF": {".pdf"},
            "Excel": {".xls", ".xlsx", ".xlsm", ".csv", ".ods"},
            "Изображения": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".avif"},
            "Архивы": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"},
            "Документы": {".doc", ".docx", ".odt", ".rtf", ".txt", ".ppt", ".pptx", ".odp"},
        }
        return next((category for category, values in categories.items() if extension in values), "Другое")

    def load_downloads(self):
        try:
            with open(self.downloads_file, "r", encoding="utf-8") as file:
                records = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            records = []
        tasks = []
        for record in records[-300:]:
            if not isinstance(record, dict):
                continue
            task = {
                "id": str(record.get("id", "")),
                "name": str(record.get("name", "download")),
                "path": str(record.get("path", "")),
                "url": str(record.get("url", "")),
                "status": str(record.get("status", "Готово")),
                "received": int(record.get("received", 0)),
                "total": int(record.get("total", 0)),
                "date": str(record.get("date", "")),
                "category": str(record.get("category") or self.download_category(record.get("name", ""))),
                "source_url": str(record.get("source_url", "")),
                "source_host": str(
                    record.get("source_host")
                    or QUrl(str(record.get("source_url") or record.get("url", ""))).host()
                ),
                "reply": None,
                "file": None,
                "ui": None,
                "offset": int(record.get("received", 0)) if str(record.get("status", "")) == "Приостановлено" else 0,
                "pause_requested": False,
                "checksum": str(record.get("checksum", "")),
                "security_status": str(record.get("security_status", "")),
                "network_finished": False,
                "pump_scheduled": False,
            }
            if task["status"] == "Загрузка":
                task["status"] = "Приостановлено"
                task["offset"] = QFileInfo(task["path"]).size() if task["path"] else task["received"]
            tasks.append(task)
        return tasks

    def save_downloads(self):
        fields = (
            "id", "name", "path", "url", "status", "received", "total", "date",
            "category", "source_url", "source_host", "checksum", "security_status",
        )
        records = [{field: task.get(field) for field in fields} for task in self.download_tasks[-300:]]
        with open(self.downloads_file, "w", encoding="utf-8") as file:
            json.dump(records, file, ensure_ascii=False, indent=2)

    def unique_download_path(self, name, category=None):
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
        if not name:
            name = f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        stem, extension = os.path.splitext(name)
        folder = os.path.join(self.downloads_dir, category or self.download_category(name))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name)
        counter = 1
        while os.path.exists(path):
            path = os.path.join(folder, f"{stem} ({counter}){extension}")
            counter += 1
        return path

    def start_download(self, download, source_url=None):
        if not isinstance(download, dict):
            return
        url = QUrl(str(download.get("url", "")))
        if not url.isValid() or url.scheme().lower() not in ("http", "https"):
            return

        suggested_name = str(download.get("name", "")).strip()
        filename = suggested_name or url.fileName() or "download"
        extension = os.path.splitext(filename)[1].lower()
        if extension in self.DANGEROUS_DOWNLOAD_EXTENSIONS:
            answer = QMessageBox.warning(
                self,
                "Потенциально опасный файл",
                f"Файл {filename} может запускать команды или устанавливать программы.\n"
                "Скачивайте его только из доверенного источника.",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Save:
                return
        category = self.download_category(filename)
        path = self.unique_download_path(filename, category)
        source = QUrl(source_url) if source_url else QUrl()
        task = {
            "id": f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{len(self.download_tasks)}",
            "name": os.path.basename(path),
            "path": path,
            "url": url.toString(),
            "status": "В очереди",
            "received": 0,
            "total": 0,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "source_url": source.toString(),
            "source_host": source.host() or url.host(),
            "reply": None,
            "file": None,
            "ui": None,
            "offset": 0,
            "pause_requested": False,
            "range_checked": False,
            "checksum": "",
            "security_status": "Требует осторожности" if extension in self.DANGEROUS_DOWNLOAD_EXTENSIONS else "",
            "network_finished": False,
            "pump_scheduled": False,
        }
        self.download_tasks.append(task)
        self.save_downloads()
        self.process_download_queue()
        self.show_downloads_popup(force_open=True)

    def active_download_count(self):
        return sum(1 for task in self.download_tasks if task.get("reply") is not None)

    def process_download_queue(self):
        maximum = max(1, min(8, int(self.app_settings.get("max_concurrent_downloads", 3))))
        for task in self.download_tasks:
            if self.active_download_count() >= maximum:
                break
            if task.get("status") != "В очереди":
                continue
            if not self.begin_download_request(task, resume=bool(task.get("resume_queued"))):
                task["status"] = "Ошибка"
                task["error"] = "Не удалось создать файл загрузки"
            task["resume_queued"] = False
        self.save_downloads()

    def begin_download_request(self, task, resume=False):
        path = task.get("path", "")
        offset = QFileInfo(path).size() if resume and os.path.isfile(path) else 0
        output = QFile(path, self)
        mode = QIODevice.OpenModeFlag.WriteOnly
        if offset:
            mode |= QIODevice.OpenModeFlag.Append
        if not output.open(mode):
            QMessageBox.warning(self, "Загрузки", f"Не удалось открыть файл:\n{path}")
            return False
        request = QNetworkRequest(QUrl(task.get("url", "")))
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 GromBrowser/1.0",
        )
        if offset:
            request.setRawHeader(b"Range", f"bytes={offset}-".encode("ascii"))
        reply = self.download_network.get(request)
        speed_limit = max(0, int(self.app_settings.get("download_speed_limit_kbps", 0)))
        if speed_limit:
            reply.setReadBufferSize(max(32 * 1024, speed_limit * 2048))
        task.update({
            "reply": reply,
            "file": output,
            "status": "Загрузка",
            "offset": offset,
            "received": offset,
            "pause_requested": False,
            "range_checked": False,
            "network_finished": False,
            "pump_scheduled": False,
            "speed_window_started": time.monotonic(),
            "speed_window_bytes": 0,
            "hasher": self.create_download_hasher(path, offset),
        })
        reply.readyRead.connect(lambda current=task: self.write_download_data(current))
        reply.downloadProgress.connect(
            lambda received, total, current=task: self.download_progress(current, received, total)
        )
        reply.finished.connect(lambda current=task: self.finish_download(current))
        self.update_download_ui(task)
        return True

    def write_download_data(self, task):
        reply = task.get("reply")
        output = task.get("file")
        if reply and output and output.isOpen():
            if task.get("offset", 0) and not task.get("range_checked"):
                task["range_checked"] = True
                status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
                if status == 200:
                    output.close()
                    if not output.open(QIODevice.OpenModeFlag.WriteOnly | QIODevice.OpenModeFlag.Truncate):
                        reply.abort()
                        return
                    task["offset"] = 0
                    task["hasher"] = hashlib.sha256()
            limit = max(0, int(self.app_settings.get("download_speed_limit_kbps", 0))) * 1024
            amount = int(reply.bytesAvailable())
            if limit:
                now = time.monotonic()
                elapsed = now - float(task.get("speed_window_started", now))
                if elapsed >= 1:
                    task["speed_window_started"] = now
                    task["speed_window_bytes"] = 0
                    elapsed = 0
                allowance = limit - int(task.get("speed_window_bytes", 0))
                if allowance <= 0:
                    self.schedule_download_pump(task, max(20, int((1 - elapsed) * 1000)))
                    return
                amount = min(amount, allowance, max(4096, limit // 10))
            if amount > 0:
                data = reply.read(amount)
                output.write(data)
                task.get("hasher", hashlib.sha256()).update(bytes(data))
                task["speed_window_bytes"] = int(task.get("speed_window_bytes", 0)) + data.size()
                task["received"] = output.size()
            if reply.bytesAvailable() > 0:
                self.schedule_download_pump(task, 80 if limit else 0)
            elif task.get("network_finished"):
                self.finalize_download(task)

    def schedule_download_pump(self, task, delay):
        if task.get("pump_scheduled"):
            return
        task["pump_scheduled"] = True
        QTimer.singleShot(delay, lambda current=task: self.run_download_pump(current))

    def run_download_pump(self, task):
        task["pump_scheduled"] = False
        self.write_download_data(task)

    def download_progress(self, task, received, total):
        offset = int(task.get("offset", 0))
        task["received"] = offset + max(0, int(received))
        task["total"] = offset + max(0, int(total)) if total >= 0 else 0
        self.update_download_ui(task)

    def finish_download(self, task):
        task["network_finished"] = True
        self.write_download_data(task)
        if task.get("reply") is None:
            return
        reply = task.get("reply")
        if reply and reply.bytesAvailable() > 0:
            self.schedule_download_pump(task, 80)
            return
        self.finalize_download(task)

    def finalize_download(self, task):
        reply = task.get("reply")
        output = task.get("file")
        if reply is None and output is None:
            return
        if reply and output and output.isOpen():
            output.close()
        if task.get("pause_requested"):
            task["status"] = "Приостановлено"
            task["received"] = QFileInfo(task.get("path", "")).size()
            task["offset"] = task["received"]
        elif task.get("status") != "Отменено":
            if reply and reply.error() == QNetworkReply.NetworkError.NoError:
                task["status"] = "Готово"
                if not task.get("total"):
                    task["received"] = QFileInfo(task["path"]).size()
                    task["total"] = task["received"]
                hasher = task.pop("hasher", None)
                task["checksum"] = hasher.hexdigest() if hasher else self.file_sha256(task["path"])
                task["security_status"] = "SHA-256 рассчитан"
                self.scan_download_with_windows_defender(task)
            else:
                task["status"] = "Ошибка"
                task["error"] = reply.errorString() if reply else "Неизвестная ошибка"
        self.update_download_ui(task)
        if reply:
            reply.deleteLater()
        task["reply"] = None
        task["file"] = None
        task["pause_requested"] = False
        self.save_downloads()
        QTimer.singleShot(0, self.refresh_downloads_pages)
        QTimer.singleShot(0, self.process_download_queue)

    def file_sha256(self, path):
        digest = hashlib.sha256()
        try:
            with open(path, "rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except OSError:
            return ""

    def create_download_hasher(self, path, existing_size=0):
        digest = hashlib.sha256()
        if existing_size <= 0:
            return digest
        try:
            with open(path, "rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            pass
        return digest

    def scan_download_with_windows_defender(self, task):
        candidates = [
            QStandardPaths.findExecutable("MpCmdRun.exe"),
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Windows Defender", "MpCmdRun.exe"),
        ]
        executable = next((path for path in candidates if path and os.path.isfile(path)), "")
        if not executable or not os.path.isfile(task.get("path", "")):
            task["security_status"] = "SHA-256 рассчитан · антивирусная проверка недоступна"
            return
        process = QProcess(self)
        task["security_process"] = process
        task["security_status"] = "Проверка Защитником Windows…"
        process.finished.connect(
            lambda exit_code, _status, current=task:
            self.finish_download_security_scan(current, exit_code)
        )
        process.start(executable, ["-Scan", "-ScanType", "3", "-File", task["path"], "-DisableRemediation"])

    def finish_download_security_scan(self, task, exit_code):
        task["security_status"] = (
            "Проверено Защитником Windows"
            if int(exit_code) == 0
            else "Защитник Windows сообщил об угрозе или ошибке проверки"
        )
        process = task.pop("security_process", None)
        if process:
            process.deleteLater()
        self.save_downloads()
        self.update_download_ui(task)
        self.refresh_downloads_pages()

    def pause_download(self, task):
        reply = task.get("reply")
        if not reply or task.get("status") != "Загрузка":
            return
        self.write_download_data(task)
        task["pause_requested"] = True
        task["status"] = "Приостановлено"
        task["received"] = QFileInfo(task.get("path", "")).size()
        self.save_downloads()
        reply.abort()
        self.update_download_ui(task)

    def resume_download(self, task):
        if task.get("status") not in ("Приостановлено", "Ошибка"):
            return
        task["status"] = "В очереди"
        task["resume_queued"] = True
        self.save_downloads()
        self.process_download_queue()

    def retry_download(self, task):
        if task.get("status") != "Ошибка":
            return
        path = task.get("path", "")
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                return
        task.update({"status": "В очереди", "received": 0, "total": 0, "offset": 0, "error": "", "checksum": ""})
        self.save_downloads()
        self.process_download_queue()

    def cleanup_temporary_downloads(self):
        removed = 0
        for task in self.download_tasks:
            if task.get("status") not in ("Ошибка", "Отменено"):
                continue
            path = task.get("path", "")
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                    removed += 1
                except OSError:
                    pass
        return removed

    def cancel_download(self, task):
        reply = task.get("reply")
        if not reply:
            return
        task["status"] = "Отменено"
        reply.abort()
        self.update_download_ui(task)

    def open_download(self, task):
        path = task.get("path", "")
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.information(self, "Загрузки", "Файл больше не найден на диске.")

    def delete_download(self, task, refresh_popup=True):
        reply = task.get("reply")
        if reply:
            task["status"] = "Отменено"
            reply.abort()
        path = task.get("path", "")
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                QMessageBox.warning(self, "Загрузки", "Не удалось удалить файл.")
                return
        if task in self.download_tasks:
            self.download_tasks.remove(task)
        self.save_downloads()
        if refresh_popup and self.downloads_popup and self.downloads_popup.isVisible():
            self.downloads_popup.close()
            QTimer.singleShot(0, lambda: self.show_downloads_popup(force_open=True))

    def clear_downloads(self):
        answer = QMessageBox.question(
            self,
            "Удалить все загрузки",
            "Удалить все файлы из списка загрузок и с диска?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        for task in list(self.download_tasks):
            self.delete_download(task, refresh_popup=False)
        self.save_downloads()
        return True

    def human_size(self, value):
        size = float(max(0, value or 0))
        for unit in ("Б", "КБ", "МБ", "ГБ"):
            if size < 1024 or unit == "ГБ":
                return f"{size:.0f} {unit}" if unit == "Б" else f"{size:.1f} {unit}"
            size /= 1024

    def show_downloads_popup(self, force_open=False):
        if self.downloads_popup and self.downloads_popup.isVisible():
            if not force_open:
                self.downloads_popup.close()
            return

        colors = self.theme_colors
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.prepare_rounded_popup(popup)
        popup.setObjectName("downloadsPopup")
        popup.setFixedSize(470, 560)
        popup.setStyleSheet(f"""
            QFrame#downloadsPopup {{ background:{colors['popup']}; border:1px solid {colors['border']}; border-radius:12px; }}
            QFrame#downloadRow {{ background:{colors['surface']}; border:none; border-radius:6px; }}
            QLabel {{ color:{colors['text']}; border:none; }}
            QLabel#downloadDetails {{ color:{colors['muted']}; }}
            QPushButton {{ color:{colors['text']}; background:transparent; border:none; border-radius:5px; padding:7px 10px; }}
            QPushButton:hover {{ background:{colors['hover']}; }}
            QScrollArea {{ background:transparent; border:none; }}
            QScrollBar:vertical {{ background:{colors['background']}; width:10px; }}
            QScrollBar::handle:vertical {{ background:{colors['border']}; min-height:30px; border-radius:4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QProgressBar {{ height:5px; background:{colors['input']}; border:none; border-radius:2px; text-align:center; }}
            QProgressBar::chunk {{ background:{colors['accent']}; border-radius:2px; }}
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 0, 0)
        title = QLabel("Загрузки")
        title.setStyleSheet("font-size:16px; font-weight:600;")
        open_folder = QPushButton("Открыть загрузки")
        open_folder.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.downloads_dir))
        )
        header_layout.addWidget(title)
        header_layout.addStretch()
        cleanup = QPushButton("Очистить временные")
        cleanup.setToolTip("Удалить неполные файлы ошибочных и отменённых загрузок")
        cleanup.clicked.connect(
            lambda: QMessageBox.information(
                self,
                "Временные файлы",
                f"Удалено файлов: {self.cleanup_temporary_downloads()}",
            )
        )
        header_layout.addWidget(cleanup)
        header_layout.addWidget(open_folder)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("background:transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(7)
        if self.download_tasks:
            for task in reversed(self.download_tasks):
                content_layout.addWidget(self.create_download_row(task))
        else:
            empty = QLabel("Загрузок пока нет")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{colors['muted']}; padding:50px;")
            content_layout.addWidget(empty)
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        all_downloads = QPushButton("Все загрузки")
        all_downloads.setFixedHeight(38)
        all_downloads.setStyleSheet(f"""
            QPushButton {{ color:{colors['text']}; background:{colors['surface']}; border:none; border-radius:0; }}
            QPushButton:hover {{ background:{colors['hover']}; }}
        """)
        all_downloads.clicked.connect(lambda: (popup.close(), self.open_downloads_tab()))
        layout.addWidget(all_downloads)
        popup.destroyed.connect(self.clear_download_uis)
        self.downloads_popup = popup
        self.position_popup(popup)
        popup.show()
        popup.raise_()

    def create_download_row(self, task):
        row = QFrame()
        row.setObjectName("downloadRow")
        layout = QGridLayout(row)
        layout.setContentsMargins(12, 10, 8, 10)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(5)
        name = QLabel(task["name"])
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        name.setStyleSheet("font-weight:600;")
        details = QLabel()
        details.setObjectName("downloadDetails")
        details.setWordWrap(True)
        progress = QProgressBar()
        progress.setTextVisible(False)
        open_button = QPushButton("Открыть")
        delete_button = QPushButton("Удалить")
        open_button.clicked.connect(lambda _checked=False, current=task: self.download_action(current))
        delete_button.clicked.connect(lambda _checked=False, current=task: self.delete_download(current))
        layout.addWidget(name, 0, 0)
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(2)
        actions_layout.addWidget(open_button)
        actions_layout.addWidget(delete_button)
        layout.addWidget(actions, 0, 1, 2, 1)
        layout.addWidget(details, 1, 0)
        layout.addWidget(progress, 2, 0, 1, 2)
        task["ui"] = {
            "details": details,
            "progress": progress,
            "open": open_button,
            "delete": delete_button,
        }
        self.update_download_ui(task)
        return row

    def download_action(self, task):
        if task.get("status") == "Загрузка":
            self.pause_download(task)
        elif task.get("status") == "Приостановлено":
            self.resume_download(task)
        elif task.get("status") == "Готово":
            self.open_download(task)
        elif task.get("status") == "Ошибка":
            self.retry_download(task)

    def update_download_ui(self, task):
        ui = task.get("ui")
        if not ui:
            return
        try:
            status = task.get("status", "")
            received, total = task.get("received", 0), task.get("total", 0)
            details = [status, task.get("category", "")]
            if task.get("source_host"):
                details.append(f"с сайта {task['source_host']}")
            if task.get("security_status"):
                details.append(task["security_status"])
            ui["details"].setText(" · ".join(value for value in details if value))
            if status == "Загрузка" and total <= 0:
                ui["progress"].setRange(0, 0)
            else:
                ui["progress"].setRange(0, 100)
                value = 100 if status == "Готово" else int(received * 100 / total) if total else 0
                ui["progress"].setValue(value)
            ui["progress"].setVisible(status in ("Загрузка", "Приостановлено"))
            ui["delete"].setEnabled(status != "Загрузка")
            if status == "Загрузка":
                ui["open"].setText("Пауза")
                ui["open"].setEnabled(True)
            elif status == "Приостановлено":
                ui["open"].setText("Продолжить")
                ui["open"].setEnabled(True)
            elif status == "Готово":
                ui["open"].setText("Открыть")
                ui["open"].setEnabled(True)
            elif status == "Ошибка":
                ui["open"].setText("Повторить")
                ui["open"].setEnabled(True)
            elif status == "В очереди":
                ui["open"].setText("В очереди")
                ui["open"].setEnabled(False)
            else:
                ui["open"].setEnabled(False)
        except RuntimeError:
            task["ui"] = None

    def clear_download_uis(self):
        for task in self.download_tasks:
            task["ui"] = None
