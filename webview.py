from __future__ import annotations

import json
import re

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWebView import QWebView, QWebViewLoadingInfo, QWebViewSettings
from i18n import get_language, translate_html


class AddressLineEdit(QLineEdit):
    focusStateChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.strong_color = QColor("#f1f3f4")
        self.dim_color = QColor("#9aa0a6")
        self.setFrame(False)

    def set_url_colors(self, strong, dim):
        self.strong_color = QColor(strong)
        self.dim_color = QColor(dim)
        self.update()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)
        self.focusStateChanged.emit(True)
        self.update()

    def mousePressEvent(self, event):
        had_focus = self.hasFocus()
        super().mousePressEvent(event)
        if not had_focus:
            self.selectAll()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background:#292a2d; color:#f1f3f4; border:1px solid #5f6368; padding:5px; }
            QMenu::item { padding:8px 28px 8px 12px; border-radius:5px; }
            QMenu::item:selected { background:#45474c; }
            QMenu::item:disabled { color:#777b82; }
            QMenu::separator { height:1px; background:#4b4e53; margin:5px 7px; }
        """)
        cut_action = menu.addAction("Вырезать")
        copy_action = menu.addAction("Копировать")
        paste_action = menu.addAction("Вставить")
        menu.addSeparator()
        select_all_action = menu.addAction("Выбрать всё")
        cut_action.setEnabled(self.hasSelectedText() and not self.isReadOnly())
        copy_action.setEnabled(self.hasSelectedText())
        paste_action.setEnabled(bool(QApplication.clipboard().text()) and not self.isReadOnly())
        select_all_action.setEnabled(bool(self.text()))
        selected = menu.exec(event.globalPos())
        if selected == cut_action:
            self.cut()
        elif selected == copy_action:
            self.copy()
        elif selected == paste_action:
            self.paste()
        elif selected == select_all_action:
            self.selectAll()
        event.accept()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.focusStateChanged.emit(False)
        self.update()

    def paintEvent(self, event):
        value = self.text()
        match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)?([^/?#]+)(.*)$", value)
        if self.hasFocus() or self.hasSelectedText() or not match:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        metrics = QFontMetrics(self.font())
        rect = self.contentsRect().adjusted(3, 0, -3, 0)
        baseline = rect.center().y() + (metrics.ascent() - metrics.descent()) // 2
        x = rect.left()
        available = rect.width()
        segments = (
            (match.group(1) or "", self.dim_color),
            (match.group(2) or "", self.strong_color),
            (match.group(3) or "", self.dim_color),
        )
        for text_value, color in segments:
            if not text_value or available <= 0:
                continue
            visible = metrics.elidedText(text_value, Qt.TextElideMode.ElideRight, available)
            painter.setPen(color)
            painter.drawText(x, baseline, visible)
            width = metrics.horizontalAdvance(visible)
            x += width
            available -= width
            if visible != text_value:
                break
        painter.end()

class CircularIconButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_color = QColor("#45474c")
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_hover_color(self, color):
        self._hover_color = QColor(color)
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered and self.isEnabled():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._hover_color)
            painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        icon = self.icon()
        if not icon.isNull():
            size = self.iconSize()
            rect = QRect(
                (self.width() - size.width()) // 2,
                (self.height() - size.height()) // 2,
                size.width(),
                size.height(),
            )
            mode = QIcon.Mode.Normal if self.isEnabled() else QIcon.Mode.Disabled
            icon.paint(painter, rect, Qt.AlignmentFlag.AlignCenter, mode)

class DevtoolsSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, mode="html"):
        super().__init__(document)
        self.mode = mode
        self.set_colors(True, "#8ab4f8")

    @staticmethod
    def text_format(color, bold=False, italic=False):
        value = QTextCharFormat()
        value.setForeground(QColor(color))
        value.setFontWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        value.setFontItalic(italic)
        return value

    def set_colors(self, dark, accent):
        self.formats = {
            "tag": self.text_format("#78a9ff" if dark else "#174ea6", True),
            "attribute": self.text_format("#c58af9" if dark else "#7b1fa2"),
            "string": self.text_format("#81c995" if dark else "#188038"),
            "comment": self.text_format("#9aa0a6" if dark else "#6f7378", italic=True),
            "number": self.text_format("#f6c177" if dark else "#b06000"),
            "error": self.text_format("#f28b82" if dark else "#c5221f", True),
            "warning": self.text_format("#fdd663" if dark else "#b06000", True),
            "accent": self.text_format(accent, True),
        }
        self.rehighlight()

    def apply_pattern(self, text, pattern, value_format, capture=0):
        iterator = QRegularExpression(pattern).globalMatch(text)
        while iterator.hasNext():
            match = iterator.next()
            self.setFormat(match.capturedStart(capture), match.capturedLength(capture), value_format)

    def highlightBlock(self, text):
        if self.mode == "console":
            if "ERROR" in text or "Ошибка" in text:
                self.setFormat(0, len(text), self.formats["error"])
            elif "WARN" in text:
                self.setFormat(0, len(text), self.formats["warning"])
            elif text.startswith(">"):
                self.setFormat(0, len(text), self.formats["accent"])
            self.apply_pattern(text, r"\b\d+(?:\.\d+)?\b", self.formats["number"])
            return
        self.apply_pattern(text, r"</?[A-Za-z][^>]*>|<!DOCTYPE[^>]*>", self.formats["tag"])
        self.apply_pattern(text, r"\b[A-Za-z_:][-A-Za-z0-9_:.]*(?=\s*=)", self.formats["attribute"])
        self.apply_pattern(text, r'"[^"\n]*"|\'[^\'\n]*\'', self.formats["string"])
        self.apply_pattern(text, r"\b\d+(?:\.\d+)?\b", self.formats["number"])
        self.apply_pattern(text, r"<!--[\s\S]*?-->", self.formats["comment"])

class BrowserWebView(QWidget):
    urlChanged = Signal(QUrl)
    iconChanged = Signal(QIcon)
    loadFinished = Signal(bool)
    fullScreenChanged = Signal(bool)
    activated = Signal()
    zoomChanged = Signal(int)
    settingsChanged = Signal(object)
    loadStarted = Signal()
    downloadRequested = Signal(object)
    browserCommand = Signal(object)
    consoleMessages = Signal(object)
    passwordSubmitted = Signal(object)
    languageDetected = Signal(str)

    def __init__(self, parent=None, private=False):
        super().__init__(parent)
        self._icon = QIcon()
        self._is_fullscreen = False
        self._fullscreen_check_pending = False
        self._interaction_count = 0
        self._zoom_percent = 100
        self._settings_revision = 0
        self._display_url_override = None
        self._requested_url = QUrl()
        self._fallback_title = ""
        self.is_settings_page = False
        self.internal_page = None
        self._last_history_url = ""
        self.is_sleeping = False
        self._sleeping_url = QUrl()
        self._sleeping_title = ""
        self.permission_policy = {}
        self.is_private = bool(private)
        self.reader_mode = False
        self.detected_language = ""
        self.translation_source_url = ""
        self.translation_language = ""
        self.translation_prompted_url = ""
        self._font_scale_percent = 100
        self._known_cookies = set()
        self._polling_allowed = True
        self._allow_hidden_polling = False
        self._internal_html_source = ""
        self._reload_page_when_shown = False
        self._deferred_url = QUrl()
        self._deferred_background_attempted = False
        self._refresh_surface_when_shown = False
        self._tab_preview_pixmap = QPixmap()
        self._native_context_pending = False
        self._google_account_fallback_pending = False
        self.force_qt_click_bridge = False
        self.popup_id = ""
        self.popup_opener_browser = None
        self._popup_bridge_generation = 0

        self.web_view = QWebView()
        self.web_view.setFlag(Qt.WindowType.WindowDoesNotAcceptFocus, False)
        self.web_view.installEventFilter(self)
        settings = self.web_view.settings()
        settings.setAttribute(QWebViewSettings.WebAttribute.JavaScriptEnabled, True)

        self.container = QWidget.createWindowContainer(self.web_view, self)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background:#202124;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.container)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocusProxy(self.container)

        self.network = QNetworkAccessManager(self)
        self.web_view.urlChanged.connect(self._web_url_changed)
        self.web_view.loadingChanged.connect(self._on_loading_changed)
        self.web_view.cookieAdded.connect(self._cookie_added)
        self.web_view.cookieRemoved.connect(self._cookie_removed)

        self.fullscreen_timer = QTimer(self)
        self.fullscreen_timer.setInterval(1500)
        self.fullscreen_timer.timeout.connect(self._check_fullscreen_state)
        self.fullscreen_timer.start()
        self.page_state_probe_timer = QTimer(self)
        self.page_state_probe_timer.setSingleShot(True)
        self.page_state_probe_timer.timeout.connect(self._check_fullscreen_state)
        self.native_layout_timer = QTimer(self)
        self.native_layout_timer.setSingleShot(True)
        self.native_layout_timer.timeout.connect(self.sync_native_view_geometry)
        self.popup_bridge_timer = QTimer(self)
        self.popup_bridge_timer.setInterval(30)
        self.popup_bridge_timer.timeout.connect(self._install_popup_opener_bridge)

    def eventFilter(self, watched, event):
        if watched is self.web_view:
            event_type = event.type()
            if event_type in (
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.KeyRelease,
                QEvent.Type.Wheel,
                QEvent.Type.TouchEnd,
            ):
                self.schedule_page_state_probe()
            if event_type == QEvent.Type.ContextMenu:
                event.accept()
                return True
            if event_type in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseButtonDblClick,
            ) and getattr(event, "button", lambda: Qt.MouseButton.NoButton)() == Qt.MouseButton.RightButton:
                if event_type == QEvent.Type.MouseButtonRelease and not self._native_context_pending:
                    self._native_context_pending = True
                    position = event.position()
                    self._request_native_context_menu(position.x(), position.y())
                    QTimer.singleShot(300, self._clear_native_context_pending)
                event.accept()
                return True
            if (
                event_type == QEvent.Type.MouseButtonRelease
                and getattr(event, "button", lambda: Qt.MouseButton.NoButton)() == Qt.MouseButton.LeftButton
            ):
                if self.force_qt_click_bridge:
                    position = event.position()
                    self._dispatch_bridged_click(position.x(), position.y())
                    event.accept()
                    return True
                position = event.position()
                QTimer.singleShot(
                    0,
                    lambda x=position.x(), y=position.y():
                    self._request_google_account_fallback(x, y),
                )
                QTimer.singleShot(0, self._request_selection_quick_action)
        return super().eventFilter(watched, event)

    def schedule_page_state_probe(self, delay=80):
        if self._polling_allowed and not self.is_sleeping:
            self.page_state_probe_timer.start(max(0, int(delay)))

    def _dispatch_bridged_click(self, x, y):
        self.runJavaScript(f"""
            (() => {{
                const target = document.elementFromPoint({float(x):.2f}, {float(y):.2f});
                if (!target) return false;
                if (target.matches?.('input[type="range"]')) {{
                    const rect = target.getBoundingClientRect();
                    const ratio = Math.max(0, Math.min(1, ({float(x):.2f} - rect.left) / Math.max(1, rect.width)));
                    target.value = Number(target.min || 0) + ratio * (Number(target.max || 100) - Number(target.min || 0));
                    target.dispatchEvent(new Event('input', {{bubbles:true}}));
                    target.dispatchEvent(new Event('change', {{bubbles:true}}));
                    return true;
                }}
                const clickable = target.closest?.('button,label,a') || target;
                clickable.click?.();
                return true;
            }})()
        """)

    def _clear_native_context_pending(self):
        self._native_context_pending = False

    def _request_native_context_menu(self, x, y):
        script = rf"""
            (() => {{
                const target = document.elementFromPoint({float(x):.2f}, {float(y):.2f});
                if (!target) return JSON.stringify({{action:'page_context'}});
                const streamHost = /(^|\.)(?:twitch\.tv|kick\.com)$/i.test(location.hostname);
                const twitchMenu = Boolean(
                    window.__gromBuiltinsConfig?.enabled?.twitch_enhancer
                    && window.__gromBuiltinsConfig?.twitch?.messageMenu
                );
                const chatMessage = streamHost && twitchMenu
                    ? target.closest?.('.chat-line__message,[data-a-target="chat-line-message"],[data-chat-entry]')
                    : null;
                if (chatMessage) {{
                    const author = chatMessage.querySelector?.('[data-a-target="chat-message-username"],.chat-author__display-name,[data-chat-author]');
                    return JSON.stringify({{
                        action:'twitch_message_context',
                        username:String(author?.textContent || '').trim().slice(0,200),
                        text:String(chatMessage.textContent || '').trim().slice(0,12000)
                    }});
                }}
                const image = target.closest?.('img');
                if (image && (image.currentSrc || image.src)) return JSON.stringify({{
                    action:'image_context',
                    url:image.currentSrc || image.src,
                    link:image.closest?.('a[href]')?.href || ''
                }});
                let text = String(window.getSelection?.() || '').trim();
                if (/^(INPUT|TEXTAREA)$/.test(target.tagName)) {{
                    const start = target.selectionStart ?? 0;
                    const end = target.selectionEnd ?? start;
                    text = String(target.value || '').slice(start, end).trim();
                }}
                const editable = Boolean(
                    target.isContentEditable
                    || target.closest?.('[contenteditable="true"]')
                    || target.matches?.('textarea,input:not([type]),input[type="text"],input[type="search"],input[type="email"],input[type="url"],input[type="tel"]')
                );
                if (text || editable) return JSON.stringify({{
                    action:'text_context',
                    text:text.slice(0,12000),
                    editable,
                    html:String(target.outerHTML || '').slice(0,20000)
                }});
                const link = target.closest?.('a[href]');
                return JSON.stringify({{
                    action:'page_context',
                    link:link?.href || '',
                    html:String(target.outerHTML || '').slice(0,20000)
                }});
            }})()
        """
        self.runJavaScript(script, self._emit_native_context_menu)

    def _emit_native_context_menu(self, result):
        try:
            command = json.loads(result) if result else {"action": "page_context"}
        except (TypeError, ValueError):
            command = {"action": "page_context"}
        if isinstance(command, dict) and command.get("action"):
            self.browserCommand.emit(command)

    def _request_selection_quick_action(self):
        self.runJavaScript(
            """
            (() => {
                const active = document.activeElement;
                let text = String(window.getSelection?.() || '').trim();
                if (active && /^(INPUT|TEXTAREA)$/.test(active.tagName)) {
                    const start = active.selectionStart ?? 0;
                    const end = active.selectionEnd ?? start;
                    text = String(active.value || '').slice(start, end).trim();
                }
                return text.slice(0, 12000);
            })()
            """,
            lambda text: self.browserCommand.emit(
                {"action": "selection_quick", "text": str(text)}
            ) if str(text or "").strip() else None,
        )

    def _request_google_account_fallback(self, x, y):
        if self._google_account_fallback_pending or self.internal_page:
            return
        self._google_account_fallback_pending = True
        self.runJavaScript(
            rf"""
            (() => {{
                const host = location.hostname.toLowerCase();
                const googlePage = host === 'google.com'
                    || host.endsWith('.google.com')
                    || host === 'youtube.com'
                    || host.endsWith('.youtube.com');
                if (!googlePage) return '';
                const target = document.elementFromPoint({float(x):.2f}, {float(y):.2f});
                const frame = target?.closest?.('iframe');
                const source = String(frame?.src || frame?.getAttribute?.('src') || '');
                if (!source) return '';
                const accountWidget = /(?:^|\\.)ogs\\.google\\.[^/]+\/.*widget\/account/i.test(source)
                    || /accounts\\.google\\.[^/]+\/.*(?:account|chooser)/i.test(source);
                return accountWidget ? location.href : '';
            }})()
            """,
            self._google_account_fallback_result,
        )

    def _google_account_fallback_result(self, original_url):
        self._google_account_fallback_pending = False
        value = str(original_url or "")
        if value:
            self.browserCommand.emit({
                "action": "google_account_switch_fallback",
                "url": value,
            })

    def showEvent(self, event):
        super().showEvent(event)
        self.web_view.show()
        self.web_view.raise_()
        if self._polling_allowed and not self.is_sleeping and not self.fullscreen_timer.isActive():
            self.fullscreen_timer.start()
        self.native_layout_timer.start(0)
        if self._reload_page_when_shown or not self._deferred_url.isEmpty():
            QTimer.singleShot(80, self.reload_deferred_page)
        elif self._refresh_surface_when_shown:
            QTimer.singleShot(80, self.refresh_background_surface)

    def hideEvent(self, event):
        if not self._allow_hidden_polling:
            self.fullscreen_timer.stop()
        try:
            self.web_view.hide()
        except RuntimeError:
            pass
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.native_layout_timer.start(0)

    def sync_native_view_geometry(self):
        size = self.container.size()
        if size.width() < 2 or size.height() < 2:
            return
        # WebView2 can retain its old backing surface after a maximize event.
        self.web_view.resize(size.width() - 1, size.height())
        self.web_view.resize(size)
        self.web_view.requestUpdate()
        self.container.update()

    def activate_native_view(self):
        if not self.isVisible():
            return
        self.web_view.show()
        self.web_view.raise_()
        self.sync_native_view_geometry()
        self.web_view.requestUpdate()

    def capture_tab_preview(self):
        if not self.isVisible():
            return QPixmap(self._tab_preview_pixmap)
        try:
            origin = self.container.mapToGlobal(QPoint(0, 0))
            size = self.container.size()
            screen = QGuiApplication.screenAt(origin) or QApplication.primaryScreen()
            pixmap = (
                screen.grabWindow(
                    0,
                    origin.x(),
                    origin.y(),
                    size.width(),
                    size.height(),
                )
                if screen and size.width() > 8 and size.height() > 8
                else QPixmap()
            )
        except (RuntimeError, TypeError):
            pixmap = QPixmap()
        if not pixmap.isNull() and pixmap.width() > 8 and pixmap.height() > 8:
            self._tab_preview_pixmap = pixmap.scaled(
                640,
                360,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        return QPixmap(self._tab_preview_pixmap)

    def set_polling_enabled(self, enabled, allow_hidden=False):
        self._polling_allowed = bool(enabled)
        self._allow_hidden_polling = bool(allow_hidden and enabled)
        if (
            self._polling_allowed
            and not self.is_sleeping
            and (self.isVisible() or self._allow_hidden_polling)
        ):
            self.fullscreen_timer.start()
            self.schedule_page_state_probe(0)
        else:
            self.fullscreen_timer.stop()
            self.page_state_probe_timer.stop()

    def reload_internal_on_next_show(self):
        self.reload_on_next_show()

    def reload_on_next_show(self, schedule_if_visible=True):
        self._reload_page_when_shown = True
        if schedule_if_visible and self.isVisible():
            QTimer.singleShot(0, self.reload_deferred_page)

    def set_deferred_url(self, url):
        self.is_sleeping = False
        self._sleeping_url = QUrl()
        self._internal_html_source = ""
        self._reload_page_when_shown = False
        self._display_url_override = None
        self.is_settings_page = False
        self.internal_page = None
        self._deferred_url = QUrl(url)
        self._deferred_background_attempted = False
        self._requested_url = QUrl(url)
        self.urlChanged.emit(QUrl(self._requested_url))

    def has_deferred_navigation(self):
        return not self._deferred_url.isEmpty()

    def is_loading(self):
        return self.web_view.isLoading()

    def reload_deferred_page(self, allow_hidden=False):
        if not allow_hidden and not self.isVisible():
            return
        if not self._deferred_url.isEmpty():
            url = QUrl(self._deferred_url)
            self._requested_url = QUrl(url)
            self._deferred_background_attempted = bool(
                allow_hidden and not self.isVisible()
            )
            self._refresh_surface_when_shown = allow_hidden and not self.isVisible()
            self.sync_native_view_geometry()
            self.web_view.setUrl(url)
            QTimer.singleShot(120, self.sync_native_view_geometry)
            return
        if not self._reload_page_when_shown:
            return
        self._reload_page_when_shown = False
        if self.internal_page and self._internal_html_source:
            self.web_view.loadHtml(self._internal_html_source)
        elif self.web_view.url().isValid() and not self.web_view.url().isEmpty():
            self.web_view.reload()

    def refresh_background_surface(self):
        if not self._refresh_surface_when_shown or not self.isVisible():
            return
        self._refresh_surface_when_shown = False
        self.web_view.hide()
        self.web_view.show()
        self.web_view.raise_()
        self.sync_native_view_geometry()
        actual = self.web_view.url()
        if actual.isValid() and not actual.isEmpty() and actual.toString() != "about:blank":
            self.web_view.reload()
        elif self._requested_url.scheme() in ("http", "https", "file"):
            self.web_view.setUrl(QUrl(self._requested_url))
        QTimer.singleShot(160, self.sync_native_view_geometry)

    def ensure_visible_navigation(self):
        if not self.isVisible():
            return
        if not self._deferred_url.isEmpty():
            self.reload_deferred_page()
            return
        actual = self.web_view.url()
        if (
            self._requested_url.scheme() in ("http", "https", "file")
            and (actual.isEmpty() or actual.toString() == "about:blank")
        ):
            self._refresh_surface_when_shown = False
            self.web_view.setUrl(QUrl(self._requested_url))
            return
        self.refresh_background_surface()

    def setUrl(self, url):
        self.is_sleeping = False
        self._sleeping_url = QUrl()
        self._deferred_url = QUrl()
        self._deferred_background_attempted = False
        self._requested_url = QUrl(url)
        self._internal_html_source = ""
        self._reload_page_when_shown = False
        self._display_url_override = None
        self.is_settings_page = False
        self.internal_page = None
        self.urlChanged.emit(QUrl(self._requested_url))
        self.web_view.setUrl(url)

    def url(self):
        if self._display_url_override is not None:
            return QUrl(self._display_url_override)
        if not self._deferred_url.isEmpty():
            return QUrl(self._deferred_url)
        if self.is_sleeping and not self._sleeping_url.isEmpty():
            return QUrl(self._sleeping_url)
        if not self._requested_url.isEmpty():
            return QUrl(self._requested_url)
        return self.web_view.url()

    def load_internal_html(self, html, display_url):
        self._deferred_url = QUrl()
        self._deferred_background_attempted = False
        self._requested_url = QUrl()
        html = translate_html(html, get_language())
        self._internal_html_source = html
        self._reload_page_when_shown = False
        self._display_url_override = QUrl(display_url)
        if "downloads" in display_url:
            self.internal_page = "downloads"
        elif "welcome" in display_url:
            self.internal_page = "welcome"
        elif "home" in display_url:
            self.internal_page = "home"
        else:
            self.internal_page = "settings"
        self.is_settings_page = self.internal_page == "settings"
        self.web_view.loadHtml(html)
        self.urlChanged.emit(self._display_url_override)

    def title(self):
        if self.is_sleeping and self._sleeping_title:
            return self._sleeping_title
        return self.web_view.title() or self._fallback_title

    def set_fallback_title(self, title):
        self._fallback_title = str(title or "")

    def icon(self):
        return self._icon

    def back(self):
        self.web_view.goBack()

    def forward(self):
        self.web_view.goForward()

    def can_go_back(self):
        return bool(self.web_view.canGoBack())

    def can_go_forward(self):
        return bool(self.web_view.canGoForward())

    def _cookie_added(self, domain, name):
        self._known_cookies.add((str(domain).lower().lstrip("."), str(name)))

    def _cookie_removed(self, domain, name):
        self._known_cookies.discard((str(domain).lower().lstrip("."), str(name)))

    def cookie_names_for_host(self, host=None):
        host = str(host or self.url().host()).lower().lstrip(".")
        return sorted({
            name
            for domain, name in self._known_cookies
            if host == domain or host.endswith("." + domain) or domain.endswith("." + host)
        })

    def delete_site_cookies(self, host=None):
        host = str(host or self.url().host()).lower().lstrip(".")
        matching = [
            (domain, name)
            for domain, name in self._known_cookies
            if host == domain or host.endswith("." + domain) or domain.endswith("." + host)
        ]
        for domain, name in matching:
            self.web_view.deleteCookie(domain, name)
            if domain != host:
                self.web_view.deleteCookie(host, name)
        self.runJavaScript("""
            (() => {
                document.cookie.split(';').forEach(value => {
                    const name = value.split('=')[0].trim();
                    if (name) document.cookie = `${name}=; Max-Age=0; path=/`;
                });
            })();
        """)
        return len(matching)

    def clear_site_storage(self):
        removed = self.delete_site_cookies(self.url().host())
        self.runJavaScript(r"""
            (() => {
                try { localStorage.clear(); } catch (_) {}
                try { sessionStorage.clear(); } catch (_) {}
                try {
                    document.cookie.split(';').forEach(value => {
                        const name = value.split('=')[0].trim();
                        if (!name) return;
                        const parts = location.hostname.split('.');
                        for (let index = 0; index < parts.length; index++) {
                            const domain = parts.slice(index).join('.');
                            document.cookie = `${name}=; Max-Age=0; path=/`;
                            document.cookie = `${name}=; Max-Age=0; path=/; domain=${domain}`;
                            document.cookie = `${name}=; Max-Age=0; path=/; domain=.${domain}`;
                        }
                    });
                } catch (_) {}
                try {
                    if (window.caches) caches.keys().then(keys => keys.forEach(key => caches.delete(key)));
                } catch (_) {}
                try {
                    if (indexedDB.databases) {
                        indexedDB.databases().then(items => items.forEach(item => item.name && indexedDB.deleteDatabase(item.name)));
                    }
                } catch (_) {}
                try {
                    navigator.serviceWorker?.getRegistrations().then(items => items.forEach(item => item.unregister()));
                } catch (_) {}
                return true;
            })();
        """)
        return removed

    def create_page_snapshot(self, callback):
        self.runJavaScript(r"""
            (() => {
                try {
                    const sourceRoot = document.documentElement;
                    if (!sourceRoot) return '';
                    const clone = sourceRoot.cloneNode(true);
                    const sourceElements = [...sourceRoot.querySelectorAll('*')];
                    const cloneElements = [...clone.querySelectorAll('*')];
                    const absolute = value => {
                        try { return new URL(value, document.baseURI).href; } catch (_) { return value; }
                    };
                    sourceElements.forEach((source, index) => {
                        const target = cloneElements[index];
                        if (!target) return;
                        ['src', 'href', 'poster', 'action'].forEach(attribute => {
                            const value = source.getAttribute?.(attribute);
                            if (value && !value.startsWith('data:') && !value.startsWith('#')) {
                                target.setAttribute(attribute, absolute(value));
                            }
                        });
                        if (source instanceof HTMLInputElement) {
                            target.setAttribute('value', source.value);
                            if (source.checked) target.setAttribute('checked', 'checked');
                            else target.removeAttribute('checked');
                        } else if (source instanceof HTMLTextAreaElement) {
                            target.textContent = source.value;
                        } else if (source instanceof HTMLSelectElement) {
                            [...target.options].forEach((option, optionIndex) => {
                                option.toggleAttribute('selected', optionIndex === source.selectedIndex);
                            });
                        }
                        if (source instanceof HTMLImageElement && source.complete && source.naturalWidth) {
                            try {
                                const canvas = document.createElement('canvas');
                                canvas.width = source.naturalWidth;
                                canvas.height = source.naturalHeight;
                                canvas.getContext('2d').drawImage(source, 0, 0);
                                target.setAttribute('src', canvas.toDataURL('image/png'));
                                target.removeAttribute('srcset');
                            } catch (_) {
                                target.setAttribute('src', absolute(source.currentSrc || source.src));
                            }
                        }
                    });
                    [...document.querySelectorAll('canvas')].forEach((canvas, index) => {
                        const target = clone.querySelectorAll('canvas')[index];
                        if (!target) return;
                        try {
                            const image = document.createElement('img');
                            image.src = canvas.toDataURL('image/png');
                            image.width = canvas.width;
                            image.height = canvas.height;
                            target.replaceWith(image);
                        } catch (_) {}
                    });
                    const embeddedStyles = document.createElement('style');
                    embeddedStyles.setAttribute('data-grom-snapshot', '');
                    embeddedStyles.textContent = [...document.styleSheets].map(sheet => {
                        try { return [...sheet.cssRules].map(rule => rule.cssText).join('\n'); }
                        catch (_) { return ''; }
                    }).join('\n');
                    clone.querySelector('head')?.append(embeddedStyles);
                    clone.querySelectorAll('script,noscript').forEach(node => node.remove());
                    clone.querySelectorAll('video,audio').forEach(media => {
                        media.removeAttribute('autoplay');
                        media.setAttribute('controls', 'controls');
                    });
                    const meta = document.createElement('meta');
                    meta.setAttribute('name', 'generator');
                    meta.setAttribute('content', 'Grom offline snapshot');
                    clone.querySelector('head')?.prepend(meta);
                    return '<!doctype html>\n' + clone.outerHTML;
                } catch (error) {
                    return '';
                }
            })();
        """, callback)

    def reload(self):
        if not self._deferred_url.isEmpty():
            self.reload_deferred_page()
            return
        if self.is_sleeping:
            self.wake_page()
            return
        actual = self.web_view.url()
        if (
            self._requested_url.scheme() in ("http", "https", "file")
            and (actual.isEmpty() or actual.toString() == "about:blank")
        ):
            self.web_view.setUrl(QUrl(self._requested_url))
            return
        self.web_view.reload()

    def stop(self):
        self.web_view.stop()

    def sleep_page(self):
        if self.is_sleeping or self.internal_page or self.url().scheme() not in ("http", "https"):
            return False
        self._sleeping_url = QUrl(self.url())
        self._sleeping_title = self.title() or self._sleeping_url.host()
        self.is_sleeping = True
        self.fullscreen_timer.stop()
        self.web_view.setUrl(QUrl("about:blank"))
        return True

    def wake_page(self):
        if not self.is_sleeping:
            return False
        url = QUrl(self._sleeping_url)
        self.is_sleeping = False
        self._sleeping_url = QUrl()
        self._requested_url = QUrl(url)
        if self._polling_allowed:
            self.fullscreen_timer.start()
        self.web_view.setUrl(url)
        return True

    def set_permission_policy(self, policy):
        self.permission_policy = dict(policy or {})
        if not self.is_sleeping:
            self.apply_permission_policy()

    def zoom_percent(self):
        return self._zoom_percent

    def set_zoom_percent(self, percent):
        percent = max(25, min(500, int(percent)))
        if percent == self._zoom_percent:
            return
        self._zoom_percent = percent
        self._apply_zoom()
        self.zoomChanged.emit(percent)

    def set_font_scale_percent(self, percent):
        self._font_scale_percent = max(50, min(200, int(percent)))
        if not self.is_sleeping:
            self._apply_font_scale()

    def set_placeholder_color(self, color):
        self.setStyleSheet(f"background:{QColor(color).name()};")

    def runJavaScript(self, script, callback=lambda _result: None):
        self.web_view.runJavaScript(script, callback)

    def _web_url_changed(self, url):
        if (
            self._display_url_override is None
            and url.isValid()
            and not url.isEmpty()
            and url.toString() != "about:blank"
        ):
            self._requested_url = QUrl(url)
        self.urlChanged.emit(self.url())

    def exit_fullscreen(self):
        self.runJavaScript(
            "if (document.fullscreenElement) document.exitFullscreen();"
        )

    def toggle_fullscreen(self):
        script = """
            (() => {
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                    return;
                }
                const videos = [...document.querySelectorAll('video')]
                    .filter(video => {
                        const rect = video.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    })
                    .sort((left, right) => {
                        const a = left.getBoundingClientRect();
                        const b = right.getBoundingClientRect();
                        return b.width * b.height - a.width * a.height;
                    });
                const video = videos.find(item => !item.paused) || videos[0];
                const target = video?.closest(
                    '#movie_player, .html5-video-player, [data-a-target="video-player"], .video-player'
                ) || video;
                const requestTarget = target?.requestFullscreen || target?.webkitRequestFullscreen
                    ? target
                    : video;
                const request = requestTarget?.requestFullscreen
                    || requestTarget?.webkitRequestFullscreen;
                if (request) {
                    try {
                        const result = request.call(requestTarget, {navigationUI:'hide'});
                        result?.catch?.(() => video?.requestFullscreen?.());
                    } catch (_) {
                        video?.requestFullscreen?.();
                    }
                }
            })();
        """
        self.runJavaScript(script)

    def find_text(self, text, backward=False, callback=lambda _found: None):
        if not text:
            self.clear_find()
            callback(False)
            return
        script = f"""
            (() => {{
                const query = {json.dumps(text)};
                const backward = {str(bool(backward)).lower()};
                const normalize = value => value.toLocaleLowerCase();
                const rebuild = !window.__gromFindState || window.__gromFindState.query !== query;
                if (rebuild) {{
                    const ranges = [];
                    const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT, {{
                        acceptNode(node) {{
                            const parent = node.parentElement;
                            if (!parent || !node.data.trim() || parent.closest('script,style,noscript,textarea,input,select')) return NodeFilter.FILTER_REJECT;
                            return NodeFilter.FILTER_ACCEPT;
                        }}
                    }});
                    const needle = normalize(query);
                    while (walker.nextNode()) {{
                        const node = walker.currentNode;
                        const haystack = normalize(node.data);
                        let start = 0;
                        while ((start = haystack.indexOf(needle, start)) !== -1) {{
                            const range = new Range();
                            range.setStart(node, start);
                            range.setEnd(node, start + query.length);
                            ranges.push(range);
                            start += Math.max(1, query.length);
                        }}
                    }}
                    window.__gromFindState = {{query, ranges, index: backward ? ranges.length : -1}};
                    if (window.CSS?.highlights && window.Highlight) {{
                        CSS.highlights.set('grom-find', new Highlight(...ranges));
                        let style = document.getElementById('__gromFindStyle');
                        if (!style) {{
                            style = document.createElement('style');
                            style.id = '__gromFindStyle';
                            style.textContent = '::highlight(grom-find){{background:#4d90fe;color:#fff}}';
                            document.head?.append(style);
                        }}
                    }}
                }}
                const state = window.__gromFindState;
                if (!state.ranges.length) return false;
                state.index = (state.index + (backward ? -1 : 1) + state.ranges.length) % state.ranges.length;
                const current = state.ranges[state.index];
                const selection = getSelection();
                selection.removeAllRanges();
                selection.addRange(current);
                const rect = current.getBoundingClientRect();
                if (rect.top < 80 || rect.bottom > innerHeight - 40) scrollBy({{top:rect.top-innerHeight*.4,behavior:'smooth'}});
                return true;
            }})();
        """
        self.runJavaScript(script, lambda found: callback(bool(found)))

    def clear_find(self):
        self.runJavaScript("CSS.highlights?.delete('grom-find');document.getElementById('__gromFindStyle')?.remove();window.__gromFindState=null;window.getSelection()?.removeAllRanges();")

    def toggle_reader_mode(self, font_size=18):
        self.reader_mode = not self.reader_mode
        size = max(14, min(28, int(font_size)))
        script = f"""
            (() => {{
                const id = '__gromReaderStyle';
                document.getElementById(id)?.remove();
                document.documentElement.classList.remove('__gromReader');
                if (!{str(self.reader_mode).lower()}) return;
                const style = document.createElement('style');
                style.id = id;
                style.textContent = `
                    html.__gromReader body {{ max-width: 820px !important; margin: 0 auto !important;
                        padding: 42px 28px !important; font: {size}px/1.72 Georgia, serif !important;
                        color: #202124 !important; background: #f7f7f5 !important; }}
                    html.__gromReader body * {{ max-width: 100% !important; }}
                    html.__gromReader nav, html.__gromReader aside, html.__gromReader footer,
                    html.__gromReader [role='navigation'], html.__gromReader [class*='advert'],
                    html.__gromReader [class*='banner'], html.__gromReader [id*='advert'],
                    html.__gromReader iframe, html.__gromReader video {{ display: none !important; }}
                    html.__gromReader article, html.__gromReader main {{ display: block !important;
                        width: auto !important; margin: 0 !important; padding: 0 !important; }}
                    html.__gromReader img {{ height: auto !important; }}
                `;
                document.head.appendChild(style);
                document.documentElement.classList.add('__gromReader');
            }})();
        """
        self.runJavaScript(script)
        return self.reader_mode

    def toggle_picture_in_picture(self):
        self.runJavaScript("""
            (async () => {
                try {
                    if (document.pictureInPictureElement) {
                        await document.exitPictureInPicture();
                        return 'closed';
                    }
                    const video = [...document.querySelectorAll('video')]
                        .find(item => !item.paused && item.readyState >= 2)
                        || document.querySelector('video');
                    if (!video || !document.pictureInPictureEnabled) return 'unavailable';
                    await video.requestPictureInPicture();
                    return 'opened';
                } catch (error) { return String(error); }
            })();
        """)

    def detect_language(self):
        script = """
            (() => {
                const declared = (document.documentElement.lang || '').toLowerCase().split('-')[0];
                if (declared) return declared;
                const text = (document.body?.innerText || '').slice(0, 6000);
                const cyrillic = (text.match(/[А-Яа-яЁё]/g) || []).length;
                const latin = (text.match(/[A-Za-z]/g) || []).length;
                return cyrillic > latin * 0.35 ? 'ru' : latin ? 'en' : 'unknown';
            })();
        """
        self.runJavaScript(script, self._language_received)

    def _language_received(self, language):
        self.detected_language = str(language or "unknown")
        self.languageDetected.emit(self.detected_language)

    def autofill_login(self, username, password):
        script = f"""
            (() => {{
                const password = document.querySelector('input[type="password"]');
                if (!password) return false;
                const form = password.form || password.closest('form');
                const username = form?.querySelector('input[autocomplete="username"],input[type="email"],input[type="text"]');
                const setValue = (element, value) => {{
                    if (!element || element.value) return;
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
                    setter?.call(element, value);
                    element.dispatchEvent(new Event('input', {{bubbles:true}}));
                    element.dispatchEvent(new Event('change', {{bubbles:true}}));
                }};
                setValue(username, {json.dumps(username)});
                setValue(password, {json.dumps(password)});
                return true;
            }})();
        """
        self.runJavaScript(script)

    def set_popup_context(self, popup_id, opener_browser=None):
        self.popup_id = str(popup_id or "")
        self.popup_opener_browser = opener_browser
        if self.popup_id:
            self._popup_bridge_generation += 1
            self.popup_bridge_timer.start()
            self._install_popup_opener_bridge()

    def _stop_popup_bridge(self, generation):
        if generation == self._popup_bridge_generation:
            self.popup_bridge_timer.stop()

    def _install_popup_opener_bridge(self):
        if not self.popup_id:
            return
        popup_id = json.dumps(self.popup_id)
        script = r"""
            (() => {
                const popupId = __POPUP_ID__;
                window.__gromCommandQueue = window.__gromCommandQueue || [];
                const cloneMessage = value => {
                    try { return JSON.parse(JSON.stringify(value)); }
                    catch (_) { return String(value ?? ''); }
                };
                if (window.__gromPopupOpenerId !== popupId) {
                    const openerProxy = {
                        closed: false,
                        focus() {},
                        postMessage(message, targetOrigin='*') {
                            window.__gromCommandQueue.push({
                                action:'popup_message_to_opener', popup_id:popupId,
                                data:cloneMessage(message), target_origin:String(targetOrigin || '*')
                            });
                        }
                    };
                    window.__gromPopupOpenerId = popupId;
                    window.__gromOpenerProxy = openerProxy;
                    try {
                        Object.defineProperty(window, 'opener', {
                            configurable:true, get:() => openerProxy
                        });
                    } catch (_) {
                        try { window.opener = openerProxy; } catch (_) {}
                    }
                    const closePopup = () => window.__gromCommandQueue.push({
                        action:'popup_close', popup_id:popupId
                    });
                    try {
                        Object.defineProperty(window, 'close', {
                            configurable:true, writable:true, value:closePopup
                        });
                    } catch (_) {
                        try { window.close = closePopup; } catch (_) {}
                    }
                    window.__gromReceiveOpenerMessage = (data, origin) => {
                        let event;
                        try {
                            event = new MessageEvent('message', {
                                data, origin:String(origin || '')
                            });
                            Object.defineProperty(event, 'source', {value:openerProxy});
                        } catch (_) {
                            event = new Event('message');
                            Object.defineProperties(event, {
                                data:{value:data}, origin:{value:String(origin || '')},
                                source:{value:openerProxy}
                            });
                        }
                        window.dispatchEvent(event);
                    };
                }
                return Boolean(window.opener);
            })();
        """.replace("__POPUP_ID__", popup_id)
        try:
            self.runJavaScript(script)
        except RuntimeError:
            pass

    def _on_loading_changed(self, info):
        if info.status() == QWebViewLoadingInfo.LoadStatus.Started:
            if not self._deferred_url.isEmpty():
                self._deferred_url = QUrl()
                self._deferred_background_attempted = False
            if self.is_sleeping:
                return
            if self.popup_id:
                self._popup_bridge_generation += 1
                self.popup_bridge_timer.start()
                QTimer.singleShot(0, self._install_popup_opener_bridge)
            self.reader_mode = False
            self._icon = QIcon()
            self.loadStarted.emit()
        elif info.status() == QWebViewLoadingInfo.LoadStatus.Succeeded:
            if not self._deferred_url.isEmpty():
                self._deferred_url = QUrl()
                self._deferred_background_attempted = False
            if self.is_sleeping:
                return
            self._install_page_bridge()
            self._install_popup_opener_bridge()
            if self.popup_id:
                generation = self._popup_bridge_generation
                QTimer.singleShot(
                    5000,
                    lambda current=generation: self._stop_popup_bridge(current),
                )
            self.apply_permission_policy()
            self._apply_zoom()
            self._apply_font_scale()
            self._request_page_icon()
            self.schedule_page_state_probe(0)
            self.loadFinished.emit(True)
            if self.isVisible():
                QTimer.singleShot(0, self.activate_native_view)
                QTimer.singleShot(250, self.activate_native_view)
        elif info.status() == QWebViewLoadingInfo.LoadStatus.Failed:
            self.loadFinished.emit(False)

    def _check_fullscreen_state(self):
        try:
            if (
                self._fullscreen_check_pending
                or (not self.isVisible() and not self._allow_hidden_polling)
                or QApplication.applicationState() != Qt.ApplicationState.ApplicationActive
            ):
                return
            self._fullscreen_check_pending = True
            self.runJavaScript(
                "JSON.stringify({fullscreen: Boolean(document.fullscreenElement), "
                "interaction: window.__gromInteractionCount || 0, "
                "settingsRevision: window.__gromSettingsRevision || 0, "
                "settingsState: window.__gromSettingsState || '', "
                "downloads: window.__gromDownloadQueue?.splice(0) || [], "
                "commands: window.__gromCommandQueue?.splice(0) || [], "
                "console: window.__gromConsoleQueue?.splice(0) || [], "
                "passwords: window.__gromPasswordQueue?.splice(0) || []})",
                self._page_state_received,
            )
        except KeyboardInterrupt:
            QApplication.quit()

    def _page_state_received(self, state):
        self._fullscreen_check_pending = False
        try:
            page_state = json.loads(state) if state else {}
        except (TypeError, ValueError):
            return

        fullscreen = bool(page_state.get("fullscreen"))
        if fullscreen != self._is_fullscreen:
            self._is_fullscreen = fullscreen
            self.fullScreenChanged.emit(fullscreen)
        target_interval = 250 if fullscreen else 1500
        if self.fullscreen_timer.interval() != target_interval:
            self.fullscreen_timer.setInterval(target_interval)

        interaction = int(page_state.get("interaction", 0))
        if interaction != self._interaction_count:
            self._interaction_count = interaction
            self.activated.emit()

        settings_revision = int(page_state.get("settingsRevision", 0))
        settings_state = page_state.get("settingsState", "")
        if settings_state and settings_revision != self._settings_revision:
            self._settings_revision = settings_revision
            try:
                self.settingsChanged.emit(json.loads(settings_state))
            except (TypeError, ValueError):
                pass

        downloads = page_state.get("downloads", [])
        if isinstance(downloads, list):
            for download in downloads:
                if isinstance(download, dict) and download.get("url"):
                    self.downloadRequested.emit(download)

        commands = page_state.get("commands", [])
        if isinstance(commands, list):
            for command in commands:
                if isinstance(command, dict) and command.get("action"):
                    self.browserCommand.emit(command)

        console_messages = page_state.get("console", [])
        if isinstance(console_messages, list) and console_messages:
            self.consoleMessages.emit(console_messages)

        passwords = page_state.get("passwords", [])
        if isinstance(passwords, list):
            for credentials in passwords:
                if isinstance(credentials, dict) and credentials.get("password"):
                    self.passwordSubmitted.emit(credentials)

    def _install_page_bridge(self):
        script = r"""
            (() => {
                if (window.__gromInteractionBridgeInstalled) return;
                window.__gromInteractionBridgeInstalled = true;
                window.__gromInteractionCount = 0;
                const activate = () => window.__gromInteractionCount++;
                document.addEventListener('pointerdown', activate, true);
                document.addEventListener('keydown', activate, true);
                window.__gromDownloadQueue = [];
                window.__gromPasswordQueue = [];
                window.__gromCommandQueue = window.__gromCommandQueue || [];
                window.__gromConsoleQueue = window.__gromConsoleQueue || [];
                window.__gromLongTaskMs = 0;
                window.__gromLongTaskStarted = performance.now();
                try {
                    new PerformanceObserver(list => {
                        for (const entry of list.getEntries()) window.__gromLongTaskMs += entry.duration || 0;
                    }).observe({type:'longtask', buffered:true});
                } catch (_) {}
                const resolvePopupUrl = value => {
                    try { return new URL(String(value || ''), document.baseURI).href; }
                    catch (_) { return ''; }
                };
                if (!window.__gromPopupBridgeInstalled) {
                    window.__gromPopupBridgeInstalled = true;
                    window.__gromPopupHandles = window.__gromPopupHandles || {};
                    const clonePopupMessage = value => {
                        try { return JSON.parse(JSON.stringify(value)); }
                        catch (_) { return String(value ?? ''); }
                    };
                    const makePopupId = () => {
                        try { return crypto.randomUUID(); }
                        catch (_) { return `grom-popup-${Date.now()}-${Math.random().toString(16).slice(2)}`; }
                    };
                    const createPopupProxy = initialUrl => {
                        const id = makePopupId();
                        const state = {id, closed:false, opened:false, proxy:null};
                        const navigate = value => {
                            const url = resolvePopupUrl(value);
                            if (!/^https?:/i.test(url) || state.closed) return;
                            window.__gromCommandQueue.push({
                                action: state.opened ? 'popup_navigate' : 'open_popup',
                                popup_id: id,
                                url
                            });
                            state.opened = true;
                        };
                        const locationProxy = {assign:navigate, replace:navigate};
                        Object.defineProperty(locationProxy, 'href', {set:navigate, get:() => ''});
                        const target = {
                            focus() {},
                            close() {
                                if (!state.closed && state.opened)
                                    window.__gromCommandQueue.push({action:'popup_close', popup_id:id});
                                state.closed = true;
                            },
                            postMessage(message, targetOrigin='*') {
                                if (!state.closed && state.opened) window.__gromCommandQueue.push({
                                    action:'popup_message_to_child', popup_id:id,
                                    data:clonePopupMessage(message), target_origin:String(targetOrigin || '*')
                                });
                            }
                        };
                        Object.defineProperty(target, 'closed', {get:() => state.closed});
                        const proxy = new Proxy(target, {
                            get(object, property) {
                                if (property === 'location') return locationProxy;
                                return object[property];
                            },
                            set(object, property, value) {
                                if (property === 'location') { navigate(value); return true; }
                                object[property] = value; return true;
                            }
                        });
                        state.proxy = proxy;
                        window.__gromPopupHandles[id] = state;
                        if (initialUrl) navigate(initialUrl);
                        return proxy;
                    };
                    window.__gromMarkPopupClosed = id => {
                        const state = window.__gromPopupHandles?.[id];
                        if (state) state.closed = true;
                    };
                    window.__gromReceivePopupMessage = (id, data, origin) => {
                        const state = window.__gromPopupHandles?.[id];
                        let event;
                        try {
                            event = new MessageEvent('message', {
                                data, origin:String(origin || '')
                            });
                            Object.defineProperty(event, 'source', {
                                value:state?.proxy || null
                            });
                        } catch (_) {
                            event = new Event('message');
                            Object.defineProperties(event, {
                                data:{value:data}, origin:{value:String(origin || '')},
                                source:{value:state?.proxy || null}
                            });
                        }
                        window.dispatchEvent(event);
                    };
                    window.open = (url) => createPopupProxy(url);
                    window.__gromOpenPopup = createPopupProxy;
                }
                const openPopupFallback = value => {
                    if (value) window.__gromOpenPopup?.(value);
                };
                if (!window.__gromConsoleCaptureInstalled) {
                    window.__gromConsoleCaptureInstalled = true;
                    ['log', 'info', 'warn', 'error'].forEach(level => {
                        const original = console[level]?.bind(console);
                        console[level] = (...args) => {
                            try {
                                window.__gromConsoleQueue.push({
                                    level,
                                    text: args.map(value => typeof value === 'string' ? value : JSON.stringify(value)).join(' '),
                                    time: new Date().toLocaleTimeString()
                                });
                                if (window.__gromConsoleQueue.length > 300) window.__gromConsoleQueue.shift();
                            } catch (_) {}
                            original?.(...args);
                        };
                    });
                    window.addEventListener('error', event => window.__gromConsoleQueue.push({
                        level: 'error', text: `${event.message} (${event.filename}:${event.lineno})`, time: new Date().toLocaleTimeString()
                    }));
                }
                const downloadable = /\.(7z|avi|csv|docx?|exe|gif|gz|iso|jpe?g|mkv|mov|mp3|mp4|msi|pdf|png|pptx?|rar|tar|webp|xlsx?|zip)(?:$|[?#])/i;
                document.addEventListener('click', event => {
                    const link = event.target?.closest?.('a[href]');
                    if (!link) return;
                    const url = link.href || '';
                    if (!/^https?:/i.test(url)) return;
                    if (link.hasAttribute('download') || downloadable.test(url)) {
                        event.preventDefault();
                        event.stopPropagation();
                        window.__gromDownloadQueue.push({
                            url,
                            name: link.getAttribute('download') || ''
                        });
                        return;
                    }
                    if ((link.target || '').toLowerCase() === '_blank') {
                        event.preventDefault();
                        event.stopPropagation();
                        openPopupFallback(url);
                    }
                }, true);
                document.addEventListener('contextmenu', event => {
                    const image = event.target?.closest?.('img');
                    const url = image?.currentSrc || image?.src || '';
                    if (image && url) {
                        event.preventDefault();
                        event.stopPropagation();
                        window.__gromCommandQueue.push({
                            action: 'image_context',
                            url: resolvePopupUrl(url),
                            link: resolvePopupUrl(image.closest?.('a[href]')?.href || '')
                        });
                        return;
                    }
                    const target = event.target;
                    let selection = String(window.getSelection?.() || '').trim();
                    if (target && /^(INPUT|TEXTAREA)$/.test(target.tagName)) {
                        const start = target.selectionStart ?? 0;
                        const end = target.selectionEnd ?? start;
                        selection = String(target.value || '').slice(start, end).trim();
                    }
                    const editable = Boolean(
                        target?.isContentEditable
                        || target?.closest?.('[contenteditable="true"]')
                        || target?.matches?.('textarea,input:not([type]),input[type="text"],input[type="search"],input[type="email"],input[type="url"],input[type="tel"]')
                    );
                    if (!selection && !editable) return;
                    event.preventDefault();
                    event.stopPropagation();
                    const inspected = target?.nodeType === Node.TEXT_NODE ? target.parentElement : target;
                    window.__gromCommandQueue.push({
                        action: 'text_context',
                        text: selection.slice(0, 12000),
                        editable,
                        html: String(inspected?.outerHTML || '').slice(0, 20000)
                    });
                }, true);
                window.__gromEditSelection = action => {
                    const active = document.activeElement;
                    if (active && /^(INPUT|TEXTAREA)$/.test(active.tagName)) {
                        const start = active.selectionStart ?? active.value.length;
                        const end = active.selectionEnd ?? start;
                        if (action.type === 'cut') active.setRangeText('', start, end, 'end');
                        if (action.type === 'paste') active.setRangeText(String(action.text || ''), start, end, 'end');
                        active.dispatchEvent(new InputEvent('input', {bubbles:true,inputType:action.type === 'cut'?'deleteByCut':'insertFromPaste',data:action.text || null}));
                        return true;
                    }
                    const selection = window.getSelection?.();
                    if (!selection?.rangeCount) return false;
                    const range = selection.getRangeAt(0);
                    if (!range.commonAncestorContainer.parentElement?.closest?.('[contenteditable="true"]')) return false;
                    range.deleteContents();
                    if (action.type === 'paste') {
                        const node = document.createTextNode(String(action.text || ''));
                        range.insertNode(node);
                        range.setStartAfter(node); range.collapse(true);
                    }
                    selection.removeAllRanges(); selection.addRange(range);
                    document.activeElement?.dispatchEvent(new InputEvent('input', {bubbles:true}));
                    return true;
                };
                const queueLogin = form => {
                    const root = form || document;
                    const passwords = [...root.querySelectorAll?.('input[type="password"]') || []]
                        .filter(input => input.value && input.offsetParent !== null);
                    if (!passwords.length) return;
                    const password = passwords.find(input => /current-password/i.test(input.autocomplete || '')) || passwords[0];
                    const username = root.querySelector?.(
                        'input[autocomplete="username"],input[type="email"],input[name*="login" i],input[name*="user" i],input[type="text"]'
                    ) || document.querySelector('input[autocomplete="username"],input[type="email"]');
                    const payload = {
                        origin: location.origin,
                        username: String(username?.value || '').trim(),
                        password: password.value
                    };
                    if (!payload.username || !payload.password) return;
                    const signature = `${payload.origin}\n${payload.username}\n${payload.password}`;
                    if (window.__gromLastPasswordSignature === signature && Date.now() - Number(window.__gromLastPasswordTime || 0) < 5000) return;
                    window.__gromLastPasswordSignature = signature;
                    window.__gromLastPasswordTime = Date.now();
                    window.__gromPasswordQueue.push(payload);
                };
                document.addEventListener('submit', event => queueLogin(event.target), true);
                document.addEventListener('click', event => {
                    const button = event.target?.closest?.('button,input[type="submit"],[role="button"]');
                    if (!button) return;
                    const form = button.form || button.closest?.('form');
                    if (form?.querySelector?.('input[type="password"]')) queueLogin(form);
                }, true);
            })();
        """
        self.runJavaScript(script)

    def _apply_zoom(self):
        stacking_fix = """
            const hasNegativeBackground = [...document.querySelectorAll('body *')].some(element => {
                const style = getComputedStyle(element);
                const zIndex = Number.parseInt(style.zIndex, 10);
                return (style.position === 'fixed' || style.position === 'absolute')
                    && Number.isFinite(zIndex) && zIndex < 0
                    && style.backgroundImage && style.backgroundImage !== 'none';
            });
            if (hasNegativeBackground && document.body) {
                document.body.style.isolation = 'isolate';
            }
        """
        if self._zoom_percent == 100:
            self.runJavaScript(
                "(() => { document.documentElement.style.removeProperty('zoom');"
                + stacking_fix
                + "})();"
            )
        else:
            self.runJavaScript(
                f"(() => {{ document.documentElement.style.zoom = '{self._zoom_percent}%';"
                + stacking_fix
                + "})();"
            )

    def _apply_font_scale(self):
        scale = self._font_scale_percent
        self.runJavaScript(
            "(() => {"
            "let style=document.getElementById('__gromFontScaleStyle');"
            "if(!style){style=document.createElement('style');style.id='__gromFontScaleStyle';document.head.appendChild(style);}"
            f"style.textContent='html {{ -webkit-text-size-adjust: {scale}% !important; text-size-adjust: {scale}% !important; }}';"
            "})();"
        )

    def apply_permission_policy(self):
        policy = self.permission_policy
        blocked = {
            key: policy.get(key, "ask") == "block"
            for key in (
                "camera", "microphone", "geolocation", "notifications",
                "autoplay", "clipboard", "popups",
            )
        }
        script = f"""
            (() => {{
                window.__gromPermissionBlocks = {json.dumps(blocked)};
                if (window.__gromPermissionBridgeInstalled) return;
                window.__gromPermissionBridgeInstalled = true;
                if (navigator.geolocation) {{
                    const originalGet = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);
                    const originalWatch = navigator.geolocation.watchPosition.bind(navigator.geolocation);
                    const deny = callback => callback?.({{code: 1, message: 'Permission denied by Grom'}});
                    navigator.geolocation.getCurrentPosition = (ok, error, options) => {{
                        if (window.__gromPermissionBlocks.geolocation) return deny(error);
                        return originalGet(ok, error, options);
                    }};
                    navigator.geolocation.watchPosition = (ok, error, options) => {{
                        if (window.__gromPermissionBlocks.geolocation) {{ deny(error); return -1; }}
                        return originalWatch(ok, error, options);
                    }};
                }}
                if (navigator.mediaDevices?.getUserMedia) {{
                    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                    navigator.mediaDevices.getUserMedia = constraints => {{
                        const current = window.__gromPermissionBlocks;
                        if ((current.camera && constraints?.video) || (current.microphone && constraints?.audio)) {{
                            return Promise.reject(new DOMException('Permission denied by Grom', 'NotAllowedError'));
                        }}
                        return original(constraints);
                    }};
                }}
                if (window.Notification) {{
                    try {{
                        const original = Notification.requestPermission.bind(Notification);
                        Notification.requestPermission = (...args) => window.__gromPermissionBlocks.notifications
                            ? Promise.resolve('denied') : original(...args);
                    }} catch (_) {{}}
                }}
                if (!window.__gromPermissionOpenInstalled) {{
                    window.__gromPermissionOpenInstalled = true;
                    const originalOpen = window.open.bind(window);
                    window.open = (...args) => window.__gromPermissionBlocks.popups
                        ? null : originalOpen(...args);
                }}
                if (!window.__gromPermissionClipboardInstalled && navigator.clipboard) {{
                    window.__gromPermissionClipboardInstalled = true;
                    for (const name of ['read','readText','write','writeText']) {{
                        const original = navigator.clipboard[name]?.bind(navigator.clipboard);
                        if (!original) continue;
                        try {{
                            navigator.clipboard[name] = (...args) => window.__gromPermissionBlocks.clipboard
                                ? Promise.reject(new DOMException('Permission denied by Grom', 'NotAllowedError'))
                                : original(...args);
                        }} catch (_) {{}}
                    }}
                }}
                if (!window.__gromPermissionMediaInstalled) {{
                    window.__gromPermissionMediaInstalled = true;
                    window.__gromMediaGestureUntil = 0;
                    const markGesture = () => window.__gromMediaGestureUntil = Date.now() + 1800;
                    document.addEventListener('pointerdown', markGesture, true);
                    document.addEventListener('keydown', markGesture, true);
                    const originalPlay = HTMLMediaElement.prototype.play;
                    HTMLMediaElement.prototype.play = function(...args) {{
                        if (window.__gromPermissionBlocks.autoplay && Date.now() > window.__gromMediaGestureUntil) {{
                            return Promise.reject(new DOMException('Autoplay blocked by Grom', 'NotAllowedError'));
                        }}
                        return originalPlay.apply(this, args);
                    }};
                    if (window.__gromPermissionBlocks.autoplay) {{
                        document.querySelectorAll('video,audio').forEach(media => media.pause());
                    }}
                }}
            }})();
        """
        self.runJavaScript(script)

    def _request_page_icon(self):
        script = """
            (() => {
                const icon = document.querySelector('link[rel~="icon"]');
                if (icon?.href) return icon.href;
                if (location.origin && location.origin !== 'null') {
                    return new URL('/favicon.ico', location.origin).href;
                }
                return '';
            })();
        """
        self.runJavaScript(script, self._download_page_icon)

    def _download_page_icon(self, icon_url):
        url = QUrl(str(icon_url or ""))
        if not url.isValid() or url.scheme() not in ("http", "https"):
            return
        reply = self.network.get(QNetworkRequest(url))
        reply.finished.connect(
            lambda current_reply=reply: self._set_page_icon(current_reply)
        )

    def _set_page_icon(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pixmap = QPixmap()
            if pixmap.loadFromData(reply.readAll()):
                self._icon = QIcon(pixmap)
                self.iconChanged.emit(self._icon)
        reply.deleteLater()
