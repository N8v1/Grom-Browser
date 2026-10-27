import sys
import os
import json
import re
import time
import uuid
import base64
import mimetypes
import subprocess
import math
import ctypes
import difflib
from ctypes import wintypes
from datetime import datetime, timedelta

# Keep relative icon/resource paths stable when started from a shortcut or a
# frozen PyInstaller build whose current working directory is elsewhere.
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def configure_webview_runtime():
    base_path = os.path.join(os.path.dirname(__file__), "browser_data")
    profile_id = "default"
    if "--profile" in sys.argv:
        position = sys.argv.index("--profile")
        if position + 1 < len(sys.argv):
            profile_id = re.sub(r"[^a-zA-Z0-9_-]", "", sys.argv[position + 1]) or "default"
    settings_path = (
        os.path.join(base_path, "settings.json")
        if profile_id == "default"
        else os.path.join(base_path, "profiles", profile_id, "settings.json")
    )
    try:
        with open(settings_path, "r", encoding="utf-8") as file:
            settings = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        settings = {}
    if settings.get("hardware_acceleration", True):
        return
    arguments = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
    if "--disable-gpu" not in arguments:
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
            f"{arguments} --disable-gpu".strip()
        )


configure_webview_runtime()

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWebView import QWebView, QWebViewLoadingInfo, QWebViewSettings, QtWebView


def grom_qt_message_handler(message_type, context, message):
    message = str(message)
    if (
        "Base URLs for loadHtml() are not supported on this platform" in message
        or (
            "requestActivate() called for" in message
            and "WindowDoesNotAcceptFocus" in message
        )
    ):
        return
    stream = sys.stderr if message_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg) else sys.stdout
    stream.write(message + "\n")
    stream.flush()


qInstallMessageHandler(grom_qt_message_handler)
QtWebView.initialize()

from builtin_extensions import BuiltinExtensionsMixin, default_builtin_extensions
from downloads import DownloadsMixin
from internal_pages import InternalPagesMixin
from i18n import get_language, install_qt_translation, set_language, translate_text
from profiles import ProfilesMixin, WindowsCredentialStore
from tabs import ChromeTabBar, TabCloseButton, TabWorkspace
from webview import AddressLineEdit, BrowserWebView, CircularIconButton, DevtoolsSyntaxHighlighter

ZOOM_LEVELS = (25, 50, 67, 75, 80, 90, 100, 110, 120, 125, 150, 175, 200, 250, 300, 400, 500)

SITE_PERMISSION_KEYS = (
    "camera",
    "microphone",
    "notifications",
    "geolocation",
    "autoplay",
    "clipboard",
    "popups",
)

WEB_PAGE_COMMANDS = {
    "open_popup",
    "popup_navigate",
    "popup_message_to_opener",
    "popup_message_to_child",
    "popup_close",
    "google_account_switch_fallback",
    "twitch_message_context",
    "image_context",
    "text_context",
    "page_context",
    "selection_quick",
}

INTERNAL_PAGE_COMMANDS = {
    "home": {
        "navigate_home", "add_home_shortcut", "rename_home_shortcut",
        "delete_home_shortcut", "set_home_customization",
        "choose_home_background", "clear_home_background", "set_interface_language",
    },
    "downloads": {
        "open_download", "pause_download", "resume_download", "retry_download",
        "delete_download", "clear_downloads", "cleanup_download_temps",
    },
    "welcome": {"welcome_preferences", "finish_welcome", "set_interface_language"},
    "settings": {
        "register_default_browser", "choose_theme_image", "create_profile",
        "rename_profile", "profile_avatar", "delete_profile", "switch_profile",
        "guest_profile", "delete_password", "copy_password", "add_password",
        "clear_password_never", "allow_password_origin", "clear_site_permissions",
        "install_current_site",
    },
}



# --- ОКНО ИСТОРИИ ---
class HistoryWindow(QDialog):
    open_url = Signal(str)  # Сигнал для открытия URL
    open_url_new_tab = Signal(str)  # Сигнал для открытия в новой вкладке
    
    def __init__(self, history_data, get_cached_icon_func, parent=None):
        super().__init__(parent)
        self.history_data = history_data
        self.get_cached_icon = get_cached_icon_func
        self.parent_browser = parent
        
        self.setWindowTitle("История")
        self.setFixedSize(600, 700)
        self.setStyleSheet("QDialog { background-color: #1e1e1e; }")
        
        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Заголовок
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet("background-color: #252525;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        title_label = QLabel("История посещений")
        title_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Кнопка закрытия
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                background: #333;
                color: white;
                border-radius: 5px;
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        # Scroll area для списка истории
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #1a1a1a;
                width: 8px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        
        # Контейнер для элементов истории
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.populate_history()
        
        scroll.setWidget(self.content_widget)
        
        main_layout.addWidget(header)
        main_layout.addWidget(scroll)
    
    def populate_history(self):
        """Заполняет окно элементами истории"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        current_group = ""
        
        # Отображаем последние 100 записей
        for item in reversed(self.history_data[-100:]):
            dt_obj = datetime.strptime(item['date'], "%Y-%m-%d %H:%M:%S")
            item_date = dt_obj.date()
            item_time = dt_obj.strftime("%H:%M")
            
            # Логика группировки по датам
            if item_date == today: 
                group_name = "Сегодня"
            elif item_date == yesterday: 
                group_name = "Вчера"
            else: 
                group_name = item_date.strftime("%d.%m.%Y")
            
            if group_name != current_group:
                current_group = group_name
                # Добавляем заголовок группы
                group_header = QLabel(group_name)
                group_header.setStyleSheet("""
                    color: #888; 
                    font-weight: bold; 
                    font-size: 12px; 
                    padding: 12px 20px 8px 20px;
                    background: transparent;
                """)
                self.content_layout.addWidget(group_header)
            
            # Создаем виджет записи истории
            icon = self.get_cached_icon(item["url"])
            history_item = HistoryItemWidget(icon, item['title'], item_time, item['url'])
            
            # Подключаем сигналы
            history_item.delete_requested.connect(self.handle_delete)
            history_item.open_in_new_tab.connect(lambda u: self.open_url_new_tab.emit(u))
            
            # Обработка клика
            def make_click_handler(url):
                return lambda e: self.open_url.emit(url) if e.button() == Qt.LeftButton else None
            
            history_item.mousePressEvent = make_click_handler(item['url'])
            
            self.content_layout.addWidget(history_item)
        
        # Добавляем растяжку в конец
        self.content_layout.addStretch()
    
    def handle_delete(self, url):
        """Обрабатывает удаление записи или всей истории"""
        if url == "__CLEAR_ALL_HISTORY__":
            # Подтверждение очистки всей истории
            reply = QMessageBox.question(
                self, 
                'Подтверждение', 
                'Вы уверены, что хотите удалить всю историю?',
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.parent_browser:
                    self.parent_browser.delete_from_history(url)
                self.close()
        else:
            # Удаление отдельной записи
            if self.parent_browser:
                self.parent_browser.delete_from_history(url)
            # Перезагружаем историю
            self.refresh_history()
    
    def refresh_history(self):
        """Обновляет список истории"""
        # Очищаем текущий список
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Получаем обновленные данные
        if self.parent_browser:
            self.history_data = self.parent_browser.history_data
        
        # Заполняем заново
        self.populate_history()

# --- ВИДЖЕТ ДЛЯ СТРОКИ ИСТОРИИ ---
class HistoryItemWidget(QWidget):
    delete_requested = Signal(str)  # Сигнал для удаления записи
    open_in_new_tab = Signal(str)   # Сигнал для открытия в новой вкладке
    
    def __init__(self, icon, title, time, url, parent=None):
        super().__init__(parent)
        self.url = url
        
        # Главный контейнер с фоном
        self.container = QWidget()
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(20, 8, 20, 8)
        container_layout.setSpacing(12)

        # Иконка сайта
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(18, 18)
        if not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(18, 18))
        
        # Название страницы
        self.title_label = QLabel(title if title else "Без названия")
        self.title_label.setStyleSheet("color: #ccc; font-size: 13px; border: none; background: transparent;")
        self.title_label.setFixedWidth(400)

        # Время (серым цветом)
        self.time_label = QLabel(time)
        self.time_label.setStyleSheet("color: #666; font-size: 11px; border: none; background: transparent;")

        # Кнопка удаления (скрыта по умолчанию)
        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(QIcon("close.png"))
        self.delete_btn.setFixedSize(22, 22)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.delete_btn.setVisible(False)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.url))

        container_layout.addWidget(self.icon_label)
        container_layout.addWidget(self.title_label)
        container_layout.addStretch()
        container_layout.addWidget(self.time_label)
        container_layout.addWidget(self.delete_btn)
        
        # Основной layout для всего виджета
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.container)
        
        # Стиль контейнера при наведении
        self.container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 6px;
            }
        """)
        
        # Контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def enterEvent(self, event):
        self.container.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 6px;
            }
        """)
        self.delete_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 6px;
            }
        """)
        self.delete_btn.setVisible(False)
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        # Переопределяем для обработки кликов
        # Будет переопределено в HistoryWindow
        super().mousePressEvent(event)
    
    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { 
                background-color: #2d2d2d; 
                color: #ccc; 
                border: 1px solid #444; 
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)
        
        open_new_tab_action = menu.addAction("Открыть в новой вкладке")
        delete_action = menu.addAction("Удалить")
        menu.addSeparator()
        clear_all_action = menu.addAction("Удалить всю историю")
        
        action = menu.exec(self.mapToGlobal(pos))
        if action == delete_action:
            self.delete_requested.emit(self.url)
        elif action == open_new_tab_action:
            self.open_in_new_tab.emit(self.url)
        elif action == clear_all_action:
            # Отправляем специальный сигнал для очистки всей истории
            self.delete_requested.emit("__CLEAR_ALL_HISTORY__")

# --- КЛАСС ПЕРЕМЕЩАЕМОЙ КНОПКИ ЗАКЛАДКИ ---
class DraggableBookmark(QPushButton):
    def __init__(self, url, name, icon=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.name = name
        if icon: self.setIcon(icon)
        self.setText(name[:20])
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.apply_theme({
            "surface": "#1e1e1e",
            "hover": "#2d2d2d",
            "text": "#cccccc",
        })

    def apply_theme(self, colors):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {colors['surface']};
                color: {colors['text']};
                border: none;
                border-radius: 8px;
                padding: 4px 12px;
                text-align: left;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {colors['hover']}; }}
        """)

    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.LeftButton: return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.url)
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)















class Browser(BuiltinExtensionsMixin, ProfilesMixin, DownloadsMixin, InternalPagesMixin, QMainWindow):
    _open_windows = []

    def __init__(self, app_url=None, profile_id=None, guest=False, detached=False, shared_storage_path=None):
        super().__init__()
        Browser._open_windows.append(self)
        self.app_url = str(app_url or "").strip()
        self.app_mode = bool(self.app_url)
        self.guest_mode = bool(guest)
        self.detached_window = bool(detached)

        # --- Настройки профиля и данных ---
        self.base_storage_path = os.path.join(os.path.dirname(__file__), "browser_data")
        os.makedirs(self.base_storage_path, exist_ok=True)
        self.profiles_file = os.path.join(self.base_storage_path, "profiles.json")
        self.profile_registry = self.load_profile_registry()
        requested_profile = str(profile_id or self.profile_registry.get("active", "default"))
        known_ids = {item.get("id") for item in self.profile_registry.get("profiles", [])}
        self.profile_id = requested_profile if requested_profile in known_ids else "default"
        self.current_profile = next(
            (item for item in self.profile_registry["profiles"] if item.get("id") == self.profile_id),
            {"id": "default", "name": "Профиль 1", "avatar": ""},
        )
        if self.guest_mode and shared_storage_path:
            self.storage_path = str(shared_storage_path)
            self.current_profile = {"id": "guest", "name": "Гость", "avatar": ""}
        elif self.guest_mode:
            self.guest_storage = QTemporaryDir(os.path.join(QDir.tempPath(), "grom-guest-XXXXXX"))
            self.storage_path = self.guest_storage.path()
            self.current_profile = {"id": "guest", "name": "Гость", "avatar": ""}
        else:
            self.profile_registry["active"] = self.profile_id
            self.save_profile_registry()
            self.storage_path = (
                self.base_storage_path
                if self.profile_id == "default"
                else os.path.join(self.base_storage_path, "profiles", self.profile_id)
            )
        os.makedirs(self.storage_path, exist_ok=True)
        
        for p in ["cookies", "cache", "storage"]:
            path = os.path.join(self.storage_path, p)
            if not os.path.exists(path): os.makedirs(path)

        self.settings_file = os.path.join(self.storage_path, "settings.json")
        self.app_settings = self.load_app_settings()
        set_language(self.app_settings.get("interface_language", "ru"))
        self.password_store = WindowsCredentialStore("guest" if self.guest_mode else self.profile_id)
        self.theme_colors = self.build_theme_colors(self.current_theme_color())
        self.session_file = os.path.join(self.storage_path, "session.json")
        self.previous_session = self.load_session()
        self.recent_sessions_file = os.path.join(self.storage_path, "recent_sessions.json")
        self.recent_sessions = self.load_recent_sessions()
        self.archive_saved_session(self.previous_session)
        self._last_session_signature = None
        self.tab_groups = dict(self.previous_session.get("groups", {}))
        self._restoring_session = False
        previous_tabs = self.previous_session.get("tabs", [])
        self._session_prompt_pending = isinstance(previous_tabs, list) and bool(previous_tabs)
        if self._session_prompt_pending and len(previous_tabs) == 1:
            self._session_prompt_pending = not (
                isinstance(previous_tabs[0], dict)
                and previous_tabs[0].get("internal_page") == "home"
            )
        if self.detached_window:
            self._session_prompt_pending = False
        self.restore_popup = None
        self.closed_groups_file = os.path.join(self.storage_path, "closed_groups.json")
        self.closed_groups = self.load_closed_groups()
        self.closed_tabs_file = os.path.join(self.storage_path, "closed_tabs.json")
        self.closed_tabs = self.load_closed_tabs()
        self.session_permission_overrides = {}
        self.heavy_tab_warnings = {}
        self.url_safety_cache = {}
        self.url_safety_bypass = set()
            
        self.setWindowTitle(f"Grom Browser — {self.current_profile.get('name', 'Профиль')}")
        self.setWindowIcon(self.brand_icon())
        self.resize(1300, 900)
        self.setStyleSheet("QMainWindow { background-color: #202124; border: none; }")
        self.is_was_maximized = False
        self.menu_popup = None
        self.profile_popup = None
        self.site_info_popup = None
        self.translation_popup = None
        self.translation_prompt_popup = None
        self.password_save_popup = None
        self._last_password_offer = (None, 0.0)
        self.selection_copy_popup = None
        self.history_popup = None
        self.downloads_popup = None
        self.performance_popup = None
        self.builtin_extensions_popup = None
        self.builtin_extension_details_popup = None
        self.tab_search_popup = None
        self._popup_closed_at = {}
        self._app_fullscreen = False
        self._media_fullscreen = False
        self._media_fullscreen_browser = None
        self._media_started_inside_app_fullscreen = False
        self.shortcuts = []
        self.loading_browsers = set()
        self._session_background_queue = []
        self._session_background_loading = False
        self.loading_angle = 0
        self.loading_timer = QTimer(self)
        self.loading_timer.setInterval(75)
        self.loading_timer.timeout.connect(self.update_loading_icons)

        self.downloads_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        ) or os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.download_network = QNetworkAccessManager(self)
        self.downloads_file = os.path.join(self.storage_path, "downloads.json")
        self.download_tasks = self.load_downloads()

        # --- 1. ПАНЕЛЬ ВКЛАДОК ---
        self.tabs_panel = QWidget()
        self.tabs_panel.setFixedHeight(42)
        self.tabs_panel.setStyleSheet("background-color: #202124;")
        tabs_layout = QHBoxLayout(self.tabs_panel)
        tabs_layout.setContentsMargins(8, 5, 8, 0)
        tabs_layout.setSpacing(0)

        self.tab_bar_container = QWidget()
        self.tab_bar_container.setStyleSheet("background: transparent; border: none;")
        tab_bar_layout = QHBoxLayout(self.tab_bar_container)
        tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        tab_bar_layout.setSpacing(4)

        self.tab_bar = ChromeTabBar()
        self.tab_bar.animations_enabled = self.app_settings.get("smooth_tab_animations", True)
        self.tab_bar.tabCloseRequested.connect(self.close_current_tab)
        self.tab_bar.tabCloseAnimationFinished.connect(self.remove_tab_now)
        self.tab_bar.currentChanged.connect(self.current_tab_changed)
        self.tab_bar.tabMoved.connect(self.tab_moved)
        self.tab_bar.newTabRequested.connect(lambda: self.add_new_tab())
        self.tab_bar.tabContextMenuRequested.connect(self.show_tab_context_menu)
        self.tab_bar.tabDetachRequested.connect(self.detach_tab_to_window)
        self.tab_bar.externalUrlDropped.connect(
            lambda url: self.add_new_tab(url, url.fileName() or url.host() or "Новая вкладка")
        )
        self.tab_bar.tabHoverChanged.connect(self.schedule_tab_preview)
        self.tab_preview_popup = None
        self._tab_preview_index = -1
        self._tab_preview_position = QPoint()
        self.tab_preview_timer = QTimer(self)
        self.tab_preview_timer.setSingleShot(True)
        self.tab_preview_timer.setInterval(480)
        self.tab_preview_timer.timeout.connect(self.show_scheduled_tab_preview)
        
        # СТИЛИЗАЦИЯ ВКЛАДОК И КНОПКИ ЗАКРЫТИЯ
        self.tab_bar.setStyleSheet("""
            QTabBar { background: transparent; border: none; outline: none; }
            QTabBar::tab {
                background: transparent;
                color: transparent;
                padding-left: 14px;
                padding-right: 38px;
                min-width: 0px;
                max-width: 240px;
                height: 34px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 1px;
                font-size: 12px;
                border: none;
            }
            QTabBar::tab:selected { background: #35363a; color: transparent; }
            QTabBar::tab:!selected:hover { background: #292a2d; color: transparent; }
            QToolButton#tabCloseButton {
                color: #d7d9dd;
                background: transparent;
                border: none;
                border-radius: 12px;
                font-size: 20px;
                font-weight: 400;
                padding: 0px;
            }
            QToolButton#tabCloseButton:hover { background: #5f6368; color: white; }
        """)

        # КНОПКА ПЛЮС (КВАДРАТНАЯ С ОТСТУПАМИ)
        self.plus_btn = QPushButton()
        self.plus_btn.setIcon(QIcon("add.png"))
        self.plus_btn.setToolTip("Новая вкладка (Ctrl+T)")
        self.plus_btn.setFixedSize(34, 34)
        self.plus_btn.setStyleSheet("""
            QPushButton { 
                border: none; 
                background: transparent; 
            } 
            QPushButton:hover { 
                background: #3c4043;
                border-radius: 17px;
            }
        """)
        self.plus_btn.clicked.connect(lambda: self.add_new_tab())

        tab_bar_layout.addWidget(self.tab_bar)
        tab_bar_layout.addWidget(self.plus_btn, 0, Qt.AlignVCenter)
        tab_bar_layout.addStretch()
        tabs_layout.addWidget(self.tab_bar_container)

        # --- 2. ПАНЕЛЬ URL ---
        self.navbar = QWidget()
        self.navbar.setFixedHeight(48)
        self.navbar.setStyleSheet("background-color: #35363a;")
        nav_layout = QHBoxLayout(self.navbar)
        nav_layout.setContentsMargins(10, 6, 10, 6)
        nav_layout.setSpacing(8)

        btn_style = "QPushButton { border: none; background: transparent; width: 32px; height: 32px; } QPushButton:hover { background: #4a4b4f; border-radius: 16px; }"
        
        self.back_btn = QPushButton(icon=QIcon("back.png")); self.back_btn.setStyleSheet(btn_style)
        self.back_btn.setFixedSize(32, 32)
        self.back_btn.clicked.connect(lambda: self.current_browser().back() if self.current_browser() else None)

        self.forward_btn = QPushButton()
        forward_pixmap = QPixmap("back.png").transformed(
            QTransform().scale(-1, 1),
            Qt.TransformationMode.SmoothTransformation,
        )
        self.forward_btn.setIcon(QIcon(forward_pixmap))
        self.forward_btn.setStyleSheet(btn_style)
        self.forward_btn.setFixedSize(32, 32)
        self.forward_btn.setToolTip("Вперёд")
        self.forward_btn.clicked.connect(lambda: self.current_browser().forward() if self.current_browser() else None)

        self.home_btn = QPushButton()
        self.home_btn.setIcon(self.home_icon())
        self.home_btn.setToolTip("Главная страница Grom")
        self.home_btn.setStyleSheet(btn_style)
        self.home_btn.setFixedSize(32, 32)
        self.home_btn.clicked.connect(self.open_home_page)

        self.reload_btn = CircularIconButton(); self.reload_btn.setIcon(QIcon("reload.png")); self.reload_btn.setStyleSheet(btn_style)
        self.reload_btn.setObjectName("reloadButton")
        self.reload_btn.setFixedSize(28, 28)
        self.reload_btn.setIconSize(QSize(16, 16))
        self.reload_btn.clicked.connect(self.reload_current_page)
        self.reload_animation = None

        self.address_frame = QFrame()
        self.address_frame.setObjectName("addressBar")
        address_layout = QHBoxLayout(self.address_frame)
        address_layout.setContentsMargins(5, 0, 5, 0)
        address_layout.setSpacing(2)

        self.site_info_btn = QToolButton()
        self.site_info_btn.setObjectName("addressIconButton")
        self.site_info_btn.setFixedSize(28, 28)
        self.site_info_btn.setToolTip("Паспорт сайта")
        self.site_info_btn.clicked.connect(self.show_site_info_popup)

        self.url_bar = AddressLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.focusStateChanged.connect(self.address_bar_focus_changed)
        self._address_suggestion_entries = None
        self._address_suggestion_values = {}
        self.address_suggestion_model = QStringListModel(self)
        self.address_completer = QCompleter(self.address_suggestion_model, self.url_bar)
        self.address_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.address_completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self.address_completer.setMaxVisibleItems(9)
        self.url_bar.setCompleter(self.address_completer)
        self.prepare_rounded_popup(self.address_completer.popup(), 10)
        self.url_bar.textEdited.connect(self.refresh_address_suggestions)
        self.address_completer.activated.connect(self.activate_address_suggestion)
        
        self.translate_btn = QToolButton()
        self.translate_btn.setObjectName("addressIconButton")
        self.translate_btn.setFixedSize(28, 28)
        self.translate_btn.setToolTip("Параметры перевода")
        self.translate_btn.clicked.connect(self.show_translation_popup)
        self.translate_btn.hide()

        self.bookmark_btn = QToolButton()
        self.bookmark_btn.setObjectName("addressIconButton")
        self.bookmark_btn.setFixedSize(28, 28)
        self.bookmark_btn.setToolTip("Добавить в избранное")
        self.bookmark_btn.clicked.connect(self.toggle_bookmark)

        address_layout.addWidget(self.site_info_btn)
        address_layout.addWidget(self.url_bar, 1)
        address_layout.addWidget(self.translate_btn)
        address_layout.addWidget(self.bookmark_btn)

        self.profile_btn = QPushButton()
        self.profile_btn.setFixedSize(32, 32)
        self.profile_btn.setToolTip(self.current_profile.get("name", "Профиль"))
        self.profile_btn.clicked.connect(self.show_profile_menu)

        self.menu_btn = QPushButton(icon=QIcon("menu.png"))
        self.menu_btn.setFixedSize(32, 32); self.menu_btn.setStyleSheet(btn_style)
        self.menu_btn.clicked.connect(self.show_main_menu)

        self.extensions_btn = QPushButton()
        self.extensions_btn.setFixedSize(32, 32)
        self.extensions_btn.setToolTip("Встроенные расширения")
        self.extensions_btn.setStyleSheet(btn_style)
        self.extensions_btn.clicked.connect(self.show_builtin_extensions_popup)

        self.extension_pins_widget = QWidget()
        self.extension_pins_widget.setStyleSheet("background:transparent;border:none;")
        self.extension_pins_layout = QHBoxLayout(self.extension_pins_widget)
        self.extension_pins_layout.setContentsMargins(0, 0, 0, 0)
        self.extension_pins_layout.setSpacing(2)

        nav_layout.addWidget(self.back_btn); nav_layout.addWidget(self.forward_btn); nav_layout.addWidget(self.home_btn); nav_layout.addWidget(self.reload_btn)
        nav_layout.addWidget(self.address_frame, 1); nav_layout.addWidget(self.extension_pins_widget); nav_layout.addWidget(self.extensions_btn); nav_layout.addWidget(self.profile_btn); nav_layout.addWidget(self.menu_btn)
        self.refresh_extension_toolbar_buttons()

        # --- ПОИСК НА СТРАНИЦЕ ---
        self.find_bar = QWidget()
        self.find_bar.setFixedHeight(44)
        self.find_bar.setStyleSheet("background-color: #35363a;")
        find_layout = QHBoxLayout(self.find_bar)
        find_layout.setContentsMargins(0, 4, 12, 4)
        find_layout.addStretch()

        find_box = QFrame()
        self.find_box = find_box
        find_box.setFixedWidth(420)
        find_box.setStyleSheet("""
            QFrame { background: #292a2d; border: 1px solid #5f6368; border-radius: 6px; }
            QLineEdit { color: #f1f3f4; background: transparent; border: none; padding: 5px 8px; }
            QLabel { color: #bdc1c6; border: none; }
            QToolButton { color: #e8eaed; background: transparent; border: none; border-radius: 14px; }
            QToolButton:hover { background: #3c4043; }
        """)
        find_box_layout = QHBoxLayout(find_box)
        find_box_layout.setContentsMargins(8, 2, 4, 2)
        find_box_layout.setSpacing(4)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Найти на странице")
        self.find_status = QLabel("")
        self.find_status.setFixedWidth(105)
        self.find_prev_btn = QToolButton()
        self.find_prev_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.find_prev_btn.setToolTip("Предыдущее совпадение")
        self.find_next_btn = QToolButton()
        self.find_next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.find_next_btn.setToolTip("Следующее совпадение")
        self.find_close_btn = QToolButton()
        self.find_close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.find_close_btn.setToolTip("Закрыть")
        for button in (self.find_prev_btn, self.find_next_btn, self.find_close_btn):
            button.setFixedSize(28, 28)
        find_box_layout.addWidget(self.find_input, 1)
        find_box_layout.addWidget(self.find_status)
        find_box_layout.addWidget(self.find_prev_btn)
        find_box_layout.addWidget(self.find_next_btn)
        find_box_layout.addWidget(self.find_close_btn)
        find_layout.addWidget(find_box)
        self.find_bar.hide()
        self.find_input.returnPressed.connect(lambda: self.find_on_page(False))
        self.find_input.textChanged.connect(self.find_query_changed)
        self.find_prev_btn.clicked.connect(lambda: self.find_on_page(True))
        self.find_next_btn.clicked.connect(lambda: self.find_on_page(False))
        self.find_close_btn.clicked.connect(self.close_find_bar)
        
        # --- 3. ПАНЕЛЬ ЗАКЛАДОК ---
        self.bookmarks_panel = QWidget()
        self.bookmarks_panel.setFixedHeight(35); self.bookmarks_panel.setStyleSheet("background-color: #35363a;")
        self.bookmarks_panel.setVisible(False); self.bookmarks_panel.setAcceptDrops(True)
        self.bookmarks_panel.dragEnterEvent = lambda e: e.accept(); self.bookmarks_panel.dropEvent = self.on_bookmark_drop
        
        self.bookmarks_layout = QHBoxLayout(self.bookmarks_panel)
        self.bookmarks_layout.setContentsMargins(10, 0, 10, 5); self.bookmarks_layout.setSpacing(5); self.bookmarks_layout.addStretch()
        
        self.bookmarks = []
        self.bookmarks_file = os.path.join(self.storage_path, "bookmarks.json")
        self.history_file = os.path.join(self.storage_path, "history.json")
        self.icons_cache_dir = os.path.join(self.storage_path, "icons_cache")
        if not os.path.exists(self.icons_cache_dir):
            os.makedirs(self.icons_cache_dir)
        
        self.history_data = []  # Для хранения данных истории

        # --- ГЛАВНЫЙ МАКЕТ ---
        self.tab_content = QStackedWidget()
        main_widget = QWidget(); main_vbox = QVBoxLayout(main_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0); main_vbox.setSpacing(0)
        main_vbox.addWidget(self.tabs_panel); main_vbox.addWidget(self.navbar); main_vbox.addWidget(self.find_bar); main_vbox.addWidget(self.bookmarks_panel)
        self.content_row = QWidget()
        self.content_row_layout = QHBoxLayout(self.content_row)
        self.content_row_layout.setContentsMargins(0, 0, 0, 0)
        self.content_row_layout.setSpacing(0)
        self.vertical_tabs_panel = self.create_vertical_tabs_panel()
        self.content_row_layout.addWidget(self.vertical_tabs_panel)
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setHandleWidth(5)
        self.content_splitter.addWidget(self.tab_content)
        self.devtools_panel = self.create_devtools_panel()
        self.content_splitter.addWidget(self.devtools_panel)
        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 0)
        self.content_row_layout.addWidget(self.content_splitter, 1)
        main_vbox.addWidget(self.content_row, 1)
        self.setCentralWidget(main_widget)
        QApplication.instance().installEventFilter(self)
        
        self.apply_theme()
        self.forward_btn.setVisible(self.app_settings.get("show_forward", True))
        self.home_btn.setVisible(self.app_settings.get("show_home_button", False))
        self.load_bookmarks()
        first_run = not self.guest_mode and not self.app_settings.get("welcome_completed", False)
        if self.detached_window:
            pass
        elif self.app_mode:
            self.add_new_tab(QUrl(self.app_url), label="Grom")
        elif first_run:
            self._session_prompt_pending = False
            self.add_new_tab(
                label="Welcome",
                internal_html=self.welcome_page_html(),
                internal_url="grom://welcome",
            )
        else:
            self.add_new_tab(label="Grom")
        self.setup_shortcuts()
        self.session_timer = QTimer(self)
        self.session_timer.setInterval(10000)
        self.session_timer.timeout.connect(self.save_open_session)
        self.session_timer.start()
        self.memory_timer = QTimer(self)
        self.memory_timer.setInterval(60000)
        self.memory_timer.timeout.connect(self.run_periodic_tab_maintenance)
        self.memory_timer.start()
        self.save_open_session()
        self.update_vertical_tabs_visibility()
        if self.app_mode:
            self.tabs_panel.hide()
            self.navbar.hide()
            self.bookmarks_panel.hide()
            self.vertical_tabs_panel.hide()
        if not self.detached_window:
            self.showMaximized()
            QTimer.singleShot(250, self.bring_to_front)
        QTimer.singleShot(0, self.update_browser_polling)
        if not self.app_mode and not self.detached_window:
            QTimer.singleShot(850, self.show_restore_session_prompt)











    def create_vertical_tabs_panel(self):
        panel = QFrame()
        panel.setObjectName("verticalTabsPanel")
        panel.setFixedWidth(238)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 7, 8, 8)
        layout.setSpacing(7)
        header_widget = QWidget()
        header_widget.setObjectName("verticalTabsHeader")
        header_widget.setFixedHeight(36)
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(8, 2, 2, 2)
        header.setSpacing(6)
        title = QLabel("Вкладки")
        title.setObjectName("verticalTabsTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.vertical_add_button = QToolButton()
        self.vertical_add_button.setObjectName("verticalAddButton")
        self.vertical_add_button.setIcon(self.themed_icon("add.png", self.theme_colors["icon"]))
        self.vertical_add_button.setIconSize(QSize(18, 18))
        self.vertical_add_button.setToolTip("Новая вкладка")
        self.vertical_add_button.setFixedSize(32, 32)
        self.vertical_add_button.clicked.connect(lambda: self.add_new_tab())
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.vertical_add_button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(header_widget)
        self.vertical_tabs_list = QListWidget()
        self.vertical_tabs_list.setObjectName("verticalTabsList")
        self.vertical_tabs_list.setIconSize(QSize(18, 18))
        self.vertical_tabs_list.setSpacing(2)
        self.vertical_tabs_list.currentRowChanged.connect(self.select_vertical_tab)
        self.vertical_tabs_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.vertical_tabs_list.customContextMenuRequested.connect(
            lambda pos: self.show_tab_context_menu(
                self.vertical_tabs_list.indexAt(pos).row(),
                self.vertical_tabs_list.mapToGlobal(pos),
            ) if self.vertical_tabs_list.indexAt(pos).isValid() else None
        )
        layout.addWidget(self.vertical_tabs_list, 1)
        panel.hide()
        return panel

    def select_vertical_tab(self, row):
        if 0 <= row < self.tab_bar.count() and row != self.tab_bar.currentIndex():
            self.tab_bar.setCurrentIndex(row)

    def sync_vertical_tabs(self):
        if not hasattr(self, "vertical_tabs_list"):
            return
        current = self.tab_bar.currentIndex()
        self.vertical_tabs_list.blockSignals(True)
        self.vertical_tabs_list.clear()
        for index in range(self.tab_bar.count()):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 40))
            item.setToolTip(self.tab_bar.tabToolTip(index))
            workspace = self.tab_content.widget(index)
            if isinstance(workspace, TabWorkspace):
                if workspace.primary_browser.is_sleeping:
                    item.setForeground(QColor(self.theme_colors["muted"]))
                group = self.tab_groups.get(workspace.group_id)
                if group:
                    item.setBackground(QColor(group.get("color", "#4f8cff")).lighter(75))
            self.vertical_tabs_list.addItem(item)
            row = QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(7, 0, 3, 0)
            row_layout.setSpacing(7)
            icon_label = QLabel()
            icon_label.setFixedSize(18, 18)
            icon_label.setPixmap(self.tab_bar.tabIcon(index).pixmap(18, 18))
            icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            title_label = QLabel(self.tab_bar.tabText(index))
            title_label.setStyleSheet(f"color:{self.theme_colors['muted'] if isinstance(workspace, TabWorkspace) and workspace.primary_browser.is_sleeping else self.theme_colors['text']};")
            title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            close_button = TabCloseButton()
            close_button.setFixedSize(24, 24)
            close_button.setToolTip("Закрыть вкладку")
            close_button.set_line_color(self.theme_colors["muted"], self.theme_colors["text"])
            close_button.clicked.connect(
                lambda _checked=False, current_item=item: self.close_vertical_tab(current_item)
            )
            row_layout.addWidget(icon_label)
            row_layout.addWidget(title_label, 1)
            row_layout.addWidget(close_button)
            self.vertical_tabs_list.setItemWidget(item, row)
        self.vertical_tabs_list.setCurrentRow(current)
        self.vertical_tabs_list.blockSignals(False)
        self.update_vertical_tabs_visibility()

    def update_vertical_tabs_visibility(self):
        if not hasattr(self, "vertical_tabs_panel") or self.app_mode:
            return
        visible = bool(self.app_settings.get("vertical_tabs", False))
        self.vertical_tabs_panel.setVisible(visible)
        self.tabs_panel.setVisible(not visible and not self.isFullScreen())

    def close_vertical_tab(self, item):
        row = self.vertical_tabs_list.row(item)
        if row >= 0:
            self.close_current_tab(row)

    def create_devtools_panel(self):
        panel = QFrame()
        panel.setObjectName("devtoolsPanel")
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(900)
        panel.resize(540, panel.height())
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("devtoolsHeader")
        header.setFixedHeight(38)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 6, 0)
        self.devtools_title = QLabel("Инструменты разработчика")
        header_layout.addWidget(self.devtools_title)
        header_layout.addStretch()
        refresh_button = QToolButton()
        refresh_button.setText("↻")
        refresh_button.setToolTip("Обновить данные панели")
        refresh_button.setFixedSize(28, 28)
        refresh_button.clicked.connect(self.refresh_devtools)
        header_layout.addWidget(refresh_button)
        clear_button = QToolButton()
        clear_button.setText("⌫")
        clear_button.setToolTip("Очистить консоль")
        clear_button.setFixedSize(28, 28)
        clear_button.clicked.connect(self.devtools_console_clear)
        header_layout.addWidget(clear_button)
        close_button = QToolButton()
        close_button.setText("×")
        close_button.setToolTip("Закрыть (F12)")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.toggle_devtools)
        header_layout.addWidget(close_button)
        layout.addWidget(header)

        self.devtools_tabs = QTabWidget()
        self.devtools_console = QPlainTextEdit()
        self.devtools_console.setReadOnly(True)
        self.devtools_console.setPlaceholderText("Сообщения console.log и ошибки страницы")
        self.devtools_console.setFont(QFont("Consolas", 10))
        self.devtools_console_highlighter = DevtoolsSyntaxHighlighter(
            self.devtools_console.document(), "console"
        )
        console_page = QWidget()
        console_layout = QVBoxLayout(console_page)
        console_layout.setContentsMargins(8, 8, 8, 8)
        console_layout.setSpacing(6)
        console_layout.addWidget(self.devtools_console, 1)
        command_row = QHBoxLayout()
        self.devtools_command = QLineEdit()
        self.devtools_command.setPlaceholderText("Выполнить JavaScript")
        run_button = QPushButton("Выполнить")
        self.devtools_command.returnPressed.connect(self.evaluate_devtools_command)
        run_button.clicked.connect(self.evaluate_devtools_command)
        command_row.addWidget(self.devtools_command, 1)
        command_row.addWidget(run_button)
        console_layout.addLayout(command_row)

        self.devtools_elements = QPlainTextEdit()
        self.devtools_elements.setReadOnly(True)
        self.devtools_elements.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.devtools_elements.setFont(QFont("Consolas", 10))
        self.devtools_html_highlighter = DevtoolsSyntaxHighlighter(
            self.devtools_elements.document(), "html"
        )
        elements_page = QWidget()
        elements_layout = QVBoxLayout(elements_page)
        elements_layout.setContentsMargins(8, 8, 8, 8)
        elements_layout.setSpacing(6)
        elements_search_row = QHBoxLayout()
        self.devtools_search = QLineEdit()
        self.devtools_search.setPlaceholderText("Найти в HTML")
        elements_find = QPushButton("Найти")
        self.devtools_search.returnPressed.connect(self.find_in_devtools_elements)
        elements_find.clicked.connect(self.find_in_devtools_elements)
        elements_search_row.addWidget(self.devtools_search, 1)
        elements_search_row.addWidget(elements_find)
        elements_layout.addLayout(elements_search_row)
        elements_layout.addWidget(self.devtools_elements, 1)
        self.devtools_network = QPlainTextEdit()
        self.devtools_network.setReadOnly(True)
        self.devtools_network.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.devtools_network.setFont(QFont("Consolas", 9))
        self.devtools_tabs.addTab(console_page, "Консоль")
        self.devtools_tabs.addTab(elements_page, "Элементы")
        self.devtools_tabs.addTab(self.devtools_network, "Сеть")
        self.devtools_tabs.currentChanged.connect(lambda _index: self.refresh_devtools())
        layout.addWidget(self.devtools_tabs, 1)
        panel.hide()
        return panel

    def style_devtools(self):
        if not hasattr(self, "devtools_panel"):
            return
        colors = self.theme_colors
        self.devtools_panel.setStyleSheet(f"""
            QFrame#devtoolsPanel {{ background:{colors['popup']}; border-left:1px solid {colors['border']}; }}
            QWidget#devtoolsHeader {{ background:{colors['toolbar']}; border-bottom:1px solid {colors['border']}; }}
            QLabel {{ color:{colors['text']}; border:none; }}
            QTabWidget::pane {{ border:none; background:{colors['background']}; }}
            QTabBar::tab {{ color:{colors['muted']}; background:{colors['toolbar']}; padding:9px 14px; border:none; }}
            QTabBar::tab:selected {{ color:{colors['text']}; border-bottom:2px solid {colors['accent']}; }}
            QPlainTextEdit, QLineEdit {{ color:{colors['text']}; background:{colors['input']}; border:1px solid {colors['border']}; padding:6px; selection-background-color:{colors['accent']}; }}
            QPushButton, QToolButton {{ color:{colors['text']}; background:{colors['surface']}; border:none; border-radius:5px; padding:7px 10px; }}
            QPushButton:hover, QToolButton:hover {{ background:{colors['hover']}; }}
        """)
        self.devtools_html_highlighter.set_colors(colors["is_dark"], colors["accent"])
        self.devtools_console_highlighter.set_colors(colors["is_dark"], colors["accent"])

    def toggle_devtools(self):
        visible = not self.devtools_panel.isVisible()
        self.devtools_panel.setVisible(visible)
        if visible:
            width = max(1, self.content_splitter.width())
            panel_width = min(540, max(320, width // 2))
            self.content_splitter.setSizes([max(1, width - panel_width), panel_width])
            self.refresh_devtools()

    def refresh_devtools(self):
        if not hasattr(self, "devtools_panel") or not self.devtools_panel.isVisible():
            return
        browser = self.current_browser()
        if not browser:
            return
        self.devtools_title.setText(
            "Инструменты разработчика" + (f" · {browser.url().host()}" if browser.url().host() else "")
        )
        browser.runJavaScript(
            "document.documentElement?.outerHTML?.slice(0, 500000) || ''",
            lambda html: self.devtools_elements.setPlainText(str(html or "")),
        )
        browser.runJavaScript(
            "JSON.stringify(performance.getEntriesByType('resource').map(e=>({name:e.name,type:e.initiatorType,duration:Math.round(e.duration),size:e.transferSize||0})).slice(-300))",
            self.update_devtools_network,
        )

    def update_devtools_network(self, result):
        try:
            records = json.loads(result) if result else []
        except (TypeError, ValueError):
            records = []
        lines = [
            f"{item.get('type') or 'resource':10} {int(item.get('duration') or 0):5} ms  {self.human_size(item.get('size') or 0):>9}  {item.get('name', '')}"
            for item in records
            if isinstance(item, dict)
        ]
        self.devtools_network.setPlainText("\n".join(lines) if lines else "Сетевые ресурсы пока не зарегистрированы")

    def devtools_console_clear(self):
        if hasattr(self, "devtools_console"):
            self.devtools_console.clear()

    def find_in_devtools_elements(self):
        query = self.devtools_search.text().strip()
        if not query:
            return
        if not self.devtools_elements.find(query):
            cursor = self.devtools_elements.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.devtools_elements.setTextCursor(cursor)
            self.devtools_elements.find(query)

    def evaluate_devtools_command(self):
        browser = self.current_browser()
        command = self.devtools_command.text().strip()
        if not browser or not command:
            return
        self.devtools_console.appendPlainText(f"> {command}")
        self.devtools_command.clear()
        script = (
            "(() => { try { const value = eval("
            + json.dumps(command)
            + "); return JSON.stringify({ok:true,value:typeof value==='string'?value:JSON.stringify(value)}); }"
            " catch(error) { return JSON.stringify({ok:false,value:String(error)}); } })()"
        )
        browser.runJavaScript(script, self.show_devtools_result)

    def show_devtools_result(self, result):
        try:
            payload = json.loads(result) if result else {"ok": True, "value": "undefined"}
            prefix = "" if payload.get("ok") else "Ошибка: "
            self.devtools_console.appendPlainText(prefix + str(payload.get("value", "undefined")))
        except (TypeError, ValueError):
            self.devtools_console.appendPlainText(str(result))

    def receive_console_messages(self, browser, messages):
        if browser != self.current_browser():
            return
        for message in messages:
            if not isinstance(message, dict):
                continue
            level = str(message.get("level", "log")).upper()
            timestamp = str(message.get("time", ""))
            self.devtools_console.appendPlainText(
                f"[{timestamp}] {level}: {message.get('text', '')}"
            )

    # --- ЛОГИКА ИСТОРИИ ---
    def delete_from_history(self, url):
        """Удаляет запись из истории по URL или всю историю"""
        if not os.path.exists(self.history_file): return
        
        # Проверяем специальный флаг для очистки всей истории
        if url == "__CLEAR_ALL_HISTORY__":
            # Очищаем весь файл истории
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            self.history_data = []
        else:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # Фильтруем историю, удаляя все записи с данным URL
            history_data = [item for item in history_data if item['url'] != url]
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            # Обновляем данные истории
            self.history_data = history_data
    
    def get_icon_cache_path(self, url):
        """Возвращает путь к кешированной иконке для URL"""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.icons_cache_dir, f"{url_hash}.png")
    
    def save_icon_to_cache(self, url, icon):
        """Сохраняет иконку в кеш"""
        if icon and not icon.isNull():
            cache_path = self.get_icon_cache_path(url)
            pixmap = icon.pixmap(32, 32)
            pixmap.save(cache_path, "PNG")
    
    def get_cached_icon(self, url):
        """Получает иконку из кеша или из закладок"""
        # Сначала ищем в закладках
        for b in self.bookmarks:
            if b["url"] == url and "button" in b:
                return b["button"].icon()
        
        # Затем ищем в кеше
        cache_path = self.get_icon_cache_path(url)
        if os.path.exists(cache_path):
            return QIcon(cache_path)
        
        return QIcon()
    
    def clear_icon_cache_for_url(self, url):
        """Удаляет иконку из кеша для данного URL"""
        cache_path = self.get_icon_cache_path(url)
        if os.path.exists(cache_path):
            os.remove(cache_path)
    
    def save_to_history(self, url, title):
        if not url or url == "about:blank": return
        history_data = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f: 
                    history_data = json.load(f)
            except: 
                pass
        history_data.append({"title": title, "url": url, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        # Сохраняем последние 200 записей
        with open(self.history_file, 'w', encoding='utf-8') as f: 
            json.dump(history_data[-200:], f, ensure_ascii=False, indent=2)
        self._address_suggestion_entries = None

    def load_session(self):
        try:
            with open(self.session_file, "r", encoding="utf-8") as file:
                state = json.load(file)
            return state if isinstance(state, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return {}

    def load_recent_sessions(self):
        try:
            with open(self.recent_sessions_file, "r", encoding="utf-8") as file:
                records = json.load(file)
            return records if isinstance(records, list) else []
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return []

    def save_recent_sessions(self):
        with open(self.recent_sessions_file, "w", encoding="utf-8") as file:
            json.dump(self.recent_sessions[-12:], file, ensure_ascii=False, indent=2)

    def archive_session_for_history(self):
        tabs = []
        for index in range(self.tab_content.count()):
            record = self.tab_record(index)
            if record and not record.get("private"):
                tabs.append(record)
        if len(tabs) <= 3:
            return
        self.archive_saved_session({"tabs": tabs, "groups": dict(self.tab_groups)})

    def archive_saved_session(self, state):
        tabs = state.get("tabs", []) if isinstance(state, dict) else []
        if not isinstance(tabs, list) or len(tabs) <= 3:
            return
        signature = json.dumps(tabs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if self.recent_sessions and self.recent_sessions[-1].get("signature") == signature:
            return
        self.recent_sessions.append({
            "id": uuid.uuid4().hex,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tabs": tabs,
            "groups": dict(state.get("groups", {})),
            "signature": signature,
        })
        self.save_recent_sessions()

    def restore_recent_session(self, session_record, popup=None):
        tabs = session_record.get("tabs", []) if isinstance(session_record, dict) else []
        if not isinstance(tabs, list) or not tabs:
            return
        self._restoring_session = True
        restored = 0
        saved_groups = session_record.get("groups", {})
        group_map = {
            old_id: uuid.uuid4().hex[:10]
            for old_id in saved_groups
        } if isinstance(saved_groups, dict) else {}
        for old_id, new_id in group_map.items():
            group = saved_groups.get(old_id, {})
            self.tab_groups[new_id] = dict(group) if isinstance(group, dict) else {}
        try:
            for record in tabs:
                browser = self.restore_tab_record(dict(record)) if isinstance(record, dict) else None
                if browser:
                    workspace = self.workspace_for_browser(browser)
                    if workspace:
                        workspace.group_id = group_map.get(record.get("group_id"))
                    restored += 1
            self.refresh_tab_groups()
        finally:
            self._restoring_session = False
        if restored:
            self.tab_bar.setCurrentIndex(max(0, self.tab_bar.count() - restored))
            self.save_open_session()
        if popup:
            popup.close()

    def load_closed_groups(self):
        try:
            with open(self.closed_groups_file, "r", encoding="utf-8") as file:
                groups = json.load(file)
            return groups if isinstance(groups, list) else []
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return []

    def save_closed_groups(self):
        with open(self.closed_groups_file, "w", encoding="utf-8") as file:
            json.dump(self.closed_groups[-20:], file, ensure_ascii=False, indent=2)

    def load_closed_tabs(self):
        try:
            with open(self.closed_tabs_file, "r", encoding="utf-8") as file:
                records = json.load(file)
            return records if isinstance(records, list) else []
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return []

    def save_closed_tabs(self):
        with open(self.closed_tabs_file, "w", encoding="utf-8") as file:
            json.dump(self.closed_tabs[-50:], file, ensure_ascii=False, indent=2)

    def tab_record(self, index):
        workspace = self.tab_content.widget(index)
        if not isinstance(workspace, TabWorkspace):
            return None
        browser = workspace.primary_browser
        if getattr(browser, "popup_id", ""):
            return None
        return {
            "url": browser.url().toString(),
            "title": browser.title() or self.tab_bar.tabText(index) or "Новая вкладка",
            "internal_page": browser.internal_page,
            "private": browser.is_private,
            "group_id": workspace.group_id,
            "zoom": browser.zoom_percent(),
            "split_url": workspace.secondary_browser.url().toString() if workspace.secondary_browser else "",
        }

    def recover_session_url(self, record):
        raw_url = str(record.get("url", "")).strip()
        url = QUrl(raw_url)
        if url.isValid() and url.scheme() in ("http", "https") and url.host():
            return url

        title = str(record.get("title", "")).strip()
        normalized_title = title.casefold()
        known_services = {
            "whatsapp": "https://web.whatsapp.com/",
            "chatgpt": "https://chatgpt.com/",
            "claude": "https://claude.ai/new",
            "gmail": "https://mail.google.com/",
            "tiktok": "https://www.tiktok.com/",
            "youtube": "https://www.youtube.com/",
            "telegram": "https://web.telegram.org/",
            "twitch": "https://www.twitch.tv/",
        }
        for marker, service_url in known_services.items():
            if marker in normalized_title:
                return QUrl(service_url)
        if normalized_title:
            try:
                with open(self.history_file, "r", encoding="utf-8") as file:
                    history = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError, TypeError):
                history = []
            for item in reversed(history if isinstance(history, list) else []):
                history_title = str(item.get("title", "")).strip()
                history_url = QUrl(str(item.get("url", "")).strip())
                if (
                    history_title.casefold() == normalized_title
                    and history_url.isValid()
                    and history_url.scheme() in ("http", "https")
                    and history_url.host()
                ):
                    return history_url

        return QUrl()

    def restore_tab_record(self, record):
        if not isinstance(record, dict):
            return None
        internal = record.get("internal_page")
        private = bool(record.get("private", False))
        if internal == "home":
            browser = self.add_new_tab(label="Grom", internal_html=self.home_page_html(), internal_url="grom://home", private=private)
        elif internal == "welcome":
            browser = self.add_new_tab(label="Добро пожаловать", internal_html=self.welcome_page_html(), internal_url="grom://welcome", private=private)
        elif internal == "settings":
            browser = self.add_new_tab(label="Настройки", internal_html=self.settings_page_html(), internal_url="grom://settings/profiles", private=private)
        elif internal == "downloads":
            browser = self.add_new_tab(label="Загрузки", internal_html=self.downloads_page_html(), internal_url="grom://downloads", private=private)
        else:
            url = self.recover_session_url(record)
            if not url.isValid() or url.isEmpty():
                return None
            record["url"] = url.toString()
            browser = self.add_new_tab(url, str(record.get("title") or "Новая вкладка"), private=private)
        browser.set_zoom_percent(record.get("zoom", self.app_settings.get("default_zoom", 100)))
        split_url = QUrl(str(record.get("split_url", "")))
        workspace = self.workspace_for_browser(browser)
        if workspace and split_url.isValid() and split_url.scheme() in ("http", "https"):
            self.open_split_browser(workspace, split_url)
        return browser

    def restore_closed_tab(self):
        if not self.closed_tabs:
            return
        record = self.closed_tabs.pop()
        self.save_closed_tabs()
        self.restore_tab_record(record)

    def save_session(self, clean_exit=False):
        tabs = []
        groups = {}
        current_index = 0
        windows = [
            window for window in Browser._open_windows
            if hasattr(window, "tab_content")
            and not window.app_mode
            and window.profile_id == self.profile_id
            and window.guest_mode == self.guest_mode
            and window.storage_path == self.storage_path
        ]
        for window in windows:
            offset = len(tabs)
            groups.update(window.tab_groups)
            for index in range(window.tab_content.count()):
                workspace = window.tab_content.widget(index)
                if not isinstance(workspace, TabWorkspace):
                    continue
                browser = workspace.primary_browser
                if browser.is_private:
                    continue
                record = window.tab_record(index)
                if record:
                    tabs.append(record)
            if window is self and window.tab_bar.currentIndex() >= 0:
                current_index = offset + window.tab_bar.currentIndex()
        payload = {
            "clean_exit": bool(clean_exit),
            "current_index": current_index,
            "groups": groups,
            "tabs": tabs,
        }
        signature = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        if signature == self._last_session_signature and os.path.isfile(self.session_file):
            return
        state = {
            **payload,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.session_file, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
        for window in windows:
            window._last_session_signature = signature

    def save_open_session(self):
        if not self._restoring_session and not self._session_prompt_pending:
            self.save_session(False)

    def restore_previous_session(self):
        state = self.previous_session
        tabs = state.get("tabs", [])
        if not isinstance(tabs, list) or not tabs:
            return False
        self._restoring_session = True
        self._session_prompt_pending = False
        restored = 0
        background_browsers = []
        try:
            while self.tab_content.count():
                widget = self.tab_content.widget(0)
                self.tab_content.removeWidget(widget)
                widget.deleteLater()
            while self.tab_bar.count():
                self.tab_bar.removeTab(0)
            self.tab_groups = dict(state.get("groups", {}))
            for record in tabs:
                if not isinstance(record, dict):
                    continue
                if record.get("internal_page"):
                    browser = self.restore_tab_record(record)
                else:
                    url = self.recover_session_url(record)
                    if not url.isValid() or url.isEmpty():
                        continue
                    record["url"] = url.toString()
                    browser = self.add_new_tab(
                        url,
                        str(record.get("title") or url.host() or "New Tab"),
                        private=bool(record.get("private", False)),
                        defer_navigation=True,
                    )
                    background_browsers.append(browser)
                    browser.set_zoom_percent(
                        record.get("zoom", self.app_settings.get("default_zoom", 100))
                    )
                    split_url = QUrl(str(record.get("split_url", "")))
                    deferred_workspace = self.workspace_for_browser(browser)
                    if (
                        deferred_workspace
                        and split_url.isValid()
                        and split_url.scheme() in ("http", "https")
                    ):
                        self.open_split_browser(deferred_workspace, split_url)
                if not browser:
                    continue
                if browser.internal_page:
                    browser.reload_on_next_show(schedule_if_visible=False)
                workspace = self.workspace_for_browser(browser)
                if workspace:
                    workspace.group_id = record.get("group_id")
                restored += 1
            if restored:
                index = max(0, min(int(state.get("current_index", 0)), self.tab_bar.count() - 1))
                self.tab_bar.setCurrentIndex(index)
                self.refresh_tab_groups()
                current = self.current_browser()
                if current:
                    QTimer.singleShot(100, current.reload_deferred_page)
                    background_browsers = [
                        browser for browser in background_browsers if browser is not current
                    ]
                self.queue_restored_tabs_for_background_load(background_browsers)
        finally:
            self._restoring_session = False
        if not restored:
            self.add_new_tab(label="Grom")
        self.save_open_session()
        return restored > 0

    def queue_restored_tabs_for_background_load(self, browsers):
        self._session_background_queue = [
            browser for browser in browsers
            if browser and browser.has_deferred_navigation()
        ]
        if self._session_background_queue:
            QTimer.singleShot(700, self.load_next_restored_tab)

    def load_next_restored_tab(self):
        if self._session_background_loading:
            return
        while self._session_background_queue:
            browser = self._session_background_queue.pop(0)
            if self.workspace_for_browser(browser) and browser.has_deferred_navigation():
                self._session_background_loading = True
                browser.reload_deferred_page(allow_hidden=True)
                QTimer.singleShot(
                    120,
                    lambda target=browser: self.finish_restored_tab_start(
                        target, 0
                    ),
                )
                break

    def finish_restored_tab_start(self, browser, attempt):
        if (
            self.workspace_for_browser(browser)
            and (browser.has_deferred_navigation() or browser.is_loading())
            and attempt < 60
        ):
            QTimer.singleShot(
                100,
                lambda target=browser, current=attempt + 1:
                self.finish_restored_tab_start(target, current),
            )
            return
        self._session_background_loading = False
        if self._session_background_queue:
            QTimer.singleShot(180, self.load_next_restored_tab)

    def show_restore_session_prompt(self):
        tabs = self.previous_session.get("tabs", [])
        if not self.app_settings.get("restore_session_prompt", True):
            self._session_prompt_pending = False
            self.save_open_session()
            return
        if not self._session_prompt_pending or not isinstance(tabs, list) or not tabs:
            return
        colors = self.theme_colors
        popup = QFrame(
            self,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        popup.setObjectName("restoreSessionPopup")
        self.prepare_rounded_popup(popup)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.setFixedSize(340, 126)
        popup.setStyleSheet(f"""
            QFrame#restoreSessionPopup {{ background:{colors['popup']}; color:{colors['text']}; border:1px solid {colors['border']}; border-radius:12px; }}
            QLabel {{ color:{colors['text']}; border:none; }}
            QLabel#restoreDetails {{ color:{colors['muted']}; }}
            QPushButton {{ color:{colors['text']}; background:{colors['surface']}; border:none; border-radius:7px; padding:9px 12px; }}
            QPushButton:hover {{ background:{colors['hover']}; }}
            QPushButton#restoreAll {{ color:{'#202124' if colors['is_dark'] else '#ffffff'}; background:{colors['accent']}; font-weight:600; }}
            QPushButton#restoreAll:hover {{ background:{QColor(colors['accent']).lighter(112).name()}; }}
            QToolButton {{ color:{colors['muted']}; background:transparent; border:none; border-radius:7px; font-size:18px; }}
            QToolButton:hover {{ color:{colors['text']}; background:{colors['hover']}; }}
        """)
        layout = QGridLayout(popup)
        layout.setContentsMargins(14, 10, 10, 12)
        layout.setSpacing(6)
        title = QLabel("Восстановить прошлую сессию?")
        title.setStyleSheet("font-size:14px; font-weight:600;")
        details = QLabel(f"Вкладок: {len(tabs)}")
        details.setObjectName("restoreDetails")
        restore = QPushButton("Восстановить все вкладки")
        restore.setObjectName("restoreAll")
        close = QToolButton()
        close.setText("×")
        close.setFixedSize(28, 28)
        layout.addWidget(title, 0, 0)
        layout.addWidget(close, 0, 1)
        layout.addWidget(details, 1, 0, 1, 2)
        layout.addWidget(restore, 2, 0, 1, 2)
        restore.clicked.connect(lambda: self.accept_restore_session(popup))
        close.clicked.connect(lambda: (popup.close(), self.dismiss_restore_prompt()))
        self.restore_popup = popup
        anchor = self.mapToGlobal(QPoint(self.width() - popup.width() - 18, 126))
        popup.move(anchor)
        popup.show()
        popup.raise_()

    def accept_restore_session(self, popup):
        self.restore_popup = None
        restored = self.restore_previous_session()
        popup.close()
        if not restored:
            QMessageBox.warning(
                self,
                "Восстановление сессии",
                "В сохранённой сессии не найдено вкладок для восстановления.",
            )

    def dismiss_restore_prompt(self):
        self._session_prompt_pending = False
        self.save_open_session()

    def dismiss_restore_prompt_on_activity(self):
        if not self._session_prompt_pending:
            return
        popup = self.restore_popup
        if popup is not None:
            try:
                popup.close()
            except RuntimeError:
                pass
        self.restore_popup = None
        self.dismiss_restore_prompt()

    def eventFilter(self, watched, event):
        radius = watched.property("gromPopupRadius") if isinstance(watched, QWidget) else None
        if radius and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.apply_rounded_popup_mask(watched, int(radius))
        if (
            isinstance(watched, QWidget)
            and watched.property("gromAdditionalTools")
        ):
            if event.type() == QEvent.Type.Enter:
                self.stop_additional_tools_close_timer()
                QTimer.singleShot(80, lambda button=watched: self.show_additional_tools_menu(button))
            elif event.type() == QEvent.Type.Leave:
                self.schedule_additional_tools_close()
        if (
            isinstance(watched, QWidget)
            and watched.property("gromAdditionalToolsMenu")
        ):
            if event.type() == QEvent.Type.Enter:
                self.stop_additional_tools_close_timer()
            elif event.type() == QEvent.Type.Leave:
                self.schedule_additional_tools_close()
        if self._session_prompt_pending and event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
            QEvent.Type.TouchBegin,
        ):
            popup = self.restore_popup
            inside_restore_popup = False
            if popup is not None:
                try:
                    if isinstance(watched, QWidget):
                        inside_restore_popup = watched is popup or popup.isAncestorOf(watched)
                    if not inside_restore_popup and event.type() in (
                        QEvent.Type.MouseButtonPress,
                        QEvent.Type.Wheel,
                    ):
                        global_position = getattr(event, "globalPosition", lambda: QPointF())().toPoint()
                        inside_restore_popup = popup.frameGeometry().contains(global_position)
                    if not inside_restore_popup and event.type() == QEvent.Type.KeyPress:
                        focused = QApplication.focusWidget()
                        inside_restore_popup = bool(
                            focused and (focused is popup or popup.isAncestorOf(focused))
                        )
                except RuntimeError:
                    self.restore_popup = None
            if not inside_restore_popup:
                self.dismiss_restore_prompt_on_activity()
        return super().eventFilter(watched, event)

    def default_start_url(self):
        mode = self.app_settings.get("start_page", "grom")
        if mode == "grom":
            return QUrl("grom://home")
        if mode == "blank":
            return QUrl("about:blank")
        if mode == "custom":
            value = str(self.app_settings.get("start_page_url", "")).strip()
            if value:
                if not value.lower().startswith(("http://", "https://")):
                    value = "https://" + value
                url = QUrl(value)
                if url.isValid():
                    return url
        return QUrl("https://www.google.com")

    def load_app_settings(self):
        defaults = {
            "welcome_completed": False,
            "theme": "light",
            "custom_color": "#3f4652",
            "theme_overrides": {},
            "theme_image_path": "",
            "show_forward": True,
            "show_home_button": False,
            "show_extensions_button": True,
            "default_zoom": 100,
            "font_scale": 100,
            "font_scale_settings": False,
            "search_engine": "google",
            "start_page": "grom",
            "interface_language": "en",
            "start_page_url": "",
            "home_use_theme": True,
            "home_color": "#202124",
            "home_background_url": "",
            "home_background_path": "",
            "home_shortcuts_limit": 16,
            "hardware_acceleration": True,
            "memory_saver": True,
            "sleep_minutes": 15,
            "max_concurrent_downloads": 3,
            "download_speed_limit_kbps": 0,
            "vertical_tabs": False,
            "reader_font_size": 18,
            "restore_session_prompt": True,
            "smooth_tab_animations": True,
            "show_bookmarks_bar": True,
            "ad_blocker": True,
            "password_manager": False,
            "offer_save_passwords": True,
            "autofill_passwords": True,
            "translation_language": "ru",
            "offer_translation": True,
            "auto_translate": False,
            "builtin_extensions": default_builtin_extensions(),
            "audio_boost": 100,
            "audio_bass": 0,
            "audio_treble": 0,
            "video_speed": 1.0,
            "blocker_strict": True,
            "blocker_clean_links": True,
            "blocker_cookie_banners": True,
            "youtube_insights_panel": True,
            "youtube_hide_shorts": False,
            "youtube_hide_comments": False,
            "youtube_hide_live_chat": False,
            "youtube_hide_recommendations": False,
            "youtube_hide_end_screens": False,
            "twitch_auto_points": True,
            "twitch_compact_chat": False,
            "twitch_emote_size": 28,
            "twitch_hide_chat": False,
            "twitch_hide_sidebar": False,
            "twitch_hide_recommendations": False,
            "twitch_hide_extensions": False,
            "twitch_visible_chatters": True,
            "twitch_chat_media": True,
            "twitch_pin_streamers": True,
            "twitch_channel_tools": True,
            "twitch_highlight_mentions": True,
            "twitch_stream_latency": True,
            "twitch_vod_time": True,
            "twitch_clip_download": True,
            "twitch_message_menu": True,
            "twitch_local_watchtime": True,
            "faceit_compact_cards": True,
            "faceit_highlight_stats": True,
            "faceit_auto_accept": False,
            "password_never_save": [],
            "menu_commands": {
                "tab_search": True,
                "find_page": True,
                "screenshot": False,
                "split_screen": False,
                "developer_tools": False,
                "install_site": False,
            },
            "site_permissions": {
                "camera": "ask",
                "microphone": "ask",
                "notifications": "ask",
                "geolocation": "ask",
                "autoplay": "ask",
                "clipboard": "ask",
                "popups": "ask",
            },
            "site_permission_overrides": {},
            "safe_browsing_enabled": True,
            "safe_browsing_api_key": "",
        }
        try:
            with open(self.settings_file, "r", encoding="utf-8") as file:
                saved = json.load(file)
            defaults.update(saved)
            if "home_use_theme" not in saved:
                defaults["start_page"] = "grom"
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            pass
        defaults["default_zoom"] = max(
            25, min(500, int(defaults.get("default_zoom", 100)))
        )
        defaults["interface_language"] = (
            "en" if str(defaults.get("interface_language", "en")).lower().startswith("en") else "ru"
        )
        defaults["font_scale"] = max(
            50, min(200, int(defaults.get("font_scale", 100)))
        )
        defaults["sleep_minutes"] = max(
            1, min(120, int(defaults.get("sleep_minutes", 15)))
        )
        defaults["max_concurrent_downloads"] = max(
            1, min(8, int(defaults.get("max_concurrent_downloads", 3)))
        )
        defaults["download_speed_limit_kbps"] = max(
            0, min(1024 * 1024, int(defaults.get("download_speed_limit_kbps", 0)))
        )
        defaults["reader_font_size"] = max(
            14, min(28, int(defaults.get("reader_font_size", 18)))
        )
        try:
            shortcuts_limit = int(defaults.get("home_shortcuts_limit", 16))
        except (TypeError, ValueError):
            shortcuts_limit = 16
        defaults["home_shortcuts_limit"] = max(4, min(40, shortcuts_limit))
        allowed_theme_roles = {
            "background", "tabs", "active_tab", "toolbar", "bookmarks",
            "address", "popup", "surface", "button_hover", "border", "text",
            "muted", "icon", "disabled_icon", "accent",
        }
        theme_overrides = defaults.get("theme_overrides", {})
        if not isinstance(theme_overrides, dict):
            theme_overrides = {}
        defaults["theme_overrides"] = {
            key: QColor(value).name()
            for key, value in theme_overrides.items()
            if key in allowed_theme_roles
            and isinstance(value, str)
            and QColor(value).isValid()
        }
        permissions = defaults.get("site_permissions", {})
        defaults["site_permissions"] = {
            key: permissions.get(key, "ask") if permissions.get(key, "ask") in ("ask", "block") else "ask"
            for key in SITE_PERMISSION_KEYS
        }
        overrides = defaults.get("site_permission_overrides", {})
        clean_overrides = {}
        if isinstance(overrides, dict):
            for origin, values in overrides.items():
                if not isinstance(origin, str) or not isinstance(values, dict):
                    continue
                clean_values = {
                    key: values.get(key, "ask")
                    for key in SITE_PERMISSION_KEYS
                    if values.get(key) in ("ask", "allow", "block")
                }
                if clean_values:
                    clean_overrides[origin] = clean_values
        defaults["site_permission_overrides"] = clean_overrides
        return defaults

    def save_app_settings(self):
        with open(self.settings_file, "w", encoding="utf-8") as file:
            json.dump(self.app_settings, file, ensure_ascii=False, indent=2)

    def theme_presets(self):
        return {
            "light": "#e8eaed",
            "dark": "#202124",
            "dark_gray": "#3c4043",
            "purple": "#493267",
            "dark_green": "#1d4037",
            "blue": "#1f4f82",
            "cyan": "#176b72",
            "rose": "#7b3f57",
            "red": "#7a2830",
            "orange": "#8a4c20",
            "graphite": "#282d35",
            "indigo": "#343b73",
        }

    def current_theme_color(self):
        theme = self.app_settings.get("theme", "light")
        if theme == "custom":
            color = self.app_settings.get("custom_color", "#3f4652")
            return color if QColor(color).isValid() else "#3f4652"
        return self.theme_presets().get(theme, "#e8eaed")

    def build_theme_colors(self, seed_hex):
        seed = QColor(seed_hex)
        if not seed.isValid():
            seed = QColor("#202124")
        luminance = (seed.red() * 299 + seed.green() * 587 + seed.blue() * 114) / 1000
        is_dark = luminance < 150

        if is_dark:
            background = seed.darker(135)
            tabs = seed.darker(155)
            toolbar = seed.lighter(118)
            surface = seed.lighter(132)
            popup = seed.darker(150)
            hover = seed.lighter(155)
            input_color = seed.darker(125)
            border = seed.lighter(180)
            text = QColor("#f1f3f4")
            muted = QColor("#bdc1c6")
            icon = QColor("#e2e5e9")
            disabled_icon = QColor("#6f7378")
            accent = QColor("#8ab4f8")
        else:
            background = seed.lighter(108)
            tabs = seed.darker(112)
            toolbar = seed.darker(104)
            surface = seed.lighter(118)
            popup = QColor("#ffffff")
            hover = seed.darker(110)
            input_color = QColor("#ffffff")
            border = seed.darker(135)
            text = QColor("#202124")
            muted = QColor("#5f6368")
            icon = QColor("#4f5358")
            disabled_icon = QColor("#a9adb2")
            accent = QColor("#1a73e8")

        colors = {
            "seed": seed.name(),
            "background": background.name(),
            "tabs": tabs.name(),
            "active_tab": surface.name(),
            "toolbar": toolbar.name(),
            "bookmarks": toolbar.name(),
            "surface": surface.name(),
            "popup": popup.name(),
            "hover": hover.name(),
            "button_hover": hover.name(),
            "input": input_color.name(),
            "address": input_color.name(),
            "border": border.name(),
            "text": text.name(),
            "muted": muted.name(),
            "icon": icon.name(),
            "disabled_icon": disabled_icon.name(),
            "accent": accent.name(),
            "is_dark": is_dark,
        }
        overrides = self.app_settings.get("theme_overrides", {})
        if isinstance(overrides, dict):
            for role in (
                "background", "tabs", "active_tab", "toolbar", "bookmarks",
                "address", "popup", "surface", "button_hover", "border", "text",
                "muted", "icon", "disabled_icon", "accent",
            ):
                value = overrides.get(role)
                if isinstance(value, str) and QColor(value).isValid():
                    colors[role] = QColor(value).name()
        colors["hover"] = colors["button_hover"]
        colors["input"] = colors["address"]
        return colors

    def choose_theme_image(self, source_browser=None):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Создать тему из изображения",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff *.ico);;Все файлы (*.*)",
        )
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, "Тема из изображения", "Не удалось прочитать это изображение.")
            return
        sample = image.convertToFormat(QImage.Format.Format_RGB32).scaled(
            96, 96, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        buckets = {}
        for y in range(sample.height()):
            for x in range(sample.width()):
                color = sample.pixelColor(x, y)
                key = (color.red() // 24 * 24, color.green() // 24 * 24, color.blue() // 24 * 24)
                saturation = max(key) - min(key)
                buckets[key] = buckets.get(key, 0) + 1 + saturation / 96
        ranked = sorted(buckets, key=buckets.get, reverse=True)
        if not ranked:
            return
        dominant = QColor(*ranked[0])
        accent = dominant
        secondary = None
        for rgb in ranked:
            candidate = QColor(*rgb)
            if candidate.hsvSaturation() >= 80 and abs(candidate.lightness() - dominant.lightness()) >= 18:
                accent = candidate
            distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb, ranked[0])))
            if secondary is None and distance >= 48 and (
                candidate.lightness() < 150
            ) == (dominant.lightness() < 150):
                secondary = candidate
            if accent != dominant and secondary is not None:
                break
        self.app_settings["theme"] = "custom"
        self.app_settings["custom_color"] = dominant.name()
        self.app_settings["theme_image_path"] = path
        generated_overrides = {"accent": accent.name()}
        if secondary is not None:
            generated_overrides["active_tab"] = secondary.name()
        self.app_settings["theme_overrides"] = generated_overrides
        self.theme_colors = self.build_theme_colors(dominant.name())
        self.save_app_settings()
        self.apply_theme()
        self.refresh_home_pages()
        if source_browser:
            source_browser.runJavaScript(
                "settings.theme='custom';"
                f"settings.custom_color={json.dumps(dominant.name())};"
                f"settings.theme_overrides={json.dumps(generated_overrides)};"
                "sync();showSettingsPage('appearance');"
            )

    def themed_icon(self, path, color, mirrored=False):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return QIcon(path)
        if mirrored:
            pixmap = pixmap.transformed(
                QTransform().scale(-1, 1),
                Qt.TransformationMode.SmoothTransformation,
            )
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
        return QIcon(pixmap)

    def brand_pixmap(self, size=64):
        path = os.path.join(os.path.dirname(__file__), "browser_icon_placeholder.png")
        pixmap = QPixmap(path)
        if pixmap.isNull():
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = QColor(self.theme_colors["text"] if self.theme_colors["is_dark"] else self.theme_colors["accent"])
            painter.setPen(QPen(color, max(2, size // 18)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(5, 5, size - 10, size - 10))
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(int(size * 0.48))
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "G")
            painter.end()
        else:
            pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if self.theme_colors["is_dark"]:
                painter = QPainter(pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), QColor(self.theme_colors["text"]))
                painter.end()
        return pixmap

    def brand_icon(self):
        return QIcon(self.brand_pixmap(64))

    def brand_icon_data_uri(self):
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self.brand_pixmap(128).save(buffer, "PNG")
        buffer.close()
        return "data:image/png;base64," + bytes(data.toBase64()).decode("ascii")

    def icon_data_uri(self, icon, size=48):
        if not icon or icon.isNull():
            return ""
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        icon.pixmap(size, size).save(buffer, "PNG")
        buffer.close()
        return "data:image/png;base64," + bytes(data.toBase64()).decode("ascii")

    def home_icon(self):
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self.theme_colors["icon"]), 1.8)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(QPolygonF([QPointF(4, 11), QPointF(12, 4.5), QPointF(20, 11)]))
        painter.drawRoundedRect(QRectF(6.5, 10, 11, 9), 1.5, 1.5)
        painter.drawLine(QPointF(11, 19), QPointF(11, 14))
        painter.end()
        return QIcon(pixmap)

    def settings_icon(self):
        path = os.path.join(os.path.dirname(__file__), "settings_icon_placeholder.png")
        if os.path.exists(path):
            return self.themed_icon(path, self.theme_colors["icon"])
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.theme_colors["surface"]))
        painter.drawRoundedRect(QRectF(2, 2, 20, 20), 5, 5)
        painter.setPen(QPen(QColor(self.theme_colors["icon"]), 1.7))
        painter.drawEllipse(QRectF(8, 8, 8, 8))
        painter.drawLine(QPointF(12, 5), QPointF(12, 8))
        painter.drawLine(QPointF(12, 16), QPointF(12, 19))
        painter.drawLine(QPointF(5, 12), QPointF(8, 12))
        painter.drawLine(QPointF(16, 12), QPointF(19, 12))
        painter.end()
        return QIcon(pixmap)

    def downloads_icon(self):
        path = os.path.join(os.path.dirname(__file__), "downloads_icon_placeholder.png")
        if os.path.exists(path):
            return self.themed_icon(path, self.theme_colors["icon"])
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.theme_colors["surface"]))
        painter.drawRoundedRect(QRectF(2, 2, 20, 20), 5, 5)
        pen = QPen(QColor(self.theme_colors["icon"]), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(12, 6), QPointF(12, 15))
        painter.drawLine(QPointF(8.5, 12), QPointF(12, 15.5))
        painter.drawLine(QPointF(15.5, 12), QPointF(12, 15.5))
        painter.drawLine(QPointF(7, 18), QPointF(17, 18))
        painter.end()
        return QIcon(pixmap)

    def site_info_icon(self):
        path = os.path.join(os.path.dirname(__file__), "site_info_icon_placeholder.png")
        if os.path.exists(path):
            return self.themed_icon(path, self.theme_colors["icon"])
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self.theme_colors["icon"]), 1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(6.5, 3.5, 9, 10), 0, 180 * 16)
        painter.drawRoundedRect(QRectF(5, 9, 12, 9), 2, 2)
        painter.drawPoint(QPointF(11, 13))
        painter.end()
        return QIcon(pixmap)

    def translate_icon(self):
        path = os.path.join(os.path.dirname(__file__), "translate_icon_placeholder.png")
        if os.path.exists(path):
            return self.themed_icon(path, self.theme_colors["icon"])
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(self.theme_colors["icon"]), 1.4))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(QRectF(1, 1, 11, 11), Qt.AlignmentFlag.AlignCenter, "A")
        painter.drawText(QRectF(10, 10, 11, 11), Qt.AlignmentFlag.AlignCenter, "Я")
        painter.drawLine(QPointF(5, 14), QPointF(16, 5))
        painter.end()
        return QIcon(pixmap)

    def profile_avatar_icon(self, size=24, profile=None):
        canvas = QPixmap(size, size)
        canvas.fill(Qt.GlobalColor.transparent)
        profile = profile or self.current_profile
        source = QPixmap(str(profile.get("avatar", "")))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not source.isNull():
            path = QPainterPath()
            path.addEllipse(QRectF(1, 1, size - 2, size - 2))
            painter.setClipPath(path)
            source = source.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap((size - source.width()) // 2, (size - source.height()) // 2, source)
            painter.setClipping(False)
        else:
            color = QColor(self.theme_colors["icon"])
            painter.setPen(QPen(color, 1.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(1.5, 1.5, size - 3, size - 3))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(size * 0.36, size * 0.25, size * 0.28, size * 0.28))
            painter.drawEllipse(QRectF(size * 0.24, size * 0.56, size * 0.52, size * 0.28))
        painter.end()
        return QIcon(canvas)

    def internal_page_icon(self, browser):
        if browser.internal_page in ("home", "welcome"):
            return self.brand_icon()
        if browser.internal_page == "settings":
            return self.settings_icon()
        if browser.internal_page == "downloads":
            return self.downloads_icon()
        return browser.icon()

    def loading_icon(self):
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self.theme_colors["accent"]), 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(QRectF(3, 3, 14, 14), self.loading_angle * 16, 275 * 16)
        painter.end()
        return QIcon(pixmap)

    def start_tab_loading(self, browser):
        if self.tab_index_for_browser(browser) < 0:
            return
        self.loading_browsers.add(browser)
        if not self.loading_timer.isActive():
            self.loading_timer.start()
        self.update_loading_icons()

    def stop_tab_loading(self, browser):
        self.loading_browsers.discard(browser)
        if not self.loading_browsers:
            self.loading_timer.stop()
        index = self.tab_index_for_browser(browser)
        if index < 0:
            return
        icon = self.internal_page_icon(browser)
        workspace = self.tab_content.widget(index)
        self.tab_bar.setTabIcon(index, self.split_tab_icon(icon) if isinstance(workspace, TabWorkspace) and workspace.is_split() else icon)
        self.sync_vertical_tabs()

    def update_loading_icons(self):
        self.loading_angle = (self.loading_angle - 24) % 360
        icon = self.loading_icon()
        for browser in tuple(self.loading_browsers):
            index = self.tab_index_for_browser(browser)
            if index < 0:
                self.loading_browsers.discard(browser)
                continue
            self.tab_bar.setTabIcon(index, icon)
        if not self.loading_browsers:
            self.loading_timer.stop()

    def apply_theme(self):
        colors = self.theme_colors
        self.setStyleSheet(
            f"QMainWindow {{ background: {colors['background']}; color: {colors['text']}; }}"
        )
        self.tabs_panel.setStyleSheet(f"background: {colors['tabs']};")
        self.navbar.setStyleSheet(f"background: {colors['toolbar']};")
        self.bookmarks_panel.setStyleSheet(f"background: {colors['bookmarks']};")

        self.tab_bar.setStyleSheet(f"""
            QTabBar {{ background: transparent; border: none; outline: none; }}
            QTabBar::tab {{
                background: transparent;
                color: transparent;
                padding-left: 14px;
                padding-right: 38px;
                min-width: 0px;
                max-width: 240px;
                height: 34px;
                border: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 1px;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{ background: {colors['active_tab']}; color: transparent; }}
            QTabBar::tab:!selected:hover {{ background: {colors['button_hover']}; color: transparent; }}
            QToolButton#tabCloseButton {{
                background: transparent;
                border: none;
                border-radius: 12px;
                padding: 0;
            }}
            QToolButton#tabCloseButton:hover {{ background: {colors['button_hover']}; }}
        """)
        self.tab_bar.set_fade_colors(
            colors["tabs"], colors["active_tab"], colors["button_hover"], colors["text"], colors["muted"]
        )
        for index in range(self.tab_bar.count()):
            close_button = self.tab_bar.tabButton(index, QTabBar.ButtonPosition.RightSide)
            if isinstance(close_button, TabCloseButton):
                close_button.set_line_color(colors["muted"], colors["text"])
        self.plus_btn.setStyleSheet(f"""
            QPushButton {{ border: none; background: transparent; }}
            QPushButton:hover {{ background: {colors['button_hover']}; border-radius: 17px; }}
        """)
        nav_button_style = f"""
            QPushButton, QToolButton {{ border: none; background: transparent; border-radius: 16px; padding: 0; }}
            QPushButton:hover, QToolButton:hover {{ background: {colors['button_hover']}; border-radius: 16px; }}
            QPushButton:disabled, QToolButton:disabled {{ background: transparent; border-radius: 16px; }}
            QPushButton#reloadButton {{ border-radius: 14px; }}
            QPushButton#reloadButton:hover {{ background: {colors['button_hover']}; border-radius: 14px; }}
        """
        for button in (
            self.back_btn,
            self.forward_btn,
            self.home_btn,
            self.reload_btn,
            self.site_info_btn,
            self.translate_btn,
            self.bookmark_btn,
            self.profile_btn,
            self.menu_btn,
            self.extensions_btn,
        ):
            button.setStyleSheet(nav_button_style)
        self.home_btn.setIcon(self.home_icon())
        self.reload_btn.setIcon(self.themed_icon("reload.png", colors["icon"]))
        self.reload_btn.set_hover_color(colors["button_hover"])
        self.site_info_btn.setIcon(self.site_info_icon())
        self.translate_btn.setIcon(self.translate_icon())
        self.bookmark_btn.setIcon(self.themed_icon("bookmark.png", colors["icon"]))
        self.profile_btn.setIcon(self.profile_avatar_icon())
        self.profile_btn.setIconSize(QSize(24, 24))
        self.menu_btn.setIcon(self.themed_icon("menu.png", colors["icon"]))
        self.extensions_btn.setIcon(self.extensions_toolbar_icon())
        self.extensions_btn.setIconSize(QSize(22, 22))
        self.extensions_btn.setVisible(self.app_settings.get("show_extensions_button", True))
        self.refresh_extension_toolbar_buttons()
        self.plus_btn.setIcon(self.themed_icon("add.png", colors["icon"]))
        self.setWindowIcon(self.brand_icon())

        self.url_bar.set_url_colors(colors["text"], colors["muted"])
        self.url_bar.setStyleSheet(f"""
            QLineEdit {{ background: transparent; color: {colors['text']}; border: none; padding: 5px 3px; font-size: 13px; }}
        """)
        if hasattr(self, "address_completer"):
            self.address_completer.popup().setStyleSheet(f"""
                QListView {{
                    color:{colors['text']}; background:{colors['popup']};
                    border:1px solid {colors['border']}; border-radius:10px;
                    padding:6px; outline:none;
                }}
                QListView::item {{ min-height:34px; padding:2px 9px; border-radius:7px; }}
                QListView::item:selected {{ background:{colors['hover']}; }}
            """)
        self.update_address_bar_style(self.url_bar.hasFocus())
        self.update_navigation_buttons()
        self.update_translation_button()
        self.find_bar.setStyleSheet(f"background: {colors['toolbar']};")
        self.find_box.setStyleSheet(f"""
            QFrame {{ background: {colors['popup']}; border: 1px solid {colors['border']}; border-radius: 6px; }}
            QLineEdit {{ color: {colors['text']}; background: transparent; border: none; padding: 5px 8px; }}
            QLabel {{ color: {colors['muted']}; border: none; }}
            QToolButton {{ color: {colors['text']}; background: transparent; border: none; border-radius: 14px; }}
            QToolButton:hover {{ background: {colors['hover']}; }}
        """)
        if hasattr(self, "vertical_tabs_panel"):
            self.vertical_tabs_panel.setStyleSheet(f"""
                QFrame#verticalTabsPanel {{ background:{colors['tabs']}; border-right:1px solid {colors['border']}; }}
                QWidget#verticalTabsHeader {{ background:transparent; border:none; }}
                QLabel#verticalTabsTitle {{ color:{colors['text']}; font-size:15px; font-weight:600; }}
                QToolButton {{ color:{colors['text']}; background:transparent; border:none; border-radius:7px; font-size:20px; }}
                QToolButton:hover {{ background:{colors['hover']}; }}
                QToolButton#verticalAddButton {{ padding:0; margin:0; }}
                QListWidget#verticalTabsList {{ color:{colors['text']}; background:transparent; border:none; outline:none; }}
                QListWidget#verticalTabsList::item {{ min-height:36px; padding:3px 7px; border-radius:6px; }}
                QListWidget#verticalTabsList::item:hover {{ background:{colors['hover']}; }}
                QListWidget#verticalTabsList::item:selected {{ background:{colors['surface']}; color:{colors['text']}; }}
                QScrollBar:vertical {{ width:8px; background:{colors['background']}; }}
                QScrollBar::handle:vertical {{ background:{colors['border']}; min-height:28px; }}
            """)
            self.vertical_add_button.setIcon(self.themed_icon("add.png", colors["icon"]))

        for bookmark in self.bookmarks:
            button = bookmark.get("button")
            if isinstance(button, DraggableBookmark):
                button.apply_theme(colors)

        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if isinstance(workspace, TabWorkspace):
                workspace.setStyleSheet(f"QWidget#tabWorkspace {{ background:{colors['background']}; }}")
                workspace.splitter.setStyleSheet(
                    f"QSplitter::handle {{ background: {colors['border']}; }}"
                )
                for browser in (workspace.primary_browser, workspace.secondary_browser):
                    if browser:
                        browser.set_placeholder_color(colors["background"])
                    if browser and browser.internal_page:
                        self.update_settings_page_theme(browser)
                        browser._icon = self.internal_page_icon(browser)
                        if browser == workspace.primary_browser:
                            tab_index = self.tab_content.indexOf(workspace)
                            if tab_index >= 0:
                                self.tab_bar.setTabIcon(tab_index, browser._icon)
                self.refresh_workspace_icon(workspace)

        if self.menu_popup and self.menu_popup.isVisible():
            self.menu_popup.close()
        if self.profile_popup and self.profile_popup.isVisible():
            self.profile_popup.close()
        if self.site_info_popup and self.site_info_popup.isVisible():
            self.site_info_popup.close()
        if self.translation_popup and self.translation_popup.isVisible():
            self.translation_popup.close()
        if self.translation_prompt_popup and self.translation_prompt_popup.isVisible():
            self.translation_prompt_popup.close()
        if self.history_popup and self.history_popup.isVisible():
            self.history_popup.close()
        if self.downloads_popup and self.downloads_popup.isVisible():
            self.downloads_popup.close()
        if self.performance_popup and self.performance_popup.isVisible():
            self.performance_popup.close()
        if self.builtin_extensions_popup and self.builtin_extensions_popup.isVisible():
            self.builtin_extensions_popup.close()
        if self.builtin_extension_details_popup and self.builtin_extension_details_popup.isVisible():
            self.builtin_extension_details_popup.close()
        if self.tab_search_popup and self.tab_search_popup.isVisible():
            self.tab_search_popup.close()
        self.style_devtools()
        self.sync_vertical_tabs()

    def apply_settings_from_page(self, state):
        theme = state.get("theme", self.app_settings.get("theme", "light"))
        if theme not in {*self.theme_presets(), "custom"}:
            theme = "light"
        custom_color = state.get("custom_color", self.app_settings.get("custom_color", "#3f4652"))
        if not QColor(custom_color).isValid():
            custom_color = "#3f4652"
        allowed_theme_roles = {
            "background", "tabs", "active_tab", "toolbar", "bookmarks",
            "address", "popup", "surface", "button_hover", "border", "text",
            "muted", "icon", "disabled_icon", "accent",
        }
        theme_override_state = state.get(
            "theme_overrides", self.app_settings.get("theme_overrides", {})
        )
        if not isinstance(theme_override_state, dict):
            theme_override_state = {}
        theme_overrides = {
            key: QColor(value).name()
            for key, value in theme_override_state.items()
            if key in allowed_theme_roles
            and isinstance(value, str)
            and QColor(value).isValid()
        }
        zoom = max(25, min(500, int(state.get("default_zoom", 100))))
        search_engine = str(state.get("search_engine", "google"))
        if search_engine not in (
            "google", "bing", "duckduckgo", "yandex", "brave",
            "startpage", "ecosia", "qwant", "yahoo", "mojeek",
        ):
            search_engine = "google"
        start_page = str(state.get("start_page", "google"))
        if start_page not in ("grom", "google", "blank", "custom"):
            start_page = "grom"
        permissions = state.get("site_permissions", {})
        permissions = {
            key: permissions.get(key, "ask") if permissions.get(key, "ask") in ("ask", "block") else "ask"
            for key in SITE_PERMISSION_KEYS
        }
        override_state = state.get("site_permission_overrides", self.app_settings.get("site_permission_overrides", {}))
        clean_overrides = {}
        if isinstance(override_state, dict):
            for origin, values in override_state.items():
                if not isinstance(origin, str) or not isinstance(values, dict):
                    continue
                clean_values = {
                    key: values.get(key)
                    for key in SITE_PERMISSION_KEYS
                    if values.get(key) in ("allow", "block")
                }
                if clean_values:
                    clean_overrides[origin] = clean_values
        translation_language = str(state.get("translation_language", "ru"))
        if translation_language not in ("ru", "en", "de", "fr", "es", "it", "zh-CN", "ja", "ko"):
            translation_language = "ru"
        menu_defaults = {
            "tab_search": True,
            "find_page": True,
            "screenshot": False,
            "split_screen": False,
            "developer_tools": False,
            "install_site": False,
        }
        menu_state = state.get("menu_commands", self.app_settings.get("menu_commands", {}))
        if isinstance(menu_state, dict):
            menu_defaults.update({key: bool(value) for key, value in menu_state.items() if key in menu_defaults})

        self.app_settings.update(
            {
                "theme": theme,
                "custom_color": custom_color,
                "theme_overrides": theme_overrides,
                "show_forward": bool(state.get("show_forward", True)),
                "show_home_button": bool(state.get("show_home_button", False)),
                "show_extensions_button": bool(state.get("show_extensions_button", True)),
                "default_zoom": zoom,
                "font_scale": max(50, min(200, int(state.get("font_scale", 100)))),
                "font_scale_settings": bool(state.get("font_scale_settings", False)),
                "search_engine": search_engine,
                "start_page": start_page,
                "start_page_url": str(state.get("start_page_url", "")).strip(),
                "home_use_theme": bool(state.get("home_use_theme", self.app_settings.get("home_use_theme", True))),
                "home_color": str(state.get("home_color", self.app_settings.get("home_color", "#202124"))),
                "home_background_url": str(state.get("home_background_url", self.app_settings.get("home_background_url", ""))).strip(),
                "home_background_path": str(state.get("home_background_path", self.app_settings.get("home_background_path", ""))).strip(),
                "hardware_acceleration": bool(state.get("hardware_acceleration", True)),
                "memory_saver": bool(state.get("memory_saver", True)),
                "sleep_minutes": max(1, min(120, int(state.get("sleep_minutes", 15)))),
                "max_concurrent_downloads": max(1, min(8, int(state.get("max_concurrent_downloads", 3)))),
                "download_speed_limit_kbps": max(0, min(1024 * 1024, int(state.get("download_speed_limit_kbps", 0)))),
                "vertical_tabs": bool(state.get("vertical_tabs", False)),
                "reader_font_size": max(14, min(28, int(state.get("reader_font_size", 18)))),
                "restore_session_prompt": bool(state.get("restore_session_prompt", True)),
                "smooth_tab_animations": bool(state.get("smooth_tab_animations", True)),
                "show_bookmarks_bar": bool(state.get("show_bookmarks_bar", True)),
                "ad_blocker": bool(state.get("ad_blocker", True)),
                "password_manager": bool(state.get("password_manager", False)),
                "offer_save_passwords": bool(state.get("offer_save_passwords", True)),
                "autofill_passwords": bool(state.get("autofill_passwords", True)),
                "translation_language": translation_language,
                "offer_translation": bool(state.get("offer_translation", True)),
                "auto_translate": bool(state.get("auto_translate", False)),
                "site_permissions": permissions,
                "site_permission_overrides": clean_overrides,
                "safe_browsing_enabled": bool(state.get("safe_browsing_enabled", True)),
                "safe_browsing_api_key": str(state.get("safe_browsing_api_key", "")).strip(),
                "menu_commands": menu_defaults,
            }
        )
        self.save_app_settings()
        self.theme_colors = self.build_theme_colors(self.current_theme_color())
        self.forward_btn.setVisible(self.app_settings["show_forward"])
        self.home_btn.setVisible(self.app_settings["show_home_button"])
        self.extensions_btn.setVisible(self.app_settings["show_extensions_button"])
        extension_state = self.builtin_extension_state()
        extension_state["ad_blocker"] = self.app_settings["ad_blocker"]
        extension_state["password_manager"] = self.app_settings["password_manager"]
        self.app_settings["builtin_extensions"] = extension_state
        self.save_app_settings()
        self.tab_bar.animations_enabled = self.app_settings["smooth_tab_animations"]
        self.bookmarks_panel.setVisible(
            bool(self.bookmarks) and self.app_settings.get("show_bookmarks_bar", True)
        )

        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            for browser in (workspace.primary_browser, workspace.secondary_browser):
                if browser:
                    browser.set_zoom_percent(zoom)
                    browser.set_permission_policy(self.permission_policy_for_url(browser.url()))
                    self.apply_browser_font_scale(browser)
        self.apply_builtin_extensions_to_all()
        if not self.app_settings["memory_saver"]:
            for index in range(self.tab_content.count()):
                self.wake_tab(index)
        self.apply_theme()
        self.update_vertical_tabs_visibility()
        self.refresh_home_pages()

    def update_settings_page_theme(self, browser):
        browser.runJavaScript(
            f"window.applyThemeFromHost?.({json.dumps(self.theme_colors)});"
        )

    def file_data_uri(self, path):
        if not path or not os.path.isfile(path):
            return ""
        try:
            mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
            with open(path, "rb") as file:
                encoded = base64.b64encode(file.read()).decode("ascii")
            return f"data:{mime};base64,{encoded}"
        except OSError:
            return ""

    @staticmethod
    def search_text_variants(value):
        text = str(value or "").strip().casefold()
        if not text:
            return []
        english = "qwertyuiop[]asdfghjkl;'zxcvbnm,."
        russian = "йцукенгшщзхъфывапролджэячсмитьбю"
        to_russian = str.maketrans(english, russian)
        to_english = str.maketrans(russian, english)
        variants = [text, text.translate(to_russian), text.translate(to_english)]
        return list(dict.fromkeys(item for item in variants if item))

    @classmethod
    def fuzzy_search_score(cls, query, text):
        words = re.findall(r"[\w-]+", str(text or "").casefold(), flags=re.UNICODE)
        best = -1
        for variant in cls.search_text_variants(query):
            if variant in words:
                best = max(best, 1000)
            if any(word.startswith(variant) for word in words):
                best = max(best, 700)
            if variant in " ".join(words):
                best = max(best, 450)
            if len(variant) >= 3:
                similarity = max(
                    (difflib.SequenceMatcher(None, variant, word).ratio() for word in words),
                    default=0.0,
                )
                if similarity >= 0.72:
                    best = max(best, int(180 + similarity * 260))
        return best

    def home_suggestions(self):
        suggestions = []
        seen = set()
        popular_sites = (
            ("YouTube", "https://www.youtube.com/", "ютуб youtube видео ролики"),
            ("Google", "https://www.google.com/", "гугл google поиск"),
            ("Gmail", "https://mail.google.com/", "гмейл gmail почта google"),
            ("Twitch", "https://www.twitch.tv/", "твич twitch стримы трансляции"),
            ("Telegram Web", "https://web.telegram.org/", "телеграм telegram мессенджер"),
            ("WhatsApp Web", "https://web.whatsapp.com/", "ватсап whatsapp мессенджер"),
            ("VK", "https://vk.com/", "вк вконтакте vk"),
            ("ChatGPT", "https://chatgpt.com/", "чатгпт chatgpt ai ии"),
            ("Wikipedia", "https://ru.wikipedia.org/", "википедия wikipedia энциклопедия"),
            ("Яндекс", "https://yandex.ru/", "яндекс yandex поиск"),
            ("Google Maps", "https://maps.google.com/", "карты maps карта google"),
            ("Figma", "https://www.figma.com/", "фигма figma дизайн макеты прототипы"),
            ("Steam", "https://store.steampowered.com/", "стим steam игры магазин"),
            ("Discord", "https://discord.com/app", "дискорд discord чат серверы"),
            ("GitHub", "https://github.com/", "гитхаб github код репозитории"),
            ("GitLab", "https://gitlab.com/", "гитлаб gitlab код репозитории"),
            ("Reddit", "https://www.reddit.com/", "реддит reddit форумы"),
            ("Notion", "https://www.notion.so/", "ноушен notion заметки документы"),
            ("Spotify", "https://open.spotify.com/", "спотифай spotify музыка"),
            ("TikTok", "https://www.tiktok.com/", "тикток tik tok tiktok видео"),
            ("Instagram", "https://www.instagram.com/", "инстаграм instagram фото"),
            ("X / Twitter", "https://x.com/", "твиттер twitter икс x соцсеть"),
            ("LinkedIn", "https://www.linkedin.com/", "линкедин linkedin работа"),
            ("Microsoft 365", "https://www.office.com/", "майкрософт office офис 365"),
            ("Google Drive", "https://drive.google.com/", "гугл диск google drive файлы"),
            ("Google Translate", "https://translate.google.com/", "гугл переводчик translate перевод"),
            ("Яндекс Музыка", "https://music.yandex.ru/", "яндекс музыка yandex music"),
            ("Кинопоиск", "https://www.kinopoisk.ru/", "кинопоиск kinopoisk фильмы сериалы"),
            ("Ozon", "https://www.ozon.ru/", "озон ozon магазин покупки"),
            ("Wildberries", "https://www.wildberries.ru/", "вайлдберриз wildberries wb магазин"),
            ("Авито", "https://www.avito.ru/", "авито avito объявления"),
            ("AliExpress", "https://aliexpress.ru/", "алиэкспресс aliexpress магазин"),
            ("Amazon", "https://www.amazon.com/", "амазон amazon магазин"),
            ("Booking", "https://www.booking.com/", "букинг booking отели путешествия"),
            ("Rutube", "https://rutube.ru/", "рутуб rutube видео"),
            ("Дзен", "https://dzen.ru/", "дзен dzen статьи новости"),
        )
        for bookmark in self.bookmarks:
            url = str(bookmark.get("url", ""))
            if url and url not in seen:
                seen.add(url)
                suggestions.append({
                    "title": bookmark.get("name") or QUrl(url).host(),
                    "url": url,
                    "aliases": "избранное закладка",
                    "score": 500,
                })
        try:
            with open(self.history_file, "r", encoding="utf-8") as file:
                history = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            history = []
        if not isinstance(history, list):
            history = []
        frequency = {}
        for record in history[-500:]:
            url = str(record.get("url", ""))
            if url.startswith(("http://", "https://")):
                frequency[url] = frequency.get(url, 0) + 1
        for position, record in enumerate(reversed(history[-300:])):
            url = str(record.get("url", ""))
            if url and url not in seen and url.startswith(("http://", "https://")):
                seen.add(url)
                suggestions.append({
                    "title": record.get("title") or QUrl(url).host(),
                    "url": url,
                    "aliases": QUrl(url).host().replace(".", " "),
                    "score": min(240, frequency.get(url, 1) * 18) + max(0, 80 - position),
                })
            if len(suggestions) >= 80:
                break
        for title, url, aliases in popular_sites:
            if url in seen:
                for item in suggestions:
                    if item.get("url") == url:
                        item["aliases"] = f"{item.get('aliases', '')} {aliases}".strip()
                        item["score"] = max(int(item.get("score", 0)), 320)
                        break
                continue
            seen.add(url)
            suggestions.append({
                "title": title,
                "url": url,
                "aliases": aliases,
                "score": 320,
            })
        return suggestions

    def home_quick_links(self):
        links = []
        limit = self.app_settings.get("home_shortcuts_limit", 16)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 16
        limit = max(4, min(40, limit))
        for bookmark in self.bookmarks[:limit]:
            url = str(bookmark.get("url", ""))
            if not url:
                continue
            icon = bookmark.get("button").icon() if bookmark.get("button") else self.get_cached_icon(url)
            links.append({
                "title": str(bookmark.get("name") or QUrl(url).host() or url)[:40],
                "url": url,
                "icon": self.icon_data_uri(icon),
            })
        return links

    def refresh_address_suggestions(self, query):
        query = str(query or "").strip()
        if not query:
            self.address_suggestion_model.setStringList([])
            self._address_suggestion_values = {}
            return
        if self._address_suggestion_entries is None:
            self._address_suggestion_entries = self.home_suggestions()

        normalized = query.casefold()
        ranked = []
        for item in self._address_suggestion_entries:
            title = str(item.get("title", ""))
            url = str(item.get("url", ""))
            aliases = str(item.get("aliases", ""))
            haystack = f"{title} {aliases} {QUrl(url).host()}".casefold()
            if normalized == title.casefold() or normalized == QUrl(url).host().casefold():
                match_score = 1000
            else:
                match_score = self.fuzzy_search_score(normalized, haystack)
            if match_score < 0:
                continue
            ranked.append((match_score + int(item.get("score", 0)), title, url))
        ranked.sort(key=lambda value: (-value[0], value[1].casefold()))

        labels = []
        values = {}
        search_label = f'Искать «{query}»'
        labels.append(search_label)
        values[search_label] = query
        for _score, title, url in ranked[:8]:
            host = QUrl(url).host().removeprefix("www.")
            label = f"{title}  -  {host}"
            if label in values:
                continue
            labels.append(label)
            values[label] = url
        self._address_suggestion_values = values
        self.address_suggestion_model.setStringList(labels)
        self.address_completer.setCompletionPrefix("")
        QTimer.singleShot(0, self.address_completer.complete)

    def activate_address_suggestion(self, label):
        value = self._address_suggestion_values.get(str(label), str(label))
        self.url_bar.setText(value)
        self.navigate_to_url()



    def choose_home_background(self):
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Выбрать фон главной страницы",
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation),
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            self.app_settings["home_background_path"] = path
            self.app_settings["home_background_url"] = ""
            self.save_app_settings()
            self.refresh_home_pages()

    def refresh_home_pages(self):
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            browser = workspace.primary_browser
            if browser.internal_page == "home":
                browser.load_internal_html(self.home_page_html(), "grom://home")
                browser._icon = self.internal_page_icon(browser)
                browser.iconChanged.emit(browser._icon)

    def open_settings_tab(self, section=None):
        section = str(section or "")
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if (
                isinstance(workspace, TabWorkspace)
                and workspace.primary_browser.is_settings_page
            ):
                if index == self.tab_bar.currentIndex() and not section:
                    if self.tab_bar.count() > 1:
                        self.close_current_tab(index)
                    else:
                        self.add_new_tab()
                        self.close_current_tab(index)
                    return
                self.tab_bar.setCurrentIndex(index)
                if section:
                    workspace.primary_browser.runJavaScript(
                        f"window.showSettingsPage?.({json.dumps(section)})"
                    )
                return
        browser = self.add_new_tab(
            label="Настройки",
            internal_html=self.settings_page_html(),
            internal_url="grom://settings/profiles",
        )
        if section:
            QTimer.singleShot(
                600,
                lambda current=browser, name=section: current.runJavaScript(
                    f"window.showSettingsPage?.({json.dumps(name)})"
                ),
            )

    def open_downloads_tab(self):
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if (
                isinstance(workspace, TabWorkspace)
                and workspace.primary_browser.internal_page == "downloads"
            ):
                self.tab_bar.setCurrentIndex(index)
                workspace.primary_browser.load_internal_html(
                    self.downloads_page_html(), "grom://downloads"
                )
                return
        self.add_new_tab(
            label="Загрузки",
            internal_html=self.downloads_page_html(),
            internal_url="grom://downloads",
        )

    def popup_browser_by_id(self, popup_id):
        popup_id = str(popup_id or "")
        if not popup_id:
            return None
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            for browser in (workspace.primary_browser, workspace.secondary_browser):
                if browser and getattr(browser, "popup_id", "") == popup_id:
                    return browser
        return None

    def browser_has_open_popup(self, opener_browser):
        if not opener_browser:
            return False
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            for browser in (workspace.primary_browser, workspace.secondary_browser):
                if browser and getattr(browser, "popup_opener_browser", None) is opener_browser:
                    return True
        return False

    def browser_origin(self, browser):
        if not browser:
            return ""
        url = browser.url()
        if url.scheme() not in ("http", "https") or not url.host():
            return ""
        origin = f"{url.scheme()}://{url.host()}"
        port = url.port()
        if port >= 0 and not (
            (url.scheme() == "http" and port == 80)
            or (url.scheme() == "https" and port == 443)
        ):
            origin += f":{port}"
        return origin

    def popup_target_allows(self, target_origin, browser):
        target = str(target_origin or "*").rstrip("/")
        return target in ("", "*") or target == self.browser_origin(browser).rstrip("/")

    def open_web_popup(self, source_browser, popup_url, popup_id):
        popup_id = str(popup_id or uuid.uuid4().hex)
        existing = self.popup_browser_by_id(popup_id)
        if existing:
            existing.setUrl(popup_url)
            index = self.tab_index_for_browser(existing)
            if index >= 0:
                self.tab_bar.setCurrentIndex(index)
            return existing
        return self.add_new_tab(
            popup_url,
            popup_url.host() or "Вход",
            private=source_browser.is_private,
            popup_id=popup_id,
            popup_opener=source_browser,
        )

    def relay_popup_message(self, source_browser, command, to_opener):
        popup_id = str(command.get("popup_id", ""))
        if not popup_id:
            return
        if to_opener:
            popup = self.popup_browser_by_id(popup_id) or source_browser
            recipient = getattr(popup, "popup_opener_browser", None)
            callback = "__gromReceivePopupMessage"
        else:
            recipient = self.popup_browser_by_id(popup_id)
            callback = "__gromReceiveOpenerMessage"
        if not recipient or not self.popup_target_allows(
            command.get("target_origin", "*"), recipient
        ):
            return
        origin = self.browser_origin(source_browser)
        data = json.dumps(command.get("data"))
        if to_opener:
            script = (
                f"window.{callback}?.({json.dumps(popup_id)}, {data}, "
                f"{json.dumps(origin)})"
            )
        else:
            script = f"window.{callback}?.({data}, {json.dumps(origin)})"
        recipient.runJavaScript(script)

    def notify_popup_closed(self, browser):
        popup_id = str(getattr(browser, "popup_id", ""))
        opener = getattr(browser, "popup_opener_browser", None)
        if popup_id and opener:
            opener.runJavaScript(
                f"window.__gromMarkPopupClosed?.({json.dumps(popup_id)})"
            )
        browser.popup_opener_browser = None
        browser.popup_id = ""

    def open_google_account_chooser(self, browser, original_url):
        if not browser or browser.url().toString() != str(original_url):
            return
        if self.browser_has_open_popup(browser):
            return
        return_url = QUrl(str(original_url))
        host = return_url.host().lower()
        if not (
            host == "google.com"
            or host.endswith(".google.com")
            or host == "youtube.com"
            or host.endswith(".youtube.com")
        ):
            return
        chooser = QUrl("https://accounts.google.com/AccountChooser")
        query = QUrlQuery()
        query.addQueryItem("continue", return_url.toString())
        if host == "mail.google.com":
            query.addQueryItem("service", "mail")
        elif host.endswith("youtube.com"):
            query.addQueryItem("service", "youtube")
        chooser.setQuery(query)
        browser.setUrl(chooser)

    def handle_browser_command(self, command, source_browser=None):
        if not isinstance(command, dict) or not source_browser:
            return
        action = str(command.get("action", ""))
        page = source_browser.internal_page
        allowed = WEB_PAGE_COMMANDS if not page else WEB_PAGE_COMMANDS | INTERNAL_PAGE_COMMANDS.get(page, set())
        if action not in allowed:
            return
        task_id = str(command.get("id", ""))
        task = next(
            (item for item in self.download_tasks if str(item.get("id", "")) == task_id),
            None,
        )
        if action == "open_download" and task:
            self.open_download(task)
        elif action == "pause_download" and task:
            self.pause_download(task)
            QTimer.singleShot(200, self.refresh_downloads_pages)
        elif action == "resume_download" and task:
            self.resume_download(task)
            QTimer.singleShot(200, self.refresh_downloads_pages)
        elif action == "retry_download" and task:
            self.retry_download(task)
            QTimer.singleShot(200, self.refresh_downloads_pages)
        elif action == "cleanup_download_temps":
            self.cleanup_temporary_downloads()
            self.refresh_downloads_pages()
        elif action == "delete_download" and task:
            self.delete_download(task, refresh_popup=False)
            self.refresh_downloads_pages()
        elif action == "clear_downloads":
            if self.clear_downloads():
                self.refresh_downloads_pages()
        elif action == "navigate_home" and source_browser:
            self.navigate_browser_from_text(source_browser, str(command.get("value", "")))
        elif action in ("open_popup", "popup_navigate") and source_browser:
            popup_url = QUrl(str(command.get("url", "")))
            if popup_url.isValid() and popup_url.scheme() in ("http", "https"):
                self.open_web_popup(
                    source_browser,
                    popup_url,
                    str(command.get("popup_id", "")),
                )
        elif action == "popup_message_to_opener" and source_browser:
            self.relay_popup_message(source_browser, command, to_opener=True)
        elif action == "popup_message_to_child" and source_browser:
            self.relay_popup_message(source_browser, command, to_opener=False)
        elif action == "popup_close" and source_browser:
            popup = self.popup_browser_by_id(str(command.get("popup_id", "")))
            if popup:
                index = self.tab_index_for_browser(popup)
                if index >= 0:
                    self.remove_tab_now(index)
        elif action == "google_account_switch_fallback" and source_browser:
            original_url = str(command.get("url", source_browser.url().toString()))
            QTimer.singleShot(
                700,
                lambda browser=source_browser, url=original_url:
                self.open_google_account_chooser(browser, url),
            )
        elif action == "twitch_message_context" and source_browser:
            self.show_twitch_message_context_menu(command, source_browser)
        elif action == "image_context" and source_browser:
            self.show_image_context_menu(
                str(command.get("url", "")),
                source_browser,
            )
        elif action == "text_context" and source_browser:
            self.show_text_context_menu(command, source_browser)
        elif action == "page_context" and source_browser:
            self.show_page_context_menu(command, source_browser)
        elif action == "selection_quick" and source_browser:
            self.show_selection_copy_popup(str(command.get("text", "")))
        elif action == "register_default_browser":
            self.register_windows_browser()
        elif action == "add_home_shortcut":
            raw_url = str(command.get("url", "")).strip()
            url = QUrl.fromUserInput(raw_url)
            if url.isValid() and url.scheme() in ("http", "https") and url.host():
                normalized = url.toString()
                if not any(item.get("url") == normalized for item in self.bookmarks):
                    name = str(command.get("name", "")).strip() or url.host()
                    self.add_bookmark(normalized, name[:50], self.get_cached_icon(normalized))
                else:
                    self.refresh_home_pages()
        elif action == "rename_home_shortcut":
            target_url = str(command.get("url", ""))
            new_name = str(command.get("name", "")).strip()[:50]
            bookmark = next((item for item in self.bookmarks if item.get("url") == target_url), None)
            if bookmark and new_name:
                bookmark["name"] = new_name
                button = bookmark.get("button")
                if button:
                    button.setText(new_name)
                self.save_bookmarks()
                self.refresh_home_pages()
        elif action == "delete_home_shortcut":
            self.remove_bookmark(str(command.get("url", "")))
        elif action == "set_home_customization":
            color = str(command.get("color", self.app_settings.get("home_color", "#202124")))
            if not QColor(color).isValid():
                color = "#202124"
            try:
                shortcuts_limit = int(command.get(
                    "shortcuts_limit",
                    self.app_settings.get("home_shortcuts_limit", 16),
                ))
            except (TypeError, ValueError):
                shortcuts_limit = 16
            self.app_settings.update({
                "home_use_theme": bool(command.get("use_theme", True)),
                "home_color": color,
                "home_background_url": str(command.get("background_url", "")).strip(),
                "home_shortcuts_limit": max(4, min(40, shortcuts_limit)),
            })
            self.save_app_settings()
            self.refresh_home_pages()
        elif action == "choose_home_background":
            self.choose_home_background()
        elif action == "choose_theme_image":
            self.choose_theme_image(source_browser)
        elif action == "clear_home_background":
            self.app_settings["home_background_url"] = ""
            self.app_settings["home_background_path"] = ""
            self.save_app_settings()
            self.refresh_home_pages()
        elif action == "set_interface_language":
            self.change_interface_language(str(command.get("language", "ru")))
        elif action == "welcome_preferences":
            theme = str(command.get("theme", self.app_settings.get("theme", "light")))
            if theme not in self.theme_presets():
                theme = "light"
            self.app_settings.update({
                "theme": theme,
                "show_forward": bool(command.get("show_forward", True)),
                "show_home_button": bool(command.get("show_home_button", False)),
            })
            self.save_app_settings()
            self.theme_colors = self.build_theme_colors(self.current_theme_color())
            self.forward_btn.setVisible(self.app_settings["show_forward"])
            self.home_btn.setVisible(self.app_settings["show_home_button"])
            self.apply_theme()
        elif action == "finish_welcome":
            self.app_settings["welcome_completed"] = True
            self.save_app_settings()
            if source_browser:
                source_browser.set_fallback_title("Grom")
                source_browser.load_internal_html(self.home_page_html(), "grom://home")
                source_browser._icon = self.internal_page_icon(source_browser)
                source_browser.iconChanged.emit(source_browser._icon)
                self.update_tab_title(source_browser)
        elif action == "create_profile":
            self.create_profile(command.get("name", ""))
        elif action == "rename_profile":
            self.rename_profile(str(command.get("profile_id", "")), command.get("name", ""))
        elif action == "profile_avatar":
            self.choose_profile_avatar(str(command.get("profile_id", "")))
        elif action == "delete_profile":
            self.delete_profile(str(command.get("profile_id", "")))
        elif action == "switch_profile":
            self.switch_profile(str(command.get("profile_id", "")))
        elif action == "guest_profile":
            self.switch_profile(guest=True)
        elif action == "delete_password":
            self.delete_saved_password(str(command.get("target", "")))
        elif action == "copy_password":
            target = str(command.get("target", ""))
            record = next((item for item in self.password_store.list() if item.get("target") == target), None)
            if record:
                QApplication.clipboard().setText(record.get("password", ""))
        elif action == "add_password":
            raw_origin = QUrl.fromUserInput(str(command.get("origin", "")).strip())
            username = str(command.get("username", "")).strip()
            password = str(command.get("password", ""))
            if raw_origin.isValid() and raw_origin.scheme() in ("http", "https") and raw_origin.host() and username and password:
                origin = f"{raw_origin.scheme()}://{raw_origin.host()}"
                if raw_origin.port() >= 0:
                    origin += f":{raw_origin.port()}"
                self.save_password_credentials(origin, username, password)
        elif action == "clear_password_never":
            self.app_settings["password_never_save"] = []
            self.save_app_settings()
            self.refresh_settings_pages()
        elif action == "allow_password_origin":
            origin = str(command.get("origin", ""))
            self.app_settings["password_never_save"] = [
                item for item in self.app_settings.get("password_never_save", [])
                if item != origin
            ]
            self.save_app_settings()
            self.refresh_settings_pages()
        elif action == "clear_site_permissions":
            origin = str(command.get("origin", "")).strip()
            if origin:
                self.app_settings.setdefault("site_permission_overrides", {}).pop(origin, None)
                self.session_permission_overrides.pop(origin, None)
                self.save_app_settings()
                self.refresh_settings_pages()
                for index in range(self.tab_content.count()):
                    workspace = self.tab_content.widget(index)
                    if not isinstance(workspace, TabWorkspace):
                        continue
                    for current in (workspace.primary_browser, workspace.secondary_browser):
                        if current and self.site_origin(current.url()) == origin:
                            current.set_permission_policy(self.permission_policy_for_url(current.url()))
        elif action == "install_current_site":
            self.install_current_site_app()

    def show_image_context_menu(self, image_url, source_browser):
        self.close_selection_copy_popup()
        url = QUrl(str(image_url or ""))
        if not url.isValid() or url.scheme().lower() not in ("http", "https", "file", "data"):
            return
        menu = QMenu(self)
        menu.setStyleSheet(self.context_menu_stylesheet())
        open_action = menu.addAction("Открыть изображение в новой вкладке")
        copy_action = menu.addAction("Копировать изображение")
        copy_url_action = menu.addAction("Скопировать ссылку на изображение")
        download_action = None
        if url.scheme().lower() in ("http", "https"):
            menu.addSeparator()
            download_action = menu.addAction("Скачать изображение")
        selected = menu.exec(QCursor.pos())
        if selected == open_action:
            self.add_new_tab(
                url,
                url.fileName() or url.host() or "Изображение",
                private=bool(source_browser and source_browser.is_private),
            )
        elif selected == copy_action:
            self.copy_image_to_clipboard(url)
        elif selected == copy_url_action:
            QApplication.clipboard().setText(url.toString())
        elif download_action is not None and selected == download_action:
            self.start_download(
                {"url": url.toString(), "name": url.fileName()},
                source_browser.url() if source_browser else QUrl(),
            )

    def show_twitch_message_context_menu(self, command, source_browser):
        self.close_selection_copy_popup()
        username = str(command.get("username", "")).strip()
        message = str(command.get("text", "")).strip()
        menu = QMenu(self)
        menu.setStyleSheet(self.context_menu_stylesheet())
        copy_name = menu.addAction("Копировать имя пользователя")
        copy_message = menu.addAction("Копировать сообщение")
        copy_mention = menu.addAction("Копировать упоминание")
        copy_name.setEnabled(bool(username))
        copy_message.setEnabled(bool(message))
        copy_mention.setEnabled(bool(username))
        selected = menu.exec(QCursor.pos())
        if selected == copy_name:
            QApplication.clipboard().setText(username)
        elif selected == copy_message:
            QApplication.clipboard().setText(message)
        elif selected == copy_mention:
            QApplication.clipboard().setText(f"@{username.lstrip('@')}")

    def context_menu_stylesheet(self):
        colors = self.theme_colors
        return f"""
            QMenu {{ color:{colors['text']}; background:{colors['popup']}; border:1px solid {colors['border']}; border-radius:9px; padding:5px; }}
            QMenu::item {{ padding:8px 28px 8px 12px; border-radius:5px; }}
            QMenu::item:selected {{ background:{colors['hover']}; }}
            QMenu::item:disabled {{ color:{colors['muted']}; }}
            QMenu::separator {{ height:1px; background:{colors['border']}; margin:5px 7px; }}
        """

    def show_text_context_menu(self, command, source_browser):
        self.close_selection_copy_popup()
        text = str(command.get("text", ""))
        editable = bool(command.get("editable", False))
        element_html = str(command.get("html", ""))
        menu = QMenu(self)
        menu.setStyleSheet(self.context_menu_stylesheet())
        copy_action = menu.addAction("Копировать")
        cut_action = menu.addAction("Вырезать")
        paste_action = menu.addAction("Вставить")
        copy_action.setEnabled(bool(text))
        cut_action.setEnabled(bool(text) and editable)
        paste_action.setEnabled(editable and bool(QApplication.clipboard().text()))
        menu.addSeparator()
        translate_action = menu.addAction("Перевести выделенный текст")
        inspect_action = menu.addAction("Проверить")
        translate_action.setEnabled(bool(text))
        inspect_action.setEnabled(bool(text or element_html))
        selected = menu.exec(QCursor.pos())
        if selected == copy_action:
            QApplication.clipboard().setText(text)
        elif selected == cut_action:
            QApplication.clipboard().setText(text)
            source_browser.runJavaScript(
                "window.__gromEditSelection?.({type:'cut'})"
            )
        elif selected == paste_action:
            paste_text = QApplication.clipboard().text()
            source_browser.runJavaScript(
                f"window.__gromEditSelection?.({{type:'paste',text:{json.dumps(paste_text)}}})"
            )
        elif selected == translate_action:
            target = self.app_settings.get("translation_language", "ru")
            url = QUrl("https://translate.google.com/")
            query = QUrlQuery()
            query.addQueryItem("sl", "auto")
            query.addQueryItem("tl", target)
            query.addQueryItem("text", text)
            query.addQueryItem("op", "translate")
            url.setQuery(query)
            self.add_new_tab(url, "Перевод", private=source_browser.is_private)
        elif selected == inspect_action:
            self.inspect_page_selection(source_browser, text, element_html)

    def show_page_context_menu(self, command, source_browser):
        self.close_selection_copy_popup()
        menu = QMenu(self)
        menu.setStyleSheet(self.context_menu_stylesheet())
        back_action = menu.addAction("Назад")
        forward_action = menu.addAction("Вперёд")
        reload_action = menu.addAction("Обновить страницу")
        back_action.setEnabled(source_browser.can_go_back())
        forward_action.setEnabled(source_browser.can_go_forward())
        link = QUrl(str(command.get("link", "")))
        open_link_action = None
        if link.isValid() and link.scheme().lower() in ("http", "https"):
            menu.addSeparator()
            open_link_action = menu.addAction("Открыть ссылку в новой вкладке")
        menu.addSeparator()
        select_all_action = menu.addAction("Выделить всё")
        save_action = menu.addAction("Сохранить страницу")
        inspect_action = menu.addAction("Проверить")
        selected = menu.exec(QCursor.pos())
        if selected == back_action:
            source_browser.back()
        elif selected == forward_action:
            source_browser.forward()
        elif selected == reload_action:
            source_browser.reload()
        elif open_link_action is not None and selected == open_link_action:
            self.add_new_tab(link, link.host() or "Новая вкладка", private=source_browser.is_private)
        elif selected == select_all_action:
            source_browser.runJavaScript(
                "(() => { const selection=getSelection(); const range=document.createRange(); range.selectNodeContents(document.body || document.documentElement); selection.removeAllRanges(); selection.addRange(range); return true; })()"
            )
        elif selected == save_action:
            self.save_page_snapshot()
        elif selected == inspect_action:
            self.inspect_page_selection(source_browser, "", str(command.get("html", "")))

    def close_selection_copy_popup(self):
        popup = getattr(self, "selection_copy_popup", None)
        if popup:
            try:
                popup.close()
            except RuntimeError:
                pass
        self.selection_copy_popup = None

    def show_selection_copy_popup(self, text):
        text = str(text or "").strip()
        if not text:
            self.close_selection_copy_popup()
            return
        self.close_selection_copy_popup()
        popup = QFrame(
            self,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.prepare_rounded_popup(popup, 9)
        popup.setObjectName("selectionCopyPopup")
        popup.setStyleSheet(f"""
            QFrame#selectionCopyPopup {{ background:{self.theme_colors['popup']}; border:1px solid {self.theme_colors['border']}; border-radius:7px; }}
            QPushButton {{ color:{self.theme_colors['text']}; background:transparent; border:none; border-radius:5px; padding:7px 12px; }}
            QPushButton:hover {{ background:{self.theme_colors['hover']}; }}
        """)
        layout = QHBoxLayout(popup)
        layout.setContentsMargins(4, 4, 4, 4)
        copy_button = QPushButton("Копировать")
        copy_button.clicked.connect(
            lambda: (QApplication.clipboard().setText(text), popup.close())
        )
        layout.addWidget(copy_button)
        popup.adjustSize()
        cursor = QCursor.pos()
        screen = self.screen().availableGeometry()
        x = max(screen.left() + 6, min(cursor.x() - popup.width() // 2, screen.right() - popup.width() - 6))
        y = max(screen.top() + 6, cursor.y() - popup.height() - 12)
        popup.move(x, y)
        self.selection_copy_popup = popup
        popup.show()
        popup.raise_()
        QTimer.singleShot(
            3500,
            lambda current=popup: current.close() if current is self.selection_copy_popup else None,
        )

    def inspect_page_selection(self, browser, text, element_html=""):
        index = self.tab_index_for_browser(browser)
        if index >= 0 and index != self.tab_bar.currentIndex():
            self.tab_bar.setCurrentIndex(index)
        self.devtools_panel.show()
        self.devtools_tabs.setCurrentIndex(1)
        self.refresh_devtools()
        query = " ".join(str(text or "").split())[:120]
        if not query:
            tag = re.match(r"\s*<([\w:-]+)", str(element_html or ""))
            query = f"<{tag.group(1)}" if tag else ""
        self.devtools_search.setText(query)
        if query:
            QTimer.singleShot(350, self.find_in_devtools_elements)

    def copy_image_to_clipboard(self, url):
        if url.scheme().lower() == "file":
            image = QImage(url.toLocalFile())
            if not image.isNull():
                QApplication.clipboard().setImage(image)
            return
        request = QNetworkRequest(url)
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        reply = self.download_network.get(request)

        def finish_copy():
            data = bytes(reply.readAll())
            image = QImage.fromData(data)
            if not image.isNull():
                QApplication.clipboard().setImage(image)
            else:
                QMessageBox.warning(self, "Изображение", "Не удалось скопировать изображение.")
            reply.deleteLater()

        reply.finished.connect(finish_copy)

    def register_windows_browser(self):
        if sys.platform != "win32":
            QMessageBox.information(
                self,
                "Браузер по умолчанию",
                "Регистрация браузера по умолчанию доступна только в Windows.",
            )
            return
        try:
            import winreg

            script_path = os.path.abspath(__file__)
            python_path = os.path.abspath(sys.executable)
            pythonw_path = os.path.join(os.path.dirname(python_path), "pythonw.exe")
            launcher = pythonw_path if os.path.isfile(pythonw_path) else python_path
            command = f'"{launcher}" "{script_path}" "%1"'
            app_name = "Grom Browser"
            url_progid = "GromBrowser.URL"
            html_progid = "GromBrowser.HTML"
            image_progid = "GromBrowser.Image"
            pdf_progid = "GromBrowser.PDF"

            def set_value(path, name, value):
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
                    winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

            progids = {
                url_progid: ("Grom Browser URL", True),
                html_progid: ("HTML-документ Grom", False),
                image_progid: ("Изображение Grom", False),
                pdf_progid: ("PDF-документ Grom", False),
            }
            for progid, (description, is_url) in progids.items():
                base = rf"Software\Classes\{progid}"
                set_value(base, "", description)
                if is_url:
                    set_value(base, "URL Protocol", "")
                set_value(base + r"\shell\open\command", "", command)

            capabilities = r"Software\GromBrowser\Capabilities"
            set_value(capabilities, "ApplicationName", app_name)
            set_value(capabilities, "ApplicationDescription", "Веб-браузер Grom")
            for protocol in ("http", "https"):
                set_value(capabilities + r"\URLAssociations", protocol, url_progid)
            associations = {
                ".htm": html_progid,
                ".html": html_progid,
                ".xhtml": html_progid,
                ".pdf": pdf_progid,
                ".bmp": image_progid,
                ".gif": image_progid,
                ".jpeg": image_progid,
                ".jpg": image_progid,
                ".png": image_progid,
                ".svg": image_progid,
                ".webp": image_progid,
            }
            for extension, progid in associations.items():
                set_value(capabilities + r"\FileAssociations", extension, progid)
                set_value(rf"Software\Classes\{extension}\OpenWithProgids", progid, "")
            set_value(
                r"Software\RegisteredApplications",
                app_name,
                capabilities,
            )
            QDesktopServices.openUrl(
                QUrl("ms-settings:defaultapps?registeredAppUser=Grom%20Browser")
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Браузер по умолчанию",
                f"Не удалось зарегистрировать Grom в Windows:\n{error}",
            )

    def refresh_downloads_pages(self):
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            browser = workspace.primary_browser
            if browser.internal_page == "downloads":
                browser.load_internal_html(self.downloads_page_html(), "grom://downloads")
                browser._icon = self.downloads_icon()
                browser.iconChanged.emit(browser._icon)




    def apply_rounded_popup_mask(self, popup, radius=12):
        if not popup or popup.width() < 2 or popup.height() < 2:
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(popup.rect()), radius, radius)
        popup.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def prepare_rounded_popup(self, popup, radius=12):
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup.setAutoFillBackground(True)
        palette = popup.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(self.theme_colors["popup"]))
        popup.setPalette(palette)
        popup.setProperty("gromPopupRadius", int(radius))
        popup.installEventFilter(self)
        QTimer.singleShot(0, lambda current=popup: self.apply_rounded_popup_mask(current, radius))
        return popup

    def popup_stylesheet(self, object_name):
        colors = self.theme_colors
        return f"""
            QFrame#{object_name} {{ background:{colors['popup']}; border:1px solid {colors['border']}; border-radius:12px; }}
            QLabel {{ color:{colors['text']}; border:none; background:transparent; }}
            QLabel#mutedLabel {{ color:{colors['muted']}; }}
            QPushButton {{ color:{colors['text']}; background:transparent; border:none; border-radius:7px; text-align:left; padding:8px 10px; }}
            QPushButton:hover {{ background:{colors['hover']}; }}
            QPushButton:disabled {{ color:{colors['muted']}; }}
            QToolButton {{ color:{colors['muted']}; background:transparent; border:none; border-radius:7px; }}
            QToolButton:hover {{ color:{colors['text']}; background:{colors['hover']}; }}
            QComboBox {{ color:{colors['text']}; background:{colors['surface']}; border:1px solid {colors['border']}; border-radius:7px; padding:5px 8px; }}
            QComboBox QAbstractItemView {{ color:{colors['text']}; background:{colors['popup']}; selection-background-color:{colors['hover']}; }}
        """

    def popup_separator(self):
        line = QFrame()
        line.setObjectName("popupSeparator")
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{self.theme_colors['border']}; border:none; margin:5px 0;")
        return line

    def begin_toggle_popup(self, attribute, key):
        now = time.monotonic()
        if now - float(self._popup_closed_at.get(key, 0.0)) < 0.22:
            return False
        popup = getattr(self, attribute, None)
        if popup is not None:
            try:
                popup.close()
            except RuntimeError:
                pass
            setattr(self, attribute, None)
            self._popup_closed_at[key] = now
            return False
        for other_attribute in ( 
            "menu_popup",
            "profile_popup",
            "builtin_extensions_popup",
        ):
            if other_attribute == attribute:
                continue
            other_popup = getattr(self, other_attribute, None)
            if other_popup is not None:
                try:
                    other_popup.close()
                except RuntimeError:
                    pass
                setattr(self, other_attribute, None)
        return True

    def register_toggle_popup(self, popup, attribute, key):
        self.prepare_rounded_popup(popup)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.destroyed.connect(
            lambda _object=None, current=popup: self.finish_toggle_popup(
                attribute, key, current
            )
        )

    def finish_toggle_popup(self, attribute, key, popup):
        if getattr(self, attribute, None) is popup:
            setattr(self, attribute, None)
        self._popup_closed_at[key] = time.monotonic()

    def show_profile_menu(self):
        if not self.begin_toggle_popup("profile_popup", "profile"):
            return
        if self.menu_popup and self.menu_popup.isVisible():
            self.menu_popup.close()

        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.register_toggle_popup(popup, "profile_popup", "profile")
        popup.setObjectName("profilePopup")
        popup.setFixedWidth(330)
        popup.setStyleSheet(self.popup_stylesheet("profilePopup"))
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(3)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(7, 5, 7, 8)
        avatar = QLabel()
        avatar.setPixmap(self.profile_avatar_icon(38).pixmap(38, 38))
        avatar.setFixedSize(42, 42)
        name_box = QVBoxLayout()
        name = QLabel(self.current_profile.get("name", "Профиль"))
        name.setStyleSheet("font-weight:600; font-size:14px;")
        mode = QLabel("Гостевой режим" if self.guest_mode else "Локальный профиль Grom")
        mode.setObjectName("mutedLabel")
        name_box.addWidget(name)
        name_box.addWidget(mode)
        header_layout.addWidget(avatar)
        header_layout.addLayout(name_box, 1)
        layout.addWidget(header)

        avatar_button = self.create_popup_action("Изменить аватар")
        avatar_button.setEnabled(not self.guest_mode)
        avatar_button.clicked.connect(lambda: (popup.close(), self.choose_profile_avatar(self.profile_id)))
        layout.addWidget(avatar_button)
        rename_button = self.create_popup_action("Переименовать профиль")
        rename_button.setEnabled(not self.guest_mode)
        rename_button.clicked.connect(lambda: (popup.close(), self.rename_current_profile_dialog()))
        layout.addWidget(rename_button)
        settings_button = self.create_popup_action("Настройки профиля")
        settings_button.clicked.connect(lambda: (popup.close(), self.open_settings_tab()))
        layout.addWidget(settings_button)
        layout.addWidget(self.popup_separator())

        profiles_title = QLabel("Профили")
        profiles_title.setObjectName("mutedLabel")
        profiles_title.setStyleSheet("padding:4px 8px; font-size:11px;")
        layout.addWidget(profiles_title)
        for profile in self.profile_registry.get("profiles", []):
            row = QFrame()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)
            is_active = not self.guest_mode and profile.get("id") == self.profile_id
            profile_button = QPushButton(("✓  " if is_active else "") + profile.get("name", "Профиль"))
            profile_button.setIcon(self.profile_avatar_icon(24, profile))
            profile_button.setIconSize(QSize(24, 24))
            profile_button.setEnabled(not is_active)
            profile_button.clicked.connect(
                lambda _checked=False, value=profile.get("id"): (popup.close(), self.switch_profile(value))
            )
            row_layout.addWidget(profile_button, 1)
            if profile.get("id") not in ("default", self.profile_id):
                delete_button = QToolButton()
                delete_button.setIcon(
                    self.themed_icon(self.menu_icon_path("close.png"), self.theme_colors["icon"])
                )
                delete_button.setIconSize(QSize(16, 16))
                delete_button.setToolTip("Удалить профиль")
                delete_button.setFixedSize(30, 30)
                delete_button.clicked.connect(
                    lambda _checked=False, value=profile.get("id"): (popup.close(), self.delete_profile(value))
                )
                row_layout.addWidget(delete_button)
            layout.addWidget(row)

        layout.addWidget(self.popup_separator())
        create_button = self.create_popup_action("Создать профиль")
        create_button.clicked.connect(lambda: (popup.close(), self.create_profile_dialog()))
        layout.addWidget(create_button)
        guest_button = self.create_popup_action("Открыть гостевое окно")
        guest_button.clicked.connect(lambda: (popup.close(), self.switch_profile(guest=True)))
        layout.addWidget(guest_button)

        self.profile_popup = popup
        popup.adjustSize()
        anchor = self.profile_btn.mapToGlobal(QPoint(self.profile_btn.width(), self.profile_btn.height() + 4))
        screen = self.screen().availableGeometry()
        popup.move(max(screen.left() + 8, anchor.x() - popup.width()), min(anchor.y(), screen.bottom() - popup.height() - 8))
        popup.show()
        popup.raise_()

    def rename_current_profile_dialog(self):
        if self.guest_mode:
            return
        name, accepted = QInputDialog.getText(
            self,
            "Переименовать профиль",
            "Название профиля:",
            QLineEdit.EchoMode.Normal,
            self.current_profile.get("name", "Профиль"),
        )
        if accepted and name.strip():
            self.rename_profile(self.profile_id, name)

    def create_profile_dialog(self):
        name, accepted = QInputDialog.getText(self, "Новый профиль", "Название профиля:")
        if accepted and name.strip():
            self.create_profile(name)

    def site_origin(self, url):
        if url.scheme() not in ("http", "https") or not url.host():
            return ""
        origin = QUrl()
        origin.setScheme(url.scheme())
        origin.setHost(url.host())
        if url.port() >= 0:
            origin.setPort(url.port())
        return origin.toString().rstrip("/")

    def permission_policy_for_url(self, url):
        policy = dict(self.app_settings.get("site_permissions", {}))
        origin = self.site_origin(url)
        overrides = self.app_settings.get("site_permission_overrides", {}).get(origin, {})
        for key, value in overrides.items():
            if value in ("allow", "block"):
                policy[key] = value
        session_overrides = self.session_permission_overrides.get(origin, {})
        for key, value in session_overrides.items():
            if value == "allow":
                policy[key] = value
        return policy

    def set_site_permission(self, origin, permission, value, browser):
        if not origin or permission not in SITE_PERMISSION_KEYS:
            return
        overrides = self.app_settings.setdefault("site_permission_overrides", {})
        values = overrides.setdefault(origin, {})
        session_values = self.session_permission_overrides.setdefault(origin, {})
        session_values.pop(permission, None)
        if value == "allow_once":
            values.pop(permission, None)
            session_values[permission] = "allow"
        elif value == "ask":
            values.pop(permission, None)
        elif value in ("allow", "block"):
            values[permission] = value
        if not values:
            overrides.pop(origin, None)
        if not session_values:
            self.session_permission_overrides.pop(origin, None)
        self.save_app_settings()
        for window in Browser._open_windows:
            if window.storage_path != self.storage_path:
                continue
            for index in range(window.tab_content.count()):
                workspace = window.tab_content.widget(index)
                if not isinstance(workspace, TabWorkspace):
                    continue
                for current in (workspace.primary_browser, workspace.secondary_browser):
                    if current and window.site_origin(current.url()) == origin:
                        current.set_permission_policy(window.permission_policy_for_url(current.url()))

    def show_site_info_popup(self):
        if self.site_info_popup and self.site_info_popup.isVisible():
            self.site_info_popup.close()
            return
        browser = self.current_browser()
        if not browser:
            return
        url = browser.url()
        origin = self.site_origin(url)
        internal = bool(browser.internal_page)
        secure = url.scheme() == "https" or internal
        colors = self.theme_colors

        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.prepare_rounded_popup(popup)
        popup.setObjectName("siteInfoPopup")
        popup.setFixedWidth(380)
        popup.setStyleSheet(self.popup_stylesheet("siteInfoPopup"))
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)

        status = QLabel("Страница Grom" if internal else ("Защищённое соединение" if secure else "Незащищённое соединение"))
        status.setStyleSheet(f"font-size:14px; font-weight:600; color:{colors['accent'] if secure else '#d93025'};")
        description = QLabel(
            "Внутренняя страница браузера."
            if internal
            else ("Соединение с сайтом зашифровано. Это не гарантирует надёжность содержимого сайта." if secure else "Данные передаются без защищённого HTTPS-соединения.")
        )
        description.setObjectName("mutedLabel")
        description.setWordWrap(True)
        host = QLabel(origin or url.toString())
        host.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(status)
        layout.addWidget(description)
        layout.addWidget(host)
        layout.addWidget(self.popup_separator())

        permissions_title = QLabel("Разрешения сайта")
        permissions_title.setStyleSheet("font-weight:600;")
        layout.addWidget(permissions_title)
        labels = {
            "camera": "Камера",
            "microphone": "Микрофон",
            "notifications": "Уведомления",
            "geolocation": "Геолокация",
            "autoplay": "Автозапуск видео",
            "clipboard": "Буфер обмена",
            "popups": "Всплывающие окна",
        }
        overrides = self.app_settings.get("site_permission_overrides", {}).get(origin, {})
        temporary = self.session_permission_overrides.get(origin, {})
        for key, title in labels.items():
            row = QFrame()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(2, 0, 2, 0)
            row_layout.addWidget(QLabel(title))
            row_layout.addStretch()
            choice = QComboBox()
            choice.addItem("По умолчанию", "ask")
            choice.addItem("Разрешить", "allow")
            choice.addItem("Только сейчас", "allow_once")
            choice.addItem("Блокировать", "block")
            selected_value = "allow_once" if temporary.get(key) == "allow" else overrides.get(key, "ask")
            selected = choice.findData(selected_value)
            choice.setCurrentIndex(max(0, selected))
            choice.setEnabled(not internal)
            choice.currentIndexChanged.connect(
                lambda _index, permission=key, combo=choice: self.set_site_permission(
                    origin, permission, combo.currentData(), browser
                )
            )
            row_layout.addWidget(choice)
            layout.addWidget(row)

        layout.addWidget(self.popup_separator())
        cookie_count = len(browser.cookie_names_for_host())
        cookie_label = QLabel(f"Cookies этого сайта: {cookie_count}")
        cookie_label.setObjectName("mutedLabel")
        delete_cookies = QPushButton("Удалить cookies сайта")
        delete_cookies.setEnabled(not internal and bool(url.host()))
        delete_cookies.clicked.connect(
            lambda: self.delete_current_site_cookies(browser, cookie_label)
        )
        layout.addWidget(cookie_label)
        layout.addWidget(delete_cookies)

        clear_site_data = QPushButton("Удалить все данные сайта")
        clear_site_data.setEnabled(not internal and bool(url.host()))
        clear_site_data.setToolTip("Удалить cookies, хранилища, разрешения и записи истории этого сайта")
        clear_site_data.clicked.connect(
            lambda: self.clear_current_site_data(browser, origin, popup)
        )
        layout.addWidget(clear_site_data)

        self.site_info_popup = popup
        popup.adjustSize()
        anchor = self.site_info_btn.mapToGlobal(QPoint(0, self.site_info_btn.height() + 5))
        screen = self.screen().availableGeometry()
        popup.move(max(screen.left() + 8, min(anchor.x(), screen.right() - popup.width() - 8)), anchor.y())
        popup.show()
        popup.raise_()

    def delete_current_site_cookies(self, browser, label):
        removed = browser.delete_site_cookies(browser.url().host())
        label.setText("Cookies сайта удалены" if removed else "Доступных cookies не найдено")

    def clear_current_site_data(self, browser, origin, popup):
        host = browser.url().host().lower()
        if not host:
            return
        answer = QMessageBox.question(
            self,
            "Удалить данные сайта",
            f"Удалить cookies, локальные хранилища, разрешения и историю для {host}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        browser.clear_site_storage()
        overrides = self.app_settings.setdefault("site_permission_overrides", {})
        overrides.pop(origin, None)
        self.save_app_settings()
        browser.set_permission_policy(self.permission_policy_for_url(browser.url()))
        try:
            with open(self.history_file, "r", encoding="utf-8") as file:
                records = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            records = []
        filtered = [
            item for item in records
            if not isinstance(item, dict)
            or QUrl(str(item.get("url", ""))).host().lower() != host
        ]
        if filtered != records:
            with open(self.history_file, "w", encoding="utf-8") as file:
                json.dump(filtered, file, ensure_ascii=False, indent=2)
        popup.close()
        QMessageBox.information(
            self,
            "Данные удалены",
            "Данные сайта очищены. Страница будет загружена заново.",
        )
        browser.reload()

    def snapshots_directory(self):
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        ) or os.path.expanduser("~")
        return os.path.join(documents, "Grom Snapshots")

    def save_page_snapshot(self):
        browser = self.current_browser()
        if not browser:
            return
        os.makedirs(self.snapshots_directory(), exist_ok=True)
        title = browser.title() or browser.url().host() or "Снимок страницы"
        safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")[:90]
        suggested = os.path.join(self.snapshots_directory(), f"{safe_title or 'snapshot'}.html")
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить снимок страницы",
            suggested,
            "Веб-страница (*.html)",
        )
        if not path:
            return
        if not path.lower().endswith((".html", ".htm")):
            path += ".html"

        def write_snapshot(html):
            if not isinstance(html, str) or not html.strip():
                QMessageBox.warning(self, "Снимок страницы", "Не удалось получить содержимое страницы.")
                return
            try:
                with open(path, "w", encoding="utf-8") as file:
                    file.write(html)
            except OSError as error:
                QMessageBox.warning(self, "Снимок страницы", f"Не удалось сохранить файл:\n{error}")
                return
            QMessageBox.information(
                self,
                "Снимок сохранён",
                f"Страница сохранена для просмотра без интернета:\n{path}",
            )

        browser.create_page_snapshot(write_snapshot)

    def open_page_snapshot(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Открыть снимок страницы",
            self.snapshots_directory(),
            "Веб-страницы (*.html *.htm)",
        )
        if path:
            self.add_new_tab(QUrl.fromLocalFile(path), label=os.path.basename(path))

    def show_main_menu(self):
        if not self.begin_toggle_popup("menu_popup", "menu"):
            return

        colors = self.theme_colors
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.register_toggle_popup(popup, "menu_popup", "menu")
        popup.setObjectName("browserMenuPopup")
        popup.setFixedWidth(330)
        popup.setStyleSheet(f"""
            QFrame#browserMenuPopup {{
                background: {colors['popup']};
                border: 1px solid {colors['border']};
                border-radius: 12px;
            }}
            QPushButton#popupAction {{
                background: transparent;
                border: none;
                border-radius: 7px;
                color: {colors['text']};
                text-align: left;
            }}
            QPushButton#popupAction:hover {{ background: {colors['hover']}; }}
            QLabel {{ color: {colors['text']}; border: none; }}
            QLabel#shortcutLabel {{ color: {colors['muted']}; }}
            QToolButton {{
                background: {colors['surface']};
                color: {colors['text']};
                border: none;
                border-radius: 7px;
                font-size: 17px;
            }}
            QToolButton:hover {{ background: {colors['hover']}; }}
        """)
        outer_layout = QVBoxLayout(popup)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background:{colors['popup']}; border:none; }}
            QScrollArea > QWidget > QWidget {{ background:{colors['popup']}; }}
            QScrollBar:vertical {{ width:8px; background:{colors['popup']}; }}
            QScrollBar::handle:vertical {{ background:{colors['border']}; min-height:28px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        menu_commands = self.app_settings.get("menu_commands", {})
        def command_visible(name, default=False):
            return bool(menu_commands.get(name, default)) if isinstance(menu_commands, dict) else default

        new_window_button = self.create_popup_action("Новое окно", "Ctrl+N")
        new_window_button.clicked.connect(lambda: (popup.close(), self.launch_new_window()))
        layout.addWidget(new_window_button)

        new_tab_button = self.create_popup_action("Новая вкладка", "Ctrl+T")
        new_tab_button.clicked.connect(lambda: (popup.close(), self.add_new_tab()))
        layout.addWidget(new_tab_button)

        private_button = self.create_popup_action("Новая приватная вкладка", "Ctrl+Shift+N")
        private_button.clicked.connect(lambda: (popup.close(), self.add_private_tab()))
        layout.addWidget(private_button)
        layout.addWidget(self.popup_separator())

        history_button = self.create_popup_action("История", "Ctrl+H")
        history_button.clicked.connect(
            lambda: (popup.close(), QTimer.singleShot(0, self.show_history_popup))
        )
        layout.addWidget(history_button)

        downloads_button = self.create_popup_action("Загрузки", "Ctrl+J")
        downloads_button.clicked.connect(
            lambda: (popup.close(), QTimer.singleShot(0, self.show_downloads_popup))
        )
        layout.addWidget(downloads_button)

        if command_visible("tab_search", True):
            tab_search_button = self.create_popup_action("Поиск по вкладкам", "Ctrl+Shift+A")
            tab_search_button.clicked.connect(
                lambda: (popup.close(), QTimer.singleShot(0, self.show_tab_search))
            )
            layout.addWidget(tab_search_button)

        if command_visible("find_page", True):
            find_button = self.create_popup_action("Найти на странице", "Ctrl+F")
            find_button.clicked.connect(lambda: (popup.close(), self.show_find_bar()))
            layout.addWidget(find_button)
        rare_commands_visible = any((
            command_visible("screenshot"),
            command_visible("split_screen"),
            command_visible("developer_tools"),
            command_visible("install_site"),
        ))
        if rare_commands_visible:
            layout.addWidget(self.popup_separator())

        if command_visible("screenshot"):
            screenshot_button = self.create_popup_action("Сделать скриншот", "Ctrl+Shift+S")
            screenshot_button.clicked.connect(
                lambda: (popup.close(), QTimer.singleShot(0, self.show_screenshot_menu))
            )
            layout.addWidget(screenshot_button)

        workspace = self.current_workspace()
        if command_visible("split_screen"):
            split_text = "Закрыть разделение" if workspace and workspace.is_split() else "Разделить экран"
            split_button = self.create_popup_action(split_text)
            split_button.clicked.connect(lambda: (popup.close(), self.toggle_split_screen()))
            layout.addWidget(split_button)

        if command_visible("developer_tools"):
            devtools_button = self.create_popup_action("Инструменты разработчика", "F12")
            devtools_button.clicked.connect(lambda: (popup.close(), self.toggle_devtools()))
            layout.addWidget(devtools_button)

        if command_visible("install_site"):
            install_button = self.create_popup_action("Установить сайт")
            install_button.clicked.connect(lambda: (popup.close(), self.install_current_site_app()))
            layout.addWidget(install_button)

        if rare_commands_visible:
            layout.addWidget(self.popup_separator())

        additional_tools = self.create_popup_action("Дополнительные инструменты", "›")
        additional_tools.setProperty("gromAdditionalTools", True)
        additional_tools.installEventFilter(self)
        additional_tools.clicked.connect(
            lambda _checked=False, button=additional_tools:
            self.show_additional_tools_menu(button)
        )
        layout.addWidget(additional_tools)
        layout.addWidget(self.popup_separator())

        settings_button = self.create_popup_action("Настройки")
        settings_button.clicked.connect(lambda: (popup.close(), self.open_settings_tab()))
        layout.addWidget(settings_button)

        about_button = self.create_popup_action("О разработчике")
        about_button.clicked.connect(lambda: (popup.close(), self.show_about_developer()))
        layout.addWidget(about_button)

        layout.addWidget(self.popup_separator())

        zoom_row = QFrame()
        zoom_layout = QHBoxLayout(zoom_row)
        zoom_layout.setContentsMargins(10, 5, 6, 5)
        zoom_layout.setSpacing(8)
        zoom_layout.addWidget(QLabel("Масштаб"))
        zoom_layout.addStretch()
        minus_button = QToolButton()
        minus_button.setText("−")
        minus_button.setToolTip("Уменьшить")
        minus_button.setFixedSize(30, 30)
        self.zoom_value_label = QLabel(
            f"{self.current_browser().zoom_percent() if self.current_browser() else 100}%"
        )
        self.zoom_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_value_label.setFixedWidth(52)
        self.zoom_value_label.setToolTip("Нажмите, чтобы вернуть 100%")
        self.zoom_value_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_value_label.mousePressEvent = lambda _event: self.reset_zoom()
        plus_button = QToolButton()
        plus_button.setText("+")
        plus_button.setToolTip("Увеличить")
        plus_button.setFixedSize(30, 30)
        minus_button.clicked.connect(lambda: self.change_zoom(-10))
        plus_button.clicked.connect(lambda: self.change_zoom(10))
        zoom_layout.addWidget(minus_button)
        zoom_layout.addWidget(self.zoom_value_label)
        zoom_layout.addWidget(plus_button)
        layout.addWidget(zoom_row)

        self.menu_popup = popup
        content.adjustSize()
        popup.setFixedHeight(
            min(content.sizeHint().height() + 2, self.screen().availableGeometry().height() - 24)
        )
        self.position_popup(popup)
        popup.show()
        popup.raise_()

    def menu_icon_path(self, filename):
        root = os.path.dirname(__file__)
        for candidate in (
            os.path.join(root, "menu_icons", filename),
            os.path.join(root, filename),
        ):
            if os.path.isfile(candidate):
                return candidate
        return os.path.join(root, "menu_icons", filename)

    def popup_action_icon(self, text):
        rules = (
            ("Новое окно", "new_window.png", "▣"),
            ("Новая приватная", "private_tab.png", "◐"),
            ("Новая вкладка", "new_tab.png", "+"),
            ("История", "history.png", "↶"),
            ("Загрузки", "downloads_icon_placeholder.png", "↓"),
            ("Найти на странице", "find.png", "⌕"),
            ("Сохранить снимок", "snapshot_save.png", "▧"),
            ("Открыть снимок", "snapshot_open.png", "□"),
            ("Режим чтения", "reader.png", "A"),
            ("Картинка в картинке", "picture_in_picture.png", "▱"),
            ("Перевести страницу", "translate_icon_placeholder.png", "Я"),
            ("Блокировщик рекламы", "ad_blocker.png", "◇"),
            ("Встроенные расширения", "extensions.png", "⊕"),
            ("Дополнительные инструменты", "more_tools.png", "⋯"),
            ("Поиск по вкладкам", "tab_search.png", "⌕"),
            ("Сделать скриншот", "screenshot.png", "▣"),
            ("Разделить экран", "split_screen.png", "Ⅱ"),
            ("Закрыть разделение", "split_screen.png", "Ⅱ"),
            ("Вертикальные вкладки", "vertical_tabs.png", "☷"),
            ("Обычные вкладки", "horizontal_tabs.png", "═"),
            ("Производительность", "performance.png", "⌁"),
            ("Инструменты разработчика", "developer_tools.png", "<>"),
            ("Установить сайт", "install_app.png", "↓"),
            ("Настройки", "settings_icon_placeholder.png", "⚙"),
            ("Изменить аватар", "profile_avatar.png", "●"),
            ("Переименовать профиль", "rename.png", "I"),
            ("Создать профиль", "profile_add.png", "+"),
            ("Открыть гостевое", "guest.png", "○"),
        )
        filename, glyph = "action.png", "•"
        for prefix, candidate, fallback in rules:
            if str(text).startswith(prefix):
                filename, glyph = candidate, fallback
                break
        path = self.menu_icon_path(filename)
        icon = self.themed_icon(path, self.theme_colors["icon"])
        if not icon.isNull():
            return icon
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setPen(QColor(self.theme_colors["icon"]))
        font = painter.font()
        font.setPixelSize(13 if len(glyph) == 1 else 10)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
        painter.end()
        return QIcon(pixmap)

    def show_additional_tools_menu(self, anchor_button):
        try:
            if not anchor_button.isVisible():
                return
        except RuntimeError:
            return
        existing = getattr(self, "additional_tools_menu", None)
        if existing:
            try:
                if existing.isVisible():
                    return
            except RuntimeError:
                pass
        parent_popup = getattr(self, "menu_popup", None)
        menu = QMenu(parent_popup or self)
        menu.setObjectName("additionalToolsMenu")
        menu.setProperty("gromAdditionalToolsMenu", True)
        menu.installEventFilter(self)
        menu.setStyleSheet(self.context_menu_stylesheet())
        self.additional_tools_menu = menu
        self.additional_tools_anchor = anchor_button
        menu.aboutToHide.connect(self.additional_tools_hidden)

        def add_action(text, callback, shortcut=""):
            label = f"{text}\t{shortcut}" if shortcut else text
            action = menu.addAction(self.popup_action_icon(text), label)
            def run():
                if parent_popup:
                    try:
                        parent_popup.close()
                    except RuntimeError:
                        pass
                QTimer.singleShot(0, callback)
            action.triggered.connect(run)

        configured = self.app_settings.get("menu_commands", {})
        configured = configured if isinstance(configured, dict) else {}
        hidden_commands = (
            ("tab_search", "Поиск по вкладкам", self.show_tab_search, "Ctrl+Shift+A", True),
            ("find_page", "Найти на странице", self.show_find_bar, "Ctrl+F", True),
            ("screenshot", "Сделать скриншот", self.show_screenshot_menu, "Ctrl+Shift+S", False),
            ("split_screen", "Разделить экран", self.toggle_split_screen, "", False),
            ("developer_tools", "Инструменты разработчика", self.toggle_devtools, "F12", False),
            ("install_site", "Установить сайт", self.install_current_site_app, "", False),
        )
        for key, text, callback, shortcut, default in hidden_commands:
            if not bool(configured.get(key, default)):
                add_action(text, callback, shortcut)
        if menu.actions():
            menu.addSeparator()
        add_action("Сохранить снимок страницы", self.save_page_snapshot)
        add_action("Открыть снимок страницы", self.open_page_snapshot)
        add_action("Режим чтения", self.toggle_reader_mode)
        add_action("Картинка в картинке", self.toggle_picture_in_picture)
        add_action("Перевести страницу", self.translate_browser)
        add_action("Производительность", self.show_performance_popup)

        menu.adjustSize()
        position = anchor_button.mapToGlobal(QPoint(anchor_button.width() + 5, 0))
        screen = self.screen().availableGeometry()
        if position.x() + menu.sizeHint().width() > screen.right():
            position.setX(anchor_button.mapToGlobal(QPoint(0, 0)).x() - menu.sizeHint().width() - 5)
        position.setY(max(screen.top() + 6, min(position.y(), screen.bottom() - menu.sizeHint().height() - 6)))
        menu.popup(position)

    def additional_tools_hidden(self):
        self.stop_additional_tools_close_timer()
        self.additional_tools_menu = None
        self.additional_tools_anchor = None

    def stop_additional_tools_close_timer(self):
        timer = getattr(self, "_additional_tools_close_timer", None)
        if timer and timer.isActive():
            timer.stop()

    def schedule_additional_tools_close(self):
        timer = getattr(self, "_additional_tools_close_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self.close_additional_tools_if_outside)
            self._additional_tools_close_timer = timer
        timer.start(220)

    def close_additional_tools_if_outside(self):
        menu = getattr(self, "additional_tools_menu", None)
        anchor = getattr(self, "additional_tools_anchor", None)
        if menu is None:
            return
        cursor = QCursor.pos()
        try:
            menu_area = menu.frameGeometry().adjusted(-7, -7, 7, 7)
            anchor_top_left = anchor.mapToGlobal(QPoint(0, 0)) if anchor else QPoint()
            anchor_area = QRect(anchor_top_left, anchor.size()).adjusted(-5, -5, 5, 5) if anchor else QRect()
            if menu_area.contains(cursor) or anchor_area.contains(cursor):
                return
            menu.close()
        except RuntimeError:
            self.additional_tools_menu = None
            self.additional_tools_anchor = None

    def create_popup_action(self, text, shortcut=""):
        button = QPushButton()
        button.setObjectName("popupAction")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(40)
        row = QHBoxLayout(button)
        row.setContentsMargins(12, 0, 12, 0)
        icon = QLabel()
        icon.setPixmap(self.popup_action_icon(text).pixmap(18, 18))
        icon.setFixedSize(22, 22)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title = QLabel(text)
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        shortcut_label = QLabel(shortcut)
        shortcut_label.setObjectName("shortcutLabel")
        shortcut_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(icon)
        row.addWidget(title)
        row.addStretch()
        row.addWidget(shortcut_label)
        return button

    def position_popup(self, popup):
        popup.adjustSize()
        anchor = self.menu_btn.mapToGlobal(QPoint(self.menu_btn.width(), self.menu_btn.height() + 4))
        screen = self.screen().availableGeometry()
        x = max(screen.left() + 8, min(anchor.x() - popup.width(), screen.right() - popup.width() - 8))
        y = min(anchor.y(), screen.bottom() - popup.height() - 8)
        popup.move(x, y)





















    def show_history_popup(self):
        if self.history_popup and self.history_popup.isVisible():
            self.history_popup.close()
            return

        try:
            with open(self.history_file, "r", encoding="utf-8") as file:
                history = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            history = []

        colors = self.theme_colors
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.prepare_rounded_popup(popup)
        popup.setObjectName("historyPopup")
        popup.setFixedSize(430, 560)
        popup.setStyleSheet(f"""
            QFrame#historyPopup {{ background: {colors['popup']}; border: 1px solid {colors['border']}; border-radius: 12px; }}
            QLabel {{ color: {colors['text']}; border: none; }}
            QPushButton#historyItem {{ background: transparent; border: none; border-radius: 5px; text-align: left; }}
            QPushButton#historyItem:hover {{ background: {colors['hover']}; }}
            QPushButton#clearHistory {{ color: {colors['accent']}; background: transparent; border: none; padding: 6px; }}
            QPushButton#clearHistory:hover {{ background: {colors['hover']}; border-radius: 4px; }}
            QPushButton#closedGroup {{ color:{colors['text']}; background:{colors['surface']}; border:none; text-align:left; padding:8px 12px; }}
            QPushButton#closedGroup:hover {{ background:{colors['hover']}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: {colors['background']}; width: 10px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {colors['border']}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {colors['background']}; }}
            QToolButton#deleteHistoryItem {{ color: {colors['muted']}; background: transparent; border: none; font-size: 18px; }}
            QToolButton#deleteHistoryItem:hover {{ color: {colors['text']}; background: {colors['hover']}; }}
        """)
        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(10, 8, 10, 10)
        popup_layout.setSpacing(6)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 4, 0)
        title = QLabel("История")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        clear_button = QPushButton("Очистить")
        clear_button.setObjectName("clearHistory")
        clear_button.clicked.connect(lambda: self.clear_history_popup(popup))
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(clear_button)
        popup_layout.addWidget(header)

        if self.recent_sessions:
            sessions_title = QLabel("Закрытые сессии")
            sessions_title.setStyleSheet(f"color:{colors['muted']}; padding:4px 8px; font-size:12px;")
            popup_layout.addWidget(sessions_title)
            for session in reversed(self.recent_sessions[-3:]):
                tabs = session.get("tabs", [])
                if not tabs:
                    continue
                button = QPushButton(f"{len(tabs)} вкладок  ·  {session.get('saved_at', '')}")
                button.setObjectName("closedGroup")
                button.setFixedHeight(40)
                sites = []
                for record in tabs:
                    url = QUrl(str(record.get("url", "")))
                    sites.append(str(record.get("title") or url.host() or "Grom"))
                button.setToolTip("\n".join(sites[:20]))
                button.clicked.connect(
                    lambda _checked=False, record=dict(session): self.restore_recent_session(record, popup)
                )
                popup_layout.addWidget(button)

        if self.closed_groups:
            groups_title = QLabel("Недавно закрытые группы")
            groups_title.setStyleSheet(f"color:{colors['muted']}; padding:4px 8px; font-size:12px;")
            popup_layout.addWidget(groups_title)
            for group in reversed(self.closed_groups[-3:]):
                button = QPushButton(
                    f"{group.get('name', 'Группа')}  ·  {len(group.get('tabs', []))} вкладок"
                )
                button.setObjectName("closedGroup")
                button.setFixedHeight(40)
                button.setStyleSheet(
                    f"QPushButton#closedGroup {{ border-left:3px solid {group.get('color', '#4f8cff')}; }}"
                )
                button.clicked.connect(
                    lambda _checked=False, record=dict(group): self.restore_closed_group(record, popup)
                )
                popup_layout.addWidget(button)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        if history:
            for item in reversed(history[-100:]):
                history_row = self.create_history_item(item)
                item_button = history_row.open_button
                item_button.clicked.connect(
                    lambda _checked=False, url=item.get("url", ""): self.open_history_url(url, popup)
                )
                item_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                item_button.customContextMenuRequested.connect(
                    lambda pos, button=item_button, data=item: self.show_history_item_menu(
                        button, pos, data, popup
                    )
                )
                history_row.delete_button.clicked.connect(
                    lambda _checked=False, data=dict(item): self.delete_history_item(
                        data, popup
                    )
                )
                content_layout.addWidget(history_row)
        else:
            empty = QLabel("История пока пуста")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #9aa0a6; padding: 40px;")
            content_layout.addWidget(empty)
        content_layout.addStretch()
        scroll.setWidget(content)
        popup_layout.addWidget(scroll)

        self.history_popup = popup
        self.position_popup(popup)
        popup.show()
        popup.raise_()

    def create_history_item(self, item):
        colors = self.theme_colors
        row = QFrame()
        row.setStyleSheet("QFrame { background: transparent; border: none; }")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)
        button = QPushButton()
        button.setObjectName("historyItem")
        button.setFixedHeight(62)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        icon = self.get_cached_icon(item.get("url", ""))
        if not icon.isNull():
            button.setIcon(icon)
            button.setIconSize(QSize(20, 20))
        layout = QVBoxLayout(button)
        layout.setContentsMargins(42, 7, 10, 7)
        layout.setSpacing(2)
        title = QLabel(item.get("title") or item.get("url") or "Без названия")
        title.setStyleSheet(f"font-size: 13px; color: {colors['text']};")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        details = QLabel(f"{QUrl(item.get('url', '')).host()}   {item.get('date', '')}")
        details.setStyleSheet(f"font-size: 11px; color: {colors['muted']};")
        details.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        layout.addWidget(details)
        delete_button = QToolButton()
        delete_button.setObjectName("deleteHistoryItem")
        delete_button.setText("×")
        delete_button.setToolTip("Удалить из истории")
        delete_button.setFixedSize(32, 32)
        row_layout.addWidget(button, 1)
        row_layout.addWidget(delete_button)
        row.open_button = button
        row.delete_button = delete_button
        return row

    def delete_history_item(self, item, popup):
        try:
            with open(self.history_file, "r", encoding="utf-8") as file:
                history = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            history = []
        for index, record in enumerate(history):
            if record == item:
                history.pop(index)
                break
        with open(self.history_file, "w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=2)
        self.history_data = history
        popup.close()
        QTimer.singleShot(0, self.show_history_popup)

    def open_history_url(self, url, popup, new_tab=False):
        popup.close()
        if new_tab:
            self.add_new_tab(QUrl(url))
        elif self.current_browser():
            self.current_browser().setUrl(QUrl(url))

    def show_history_item_menu(self, button, pos, item, popup):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: #292a2d; color: #f1f3f4; border: 1px solid #5f6368; }")
        open_new = menu.addAction("Открыть в новой вкладке")
        delete = menu.addAction("Удалить из истории")
        action = menu.exec(button.mapToGlobal(pos))
        if action == open_new:
            self.open_history_url(item.get("url", ""), popup, True)
        elif action == delete:
            self.delete_history_item(item, popup)

    def clear_history_popup(self, popup):
        self.delete_from_history("__CLEAR_ALL_HISTORY__")
        popup.close()
        QTimer.singleShot(0, self.show_history_popup)

    def setup_shortcuts(self):
        shortcuts = {
            "Ctrl+N": self.launch_new_window,
            "Ctrl+T": lambda: self.add_new_tab(),
            "Ctrl+W": lambda: self.close_current_tab(self.tab_bar.currentIndex()),
            "Ctrl+L": self.focus_url_bar,
            "Ctrl+F": self.show_find_bar,
            "Ctrl+H": self.show_history_popup,
            "Ctrl+J": self.show_downloads_popup,
            "Ctrl+S": self.save_page_snapshot,
            "Ctrl+Shift+S": self.show_screenshot_menu,
            "Ctrl++": lambda: self.change_zoom(10),
            "Ctrl+=": lambda: self.change_zoom(10),
            "Ctrl+-": lambda: self.change_zoom(-10),
            "Ctrl+0": self.reset_zoom,
            "Ctrl+Tab": lambda: self.activate_relative_tab(1),
            "Ctrl+Shift+Tab": lambda: self.activate_relative_tab(-1),
            "Ctrl+Shift+T": self.restore_closed_tab,
            "Ctrl+Shift+A": self.show_tab_search,
            "Ctrl+Shift+N": self.add_private_tab,
            "F9": self.toggle_reader_mode,
            "F8": self.toggle_picture_in_picture,
            "Ctrl+Shift+L": self.translate_browser,
            "F11": self.toggle_app_fullscreen,
            "F12": self.toggle_devtools,
        }
        for sequence, slot in shortcuts.items():
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(slot)
            self.shortcuts.append(shortcut)

        self.fullscreen_escape_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.fullscreen_escape_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.fullscreen_escape_shortcut.activated.connect(self.exit_active_fullscreen)
        self.fullscreen_escape_shortcut.setEnabled(False)
        self.shortcuts.append(self.fullscreen_escape_shortcut)

        previous_match = QShortcut(QKeySequence("Shift+Return"), self.find_input)
        previous_match.setContext(Qt.ShortcutContext.WidgetShortcut)
        previous_match.activated.connect(lambda: self.find_on_page(True))
        self.shortcuts.append(previous_match)

    def bring_to_front(self):
        self.showMaximized()
        self.raise_()
        self.activateWindow()
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.SetForegroundWindow(int(self.winId()))
            except (AttributeError, OSError):
                pass

    def focus_url_bar(self, browser=None, retry=False):
        browser = browser or self.current_browser()
        if browser is not self.current_browser():
            return
        if retry:
            if self.url_bar.hasFocus():
                return
            expected = browser.url().toString() if browser else ""
            if self.url_bar.text() not in ("", expected):
                return
        self.url_bar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.url_bar.selectAll()

    def address_bar_focus_changed(self, focused):
        self.update_address_bar_style(focused)
        if not focused:
            browser = self.current_browser()
            if browser:
                self.url_bar.setText(browser.url().toString())
                self.url_bar.setCursorPosition(0)

    def update_address_bar_style(self, focused=False):
        colors = self.theme_colors
        address_color = colors.get("address", colors["input"])
        border = colors["accent"] if focused else "transparent"
        hover_border = colors["accent"] if focused else colors["border"]
        hover_background = address_color if focused else colors["surface"]
        self.address_frame.setStyleSheet(f"""
            QFrame#addressBar {{
                background: {address_color};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            QFrame#addressBar:hover {{
                background: {hover_background};
                border: 1px solid {hover_border};
            }}
            QFrame#addressBar QPushButton, QFrame#addressBar QToolButton {{
                background: transparent;
                border: none;
                border-radius: 14px;
                padding: 0;
            }}
            QFrame#addressBar QPushButton:hover, QFrame#addressBar QToolButton:hover {{
                background: {colors['button_hover']};
                border-radius: 14px;
            }}
        """)

    def update_navigation_buttons(self):
        browser = self.current_browser()
        can_back = bool(browser and browser.can_go_back())
        can_forward = bool(browser and browser.can_go_forward())
        self.back_btn.setEnabled(can_back)
        self.forward_btn.setEnabled(can_forward)
        back_color = self.theme_colors["icon"] if can_back else self.theme_colors["disabled_icon"]
        forward_color = self.theme_colors["icon"] if can_forward else self.theme_colors["disabled_icon"]
        self.back_btn.setIcon(self.themed_icon("back.png", back_color))
        self.forward_btn.setIcon(self.themed_icon("back.png", forward_color, mirrored=True))

    def reload_current_page(self):
        browser = self.current_browser()
        if browser:
            browser.reload()
        if self.reload_animation and self.reload_animation.state() == QAbstractAnimation.State.Running:
            self.reload_animation.stop()
        animation = QVariantAnimation(self)
        animation.setDuration(520)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.valueChanged.connect(self.update_reload_animation)
        animation.finished.connect(self.finish_reload_animation)
        self.reload_animation = animation
        animation.start()

    def update_reload_animation(self, progress):
        source = self.themed_icon("reload.png", self.theme_colors["icon"]).pixmap(24, 24)
        canvas = QPixmap(24, 24)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scale = 1.0 - 0.18 * math.sin(math.pi * float(progress))
        painter.translate(12, 12)
        painter.rotate(360 * float(progress))
        painter.scale(scale, scale)
        painter.translate(-12, -12)
        painter.drawPixmap(0, 0, source)
        painter.end()
        self.reload_btn.setIcon(QIcon(canvas))

    def finish_reload_animation(self):
        self.reload_btn.setIcon(self.themed_icon("reload.png", self.theme_colors["icon"]))
        if self.reload_animation:
            self.reload_animation.deleteLater()
        self.reload_animation = None

    def activate_relative_tab(self, offset):
        count = self.tab_bar.count()
        if count:
            self.tab_bar.setCurrentIndex((self.tab_bar.currentIndex() + offset) % count)

    def change_zoom(self, delta):
        browser = self.current_browser()
        if not browser:
            return
        current = browser.zoom_percent()
        if delta > 0:
            target = next((value for value in ZOOM_LEVELS if value > current), ZOOM_LEVELS[-1])
        else:
            target = next((value for value in reversed(ZOOM_LEVELS) if value < current), ZOOM_LEVELS[0])
        browser.set_zoom_percent(target)
        self.set_zoom_value_label(f"{browser.zoom_percent()}%")

    def reset_zoom(self):
        browser = self.current_browser()
        if not browser:
            return
        browser.set_zoom_percent(100)
        self.set_zoom_value_label("100%")

    def set_zoom_value_label(self, text):
        label = getattr(self, "zoom_value_label", None)
        if label is None:
            return
        try:
            label.setText(str(text))
        except RuntimeError:
            self.zoom_value_label = None

    def apply_browser_font_scale(self, browser):
        if not browser:
            return
        scale = self.app_settings.get("font_scale", 100)
        if browser.internal_page == "settings" and not self.app_settings.get("font_scale_settings", False):
            scale = 100
        browser.set_font_scale_percent(scale)

    def open_home_page(self):
        browser = self.current_browser()
        if not browser:
            return
        browser.load_internal_html(self.home_page_html(), "grom://home")
        browser._icon = self.brand_icon()
        browser.iconChanged.emit(browser._icon)

    def change_interface_language(self, language):
        language = "en" if str(language).lower().startswith("en") else "ru"
        if language == self.app_settings.get("interface_language", "ru"):
            return
        self.app_settings["interface_language"] = language
        self.save_app_settings()
        set_language(language)
        application = QApplication.instance()
        if not application:
            return
        application.setQuitOnLastWindowClosed(False)
        self.close()

        def restart():
            if getattr(sys, "frozen", False):
                executable = sys.executable
                arguments = sys.argv[1:]
            else:
                executable = sys.executable
                arguments = [os.path.abspath(sys.argv[0]), *sys.argv[1:]]
            QProcess.startDetached(executable, arguments, os.path.dirname(__file__))
            application.quit()

        QTimer.singleShot(600, restart)

    def show_about_developer(self):
        developer = (
            "Ilyin Nikita Nikolaevich N8"
            if get_language() == "en"
            else "Ильин Никита Николаевич N8"
        )
        title = "About Grom Browser" if get_language() == "en" else "О Grom Browser"
        version = "Version" if get_language() == "en" else "Версия"
        role = "Developer" if get_language() == "en" else "Разработчик"
        QMessageBox.about(
            self,
            title,
            f"Grom Browser\n{version}: 1.1.0\n{role}: {developer}",
        )

    def add_private_tab(self):
        browser = self.add_new_tab(label="Приватная вкладка", private=True)
        self.update_tab_title(browser)
        return browser

    def toggle_vertical_tabs(self):
        enabled = not bool(self.app_settings.get("vertical_tabs", False))
        self.app_settings["vertical_tabs"] = enabled
        self.save_app_settings()
        self.update_vertical_tabs_visibility()

    def toggle_reader_mode(self):
        browser = self.current_browser()
        if not browser or browser.internal_page:
            return
        enabled = browser.toggle_reader_mode(self.app_settings.get("reader_font_size", 18))
        QToolTip.showText(
            self.mapToGlobal(QPoint(self.width() // 2, self.navbar.height() + 14)),
            "Режим чтения включён" if enabled else "Режим чтения выключен",
            self,
        )

    def toggle_picture_in_picture(self):
        browser = self.current_browser()
        if browser and not browser.internal_page:
            browser.toggle_picture_in_picture()

    def toggle_ad_blocker(self):
        enabled = not self.app_settings.get("ad_blocker", True)
        self.app_settings["ad_blocker"] = enabled
        extension_state = self.builtin_extension_state()
        extension_state["ad_blocker"] = enabled
        self.app_settings["builtin_extensions"] = extension_state
        self.save_app_settings()
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            for browser in (workspace.primary_browser, workspace.secondary_browser):
                if browser and not browser.internal_page:
                    self.apply_builtin_extensions(browser)
        QToolTip.showText(
            self.mapToGlobal(QPoint(self.width() // 2, self.navbar.height() + 14)),
            "Блокировщик рекламы включён" if enabled else "Блокировщик рекламы выключен",
            self,
        )

    def show_performance_popup(self):
        if self.performance_popup and self.performance_popup.isVisible():
            self.performance_popup.close()
            return
        colors = self.theme_colors
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.prepare_rounded_popup(popup)
        popup.setObjectName("performancePopup")
        popup.setFixedSize(460, min(600, 120 + self.tab_bar.count() * 52))
        popup.setStyleSheet(f"""
            QFrame#performancePopup {{ background:{colors['popup']}; border:1px solid {colors['border']}; border-radius:12px; }}
            QLabel {{ color:{colors['text']}; border:none; }}
            QListWidget {{ color:{colors['text']}; background:transparent; border:none; outline:none; }}
            QListWidget::item {{ min-height:42px; padding:5px; border-bottom:1px solid {colors['border']}; }}
            QListWidget::item:selected {{ background:{colors['surface']}; }}
            QPushButton {{ color:{colors['text']}; background:{colors['surface']}; border:none; border-radius:7px; padding:8px 12px; }}
            QPushButton:hover {{ background:{colors['hover']}; }}
        """)
        layout = QVBoxLayout(popup)
        title = QLabel("Производительность вкладок")
        title.setStyleSheet("font-size:16px;font-weight:600;padding:4px")
        note = QLabel("Память JS, оценка нагрузки CPU и сетевой трафик страницы")
        note.setStyleSheet(f"color:{colors['muted']};padding:0 4px 4px")
        tabs = QListWidget()
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(tabs, 1)
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            browser = workspace.primary_browser
            title_text = browser.title() or "Новая вкладка"
            item = QListWidgetItem(f"{title_text}\nСбор данных…")
            item.setIcon(self.tab_bar.tabIcon(index))
            item.setData(Qt.ItemDataRole.UserRole, id(browser))
            tabs.addItem(item)
            if browser.is_sleeping:
                item.setText(f"{title_text}\nСпящая вкладка · память страницы освобождена")
                continue
            script = """
                (() => {
                    const entries=performance.getEntriesByType('resource');
                    const elapsed=Math.max(1,performance.now()-Number(window.__gromLongTaskStarted||performance.now()));
                    const cpu=Math.min(100,Math.round(Number(window.__gromLongTaskMs||0)*100/elapsed));
                    const network=entries.reduce((sum,item)=>sum+Number(item.transferSize||item.encodedBodySize||0),0);
                    window.__gromLongTaskMs=0; window.__gromLongTaskStarted=performance.now();
                    return JSON.stringify({heap:performance.memory?.usedJSHeapSize||0,nodes:document.getElementsByTagName('*').length,resources:entries.length,network,cpu});
                })()
            """
            browser.runJavaScript(
                script,
                lambda result, row=item, name=title_text: self.update_performance_item(row, name, result),
            )
        refresh = QPushButton("Обновить данные")
        refresh.clicked.connect(lambda: (popup.close(), QTimer.singleShot(0, self.show_performance_popup)))
        terminate = QPushButton("Завершить выбранную вкладку")
        terminate.clicked.connect(lambda: self.terminate_performance_tab(tabs, popup))
        layout.addWidget(terminate)
        layout.addWidget(refresh)
        self.performance_popup = popup
        self.position_popup(popup)
        popup.show()

    def schedule_tab_preview(self, index, global_position):
        self.hide_tab_preview()
        if index < 0 or index >= self.tab_bar.count():
            return
        self._tab_preview_index = index
        self._tab_preview_position = QPoint(global_position)
        self.tab_preview_timer.start()

    def hide_tab_preview(self):
        if hasattr(self, "tab_preview_timer"):
            self.tab_preview_timer.stop()
        popup = getattr(self, "tab_preview_popup", None)
        self.tab_preview_popup = None
        if popup is not None:
            try:
                popup.close()
            except RuntimeError:
                pass

    def show_scheduled_tab_preview(self):
        index = self._tab_preview_index
        if index < 0 or index >= self.tab_bar.count():
            return
        cursor_index = self.tab_bar.tabAt(self.tab_bar.mapFromGlobal(QCursor.pos()))
        if cursor_index != index:
            return
        workspace = self.tab_content.widget(index)
        if not isinstance(workspace, TabWorkspace):
            return
        browser = workspace.primary_browser
        colors = self.theme_colors
        popup = QFrame(
            None,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTransparentForInput,
        )
        popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        popup.setObjectName("tabPreviewPopup")
        popup.setFixedWidth(316)
        popup.setStyleSheet(f"""
            QFrame#tabPreviewPopup {{ background:transparent; border:none; }}
            QFrame#tabPreviewSurface {{
                background:{colors['popup']};
                border:1px solid {colors['border']};
                border-radius:13px;
            }}
            QLabel {{ color:{colors['text']}; border:none; background:transparent; }}
            QLabel#tabPreviewMuted {{ color:{colors['muted']}; }}
        """)
        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        surface = QFrame()
        surface.setObjectName("tabPreviewSurface")
        popup_layout.addWidget(surface)
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)
        preview = QLabel()
        preview.setFixedSize(290, 163)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setStyleSheet(
            f"background:{colors['background']};border:1px solid {colors['border']};border-radius:10px;"
        )
        pixmap = browser.capture_tab_preview()
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                preview.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = max(0, (scaled.width() - preview.width()) // 2)
            y = max(0, (scaled.height() - preview.height()) // 2)
            cropped = scaled.copy(x, y, preview.width(), preview.height())
            rounded = QPixmap(preview.size())
            rounded.fill(Qt.GlobalColor.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            preview_path = QPainterPath()
            preview_path.addRoundedRect(
                QRectF(0.5, 0.5, preview.width() - 1, preview.height() - 1),
                10,
                10,
            )
            painter.setClipPath(preview_path)
            painter.drawPixmap(0, 0, cropped)
            painter.setClipping(False)
            painter.setPen(QPen(QColor(colors["border"]), 1))
            painter.drawPath(preview_path)
            painter.end()
            preview.setStyleSheet("background:transparent;border:none;")
            preview.setPixmap(rounded)
        else:
            preview.setText("Предпросмотр появится после загрузки страницы")
            preview.setWordWrap(True)
        raw_title = browser.title() or self.tab_bar.tabText(index) or "Новая вкладка"
        title = QLabel(QFontMetrics(self.font()).elidedText(
            raw_title, Qt.TextElideMode.ElideRight, 286
        ))
        title.setToolTip(raw_title)
        title.setStyleSheet("font-weight:600;font-size:13px;")
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        raw_address = browser.url().host() or browser.url().toString()
        address = QLabel(QFontMetrics(self.font()).elidedText(
            raw_address, Qt.TextElideMode.ElideMiddle, 286
        ))
        address.setObjectName("tabPreviewMuted")
        memory = QLabel("Память страницы: сбор данных…")
        memory.setObjectName("tabPreviewMuted")
        layout.addWidget(preview)
        layout.addWidget(title)
        layout.addWidget(address)
        layout.addWidget(memory)
        self.tab_preview_popup = popup
        popup.destroyed.connect(
            lambda _object=None, current=popup:
            setattr(self, "tab_preview_popup", None)
            if self.tab_preview_popup is current else None
        )
        tab_rect = self.tab_bar.tabRect(index)
        anchor = self.tab_bar.mapToGlobal(tab_rect.bottomLeft() + QPoint(0, 7))
        screen = self.tab_bar.screen().availableGeometry()
        x = max(screen.left() + 6, min(anchor.x(), screen.right() - popup.width() - 6))
        y = anchor.y()
        popup.adjustSize()
        popup_path = QPainterPath()
        popup_path.addRoundedRect(QRectF(popup.rect()), 13, 13)
        popup.setMask(QRegion(popup_path.toFillPolygon().toPolygon()))
        if y + popup.height() > screen.bottom():
            y = self.tab_bar.mapToGlobal(tab_rect.topLeft()).y() - popup.height() - 7
        popup.move(x, max(screen.top() + 6, y))
        popup.show()
        if browser.is_sleeping:
            memory.setText("Память страницы освобождена · вкладка спит")
        elif browser.has_deferred_navigation():
            memory.setText("Память страницы: вкладка ожидает загрузки")
        else:
            browser.runJavaScript(
                "Number(performance.memory?.usedJSHeapSize || 0)",
                lambda value, label=memory, current_popup=popup:
                self.update_tab_preview_memory(current_popup, label, value),
            )

    def update_tab_preview_memory(self, popup, label, value):
        if popup is not self.tab_preview_popup:
            return
        try:
            amount = int(value or 0)
            label.setText(
                f"Память страницы (JS): {self.human_size(amount)}"
                if amount > 0 else "Память страницы: нет данных"
            )
        except (RuntimeError, TypeError, ValueError):
            pass

    def update_performance_item(self, item, title, result):
        try:
            data = json.loads(result) if result else {}
            heap = self.human_size(int(data.get("heap", 0))) if data.get("heap") else "нет данных"
            network = self.human_size(int(data.get("network", 0)))
            cpu = int(data.get("cpu", 0))
            warning = " · высокая нагрузка" if cpu >= 35 or int(data.get("heap", 0)) >= 500 * 1024 * 1024 else ""
            item.setText(f"{title}\nJS: {heap} · CPU: ~{cpu}% · сеть: {network}{warning}")
        except (RuntimeError, TypeError, ValueError):
            pass

    def terminate_performance_tab(self, tabs, popup):
        item = tabs.currentItem()
        if not item:
            return
        browser_id = item.data(Qt.ItemDataRole.UserRole)
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if isinstance(workspace, TabWorkspace) and id(workspace.primary_browser) == browser_id:
                answer = QMessageBox.question(
                    self,
                    "Завершить вкладку",
                    "Закрыть выбранную вкладку и освободить её ресурсы?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    popup.close()
                    self.close_current_tab(index)
                return

    def install_current_site_app(self):
        browser = self.current_browser()
        if not browser or browser.internal_page:
            current_index = self.tab_bar.currentIndex()
            candidates = sorted(
                range(self.tab_content.count()),
                key=lambda index: abs(index - current_index),
            )
            for index in candidates:
                workspace = self.tab_content.widget(index)
                candidate = workspace.active_browser() if isinstance(workspace, TabWorkspace) else None
                if candidate and not candidate.internal_page and candidate.url().scheme() in ("http", "https"):
                    browser = candidate
                    break
        if not browser or browser.internal_page or browser.url().scheme() not in ("http", "https"):
            QMessageBox.information(self, "Приложение сайта", "Откройте обычный веб-сайт, который хотите закрепить.")
            return
        title = re.sub(r'[<>:"/\\|?*]', "_", browser.title() or browser.url().host() or "Grom Web App").strip()
        desktop = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        shortcut = os.path.join(desktop, f"{title}.lnk")
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        executable = pythonw if os.path.isfile(pythonw) else sys.executable
        script_path = os.path.abspath(__file__)
        def ps_quote(value):
            return str(value).replace("'", "''")
        command = (
            "$w=New-Object -ComObject WScript.Shell;"
            f"$s=$w.CreateShortcut('{ps_quote(shortcut)}');"
            f"$s.TargetPath='{ps_quote(executable)}';"
            f"$s.Arguments='\"{ps_quote(script_path)}\" --app-url \"{ps_quote(browser.url().toString())}\"';"
            f"$s.WorkingDirectory='{ps_quote(os.path.dirname(script_path))}';"
            "$s.Save()"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            QMessageBox.information(self, "Приложение сайта", f"Ярлык создан на рабочем столе:\n{title}")
        except (OSError, subprocess.CalledProcessError):
            QMessageBox.warning(self, "Приложение сайта", "Не удалось создать ярлык сайта.")

    def show_find_bar(self):
        self.find_bar.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def show_tab_search(self):
        if self.tab_search_popup and self.tab_search_popup.isVisible():
            self.tab_search_popup.close()
            return
        colors = self.theme_colors
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.prepare_rounded_popup(popup)
        popup.setObjectName("tabSearchPopup")
        popup.setFixedSize(600, 460)
        popup.setStyleSheet(f"""
            QFrame#tabSearchPopup {{ background:{colors['popup']}; border:1px solid {colors['border']}; border-radius:12px; }}
            QLabel {{ color:{colors['text']}; border:none; }}
            QLineEdit {{ color:{colors['text']}; background:{colors['input']}; border:1px solid {colors['border']}; border-radius:7px; padding:9px 12px; }}
            QLineEdit:focus {{ border-color:{colors['accent']}; }}
            QListWidget {{ color:{colors['text']}; background:transparent; border:none; outline:none; }}
            QListWidget::item {{ padding:10px 8px; border-bottom:1px solid {colors['border']}; }}
            QListWidget::item:hover {{ background:{colors['hover']}; }}
            QListWidget::item:selected {{ background:{colors['surface']}; color:{colors['text']}; }}
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(9)
        title = QLabel("Поиск по открытым вкладкам")
        title.setStyleSheet("font-size:17px;font-weight:650;")
        search = QLineEdit()
        search.setPlaceholderText("Название сайта или адрес")
        results = QListWidget()
        results.setIconSize(QSize(20, 20))
        layout.addWidget(title)
        layout.addWidget(search)
        layout.addWidget(results, 1)
        self.tab_search_popup = popup
        self.tab_search_input = search
        self.tab_search_results = results
        search.textChanged.connect(self.refresh_tab_search_results)
        search.returnPressed.connect(self.activate_tab_search_result)
        results.itemActivated.connect(self.activate_tab_search_result)
        self.refresh_tab_search_results("")
        origin = self.mapToGlobal(QPoint(0, 0))
        x = origin.x() + max(12, (self.width() - popup.width()) // 2)
        y = origin.y() + self.tabs_panel.height() + 12
        popup.move(x, y)
        popup.show()
        popup.raise_()
        search.setFocus()

    def refresh_tab_search_results(self, query=""):
        results = getattr(self, "tab_search_results", None)
        if not results:
            return
        needle = str(query).strip().casefold()
        results.clear()
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            browser = workspace.primary_browser
            title = browser.title() or self.tab_bar.tabText(index) or "Новая вкладка"
            url = browser.url().toString()
            host = browser.url().host() or url
            if needle and needle not in f"{title} {url}".casefold():
                continue
            item = QListWidgetItem(browser.icon(), f"{title}\n{host}")
            item.setData(Qt.ItemDataRole.UserRole, index)
            results.addItem(item)
        if results.count():
            results.setCurrentRow(0)

    def activate_tab_search_result(self, item=None):
        results = getattr(self, "tab_search_results", None)
        if not results:
            return
        selected = item if isinstance(item, QListWidgetItem) else results.currentItem()
        if not selected:
            return
        index = int(selected.data(Qt.ItemDataRole.UserRole))
        if 0 <= index < self.tab_bar.count():
            self.tab_bar.setCurrentIndex(index)
        if self.tab_search_popup:
            self.tab_search_popup.close()

    def show_screenshot_menu(self):
        browser = self.current_browser()
        if not browser or browser.internal_page:
            QMessageBox.information(self, "Скриншот", "Откройте веб-страницу для создания скриншота.")
            return
        colors = self.theme_colors
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{colors['popup']}; color:{colors['text']}; border:1px solid {colors['border']}; border-radius:9px; padding:5px; }}
            QMenu::item {{ padding:9px 26px; }}
            QMenu::item:selected {{ background:{colors['hover']}; }}
        """)
        visible = menu.addAction("Видимая область")
        full = menu.addAction("Вся страница")
        selected = menu.exec(QCursor.pos())
        if selected == visible:
            self.capture_visible_page()
        elif selected == full:
            self.capture_full_page()

    def grab_browser_surface(self, browser):
        screen = QGuiApplication.screenAt(browser.container.mapToGlobal(browser.container.rect().center())) or self.screen()
        position = browser.container.mapToGlobal(QPoint(0, 0))
        pixmap = screen.grabWindow(
            0, position.x(), position.y(), browser.container.width(), browser.container.height()
        )
        if not pixmap.isNull() and pixmap.width() > 1 and pixmap.height() > 1:
            return pixmap
        return screen.grabWindow(int(self.winId()), 0, 0, browser.container.width(), browser.container.height())

    def screenshot_path(self, title):
        pictures = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        folder = os.path.join(pictures or os.path.expanduser("~"), "Grom Screenshots")
        os.makedirs(folder, exist_ok=True)
        safe = re.sub(r'[^\w\-. ]+', "_", title or "page", flags=re.UNICODE).strip(" ._")[:80]
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        suggested = os.path.join(folder, f"{safe or 'page'}_{stamp}.png")
        path, _selected_filter = QFileDialog.getSaveFileName(
            self, "Сохранить скриншот", suggested, "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        return path

    def save_screenshot_image(self, image, title):
        path = self.screenshot_path(title)
        if not path:
            return
        extension = os.path.splitext(path)[1].lower()
        image_format = "JPG" if extension in (".jpg", ".jpeg") else "PNG"
        if not image.save(path, image_format, 95):
            QMessageBox.warning(self, "Скриншот", "Не удалось сохранить изображение.")
            return
        QMessageBox.information(self, "Скриншот", f"Скриншот сохранён:\n{path}")

    def capture_visible_page(self):
        browser = self.current_browser()
        if not browser:
            return
        pixmap = self.grab_browser_surface(browser)
        if pixmap.isNull():
            QMessageBox.warning(self, "Скриншот", "Не удалось получить изображение страницы.")
            return
        self.save_screenshot_image(pixmap.toImage(), browser.title() or browser.url().host())

    def capture_full_page(self):
        browser = self.current_browser()
        if not browser:
            return
        browser.runJavaScript(
            "JSON.stringify({width:Math.max(document.documentElement.scrollWidth,document.body?.scrollWidth||0),"
            "height:Math.max(document.documentElement.scrollHeight,document.body?.scrollHeight||0),"
            "viewWidth:window.innerWidth,viewHeight:window.innerHeight,x:window.scrollX,y:window.scrollY})",
            lambda value, source=browser: self.start_full_page_capture(source, value),
        )

    def start_full_page_capture(self, browser, metrics_value):
        if browser != self.current_browser():
            return
        try:
            metrics = json.loads(metrics_value or "{}")
            width = max(1, int(metrics["width"]))
            height = max(1, int(metrics["height"]))
            view_width = max(1, int(metrics["viewWidth"]))
            view_height = max(1, int(metrics["viewHeight"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            QMessageBox.warning(self, "Скриншот", "Страница не сообщила размер содержимого.")
            return
        first = self.grab_browser_surface(browser)
        if first.isNull():
            return
        scale_x = first.width() / view_width
        scale_y = first.height() / view_height
        output_width = round(width * scale_x)
        output_height = round(height * scale_y)
        if output_width * output_height > 120_000_000 or output_width > 30000 or output_height > 30000:
            QMessageBox.warning(self, "Скриншот", "Страница слишком большая для одного изображения.")
            return
        x_positions = list(range(0, width, view_width))
        y_positions = list(range(0, height, view_height))
        state = {
            "browser": browser,
            "image": QImage(output_width, output_height, QImage.Format.Format_RGB32),
            "tiles": [(x, y) for y in y_positions for x in x_positions],
            "scale_x": scale_x,
            "scale_y": scale_y,
            "old_x": int(metrics.get("x", 0)),
            "old_y": int(metrics.get("y", 0)),
            "title": browser.title() or browser.url().host(),
        }
        state["image"].fill(QColor("white"))
        self._capture_next_full_page_tile(state)

    def _capture_next_full_page_tile(self, state):
        browser = state["browser"]
        if browser != self.current_browser() or not state["tiles"]:
            if browser == self.current_browser():
                browser.runJavaScript(f"window.scrollTo({state['old_x']},{state['old_y']})")
                self.save_screenshot_image(state["image"], state["title"])
            return
        x, y = state["tiles"].pop(0)
        browser.runJavaScript(
            f"window.scrollTo({x},{y});JSON.stringify([window.scrollX,window.scrollY])",
            lambda actual, capture_state=state: QTimer.singleShot(
                160, lambda: self._capture_full_page_tile(capture_state, actual)
            ),
        )

    def _capture_full_page_tile(self, state, actual_value):
        browser = state["browser"]
        if browser != self.current_browser():
            return
        try:
            actual_x, actual_y = json.loads(actual_value or "[0,0]")
        except (TypeError, ValueError, json.JSONDecodeError):
            actual_x, actual_y = 0, 0
        tile = self.grab_browser_surface(browser).toImage()
        painter = QPainter(state["image"])
        painter.drawImage(
            QPoint(round(float(actual_x) * state["scale_x"]), round(float(actual_y) * state["scale_y"])),
            tile,
        )
        painter.end()
        self._capture_next_full_page_tile(state)

    def close_find_bar(self):
        browser = self.current_browser()
        if browser:
            browser.clear_find()
        self.find_status.clear()
        self.find_bar.hide()
        if browser:
            browser.setFocus()

    def find_query_changed(self, text):
        if text:
            self.find_on_page(False)
        else:
            self.find_status.clear()
            browser = self.current_browser()
            if browser:
                browser.clear_find()

    def find_on_page(self, backward=False):
        browser = self.current_browser()
        query = self.find_input.text()
        if not browser or not query:
            return
        browser.find_text(
            query,
            backward,
            lambda found: self.find_status.setText("Найдено" if found else "Нет совпадений"),
        )

    # --- ЛОГИКА DROP (СМЕНА ПОРЯДКА ЗАКЛАДОК) ---
    def on_bookmark_drop(self, e):
        url = e.mimeData().text(); pos_x = e.pos().x()
        target = next((b for b in self.bookmarks if b["url"] == url), None)
        if not target: return
        new_idx = 0
        for i in range(self.bookmarks_layout.count() - 1):
            widget = self.bookmarks_layout.itemAt(i).widget()
            if pos_x > widget.pos().x() + widget.width() / 2: new_idx = i + 1
        self.bookmarks.remove(target); self.bookmarks.insert(min(new_idx, len(self.bookmarks)), target)
        self.refresh_bookmarks_ui(); self.save_bookmarks()

    def refresh_bookmarks_ui(self):
        for i in reversed(range(self.bookmarks_layout.count() - 1)):
            widget = self.bookmarks_layout.itemAt(i).widget()
            if widget: self.bookmarks_layout.removeWidget(widget)
        for b in self.bookmarks:
            self.bookmarks_layout.insertWidget(self.bookmarks_layout.count() - 1, b["button"])

    # --- ЛОГИКА ЗАКЛАДОК ---
    def toggle_bookmark(self):
        curr = self.current_browser()
        if not curr: return
        url = curr.url().toString()
        existing = next((b for b in self.bookmarks if b["url"] == url), None)
        if existing: self.remove_bookmark(url)
        else: self.show_bookmark_dialog()
    
    def show_bookmark_dialog(self):
        current_browser = self.current_browser()
        url, title = current_browser.url().toString(), current_browser.title()
        dialog = QDialog(self); dialog.setWindowTitle("Добавить в избранное"); dialog.setFixedSize(400, 150)
        dialog.setStyleSheet("QDialog { background-color: #1e1e1e; } QLabel { color: white; } QLineEdit { background: #2d2d2d; color: white; padding: 5px; } QPushButton { background: #2d2d2d; color: white; padding: 8px; }")
        layout = QVBoxLayout(dialog); name_input = QLineEdit(); name_input.setText(title); layout.addWidget(QLabel("Название:")); layout.addWidget(name_input)
        btns = QHBoxLayout(); save = QPushButton("Сохранить"); cancel = QPushButton("Отмена")
        save.clicked.connect(lambda: (self.add_bookmark(url, name_input.text(), current_browser.icon()), dialog.accept()))
        cancel.clicked.connect(dialog.reject); btns.addWidget(save); btns.addWidget(cancel); layout.addLayout(btns)
        dialog.exec()
    
    def add_bookmark(self, url, name, icon):
        bookmark = {"url": url, "name": name}
        btn = DraggableBookmark(url, name, icon)
        btn.apply_theme(self.theme_colors)
        btn.customContextMenuRequested.connect(lambda pos: self.show_bookmark_menu(pos, btn, url, name))
        btn.clicked.connect(lambda: self.current_browser().setUrl(QUrl(url)) if self.current_browser() else None)
        bookmark["button"] = btn
        self.bookmarks.append(bookmark)
        self.bookmarks_layout.insertWidget(self.bookmarks_layout.count() - 1, btn)
        self.bookmarks_panel.setVisible(self.app_settings.get("show_bookmarks_bar", True))
        
        # Сохраняем иконку в кеш
        self.save_icon_to_cache(url, icon)
        
        self.save_bookmarks()
        self.refresh_home_pages()

    def show_bookmark_menu(self, pos, btn, url, name):
        colors = self.theme_colors
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {colors['popup']}; color: {colors['text']}; border: 1px solid {colors['border']}; border-radius:9px; padding: 5px; }}
            QMenu::item {{ padding: 8px 24px; border-radius: 5px; }}
            QMenu::item:selected {{ background: {colors['hover']}; }}
        """)
        delete_action = menu.addAction("Удалить")
        if menu.exec(btn.mapToGlobal(pos)) == delete_action:
            self.remove_bookmark(url)

    def remove_bookmark(self, url):
        for i, b in enumerate(self.bookmarks):
            if b["url"] == url:
                if "button" in b: b["button"].deleteLater()
                self.bookmarks.pop(i)
                # Очищаем иконку из кеша
                self.clear_icon_cache_for_url(url)
                break
        self.save_bookmarks()
        if not self.bookmarks: self.bookmarks_panel.setVisible(False)
        self.refresh_home_pages()

    def save_bookmarks(self):
        data = [{"url": b["url"], "name": b["name"]} for b in self.bookmarks]
        with open(self.bookmarks_file, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        self._address_suggestion_entries = None

    def load_bookmarks(self):
        if not os.path.exists(self.bookmarks_file): return
        try:
            with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                for b_data in json.load(f):
                    # Загружаем иконку из кеша
                    cached_icon = self.get_cached_icon(b_data["url"])
                    btn = self.create_bookmark_button(b_data["url"], b_data["name"], cached_icon if not cached_icon.isNull() else None)
                    b_data["button"] = btn
                    self.bookmarks.append(b_data)
                    self.bookmarks_layout.insertWidget(self.bookmarks_layout.count() - 1, btn)
            self.bookmarks_panel.setVisible(
                len(self.bookmarks) > 0 and self.app_settings.get("show_bookmarks_bar", True)
            )
        except: pass

    def create_bookmark_button(self, url, name, icon=None):
        btn = DraggableBookmark(url, name, icon)
        btn.apply_theme(self.theme_colors)
        btn.customContextMenuRequested.connect(lambda pos: self.show_bookmark_menu(pos, btn, url, name))
        btn.clicked.connect(lambda: self.current_browser().setUrl(QUrl(url)) if self.current_browser() else None)
        return btn

    def show_tab_context_menu(self, index, global_pos):
        workspace = self.tab_content.widget(index)
        if not isinstance(workspace, TabWorkspace):
            return
        colors = self.theme_colors
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{colors['popup']}; color:{colors['text']}; border:1px solid {colors['border']}; border-radius:9px; padding:5px; }}
            QMenu::item {{ padding:8px 24px; }}
            QMenu::item:selected {{ background:{colors['hover']}; }}
        """)
        browser = workspace.primary_browser
        close_action = menu.addAction("Закрыть вкладку")
        close_action.setEnabled(self.tab_bar.count() > 1)
        duplicate_action = menu.addAction(
            "\u0414\u0443\u0431\u043b\u0438\u0440\u043e\u0432\u0430\u0442\u044c "
            "\u0432\u043a\u043b\u0430\u0434\u043a\u0443"
        )
        sleep_action = menu.addAction("Разбудить вкладку" if browser.is_sleeping else "Перевести вкладку в сон")
        sleep_action.setEnabled(browser.is_sleeping or index != self.tab_bar.currentIndex())
        menu.addSeparator()
        new_group = menu.addAction("Новая группа…")
        groups_menu = menu.addMenu("Добавить в группу")
        group_actions = {}
        for group_id, group in self.tab_groups.items():
            action = groups_menu.addAction(group.get("name", "Группа"))
            group_actions[action] = group_id
        groups_menu.setEnabled(bool(group_actions))
        remove_group = menu.addAction("Убрать из группы")
        remove_group.setEnabled(bool(workspace.group_id))

        rename_group = change_color = delete_group = None
        if workspace.group_id in self.tab_groups:
            menu.addSeparator()
            rename_group = menu.addAction("Переименовать группу…")
            change_color = menu.addAction("Изменить цвет группы…")
            delete_group = menu.addAction("Удалить группу и вкладки")

        selected = menu.exec(global_pos)
        if selected == close_action:
            self.close_current_tab(index)
        elif selected == duplicate_action:
            self.duplicate_tab(index)
        elif selected == sleep_action:
            self.wake_tab(index) if browser.is_sleeping else self.sleep_tab(index)
        elif selected == new_group:
            self.create_tab_group(index)
        elif selected in group_actions:
            workspace.group_id = group_actions[selected]
            self.refresh_tab_groups()
            self.save_open_session()
        elif selected == remove_group:
            workspace.group_id = None
            self.refresh_tab_groups()
            self.save_open_session()
        elif selected == rename_group:
            self.rename_tab_group(workspace.group_id)
        elif selected == change_color:
            self.change_tab_group_color(workspace.group_id)
        elif selected == delete_group:
            self.delete_tab_group(workspace.group_id)

    def duplicate_tab(self, index):
        if index < 0 or index >= self.tab_content.count():
            return
        source_workspace = self.tab_content.widget(index)
        record = self.tab_record(index)
        if not isinstance(source_workspace, TabWorkspace) or not record:
            return
        browser = self.restore_tab_record(record)
        if not browser:
            return
        duplicate_workspace = self.workspace_for_browser(browser)
        if duplicate_workspace:
            duplicate_workspace.group_id = source_workspace.group_id
        new_index = self.tab_index_for_browser(browser)
        target_index = min(index + 1, self.tab_bar.count() - 1)
        if new_index >= 0 and new_index != target_index:
            self.tab_bar.moveTab(new_index, target_index)
        self.tab_bar.setCurrentIndex(target_index)
        self.refresh_tab_groups()
        self.save_open_session()

    def create_tab_group(self, index):
        name, accepted = QInputDialog.getText(self, "Новая группа", "Название группы:")
        if not accepted or not name.strip():
            return
        color = QColorDialog.getColor(QColor("#4f8cff"), self)
        if not color.isValid():
            return
        group_id = uuid.uuid4().hex[:10]
        self.tab_groups[group_id] = {
            "name": name.strip(),
            "color": color.name(),
        }
        workspace = self.tab_content.widget(index)
        if isinstance(workspace, TabWorkspace):
            workspace.group_id = group_id
        self.refresh_tab_groups()
        self.save_open_session()

    def rename_tab_group(self, group_id):
        group = self.tab_groups.get(group_id)
        if not group:
            return
        name, accepted = QInputDialog.getText(
            self, "Переименовать группу", "Название группы:", text=group.get("name", "")
        )
        if accepted and name.strip():
            group["name"] = name.strip()
            self.refresh_tab_groups()
            self.save_open_session()

    def change_tab_group_color(self, group_id):
        group = self.tab_groups.get(group_id)
        if not group:
            return
        color = QColorDialog.getColor(QColor(group.get("color", "#4f8cff")), self, "Цвет группы")
        if color.isValid():
            group["color"] = color.name()
            self.refresh_tab_groups()
            self.save_open_session()

    def delete_tab_group(self, group_id):
        group = self.tab_groups.get(group_id)
        if not group:
            return
        indexes = []
        records = []
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if isinstance(workspace, TabWorkspace) and workspace.group_id == group_id:
                indexes.append(index)
                record = self.tab_record(index)
                if record:
                    records.append(record)
        if records:
            self.closed_groups.append({
                "id": uuid.uuid4().hex[:10],
                "name": group.get("name", "Группа"),
                "color": group.get("color", "#4f8cff"),
                "tabs": records,
                "closed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            self.save_closed_groups()
        self._restoring_session = True
        try:
            for index in reversed(indexes):
                widget = self.tab_content.widget(index)
                self.tab_content.removeWidget(widget)
                widget.deleteLater()
                self.tab_bar.removeTab(index)
        finally:
            self._restoring_session = False
        self.tab_groups.pop(group_id, None)
        if not self.tab_bar.count():
            self.add_new_tab(label="Grom")
        self.refresh_tab_groups()
        self.save_open_session()

    def restore_closed_group(self, group_record, popup=None):
        if popup:
            popup.close()
        group_id = uuid.uuid4().hex[:10]
        self.tab_groups[group_id] = {
            "name": group_record.get("name", "Группа"),
            "color": group_record.get("color", "#4f8cff"),
        }
        last_index = -1
        self._restoring_session = True
        try:
            for record in group_record.get("tabs", []):
                browser = self.restore_tab_record(record)
                if not browser:
                    continue
                workspace = self.workspace_for_browser(browser)
                if workspace:
                    workspace.group_id = group_id
                    last_index = self.tab_content.indexOf(workspace)
        finally:
            self._restoring_session = False
        self.closed_groups = [item for item in self.closed_groups if item.get("id") != group_record.get("id")]
        self.save_closed_groups()
        self.refresh_tab_groups()
        if last_index >= 0:
            self.tab_bar.setCurrentIndex(last_index)
        self.save_open_session()

    def refresh_tab_groups(self):
        group_colors = {}
        sleeping_tabs = set()
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            group = self.tab_groups.get(workspace.group_id)
            if group:
                group_colors[index] = group.get("color", "#4f8cff")
            if workspace.primary_browser.is_sleeping:
                sleeping_tabs.add(index)
            self.update_tab_title(workspace.primary_browser, sync_vertical=False)
        self.tab_bar.set_group_colors(group_colors)
        self.tab_bar.set_sleeping_tabs(sleeping_tabs)
        self.sync_vertical_tabs()

    def update_sleeping_tabs(self):
        sleeping = set()
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if isinstance(workspace, TabWorkspace) and workspace.primary_browser.is_sleeping:
                sleeping.add(index)
        self.tab_bar.set_sleeping_tabs(sleeping)

    def sleep_tab(self, index):
        if index == self.tab_bar.currentIndex():
            return
        workspace = self.tab_content.widget(index)
        if isinstance(workspace, TabWorkspace) and workspace.primary_browser.sleep_page():
            self.update_tab_title(workspace.primary_browser)
            self.update_sleeping_tabs()
            self.save_open_session()

    def wake_tab(self, index):
        workspace = self.tab_content.widget(index)
        if isinstance(workspace, TabWorkspace) and workspace.primary_browser.wake_page():
            workspace.last_active = time.time()
            self.update_tab_title(workspace.primary_browser)
            self.update_sleeping_tabs()

    def sleep_inactive_tabs(self):
        if not self.app_settings.get("memory_saver", True):
            return
        timeout = max(1, int(self.app_settings.get("sleep_minutes", 15))) * 60
        now = time.time()
        current = self.tab_bar.currentIndex()
        for index in range(self.tab_content.count()):
            if index == current:
                continue
            workspace = self.tab_content.widget(index)
            if (
                isinstance(workspace, TabWorkspace)
                and not workspace.is_split()
                and now - workspace.last_active >= timeout
            ):
                self.sleep_tab(index)

    def run_periodic_tab_maintenance(self):
        self.sleep_inactive_tabs()
        self.monitor_resource_heavy_tabs()

    def monitor_resource_heavy_tabs(self):
        script = """
            (() => {
                const entries=performance.getEntriesByType('resource');
                const elapsed=Math.max(1,performance.now()-Number(window.__gromLongTaskStarted||performance.now()));
                const cpu=Math.min(100,Math.round(Number(window.__gromLongTaskMs||0)*100/elapsed));
                const network=entries.reduce((sum,item)=>sum+Number(item.transferSize||item.encodedBodySize||0),0);
                return JSON.stringify({heap:performance.memory?.usedJSHeapSize||0,cpu,network});
            })()
        """
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            browser = workspace.primary_browser
            if browser.is_sleeping or browser.has_deferred_navigation() or browser.internal_page:
                continue
            browser.runJavaScript(
                script,
                lambda result, target=browser: self.record_tab_resource_sample(target, result),
            )

    def record_tab_resource_sample(self, browser, result):
        if self.tab_index_for_browser(browser) < 0:
            return
        try:
            data = json.loads(result) if result else {}
            heap = int(data.get("heap", 0))
            cpu = int(data.get("cpu", 0))
            network = int(data.get("network", 0))
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        reasons = []
        if heap >= 500 * 1024 * 1024:
            reasons.append(f"JS-память {self.human_size(heap)}")
        if cpu >= 35:
            reasons.append(f"нагрузка CPU ~{cpu}%")
        if network >= 750 * 1024 * 1024:
            reasons.append(f"сеть {self.human_size(network)}")
        browser._resource_warning = ", ".join(reasons)
        index = self.tab_index_for_browser(browser)
        if index >= 0:
            base = browser.title() or browser.url().host() or "Вкладка"
            tooltip = base
            if reasons:
                tooltip += "\nВысокое потребление: " + browser._resource_warning
            self.tab_bar.setTabToolTip(index, tooltip)

    # --- ЛОГИКА ВКЛАДОК ---
    def add_new_tab(
        self,
        qurl=None,
        label="New Tab",
        internal_html=None,
        internal_url="grom://settings/profiles",
        private=False,
        defer_navigation=False,
        popup_id="",
        popup_opener=None,
    ):
        first_tab = self.tab_bar.count() == 0
        focus_address = qurl is None and internal_html is None and not popup_id
        if self.tab_bar.count() and not self._restoring_session:
            self.dismiss_restore_prompt_on_activity()
        if qurl is None and internal_html is None:
            qurl = self.default_start_url()
            if qurl.toString() == "grom://home":
                internal_html = self.home_page_html()
                internal_url = "grom://home"
                label = "Grom"
                qurl = None
        browser = BrowserWebView(private=private)
        browser._focus_address_requested = focus_address
        if popup_id:
            browser.set_popup_context(popup_id, popup_opener)
        browser.set_fallback_title(label)
        browser.set_zoom_percent(self.app_settings.get("default_zoom", 100))
        browser.set_permission_policy(self.permission_policy_for_url(qurl or QUrl(internal_url)))
        browser.set_placeholder_color(self.theme_colors["background"])
        workspace = TabWorkspace(browser)
        workspace.splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {self.theme_colors['border']}; }}"
        )
        workspace.activeBrowserChanged.connect(
            lambda active, current_workspace=workspace: self.active_browser_changed(
                current_workspace, active
            )
        )
        self.connect_browser(browser, workspace, primary=True)
        self.tab_content.addWidget(workspace)
        idx = self.tab_bar.addTab(label)
        close_button = self.tab_bar.tabButton(idx, QTabBar.ButtonPosition.RightSide)
        if isinstance(close_button, TabCloseButton):
            close_button.set_line_color(
                self.theme_colors["muted"], self.theme_colors["text"]
            )
        self.tab_bar.setCurrentIndex(idx)
        self.tab_content.setCurrentWidget(workspace)
        if internal_html is not None:
            browser.load_internal_html(internal_html, internal_url)
            browser._icon = self.internal_page_icon(browser)
            browser.iconChanged.emit(browser._icon)
        elif defer_navigation:
            browser.set_deferred_url(qurl)
        else:
            browser.setUrl(qurl)
        self.apply_browser_font_scale(browser)
        if not self._restoring_session:
            QTimer.singleShot(250, self.save_open_session)
            if focus_address:
                QTimer.singleShot(
                    0, lambda current=browser: self.focus_url_bar(current)
                )
                QTimer.singleShot(
                    420,
                    lambda current=browser: self.focus_url_bar(
                        current, retry=True
                    ),
                )
                if first_tab:
                    QTimer.singleShot(
                        900,
                        lambda current=browser: self.focus_url_bar(
                            current, retry=True
                        ),
                    )
        self.sync_vertical_tabs()
        QTimer.singleShot(0, self.update_browser_polling)
        return browser

    def connect_browser(self, browser, workspace, primary=False):
        browser.activated.connect(
            lambda b=browser, w=workspace: self.browser_activated(w, b)
        )
        browser.urlChanged.connect(lambda url, b=browser: self.browser_url_changed(b, url))
        browser.fullScreenChanged.connect(
            lambda enabled, source=browser: self.handle_fullscreen(source, enabled)
        )
        browser.zoomChanged.connect(
            lambda percent, b=browser: self.update_zoom_display(b, percent)
        )
        browser.settingsChanged.connect(
            lambda state, source=browser:
            self.apply_settings_from_page(state)
            if source.internal_page == "settings" else None
        )
        browser.downloadRequested.connect(
            lambda download, source=browser: self.start_download(download, source.url())
        )
        browser.browserCommand.connect(
            lambda command, source=browser: self.handle_browser_command(command, source)
        )
        browser.consoleMessages.connect(
            lambda messages, source=browser: self.receive_console_messages(source, messages)
        )
        browser.passwordSubmitted.connect(
            lambda credentials, source=browser: self.handle_password_submission(source, credentials)
        )
        browser.languageDetected.connect(
            lambda language, source=browser: self.browser_language_detected(source, language)
        )
        if primary:
            browser.loadStarted.connect(lambda b=browser: self.start_tab_loading(b))
        browser.loadFinished.connect(
            lambda success, b=browser, p=primary: self.browser_load_finished(
                b, p, success
            )
        )
        if primary:
            browser.iconChanged.connect(
                lambda icon, b=browser: self.sync_icons(b, icon)
            )

    def browser_activated(self, workspace, browser):
        workspace.set_active_browser(browser)
        self.dismiss_restore_prompt_on_activity()

    def browser_load_finished(self, browser, primary, success):
        if primary:
            self.stop_tab_loading(browser)
        if not success:
            return
        if getattr(browser, "_focus_address_requested", False):
            browser._focus_address_requested = False
            QTimer.singleShot(
                0, lambda current=browser: self.focus_url_bar(
                    current, retry=True
                )
            )
        if browser.isVisible():
            QTimer.singleShot(500, browser.capture_tab_preview)
        self.apply_browser_font_scale(browser)
        if not browser.internal_page:
            self.apply_builtin_extensions(browser)
            browser.detect_language()
            self.autofill_browser_login(browser)
        if primary:
            self.update_tab_title(browser)
            if self.app_mode:
                self.setWindowTitle(browser.title() or browser.url().host() or "Grom")
            if browser.internal_page:
                browser._icon = self.internal_page_icon(browser)
                browser.iconChanged.emit(browser._icon)
        if not browser.internal_page and not browser.is_private:
            current_url = browser.url().toString()
            if current_url != browser._last_history_url:
                self.save_to_history(current_url, browser.title())
                browser._last_history_url = current_url
        if primary:
            self.save_open_session()
        if browser == self.current_browser():
            QTimer.singleShot(0, self.update_navigation_buttons)
            QTimer.singleShot(250, self.update_navigation_buttons)

    def browser_url_changed(self, browser, url):
        if url.scheme().lower() == "grom" and not browser.internal_page:
            browser.setUrl(QUrl("about:blank"))
            return
        if url.scheme().lower() in ("http", "https"):
            self.check_navigation_safety(browser, url)
        host = url.host().lower()
        is_translation_url = "translate.google" in host or host.endswith(".translate.goog")
        if (
            browser.translation_source_url
            and not is_translation_url
            and url.toString() != browser.translation_source_url
        ):
            browser.translation_source_url = ""
            browser.translation_language = ""
        browser.set_permission_policy(self.permission_policy_for_url(url))
        self.update_url(url, browser)
        if browser == self.current_browser():
            self.update_translation_button()
            QTimer.singleShot(0, self.update_navigation_buttons)
            QTimer.singleShot(200, self.update_navigation_buttons)

    def suspicious_url_reasons(self, url):
        host = url.host().lower().strip(".")
        reasons = []
        if url.userInfo():
            reasons.append("адрес содержит скрытые данные пользователя")
        if host.startswith("xn--") or ".xn--" in host:
            reasons.append("домен использует Punycode и может имитировать знакомое имя")
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
            reasons.append("вместо домена используется IP-адрес")
        suspicious_words = ("login", "signin", "verify", "secure", "account", "wallet", "bank")
        if sum(word in host for word in suspicious_words) >= 2 and host.count("-") >= 2:
            reasons.append("домен похож на адрес страницы для кражи учётных данных")
        return reasons

    def check_navigation_safety(self, browser, url):
        if not self.app_settings.get("safe_browsing_enabled", True):
            return
        address = url.toString().split("#", 1)[0]
        if address in self.url_safety_bypass:
            return
        reasons = self.suspicious_url_reasons(url)
        if reasons:
            self.show_unsafe_navigation_warning(browser, url, "\n".join(reasons))
            return
        api_key = str(self.app_settings.get("safe_browsing_api_key", "")).strip()
        if not api_key or address in self.url_safety_cache:
            return
        self.url_safety_cache[address] = "pending"
        endpoint = QUrl("https://safebrowsing.googleapis.com/v4/threatMatches:find")
        query = QUrlQuery()
        query.addQueryItem("key", api_key)
        endpoint.setQuery(query)
        request = QNetworkRequest(endpoint)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        payload = {
            "client": {"clientId": "grom-browser", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": address}],
            },
        }
        reply = self.download_network.post(request, QByteArray(json.dumps(payload).encode("utf-8")))
        reply.finished.connect(
            lambda current=reply, target=browser, checked=QUrl(url), key=address:
            self.finish_url_safety_check(current, target, checked, key)
        )

    def finish_url_safety_check(self, reply, browser, url, cache_key):
        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8", "replace"))
        except (json.JSONDecodeError, TypeError, ValueError):
            data = {}
        reply.deleteLater()
        matches = data.get("matches", []) if isinstance(data, dict) else []
        self.url_safety_cache[cache_key] = "unsafe" if matches else "safe"
        if matches and browser.url().toString().split("#", 1)[0] == cache_key:
            threats = sorted({str(item.get("threatType", "угроза")) for item in matches if isinstance(item, dict)})
            self.show_unsafe_navigation_warning(browser, url, "Safe Browsing: " + ", ".join(threats))

    def show_unsafe_navigation_warning(self, browser, url, reason):
        address = url.toString().split("#", 1)[0]
        if address in self.url_safety_bypass:
            return
        browser.stop()
        answer = QMessageBox.warning(
            self,
            "Подозрительный сайт",
            f"Grom остановил переход на:\n{url.host()}\n\n{reason}\n\nПродолжить на свой риск?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.url_safety_bypass.add(address)
            browser.setUrl(url)
        elif browser.can_go_back():
            browser.back()
        else:
            browser.load_internal_html(self.home_page_html(), "grom://home")

    def handle_password_submission(self, browser, credentials):
        if (
            self.guest_mode
            or not self.app_settings.get("password_manager", False)
            or not self.app_settings.get("offer_save_passwords", True)
        ):
            return
        origin_url = QUrl(str(credentials.get("origin", "")))
        if not origin_url.isValid() or origin_url.scheme() not in ("http", "https") or not origin_url.host():
            return
        origin = f"{origin_url.scheme()}://{origin_url.host()}"
        if origin_url.port() >= 0:
            origin += f":{origin_url.port()}"
        if origin.rstrip("/") != self.browser_origin(browser).rstrip("/"):
            return
        username = str(credentials.get("username", "")).strip()
        password = str(credentials.get("password", ""))
        if not origin or not username or not password:
            return
        if origin in self.app_settings.get("password_never_save", []):
            return
        existing = self.password_store.credential_for_origin(origin)
        if existing and existing.get("username") == username and existing.get("password") == password:
            return
        offer_key = (origin, username, password)
        previous_key, previous_time = self._last_password_offer
        if offer_key == previous_key and time.monotonic() - previous_time < 5:
            return
        self._last_password_offer = (offer_key, time.monotonic())
        self.show_password_save_prompt(origin, username, password, bool(existing))

    def show_password_save_prompt(self, origin, username, password, updating=False):
        previous = getattr(self, "password_save_popup", None)
        if previous:
            try:
                previous.close()
            except RuntimeError:
                pass
        colors = self.theme_colors
        popup = QFrame(
            self,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.prepare_rounded_popup(popup)
        popup.setObjectName("passwordSavePopup")
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.setFixedWidth(390)
        popup.setStyleSheet(f"""
            QFrame#passwordSavePopup {{ background:{colors['popup']}; border:1px solid {colors['border']}; border-radius:12px; }}
            QLabel {{ color:{colors['text']}; border:none; background:transparent; }}
            QLabel#passwordPromptHint {{ color:{colors['muted']}; }}
            QPushButton {{ color:{colors['text']}; background:{colors['surface']}; border:none; border-radius:6px; padding:8px 11px; }}
            QPushButton:hover {{ background:{colors['hover']}; }}
            QPushButton#passwordSaveConfirm {{ color:white; background:{colors['accent']}; }}
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(15, 14, 15, 14)
        layout.setSpacing(9)
        title = QLabel("Обновить сохранённый пароль?" if updating else "Сохранить пароль?")
        title.setStyleSheet("font-size:15px;font-weight:650;")
        host = QUrl(origin).host() or origin
        hint = QLabel(f"{host}\nПользователь: {username}")
        hint.setObjectName("passwordPromptHint")
        hint.setWordWrap(True)
        buttons = QHBoxLayout()
        never = QPushButton("Никогда")
        never.setObjectName("passwordSaveNever")
        later = QPushButton("Не сейчас")
        later.setObjectName("passwordSaveLater")
        save = QPushButton("Обновить" if updating else "Сохранить")
        save.setObjectName("passwordSaveConfirm")
        save.clicked.connect(
            lambda: (self.save_password_credentials(origin, username, password), popup.close())
        )
        later.clicked.connect(popup.close)
        never.clicked.connect(
            lambda: (self.disable_password_offers_for_origin(origin), popup.close())
        )
        buttons.addWidget(never)
        buttons.addStretch()
        buttons.addWidget(later)
        buttons.addWidget(save)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(buttons)
        popup.destroyed.connect(
            lambda _object=None, current=popup:
            setattr(self, "password_save_popup", None)
            if getattr(self, "password_save_popup", None) is current else None
        )
        self.password_save_popup = popup
        popup.adjustSize()
        top_right = self.mapToGlobal(QPoint(self.width() - popup.width() - 18, self.navbar.height() + self.tabs_panel.height() + 12))
        screen = self.screen().availableGeometry()
        popup.move(
            max(screen.left() + 8, min(top_right.x(), screen.right() - popup.width() - 8)),
            max(screen.top() + 8, min(top_right.y(), screen.bottom() - popup.height() - 8)),
        )
        popup.show()
        popup.raise_()

    def save_password_credentials(self, origin, username, password):
        if self.guest_mode:
            QMessageBox.information(self, "Менеджер паролей", "В гостевом режиме пароли не сохраняются.")
            return False
        if not self.password_store.save(origin, username, password):
            QMessageBox.warning(self, "Менеджер паролей", "Windows Credential Manager не смог сохранить пароль.")
            return False
        self.refresh_settings_pages()
        return True

    def disable_password_offers_for_origin(self, origin):
        blocked = list(self.app_settings.get("password_never_save", []))
        if origin not in blocked:
            blocked.append(origin)
            self.app_settings["password_never_save"] = blocked
            self.save_app_settings()
            self.refresh_settings_pages()

    def autofill_browser_login(self, browser):
        if (
            self.guest_mode
            or not self.app_settings.get("password_manager", False)
            or not self.app_settings.get("autofill_passwords", True)
        ):
            return
        page_url = browser.url()
        origin_url = QUrl()
        origin_url.setScheme(page_url.scheme())
        origin_url.setHost(page_url.host())
        if page_url.port() >= 0:
            origin_url.setPort(page_url.port())
        origin = origin_url.toString().rstrip("/")
        credentials = self.password_store.credential_for_origin(origin)
        if credentials:
            browser.autofill_login(credentials.get("username", ""), credentials.get("password", ""))

    def password_page_records(self):
        if self.guest_mode:
            return []
        return [
            {
                "target": item.get("target", ""),
                "origin": item.get("origin", ""),
                "username": item.get("username", ""),
            }
            for item in self.password_store.list()
        ]

    def delete_saved_password(self, target):
        if self.password_store.delete(target):
            self.refresh_settings_pages()

    def browser_language_detected(self, browser, language):
        index = self.tab_index_for_browser(browser)
        if index >= 0:
            base = self.tab_bar.tabToolTip(index).split("\nЯзык:")[0]
            self.tab_bar.setTabToolTip(index, f"{base}\nЯзык: {language}")
            self.sync_vertical_tabs()
        target = self.app_settings.get("translation_language", "ru")
        target_base = str(target).lower().split("-")[0]
        source_base = str(language).lower().split("-")[0]
        host = browser.url().host().lower()
        is_translation_host = "translate.google" in host or host.endswith(".translate.goog")
        if (
            self.app_settings.get("auto_translate", False)
            and source_base not in (target_base, "unknown", "")
            and not is_translation_host
        ):
            self.translate_browser(browser)
        elif (
            self.app_settings.get("offer_translation", True)
            and source_base not in (target_base, "unknown", "")
            and not is_translation_host
        ):
            self.show_translation_prompt(browser, language, target)

    def translation_languages(self):
        return (
            ("ru", "Русский"),
            ("en", "English"),
            ("de", "Deutsch"),
            ("fr", "Français"),
            ("es", "Español"),
            ("it", "Italiano"),
            ("zh-CN", "中文"),
            ("ja", "日本語"),
            ("ko", "한국어"),
        )

    def language_name(self, code):
        return dict(self.translation_languages()).get(str(code), str(code))

    def show_translation_prompt(self, browser, source_language, target_language):
        if browser != self.current_browser() or browser.internal_page:
            return
        page_url = browser.url().toString()
        if not page_url or browser.translation_prompted_url == page_url:
            return
        browser.translation_prompted_url = page_url
        if self.translation_prompt_popup and self.translation_prompt_popup.isVisible():
            self.translation_prompt_popup.close()

        colors = self.theme_colors
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.prepare_rounded_popup(popup)
        popup.setObjectName("translationPrompt")
        popup.setFixedWidth(350)
        popup.setStyleSheet(self.popup_stylesheet("translationPrompt") + f"""
            QPushButton#translatePrimary {{ background:{colors['accent']}; color:{'#202124' if colors['is_dark'] else '#ffffff'}; font-weight:600; text-align:center; }}
            QPushButton#translatePrimary:hover {{ background:{QColor(colors['accent']).lighter(112).name()}; }}
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        title = QLabel("Перевести страницу?")
        title.setStyleSheet("font-size:14px; font-weight:600;")
        description = QLabel(
            f"Определён язык: {self.language_name(source_language)}. Перевести на {self.language_name(target_language)}?"
        )
        description.setObjectName("mutedLabel")
        description.setWordWrap(True)
        buttons = QHBoxLayout()
        decline = QPushButton("Не сейчас")
        accept = QPushButton("Перевести")
        accept.setObjectName("translatePrimary")
        decline.clicked.connect(popup.close)
        accept.clicked.connect(lambda: (popup.close(), self.translate_browser(browser, target_language)))
        buttons.addStretch()
        buttons.addWidget(decline)
        buttons.addWidget(accept)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(buttons)
        self.translation_prompt_popup = popup
        popup.adjustSize()
        screen_rect = self.rect()
        position = self.mapToGlobal(
            QPoint(screen_rect.right() - popup.width() - 18, self.tabs_panel.height() + self.navbar.height() + 8)
        )
        popup.move(position)
        popup.show()
        popup.raise_()

    def translate_browser(self, browser=None, target_language=None):
        browser = browser or self.current_browser()
        if not browser or browser.internal_page or browser.url().scheme() not in ("http", "https"):
            return
        target = target_language or self.app_settings.get("translation_language", "ru")
        source_url = browser.translation_source_url or browser.url().toString()
        if "translate.google" in browser.url().host() and not browser.translation_source_url:
            query = QUrlQuery(browser.url())
            source_url = query.queryItemValue("u") or source_url
        browser.translation_source_url = source_url
        browser.translation_language = target
        url = QUrl("https://translate.google.com/translate")
        query = QUrlQuery()
        query.addQueryItem("sl", "auto")
        query.addQueryItem("tl", target)
        query.addQueryItem("u", source_url)
        url.setQuery(query)
        browser.setUrl(url)
        self.update_translation_button()

    def restore_original_page(self, browser=None):
        browser = browser or self.current_browser()
        if not browser or not browser.translation_source_url:
            return
        source = browser.translation_source_url
        browser.translation_source_url = ""
        browser.translation_language = ""
        browser.translation_prompted_url = source
        browser.setUrl(QUrl(source))
        self.update_translation_button()

    def update_translation_button(self):
        browser = self.current_browser()
        translated = bool(browser and browser.translation_source_url)
        self.translate_btn.setVisible(translated)
        if translated:
            self.translate_btn.setToolTip(
                f"Переведено на {self.language_name(browser.translation_language)}"
            )

    def show_translation_popup(self):
        browser = self.current_browser()
        if not browser or not browser.translation_source_url:
            return
        if self.translation_popup and self.translation_popup.isVisible():
            self.translation_popup.close()
            return
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.prepare_rounded_popup(popup)
        popup.setObjectName("translationPopup")
        popup.setFixedWidth(320)
        popup.setStyleSheet(self.popup_stylesheet("translationPopup"))
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        title = QLabel("Перевод страницы")
        title.setStyleSheet("font-size:14px; font-weight:600;")
        language = QComboBox()
        for code, name in self.translation_languages():
            language.addItem(name, code)
        selected = language.findData(browser.translation_language or self.app_settings.get("translation_language", "ru"))
        language.setCurrentIndex(max(0, selected))
        language.currentIndexChanged.connect(
            lambda _index: (popup.close(), self.translate_browser(browser, language.currentData()))
        )
        original = QPushButton("Показать оригинал")
        original.clicked.connect(lambda: (popup.close(), self.restore_original_page(browser)))
        layout.addWidget(title)
        layout.addWidget(language)
        layout.addWidget(original)
        self.translation_popup = popup
        popup.adjustSize()
        anchor = self.translate_btn.mapToGlobal(QPoint(self.translate_btn.width(), self.translate_btn.height() + 5))
        popup.move(anchor.x() - popup.width(), anchor.y())
        popup.show()
        popup.raise_()

    def current_workspace(self):
        workspace = self.tab_content.currentWidget()
        return workspace if isinstance(workspace, TabWorkspace) else None

    def current_browser(self):
        workspace = self.current_workspace()
        return workspace.active_browser if workspace else None

    def workspace_for_browser(self, browser):
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            if browser in (workspace.primary_browser, workspace.secondary_browser):
                return workspace
        return None

    def tab_index_for_browser(self, browser):
        workspace = self.workspace_for_browser(browser)
        return self.tab_content.indexOf(workspace) if workspace else -1

    def sync_icons(self, browser, icon):
        idx = self.tab_index_for_browser(browser)
        if idx != -1:
            workspace = self.tab_content.widget(idx)
            self.tab_bar.setTabIcon(idx, self.split_tab_icon(icon) if isinstance(workspace, TabWorkspace) and workspace.is_split() else icon)
        url = browser.url().toString()
        
        # Сохраняем иконку в кеш
        self.save_icon_to_cache(url, icon)
        
        bookmark_updated = False
        for b in self.bookmarks:
            if b["url"] == url:
                b["button"].setIcon(icon)
                bookmark_updated = True
        if bookmark_updated and not browser.internal_page:
            self.refresh_home_pages()
        self.sync_vertical_tabs()

    def split_tab_icon(self, base_icon):
        pixmap = QPixmap(22, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if base_icon and not base_icon.isNull():
            painter.drawPixmap(0, 1, base_icon.pixmap(14, 14))
        pen = QPen(QColor(self.theme_colors["accent"]), 1.6)
        painter.setPen(pen)
        painter.setBrush(QColor(self.theme_colors["surface"]))
        painter.drawRoundedRect(QRectF(12.5, 4.5, 8, 11), 1.5, 1.5)
        painter.drawLine(QPointF(16.5, 5.5), QPointF(16.5, 14.5))
        painter.end()
        return QIcon(pixmap)

    def refresh_workspace_icon(self, workspace):
        if not isinstance(workspace, TabWorkspace):
            return
        index = self.tab_content.indexOf(workspace)
        if index >= 0:
            icon = self.internal_page_icon(workspace.primary_browser)
            self.tab_bar.setTabIcon(index, self.split_tab_icon(icon) if workspace.is_split() else icon)
            self.sync_vertical_tabs()

    def update_tab_title(self, browser, sync_vertical=True):
        idx = self.tab_index_for_browser(browser)
        title = browser.title() or "Новая вкладка"
        if idx != -1:
            workspace = self.tab_content.widget(idx)
            group = self.tab_groups.get(workspace.group_id) if isinstance(workspace, TabWorkspace) else None
            display_title = f"{group.get('name')} · {title}" if group else title
            if browser.is_sleeping:
                display_title = f"○ {display_title}"
            if browser.is_private:
                display_title = f"Приватная · {display_title}"
            self.tab_bar.setTabText(idx, display_title)
            tooltip = title + ("\nСпящая вкладка" if browser.is_sleeping else "") + ("\nБез сохранения истории" if browser.is_private else "")
            self.tab_bar.setTabToolTip(idx, tooltip)
            if sync_vertical:
                self.sync_vertical_tabs()

    def active_browser_changed(self, workspace, browser):
        if workspace != self.current_workspace():
            return
        self.update_url(browser.url(), browser)
        self.update_zoom_display(browser, browser.zoom_percent())
        self.update_navigation_buttons()
        self.update_translation_button()
        workspace.last_active = time.time()

    def update_zoom_display(self, browser, percent):
        if browser == self.current_browser():
            self.set_zoom_value_label(f"{percent}%")

    def toggle_split_screen(self):
        workspace = self.current_workspace()
        if not workspace:
            return
        if workspace.is_split():
            workspace.close_split()
            self.active_browser_changed(workspace, workspace.primary_browser)
            self.refresh_workspace_icon(workspace)
        else:
            self.show_split_chooser(workspace)
            self.refresh_workspace_icon(workspace)

    def show_split_chooser(self, workspace):
        colors = self.theme_colors
        chooser = QWidget()
        chooser.setObjectName("splitChooser")
        chooser.setStyleSheet(f"""
            QWidget#splitChooser {{ background: {colors['background']}; border-left: 1px solid {colors['border']}; }}
            QLabel {{ color: {colors['text']}; border: none; }}
            QPushButton#splitChoice {{
                background: {colors['popup']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                text-align: left;
                padding: 10px 12px;
            }}
            QPushButton#splitChoice:hover {{ background: {colors['hover']}; border-color: {colors['accent']}; }}
            QToolButton {{ background: transparent; border: none; border-radius: 14px; }}
            QToolButton:hover {{ background: {colors['hover']}; }}
            QScrollArea {{ border: none; background: transparent; }}
        """)
        chooser_layout = QVBoxLayout(chooser)
        chooser_layout.setContentsMargins(18, 14, 18, 18)
        chooser_layout.setSpacing(10)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_title = QLabel("Открыть справа")
        header_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        close_button = QToolButton()
        close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        close_button.setFixedSize(28, 28)
        close_button.setToolTip("Закрыть разделение")
        close_button.clicked.connect(lambda: self.close_workspace_split(workspace))
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        header_layout.addWidget(close_button)
        chooser_layout.addWidget(header)

        new_page = QPushButton("Новая страница")
        new_page.setObjectName("splitChoice")
        new_page.setIcon(QIcon("add.png"))
        new_page.setFixedHeight(48)
        new_page.clicked.connect(
            lambda: self.open_split_browser(workspace, QUrl("https://www.google.com"))
        )
        chooser_layout.addWidget(new_page)

        hint = QLabel("Открытые вкладки")
        hint.setStyleSheet(f"color: {colors['muted']}; font-size: 12px; padding-top: 6px;")
        chooser_layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(7)
        current_index = self.tab_content.indexOf(workspace)
        choices = 0
        for index in range(self.tab_content.count()):
            if index == current_index:
                continue
            other_workspace = self.tab_content.widget(index)
            if not isinstance(other_workspace, TabWorkspace):
                continue
            other_browser = other_workspace.primary_browser
            title = other_browser.title() or "Новая вкладка"
            host = other_browser.url().host()
            button = QPushButton(f"{title}\n{host}")
            button.setObjectName("splitChoice")
            button.setFixedHeight(64)
            if not other_browser.icon().isNull():
                button.setIcon(other_browser.icon())
                button.setIconSize(QSize(22, 22))
            button.clicked.connect(
                lambda _checked=False, url=QUrl(other_browser.url()): self.open_split_browser(
                    workspace, url
                )
            )
            content_layout.addWidget(button)
            choices += 1
        if choices == 0:
            empty = QLabel("Других вкладок пока нет")
            empty.setStyleSheet(f"color: {colors['muted']}; padding: 18px 4px;")
            content_layout.addWidget(empty)
        content_layout.addStretch()
        scroll.setWidget(content)
        chooser_layout.addWidget(scroll, 1)
        workspace.set_secondary_widget(chooser)
        self.refresh_workspace_icon(workspace)

    def open_split_browser(self, workspace, url):
        browser = BrowserWebView(private=workspace.primary_browser.is_private)
        browser.set_zoom_percent(self.app_settings.get("default_zoom", 100))
        browser.set_permission_policy(self.app_settings.get("site_permissions", {}))
        browser.set_placeholder_color(self.theme_colors["background"])
        self.apply_browser_font_scale(browser)
        self.connect_browser(browser, workspace, primary=False)
        workspace.set_secondary_widget(browser, browser)
        browser.setUrl(url)
        self.active_browser_changed(workspace, browser)
        self.refresh_workspace_icon(workspace)

    def close_workspace_split(self, workspace):
        workspace.close_split()
        self.active_browser_changed(workspace, workspace.primary_browser)
        self.refresh_workspace_icon(workspace)

    def toggle_app_fullscreen(self):
        if self._media_fullscreen:
            self.request_media_fullscreen_exit()
        elif self._app_fullscreen:
            self.exit_app_fullscreen()
        else:
            self.enter_app_fullscreen()

    def enter_app_fullscreen(self):
        if self._app_fullscreen or self._media_fullscreen:
            return
        self._app_fullscreen = True
        self.is_was_maximized = self.isMaximized()
        self._pre_fullscreen_window_state = self.windowState() & ~Qt.WindowState.WindowFullScreen
        self._pre_fullscreen_geometry = self.saveGeometry()
        self._fullscreen_visibility = {
            "tabs": self.tabs_panel.isVisible(),
            "navbar": self.navbar.isVisible(),
            "bookmarks": self.bookmarks_panel.isVisible(),
            "vertical": self.vertical_tabs_panel.isVisible(),
            "devtools": self.devtools_panel.isVisible(),
            "find": self.find_bar.isVisible(),
        }
        self.showFullScreen()
        self.set_fullscreen_chrome_visible(False)
        self.fullscreen_escape_shortcut.setEnabled(True)
        self.show_fullscreen_hint("F11 или Esc - выйти из полноэкранного режима")
        self.refresh_fullscreen_browser()

    def exit_app_fullscreen(self):
        if not self._app_fullscreen:
            return
        self._app_fullscreen = False
        restore_maximized = bool(
            getattr(self, "_pre_fullscreen_window_state", Qt.WindowState.WindowNoState)
            & Qt.WindowState.WindowMaximized
        ) or self.is_was_maximized
        self.showNormal()
        if restore_maximized:
            self.showMaximized()
            QTimer.singleShot(
                80,
                lambda: self.showMaximized() if not self.isMaximized() and not self.isFullScreen() else None,
            )
        elif hasattr(self, "_pre_fullscreen_geometry"):
            self.restoreGeometry(self._pre_fullscreen_geometry)
        self.restore_fullscreen_chrome(self._fullscreen_visibility)
        self.fullscreen_escape_shortcut.setEnabled(self._media_fullscreen)
        if hasattr(self, "fullscreen_hint"):
            self.fullscreen_hint.hide()
        self.refresh_fullscreen_browser()

    def set_fullscreen_chrome_visible(self, visible):
        if visible:
            return
        for widget in (
            self.navbar,
            self.tabs_panel,
            self.find_bar,
            self.bookmarks_panel,
            self.vertical_tabs_panel,
            self.devtools_panel,
        ):
            widget.hide()

    def restore_fullscreen_chrome(self, visibility):
        if self.app_mode:
            return
        self.tabs_panel.setVisible(visibility.get("tabs", True))
        self.navbar.setVisible(visibility.get("navbar", True))
        self.find_bar.setVisible(visibility.get("find", False))
        self.bookmarks_panel.setVisible(
            visibility.get("bookmarks", bool(self.bookmarks))
        )
        self.vertical_tabs_panel.setVisible(visibility.get("vertical", False))
        self.devtools_panel.setVisible(visibility.get("devtools", False))

    def refresh_fullscreen_browser(self):
        browser = self.current_browser()
        if not browser:
            return
        for delay in (0, 80, 240):
            QTimer.singleShot(delay, browser.activate_native_view)

    def enter_media_fullscreen(self, browser):
        if browser is not self.current_browser():
            return
        if self._media_fullscreen and self._media_fullscreen_browser is browser:
            return
        self._media_fullscreen = True
        self._media_fullscreen_browser = browser
        self._media_started_inside_app_fullscreen = self._app_fullscreen
        if not self._app_fullscreen:
            self._pre_media_window_state = (
                self.windowState() & ~Qt.WindowState.WindowFullScreen
            )
            self._pre_media_geometry = self.saveGeometry()
            self._media_fullscreen_visibility = {
                "tabs": self.tabs_panel.isVisible(),
                "navbar": self.navbar.isVisible(),
                "bookmarks": self.bookmarks_panel.isVisible(),
                "vertical": self.vertical_tabs_panel.isVisible(),
                "devtools": self.devtools_panel.isVisible(),
                "find": self.find_bar.isVisible(),
            }
            self.showFullScreen()
            self.set_fullscreen_chrome_visible(False)
        self.fullscreen_escape_shortcut.setEnabled(True)
        self.show_fullscreen_hint("Esc - выйти из полноэкранного видео")
        self.refresh_fullscreen_browser()

    def request_media_fullscreen_exit(self):
        if not self._media_fullscreen:
            return
        browser = self._media_fullscreen_browser or self.current_browser()
        if browser:
            browser.exit_fullscreen()
        QTimer.singleShot(
            500,
            lambda current=browser: self.exit_media_fullscreen(current)
            if self._media_fullscreen else None,
        )

    def exit_media_fullscreen(self, browser=None):
        if not self._media_fullscreen:
            return
        if browser and self._media_fullscreen_browser not in (None, browser):
            return
        started_inside_app = self._media_started_inside_app_fullscreen
        self._media_fullscreen = False
        self._media_fullscreen_browser = None
        self._media_started_inside_app_fullscreen = False
        if not started_inside_app and not self._app_fullscreen:
            previous_state = getattr(
                self, "_pre_media_window_state", Qt.WindowState.WindowNoState
            )
            self.showNormal()
            if previous_state & Qt.WindowState.WindowMaximized:
                self.showMaximized()
                QTimer.singleShot(
                    80,
                    lambda: self.showMaximized()
                    if not self.isMaximized() and not self.isFullScreen() else None,
                )
            elif hasattr(self, "_pre_media_geometry"):
                self.restoreGeometry(self._pre_media_geometry)
            self.restore_fullscreen_chrome(self._media_fullscreen_visibility)
        self.fullscreen_escape_shortcut.setEnabled(self._app_fullscreen)
        if hasattr(self, "fullscreen_hint"):
            self.fullscreen_hint.hide()
        self.refresh_fullscreen_browser()

    def exit_active_fullscreen(self):
        if self._media_fullscreen:
            self.request_media_fullscreen_exit()
        elif self._app_fullscreen:
            self.exit_app_fullscreen()

    def show_fullscreen_hint(self, text):
        if not hasattr(self, "fullscreen_hint"):
            self.fullscreen_hint = QLabel(self)
            self.fullscreen_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fullscreen_hint.setStyleSheet(
                "QLabel{color:white;background:rgba(24,25,28,225);padding:10px 18px;"
                "border:1px solid #666;border-radius:7px;font-size:13px;}"
            )
        self.fullscreen_hint.setText(text)
        self.fullscreen_hint.adjustSize()
        self.fullscreen_hint.move((self.width() - self.fullscreen_hint.width()) // 2, 12)
        self.fullscreen_hint.show()
        self.fullscreen_hint.raise_()
        QTimer.singleShot(4200, self.fullscreen_hint.hide)

    def handle_fullscreen(self, browser, enabled):
        if enabled:
            self.enter_media_fullscreen(browser)
        elif self._media_fullscreen_browser is browser:
            self.exit_media_fullscreen(browser)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "fullscreen_hint") and self.fullscreen_hint.isVisible():
            self.fullscreen_hint.move((self.width() - self.fullscreen_hint.width()) // 2, 12)

    def closeEvent(self, event):
        if hasattr(self, "session_timer"):
            self.session_timer.stop()
        if hasattr(self, "memory_timer"):
            self.memory_timer.stop()
        if not self._session_prompt_pending and not getattr(
            self, "_skip_close_session_save", False
        ):
            self.archive_session_for_history()
            self.save_session(True)
        if self in Browser._open_windows:
            Browser._open_windows.remove(self)
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and (
            self._media_fullscreen or self._app_fullscreen
        ):
            self.exit_active_fullscreen()
            event.accept()
            return
        if event.key() == Qt.Key_F and not event.modifiers():
            browser = self.current_browser()
            if browser:
                browser.toggle_fullscreen()
                event.accept()
                return
        super().keyPressEvent(event)

    def current_tab_changed(self, i):
        previous_workspace = self.tab_content.currentWidget()
        if (
            isinstance(previous_workspace, TabWorkspace)
            and previous_workspace is not self.tab_content.widget(i)
        ):
            previous_workspace.primary_browser.capture_tab_preview()
        self.hide_tab_preview()
        workspace = self.tab_content.widget(i) if i != -1 else None
        if isinstance(workspace, TabWorkspace):
            self.tab_content.setCurrentIndex(i)
            workspace.last_active = time.time()
            self.wake_tab(i)
            browser = workspace.active_browser
            self.update_url(browser.url(), browser)
            if browser.has_deferred_navigation():
                QTimer.singleShot(0, browser.reload_deferred_page)
            QTimer.singleShot(90, browser.ensure_visible_navigation)
            QTimer.singleShot(0, browser.activate_native_view)
            QTimer.singleShot(150, browser.activate_native_view)
            # QtWebView uses a native WebView2 window. After a restored hidden tab
            # is promoted by QStackedWidget, its native surface can arrive later
            # than the QWidget show event and needs one final raise.
            QTimer.singleShot(700, browser.activate_native_view)
            QTimer.singleShot(1100, browser.activate_native_view)
            self.update_zoom_display(browser, browser.zoom_percent())
            self.update_navigation_buttons()
            self.update_translation_button()
            self.save_open_session()
            self.sync_vertical_tabs()
            self.refresh_devtools()
            QTimer.singleShot(0, self.update_browser_polling)

    def update_browser_polling(self):
        current = self.current_workspace()
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            primary_enabled = (
                workspace is current
                or self.browser_has_open_popup(workspace.primary_browser)
            )
            workspace.primary_browser.set_polling_enabled(
                primary_enabled,
                allow_hidden=workspace is not current and primary_enabled,
            )
            if workspace.secondary_browser:
                secondary_enabled = (
                    workspace is current
                    or self.browser_has_open_popup(workspace.secondary_browser)
                )
                workspace.secondary_browser.set_polling_enabled(
                    secondary_enabled,
                    allow_hidden=workspace is not current and secondary_enabled,
                )

    def close_current_tab(self, i):
        if self.tab_bar.count() <= 1 or i < 0 or i >= self.tab_bar.count():
            return
        if self.app_settings.get("smooth_tab_animations", True):
            self.tab_bar.animate_close(i)
        else:
            self.remove_tab_now(i)

    def remove_tab_now(self, i):
        if i < 0 or i >= self.tab_bar.count():
            return
        workspace = self.tab_content.widget(i)
        if isinstance(workspace, TabWorkspace):
            for browser in (workspace.primary_browser, workspace.secondary_browser):
                if browser and getattr(browser, "popup_id", ""):
                    self.notify_popup_closed(browser)
        is_welcome = (
            isinstance(workspace, TabWorkspace)
            and workspace.primary_browser.internal_page == "welcome"
        )
        if is_welcome:
            self.app_settings["welcome_completed"] = True
            self.save_app_settings()
        if (
            isinstance(workspace, TabWorkspace)
            and not workspace.primary_browser.is_private
            and not is_welcome
        ):
            record = self.tab_record(i)
            if record:
                self.closed_tabs.append(record)
                self.save_closed_tabs()
        self.tab_content.removeWidget(workspace)
        if workspace:
            workspace.deleteLater()
        self.tab_bar.removeTab(i)
        self.refresh_tab_groups()
        self.sync_vertical_tabs()
        self.save_open_session()

    def tab_drop_target_at(self, global_position):
        candidates = reversed(list(Browser._open_windows))
        for window in candidates:
            if (
                window is self
                or window.app_mode
                or not window.isVisible()
                or window.isMinimized()
                or window.profile_id != self.profile_id
                or window.guest_mode != self.guest_mode
                or window.storage_path != self.storage_path
            ):
                continue
            drop_widgets = []
            if window.tabs_panel.isVisible():
                drop_widgets.append(window.tabs_panel)
            if window.vertical_tabs_panel.isVisible():
                drop_widgets.append(window.vertical_tabs_panel)
            for widget in drop_widgets:
                top_left = widget.mapToGlobal(QPoint(0, 0))
                if QRect(top_left, widget.size()).contains(global_position):
                    return window, widget
        return None, None

    def tab_drop_index(self, drop_widget, global_position):
        if drop_widget is self.vertical_tabs_panel:
            local_position = self.vertical_tabs_list.mapFromGlobal(global_position)
            model_index = self.vertical_tabs_list.indexAt(local_position)
            if not model_index.isValid():
                return self.tab_bar.count()
            row = model_index.row()
            item_rect = self.vertical_tabs_list.visualItemRect(
                self.vertical_tabs_list.item(row)
            )
            return row + int(local_position.y() > item_rect.center().y())

        local_position = self.tab_bar.mapFromGlobal(global_position)
        index = self.tab_bar.tabAt(local_position)
        if index < 0:
            return self.tab_bar.count()
        return index + int(
            local_position.x() > self.tab_bar.tabRect(index).center().x()
        )

    def remove_transferred_tab(self, index):
        if index < 0 or index >= self.tab_bar.count():
            return
        source_workspace = self.tab_content.widget(index)
        group_id = (
            source_workspace.group_id
            if isinstance(source_workspace, TabWorkspace)
            else None
        )
        self.tab_content.removeWidget(source_workspace)
        if source_workspace:
            source_workspace.deleteLater()
        self.tab_bar.removeTab(index)
        if group_id and not any(
            isinstance(self.tab_content.widget(current), TabWorkspace)
            and self.tab_content.widget(current).group_id == group_id
            for current in range(self.tab_content.count())
        ):
            self.tab_groups.pop(group_id, None)
        self.refresh_tab_groups()
        self.sync_vertical_tabs()
        self.save_open_session()
        if self.tab_bar.count() == 0:
            self._skip_close_session_save = True
            QTimer.singleShot(0, self.close)

    def transfer_tab_to_browser(self, index, target, drop_widget, global_position):
        record = self.tab_record(index)
        if not record:
            return False
        group_id = record.get("group_id")
        if group_id and group_id in self.tab_groups:
            target.tab_groups[group_id] = dict(self.tab_groups[group_id])
        drop_index = target.tab_drop_index(drop_widget, global_position)
        target._restoring_session = True
        try:
            restored_browser = target.restore_tab_record(record)
        finally:
            target._restoring_session = False
        if not restored_browser:
            return False
        workspace = target.workspace_for_browser(restored_browser)
        if workspace:
            workspace.group_id = group_id
        new_index = target.tab_index_for_browser(restored_browser)
        if new_index >= 0:
            final_index = max(0, min(drop_index, target.tab_bar.count() - 1))
            if final_index != new_index:
                target.tab_bar.moveTab(new_index, final_index)
            target.tab_bar.setCurrentIndex(final_index)
        if restored_browser.internal_page:
            restored_browser.reload_internal_on_next_show()
        target.refresh_tab_groups()
        target.save_open_session()
        target.show()
        target.raise_()
        target.activateWindow()
        self.remove_transferred_tab(index)
        return True

    def detach_tab_to_window(self, tab_id, global_position):
        index = next(
            (
                current
                for current in range(self.tab_bar.count())
                if self.tab_bar.tabData(current) == tab_id
            ),
            -1,
        )
        if index < 0:
            return
        record = self.tab_record(index)
        if not record:
            return
        target, drop_widget = self.tab_drop_target_at(global_position)
        if target and self.transfer_tab_to_browser(
            index, target, drop_widget, global_position
        ):
            return
        detached = Browser(
            profile_id=self.profile_id,
            guest=self.guest_mode,
            detached=True,
            shared_storage_path=self.storage_path if self.guest_mode else None,
        )
        group_id = record.get("group_id")
        if group_id and group_id in self.tab_groups:
            detached.tab_groups[group_id] = dict(self.tab_groups[group_id])
        restored_browser = detached.restore_tab_record(record)
        if not restored_browser:
            detached.close()
            return
        workspace = detached.workspace_for_browser(restored_browser)
        if workspace:
            workspace.group_id = group_id
        if restored_browser.internal_page:
            restored_browser.reload_internal_on_next_show()

        screen = QGuiApplication.screenAt(global_position) or self.screen()
        available = screen.availableGeometry()
        width = min(max(900, int(self.width() * 0.82)), available.width())
        height = min(max(650, int(self.height() * 0.82)), available.height())
        x = max(available.left(), min(global_position.x() - width // 3, available.right() - width + 1))
        y = max(available.top(), min(global_position.y() - 24, available.bottom() - height + 1))
        detached.resize(width, height)
        detached.move(x, y)
        detached.show()
        detached.raise_()
        detached.activateWindow()

        self.remove_transferred_tab(index)

    def tab_moved(self, from_index, to_index):
        if from_index == to_index:
            return
        workspace = self.tab_content.widget(from_index)
        if not workspace:
            return
        self.tab_content.removeWidget(workspace)
        self.tab_content.insertWidget(to_index, workspace)
        self.tab_content.setCurrentIndex(self.tab_bar.currentIndex())
        if isinstance(workspace, TabWorkspace) and not workspace.group_id:
            neighbors = []
            if to_index > 0:
                neighbors.append(self.tab_content.widget(to_index - 1))
            if to_index + 1 < self.tab_content.count():
                neighbors.append(self.tab_content.widget(to_index + 1))
            grouped_neighbor = next(
                (
                    neighbor
                    for neighbor in neighbors
                    if isinstance(neighbor, TabWorkspace) and neighbor.group_id in self.tab_groups
                ),
                None,
            )
            if grouped_neighbor:
                workspace.group_id = grouped_neighbor.group_id
        self.refresh_tab_groups()
        self.sync_vertical_tabs()
        self.save_open_session()

    def update_url(self, q, browser=None):
        if browser == self.current_browser() and not self.url_bar.hasFocus():
            self.url_bar.setText(q.toString())
            self.url_bar.setCursorPosition(0)

    def navigate_to_url(self):
        browser = self.current_browser()
        if browser:
            self.navigate_browser_from_text(browser, self.url_bar.text())

    def navigate_browser_from_text(self, browser, value):
        url = str(value).strip()
        if not url or not browser:
            return
        if os.path.isfile(url):
            browser.setUrl(QUrl.fromLocalFile(os.path.abspath(url)))
            return
        internal = url.lower().replace(":", "")
        if internal == "grom//home":
            browser.load_internal_html(self.home_page_html(), "grom://home")
            browser._icon = self.internal_page_icon(browser)
            browser.iconChanged.emit(browser._icon)
            return
        if internal == "grom//settings/profiles":
            browser.load_internal_html(self.settings_page_html(), "grom://settings/profiles")
            browser._icon = self.internal_page_icon(browser)
            browser.iconChanged.emit(browser._icon)
            return
        if internal == "grom//downloads":
            browser.load_internal_html(self.downloads_page_html(), "grom://downloads")
            browser._icon = self.internal_page_icon(browser)
            browser.iconChanged.emit(browser._icon)
            return
        shortcuts = {
            "youtube": "https://www.youtube.com/", "ютуб": "https://www.youtube.com/",
            "google": "https://www.google.com/", "гугл": "https://www.google.com/",
            "gmail": "https://mail.google.com/", "гмейл": "https://mail.google.com/",
            "twitch": "https://www.twitch.tv/", "твич": "https://www.twitch.tv/",
            "telegram": "https://web.telegram.org/", "телеграм": "https://web.telegram.org/",
            "whatsapp": "https://web.whatsapp.com/", "ватсап": "https://web.whatsapp.com/",
            "vk": "https://vk.com/", "вк": "https://vk.com/",
            "chatgpt": "https://chatgpt.com/", "чатгпт": "https://chatgpt.com/",
            "wikipedia": "https://ru.wikipedia.org/", "википедия": "https://ru.wikipedia.org/",
            "yandex": "https://yandex.ru/", "яндекс": "https://yandex.ru/",
        }
        normalized_value = url.casefold()
        shortcut = shortcuts.get(normalized_value)
        if not shortcut:
            if self._address_suggestion_entries is None:
                self._address_suggestion_entries = self.home_suggestions()
            for item in self._address_suggestion_entries:
                title = str(item.get("title", "")).casefold()
                aliases = str(item.get("aliases", "")).casefold().split()
                if normalized_value == title or normalized_value in aliases:
                    shortcut = str(item.get("url", ""))
                    break
        if shortcut:
            browser.setUrl(QUrl(shortcut))
            return
        looks_like_address = bool(
            re.match(r"^[a-z][a-z0-9+.-]*://", url, re.IGNORECASE)
            or re.match(r"^(?:localhost|(?:\d{1,3}\.){3}\d{1,3})(?::\d+)?(?:/|$)", url, re.IGNORECASE)
            or re.match(r"^(?:[\w-]+\.)+[a-z]{2,}(?::\d+)?(?:/|$)", url, re.IGNORECASE)
        )
        if not looks_like_address:
            query = QUrl.toPercentEncoding(url).data().decode()
            templates = {
                "google": "https://www.google.com/search?q={}",
                "bing": "https://www.bing.com/search?q={}",
                "duckduckgo": "https://duckduckgo.com/?q={}",
                "yandex": "https://yandex.ru/search/?text={}",
                "brave": "https://search.brave.com/search?q={}",
                "startpage": "https://www.startpage.com/sp/search?query={}",
                "ecosia": "https://www.ecosia.org/search?q={}",
                "qwant": "https://www.qwant.com/?q={}",
                "yahoo": "https://search.yahoo.com/search?p={}",
                "mojeek": "https://www.mojeek.com/search?q={}",
            }
            template = templates.get(
                self.app_settings.get("search_engine", "google"), templates["google"]
            )
            url = template.format(query)
            browser.setUrl(QUrl(url))
            return
        browser.setUrl(QUrl.fromUserInput(url))

if __name__ == "__main__":
    install_qt_translation()
    app = QApplication(sys.argv)
    app_url = ""
    external_target = ""
    profile_id = ""
    guest = "--guest" in sys.argv
    if "--app-url" in sys.argv:
        position = sys.argv.index("--app-url")
        if position + 1 < len(sys.argv):
            app_url = sys.argv[position + 1]
    if "--profile" in sys.argv:
        position = sys.argv.index("--profile")
        if position + 1 < len(sys.argv):
            profile_id = sys.argv[position + 1]
    skipped_positions = set()
    for option in ("--app-url", "--profile"):
        if option in sys.argv:
            position = sys.argv.index(option)
            skipped_positions.update((position, position + 1))
    for position, argument in enumerate(sys.argv[1:], start=1):
        if position in skipped_positions or argument.startswith("--"):
            continue
        external_target = argument
        break
    window = Browser(app_url=app_url, profile_id=profile_id, guest=guest)
    if external_target and not app_url:
        if os.path.isfile(external_target):
            target_url = QUrl.fromLocalFile(os.path.abspath(external_target))
        else:
            target_url = QUrl.fromUserInput(external_target)
        if target_url.isValid() and not target_url.isEmpty():
            window.add_new_tab(
                target_url,
                target_url.fileName() or target_url.host() or "Новая вкладка",
            )
    sys.exit(app.exec())
