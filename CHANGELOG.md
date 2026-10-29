# Changelog

## 1.1.2 — 2026-10-30

### Fixed

- Twitch's Google sign-in popup now exposes the expected `window` and `self` references, allowing Twitch's own OAuth URL to open in a Grom tab.
- The light theme now paints the built-in extensions panel and its scroll area with the correct background.

### Changed

- Restored the original vertical layout of the three-dot browser menu.
- Replaced the start-page submit character with a bold SVG arrow.
- Fixed search on the Grom start page: searches now start when you press Enter or select a suggestion.

## Журнал изменений

### Исправлено

- Вход Twitch через Google: всплывающее OAuth-окно Grom теперь поддерживает свойства `window` и `self`, которые ожидает страница Twitch.
- В светлой теме фон панели расширений и области прокрутки теперь отображается светлым.
- Исправлен поиск на главной странице Grom: запрос запускается при нажатии Enter и при выборе подсказки.

### Изменено

- Возвращён прежний вертикальный вид меню браузера на три точки.
- На стартовой странице Grom символ отправки заменён на более жирную SVG-стрелку.
