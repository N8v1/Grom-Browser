from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LANGUAGE = "ru"
try:
    _translations: dict[str, str] = json.loads(
        (ROOT / "ui_translations_en.json").read_text(encoding="utf-8")
    )
except (OSError, json.JSONDecodeError):
    _translations = {}
_translations.update(
    {
        "Русский": "Russian",
        "English": "English",
        "Выбор языка": "Language",
        "Язык интерфейса": "Interface language",
        "О разработчике": "About the developer",
        "Разработчик": "Developer",
        "О Grom Browser": "About Grom Browser",
        "Версия": "Version",
        "Ильин Никита Николаевич N8": "Ilyin Nikita Nikolaevich N8",
    }
)


def fix_mojibake(value: object) -> str:
    """Repair UTF-8 text that was accidentally decoded as Windows-1251."""
    text = str(value or "")
    output: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        try:
            first = char.encode("cp1251")
        except UnicodeEncodeError:
            output.append(char)
            index += 1
            continue
        lead = first[0]
        width = 2 if 0xC2 <= lead <= 0xDF else 3 if 0xE0 <= lead <= 0xEF else 4 if 0xF0 <= lead <= 0xF4 else 0
        if width:
            byte_parts = [first]
            next_index = index + 1
            while next_index < len(text) and len(b"".join(byte_parts)) < width:
                try:
                    byte_parts.append(text[next_index].encode("cp1251"))
                except UnicodeEncodeError:
                    break
                next_index += 1
            joined = b"".join(byte_parts)
            if len(joined) == width:
                try:
                    decoded = joined.decode("utf-8")
                except UnicodeDecodeError:
                    decoded = ""
                if decoded and len(decoded) == 1:
                    output.append(decoded)
                    index += width
                    continue
        output.append(char)
        index += 1
    return "".join(output)


_patterns: list[tuple[re.Pattern[str], str, str]] = []
for source, target in _translations.items():
    if "{value}" not in source:
        continue
    pieces = source.split("{value}")
    regex = "^" + "(.*?)".join(re.escape(piece) for piece in pieces) + "$"
    _patterns.append((re.compile(regex, re.DOTALL), source, target))


def set_language(language: str) -> None:
    global LANGUAGE
    LANGUAGE = "en" if str(language).lower().startswith("en") else "ru"


def get_language() -> str:
    return LANGUAGE


def translate_text(value: object) -> str:
    original = str(value or "")
    clean = fix_mojibake(original)
    if LANGUAGE != "en":
        return clean
    left = clean[: len(clean) - len(clean.lstrip())]
    right = clean[len(clean.rstrip()) :]
    body = clean.strip()
    translated = _translations.get(body)
    if translated is None:
        for pattern, source, target in _patterns:
            match = pattern.match(body)
            if not match:
                continue
            values = iter(match.groups())
            translated = re.sub(r"\{value\}", lambda _match: next(values, ""), target)
            break
    if translated is None:
        translated = body
    return left + translated + right


def translate_html(html: str, language: str | None = None) -> str:
    html = fix_mojibake(html)
    selected = language or LANGUAGE
    if selected != "en":
        return html
    exact = {key: value for key, value in _translations.items() if "{value}" not in key}
    exact.update(
        {
            "Русский": "Russian",
            "Выбор языка": "Language",
            "Язык интерфейса": "Interface language",
            "О разработчике": "About the developer",
            "Разработчик": "Developer",
        }
    )
    rules: list[list[str]] = []
    for source, target in _translations.items():
        if "{value}" not in source:
            continue
        source_parts = source.split("{value}")
        pattern = "^" + "(.*?)".join(re.escape(part) for part in source_parts) + "$"
        replacement = re.sub(
            r"\{value\}",
            lambda match, index=iter(range(1, len(source_parts))): f"${next(index)}",
            target,
        )
        rules.append([pattern, replacement])
    payload = json.dumps(exact, ensure_ascii=False).replace("</", "<\\/")
    rule_payload = json.dumps(rules, ensure_ascii=False).replace("</", "<\\/")
    script = f"""<script>
(()=>{{
const exact={payload},rules={rule_payload};
const attributes=['placeholder','title','aria-label','alt','value'];
function tr(value){{const raw=String(value??''),trimmed=raw.trim();let result=exact[trimmed];if(result===undefined){{for(const [pattern,replacement] of rules){{try{{const match=trimmed.match(new RegExp(pattern,'s'));if(match){{result=trimmed.replace(new RegExp(pattern,'s'),replacement);break}}}}catch(_e){{}}}}}}if(result===undefined)return raw;const lead=raw.match(/^\\s*/)?.[0]||'',tail=raw.match(/\\s*$/)?.[0]||'';return lead+result+tail}}
function visit(node){{if(node.nodeType===Node.TEXT_NODE){{if(!node.parentElement?.closest('script,style,code,pre'))node.nodeValue=tr(node.nodeValue)}}else if(node.nodeType===Node.ELEMENT_NODE){{for(const name of attributes)if(node.hasAttribute(name))node.setAttribute(name,tr(node.getAttribute(name)));for(const child of node.childNodes)visit(child)}}}}
function run(){{document.documentElement.lang='en';if(document.title)document.title=tr(document.title);visit(document.body||document.documentElement)}}
run();new MutationObserver(records=>records.forEach(record=>{{if(record.type==='characterData')visit(record.target);else if(record.type==='attributes')visit(record.target);else record.addedNodes.forEach(visit)}})).observe(document.documentElement,{{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:attributes}});
for(const method of ['alert','confirm','prompt']){{const original=window[method];window[method]=function(message,...args){{return original.call(window,tr(message),...args)}}}}
}})();</script>"""
    closing = html.lower().rfind("</body>")
    return html[:closing] + script + html[closing:] if closing >= 0 else html + script


def install_qt_translation() -> None:
    """Translate Qt widget labels created by the existing Russian UI code."""
    from PySide6.QtGui import QAction, QStandardItem
    from PySide6.QtWidgets import (
        QAbstractButton,
        QComboBox,
        QFileDialog,
        QGroupBox,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidgetItem,
        QMenu,
        QMessageBox,
        QTabBar,
        QTabWidget,
        QTreeWidgetItem,
        QWidget,
    )

    def patch(cls, method_name: str, transform):
        original = getattr(cls, method_name, None)
        if original is None or getattr(original, "_grom_i18n", False):
            return

        def wrapped(self, *args, **kwargs):
            args = transform(args)
            return original(self, *args, **kwargs)

        wrapped._grom_i18n = True
        setattr(cls, method_name, wrapped)

    def first_text(args):
        if not args:
            return args
        return (translate_text(args[0]), *args[1:])

    for method in ("setToolTip", "setStatusTip", "setWhatsThis", "setWindowTitle"):
        patch(QWidget, method, first_text)
    for cls, methods in (
        (QLabel, ("setText",)),
        (QAbstractButton, ("setText",)),
        (QLineEdit, ("setPlaceholderText",)),
        (QGroupBox, ("setTitle",)),
        (QAction, ("setText", "setToolTip", "setStatusTip", "setWhatsThis")),
        (QTabBar, ("setTabText", "setTabToolTip")),
        (QTabWidget, ("setTabText", "setTabToolTip")),
        (QComboBox, ("setItemText",)),
    ):
        for method in methods:
            patch(cls, method, first_text if method not in ("setTabText", "setTabToolTip", "setItemText") else lambda args: (*args[:-1], translate_text(args[-1])) if args else args)

    original_add_item = QComboBox.addItem
    if not getattr(original_add_item, "_grom_i18n", False):
        def add_item(self, *args, **kwargs):
            args = list(args)
            if args and isinstance(args[0], str):
                args[0] = translate_text(args[0])
            elif len(args) > 1 and isinstance(args[1], str):
                args[1] = translate_text(args[1])
            return original_add_item(self, *args, **kwargs)
        add_item._grom_i18n = True
        QComboBox.addItem = add_item
    original_add_items = QComboBox.addItems
    if not getattr(original_add_items, "_grom_i18n", False):
        def add_items(self, values):
            return original_add_items(self, [translate_text(value) for value in values])
        add_items._grom_i18n = True
        QComboBox.addItems = add_items

    original_add_action = QMenu.addAction
    if not getattr(original_add_action, "_grom_i18n", False):
        def add_action(self, *args, **kwargs):
            args = list(args)
            if args and isinstance(args[0], str):
                args[0] = translate_text(args[0])
            elif len(args) > 1 and isinstance(args[1], str) and not isinstance(args[0], QAction):
                args[1] = translate_text(args[1])
            return original_add_action(self, *args, **kwargs)
        add_action._grom_i18n = True
        QMenu.addAction = add_action
    patch(QMenu, "setTitle", first_text)
    for method_name in ("setText", "setInformativeText", "setDetailedText", "setWindowTitle"):
        patch(QMessageBox, method_name, first_text)

    for method_name in ("warning", "critical", "information", "question", "about"):
        original = getattr(QMessageBox, method_name)
        if getattr(original, "_grom_i18n", False):
            continue

        def make_box_wrapper(original_method):
            def wrapped(parent, title, text, *args, **kwargs):
                return original_method(parent, translate_text(title), translate_text(text), *args, **kwargs)
            wrapped._grom_i18n = True
            return staticmethod(wrapped)

        setattr(QMessageBox, method_name, make_box_wrapper(original))

    for cls, method in ((QListWidgetItem, "__init__"), (QStandardItem, "__init__")):
        original = getattr(cls, method)
        if getattr(original, "_grom_i18n", False):
            continue

        def make_item_wrapper(original_method):
            def wrapped(self, *args, **kwargs):
                args = list(args)
                if args and isinstance(args[0], str):
                    args[0] = translate_text(args[0])
                elif len(args) > 1 and isinstance(args[1], str):
                    args[1] = translate_text(args[1])
                return original_method(self, *args, **kwargs)
            wrapped._grom_i18n = True
            return wrapped

        setattr(cls, method, make_item_wrapper(original))

    original_tree_init = QTreeWidgetItem.__init__
    if not getattr(original_tree_init, "_grom_i18n", False):
        def tree_init(self, *args, **kwargs):
            args = list(args)
            if args and isinstance(args[0], (list, tuple)):
                args[0] = [translate_text(value) for value in args[0]]
            return original_tree_init(self, *args, **kwargs)
        tree_init._grom_i18n = True
        QTreeWidgetItem.__init__ = tree_init

    for method_name in ("getText", "getItem", "getInt", "getDouble"):
        original = getattr(QInputDialog, method_name)
        if getattr(original, "_grom_i18n", False):
            continue

        def make_input_wrapper(original_method):
            def wrapped(*args, **kwargs):
                args = list(args)
                if len(args) > 1:
                    args[1] = translate_text(args[1])
                if len(args) > 2:
                    args[2] = translate_text(args[2])
                return original_method(*args, **kwargs)
            wrapped._grom_i18n = True
            return staticmethod(wrapped)

        setattr(QInputDialog, method_name, make_input_wrapper(original))

    for method_name in ("getOpenFileName", "getSaveFileName", "getOpenFileNames", "getExistingDirectory"):
        original = getattr(QFileDialog, method_name)
        if getattr(original, "_grom_i18n", False):
            continue

        def make_file_wrapper(original_method):
            def wrapped(*args, **kwargs):
                args = list(args)
                if len(args) > 1:
                    args[1] = translate_text(args[1])
                if len(args) > 3 and isinstance(args[3], str):
                    args[3] = translate_text(args[3])
                return original_method(*args, **kwargs)
            wrapped._grom_i18n = True
            return staticmethod(wrapped)

        setattr(QFileDialog, method_name, make_file_wrapper(original))
