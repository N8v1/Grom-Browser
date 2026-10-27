from __future__ import annotations

import time
import uuid

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class TabCloseButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_color = QColor("#d7d9dd")
        self._hover_line_color = QColor("#ffffff")

    def set_line_color(self, color, hover_color=None):
        self._line_color = QColor(color)
        self._hover_line_color = QColor(hover_color or color)
        self.update()

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        line_color = self._hover_line_color if self.underMouse() else self._line_color
        painter.setPen(QPen(line_color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center = self.rect().center()
        radius = 3.7
        painter.drawLine(QPointF(center.x() - radius, center.y() - radius), QPointF(center.x() + radius, center.y() + radius))
        painter.drawLine(QPointF(center.x() + radius, center.y() - radius), QPointF(center.x() - radius, center.y() + radius))

class ChromeTabBar(QTabBar):
    newTabRequested = Signal()
    tabContextMenuRequested = Signal(int, QPoint)
    tabCloseAnimationFinished = Signal(int)
    tabDetachRequested = Signal(object, QPoint)
    externalUrlDropped = Signal(QUrl)
    tabHoverChanged = Signal(int, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Qt's built-in movable tab only drags its label/button proxy when the
        # tab background is custom-painted.  Reordering is handled below so the
        # drag preview contains the complete tab surface.
        self.setMovable(False)
        self.setTabsClosable(True)
        self.setExpanding(False)
        self.setDocumentMode(True)
        self.setDrawBase(False)
        self.setUsesScrollButtons(True)
        self.setElideMode(Qt.TextElideMode.ElideNone)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setSelectionBehaviorOnRemove(QTabBar.SelectionBehavior.SelectPreviousTab)
        self.setIconSize(QSize(16, 16))
        self._animated_widths = {}
        self._animations = []
        self._closing_indexes = set()
        self._group_colors = {}
        self._sleeping_tabs = set()
        self._detach_tab_id = None
        self._detach_start_position = QPoint()
        self._detach_distance_reached = False
        self._drag_active = False
        self._drag_index = -1
        self._drag_hotspot = QPoint()
        self._drag_preview = None
        self._hover_index = -1
        self.animations_enabled = True
        self._fade_colors = {
            "normal": QColor("#202124"),
            "selected": QColor("#35363a"),
            "hover": QColor("#292a2d"),
        }
        self._text_colors = {
            "normal": QColor("#bdc1c6"),
            "selected": QColor("#f1f3f4"),
            "hover": QColor("#e8eaed"),
        }

    def final_tab_width(self):
        available = max(320, self.window().width() - 110)
        preferred_width = 220
        return (
            preferred_width
            if self.count() * preferred_width <= available
            else max(84, available // max(1, self.count()))
        )

    def tabSizeHint(self, index):
        return QSize(self._animated_widths.get(index, self.final_tab_width()), 34)

    def tabInserted(self, index):
        super().tabInserted(index)
        self.setTabData(index, uuid.uuid4().hex)
        close_button = TabCloseButton(self)
        close_button.setObjectName("tabCloseButton")
        close_button.setToolTip("Закрыть вкладку")
        close_button.setFixedSize(24, 24)
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(
            lambda _checked=False, button=close_button: self._close_button_clicked(button)
        )
        self.setTabButton(index, QTabBar.ButtonPosition.RightSide, close_button)
        QTimer.singleShot(0, lambda current=index: self.animate_inserted_tab(current))

    def animate_inserted_tab(self, index):
        if index < 0 or index >= self.count():
            return
        if not self.animations_enabled:
            return
        target = self.final_tab_width()
        animation = QVariantAnimation(self)
        animation.setDuration(230)
        animation.setStartValue(42)
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.valueChanged.connect(
            lambda value, current=index: self.set_animated_width(current, int(value))
        )
        animation.finished.connect(
            lambda current=index, current_animation=animation: self.finish_tab_animation(
                current, current_animation
            )
        )
        self._animations.append(animation)
        animation.start()

    def animate_close(self, index):
        if index < 0 or index >= self.count() or self._closing_indexes:
            return
        for running in list(self._animations):
            running.stop()
            running.deleteLater()
        self._animations.clear()
        self._animated_widths.clear()
        self._closing_indexes.add(index)
        start = max(24, self.tabRect(index).width())
        animation = QVariantAnimation(self)
        animation.setDuration(190)
        animation.setStartValue(start)
        animation.setEndValue(20)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        animation.valueChanged.connect(
            lambda value, current=index: self.set_animated_width(current, int(value))
        )
        animation.finished.connect(
            lambda current=index, current_animation=animation: self.finish_close_animation(
                current, current_animation
            )
        )
        self._animations.append(animation)
        animation.start()

    def finish_close_animation(self, index, animation):
        if animation in self._animations:
            self._animations.remove(animation)
        animation.deleteLater()
        self._closing_indexes.discard(index)
        self.tabCloseAnimationFinished.emit(index)

    def set_animated_width(self, index, width):
        if 0 <= index < self.count():
            self._animated_widths[index] = width
            self.tabLayoutChange()
            current_size = self.size()
            self.resize(current_size.width() + 1, current_size.height())
            self.resize(current_size)
            self.updateGeometry()
            self.update()

    def finish_tab_animation(self, index, animation):
        self._animated_widths.pop(index, None)
        if animation in self._animations:
            self._animations.remove(animation)
        animation.deleteLater()
        self.tabLayoutChange()
        self.updateGeometry()
        self.update()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._animated_widths = {
            (key - 1 if key > index else key): value
            for key, value in self._animated_widths.items()
            if key != index
        }
        self._closing_indexes = {
            key - 1 if key > index else key
            for key in self._closing_indexes
            if key != index
        }

    def set_fade_colors(self, normal, selected, hover, text=None, muted=None):
        self._fade_colors = {
            "normal": QColor(normal),
            "selected": QColor(selected),
            "hover": QColor(hover),
        }
        if text is not None and muted is not None:
            self._text_colors = {
                "normal": QColor(muted),
                "selected": QColor(text),
                "hover": QColor(text),
            }
        self.update()

    def set_group_colors(self, colors):
        self._group_colors = {
            int(index): QColor(color) for index, color in colors.items() if QColor(color).isValid()
        }
        self.update()

    def set_sleeping_tabs(self, indexes):
        self._sleeping_tabs = {int(index) for index in indexes}
        self.update()

    def paintEvent(self, event):
        hovered = self.tabAt(self.mapFromGlobal(QCursor.pos()))
        painter = QStylePainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index in range(self.count()):
            option = QStyleOptionTab()
            self.initStyleOption(option, index)
            option.text = ""
            option.icon = QIcon()
            if self._detach_tab_id is not None and self.tabData(index) == self._detach_tab_id and self._drag_active:
                painter.save()
                painter.setOpacity(0.28)
                painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, option)
                painter.restore()
                continue
            painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, option)

        painter.setPen(Qt.PenStyle.NoPen)
        for index, color in self._group_colors.items():
            if 0 <= index < self.count():
                rect = self.tabRect(index)
                painter.setBrush(color)
                painter.drawRect(rect.left() + 7, rect.bottom() - 2, max(0, rect.width() - 14), 3)
        for index in range(self.count()):
            rect = self.tabRect(index)
            if self._detach_tab_id is not None and self.tabData(index) == self._detach_tab_id and self._drag_active:
                continue
            color_key = "selected" if index == self.currentIndex() else "hover" if index == hovered else "normal"
            icon_space = 26 if not self.tabIcon(index).isNull() else 0
            text_rect = rect.adjusted(13 + icon_space, 0, -37, 0)
            if text_rect.width() < 8:
                continue
            icon = self.tabIcon(index)
            if not icon.isNull() and rect.width() >= 62:
                icon.paint(
                    painter,
                    QRect(rect.left() + 13, rect.center().y() - 8, 16, 16),
                    Qt.AlignmentFlag.AlignCenter,
                )
            title = self.tabText(index)
            metrics = painter.fontMetrics()
            is_long = metrics.horizontalAdvance(title) > text_rect.width()
            painter.save()
            painter.setClipRect(text_rect)
            painter.setPen(self._text_colors[color_key])
            alignment = Qt.AlignmentFlag.AlignVCenter | (
                Qt.AlignmentFlag.AlignLeft if is_long else Qt.AlignmentFlag.AlignHCenter
            )
            painter.drawText(text_rect, alignment, title)
            painter.restore()
            if not is_long:
                continue
            background = QColor(self._fade_colors[color_key])
            transparent = QColor(background)
            transparent.setAlpha(0)
            fade_right = text_rect.right()
            fade_left = max(text_rect.left(), fade_right - 32)
            gradient = QLinearGradient(fade_left, 0, fade_right, 0)
            gradient.setColorAt(0, transparent)
            gradient.setColorAt(0.82, background)
            gradient.setColorAt(1, background)
            painter.fillRect(QRect(fade_left, rect.top(), fade_right - fade_left + 1, rect.height()), gradient)
        for index in self._sleeping_tabs:
            if 0 <= index < self.count():
                rect = self.tabRect(index)
                veil = QColor(self._fade_colors["normal"])
                veil.setAlpha(175)
                painter.fillRect(rect.adjusted(1, 1, -1, -1), veil)

    def contextMenuEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0:
            self.tabContextMenuRequested.emit(index, event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)

    def dragEnterEvent(self, event):
        if event.source() is not self and (
            event.mimeData().hasUrls() or event.mimeData().hasText()
        ):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.source() is self:
            super().dropEvent(event)
            return
        url = QUrl()
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                url = QUrl(urls[0])
        elif event.mimeData().hasText():
            value = event.mimeData().text().strip()
            if value:
                url = QUrl.fromUserInput(value)
        if url.isValid() and not url.isEmpty():
            self.externalUrlDropped.emit(url)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _close_button_clicked(self, button):
        for index in range(self.count()):
            if self.tabButton(index, QTabBar.ButtonPosition.RightSide) == button:
                self.tabCloseRequested.emit(index)
                return

    def mouseReleaseEvent(self, event):
        index = self.tabAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.MiddleButton and index >= 0:
            self.tabCloseRequested.emit(index)
            event.accept()
            return
        detach_id = self._detach_tab_id
        release_position = event.position().toPoint()
        outside_strip = release_position.y() < -24 or release_position.y() > self.height() + 24
        outside_window = not self.window().frameGeometry().contains(event.globalPosition().toPoint())
        should_detach = (
            event.button() == Qt.MouseButton.LeftButton
            and detach_id is not None
            and self._detach_distance_reached
            and (outside_strip or outside_window)
        )
        if self._drag_active:
            self._finish_tab_drag()
            self._detach_tab_id = None
            self._detach_distance_reached = False
            event.accept()
            if should_detach:
                self.tabDetachRequested.emit(detach_id, event.globalPosition().toPoint())
            return
        super().mouseReleaseEvent(event)
        self._detach_tab_id = None
        self._detach_distance_reached = False
        if should_detach:
            self.tabDetachRequested.emit(detach_id, event.globalPosition().toPoint())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.tabAt(event.position().toPoint())
            self._detach_tab_id = self.tabData(index) if index >= 0 else None
            self._detach_start_position = event.position().toPoint()
            self._detach_distance_reached = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._detach_tab_id is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            distance = (event.position().toPoint() - self._detach_start_position).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._detach_distance_reached = True
                if not self._drag_active:
                    self._begin_tab_drag()
                if self._drag_active:
                    self._move_tab_drag(event.globalPosition().toPoint())
                    self._reorder_dragged_tab(event.position().toPoint())
                    event.accept()
                    return
        super().mouseMoveEvent(event)
        index = self.tabAt(event.position().toPoint())
        if index != self._hover_index:
            self._hover_index = index
            self.tabHoverChanged.emit(index, event.globalPosition().toPoint())

    def leaveEvent(self, event):
        self._hover_index = -1
        self.tabHoverChanged.emit(-1, QCursor.pos())
        super().leaveEvent(event)

    def event(self, event):
        if event.type() == QEvent.Type.ToolTip:
            event.accept()
            return True
        return super().event(event)

    def _tab_index_for_id(self, tab_id):
        for index in range(self.count()):
            if self.tabData(index) == tab_id:
                return index
        return -1

    def _begin_tab_drag(self):
        index = self._tab_index_for_id(self._detach_tab_id)
        if index < 0:
            return
        rect = self.tabRect(index)
        preview = QLabel(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowTransparentForInput)
        preview.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        preview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        preview.setPixmap(self.grab(rect))
        preview.setFixedSize(rect.size())
        preview.setWindowOpacity(0.96)
        self._drag_hotspot = self._detach_start_position - rect.topLeft()
        self._drag_index = index
        self._drag_preview = preview
        close_button = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
        if close_button:
            close_button.hide()
        preview.move(QCursor.pos() - self._drag_hotspot)
        preview.show()
        preview.raise_()
        self._drag_active = True
        self.update()

    def _move_tab_drag(self, global_position):
        if self._drag_preview:
            self._drag_preview.move(global_position - self._drag_hotspot)

    def _reorder_dragged_tab(self, local_position):
        current = self._tab_index_for_id(self._detach_tab_id)
        target = self.tabAt(local_position)
        if current < 0 or target < 0 or target == current:
            return
        target_rect = self.tabRect(target)
        crossed = (
            target > current and local_position.x() >= target_rect.center().x()
        ) or (
            target < current and local_position.x() <= target_rect.center().x()
        )
        if not crossed:
            return
        self.moveTab(current, target)
        self._drag_index = target
        self.update()

    def _finish_tab_drag(self):
        index = self._tab_index_for_id(self._detach_tab_id)
        if index >= 0:
            close_button = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
            if close_button:
                close_button.show()
        if self._drag_preview:
            self._drag_preview.close()
            self._drag_preview.deleteLater()
        self._drag_preview = None
        self._drag_index = -1
        self._drag_active = False
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.tabAt(event.position().toPoint()) < 0:
            self.newTabRequested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

class TabWorkspace(QWidget):
    activeBrowserChanged = Signal(object)

    def __init__(self, primary_browser, parent=None):
        super().__init__(parent)
        self.setObjectName("tabWorkspace")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#tabWorkspace { background:#202124; }")
        self.primary_browser = primary_browser
        self.secondary_browser = None
        self.secondary_widget = None
        self.active_browser = primary_browser
        self.group_id = None
        self.last_active = time.time()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(4)
        self.splitter.setStyleSheet("QSplitter::handle { background: #4b4c50; }")
        self.splitter.addWidget(primary_browser)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

    def set_active_browser(self, browser):
        if browser and browser != self.active_browser:
            self.active_browser = browser
            self.activeBrowserChanged.emit(browser)

    def set_secondary_widget(self, widget, browser=None):
        self.close_split()
        self.secondary_widget = widget
        self.secondary_browser = browser
        self.splitter.addWidget(widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        QTimer.singleShot(0, self.balance_split)
        if browser:
            self.set_active_browser(browser)

    def balance_split(self):
        half = max(320, self.splitter.width() // 2)
        self.splitter.setSizes([half, half])

    def close_split(self):
        if self.secondary_widget:
            widget = self.secondary_widget
            self.secondary_widget = None
            self.secondary_browser = None
            widget.setParent(None)
            widget.deleteLater()
        self.set_active_browser(self.primary_browser)

    def is_split(self):
        return self.secondary_widget is not None
