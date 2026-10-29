from __future__ import annotations

import base64
import html as html_lib
import json
import os

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMenu,
)


BUILTIN_EXTENSION_DEFINITIONS = (
    {
        "id": "ad_blocker",
        "name": "Grom Block & Privacy",
        "description": "Блокирует рекламу и трекеры, очищает ссылки и скрывает навязчивые cookie-баннеры.",
        "enabled": True,
        "glyph": "B",
        "color": "#d84a4a",
    },
    {
        "id": "dark_pages",
        "name": "Тёмные страницы",
        "description": "Создаёт тёмную тему для сайтов, у которых нет собственного тёмного оформления.",
        "enabled": False,
        "glyph": "D",
        "color": "#3f4659",
    },
    {
        "id": "password_manager",
        "name": "Менеджер паролей",
        "description": "Сохраняет и подставляет пароли через защищённое хранилище Windows Credential Manager.",
        "enabled": False,
        "glyph": "K",
        "color": "#596fcb",
    },
    {
        "id": "audio_enhancer",
        "name": "Эквалайзер и усиление звука",
        "description": "Усиливает звук до 600% и настраивает низкие и высокие частоты.",
        "enabled": False,
        "glyph": "EQ",
        "color": "#487ee8",
    },
    {
        "id": "video_speed",
        "name": "Скорость видео",
        "description": "Применяет выбранную скорость ко всем новым видео на странице.",
        "enabled": False,
        "glyph": "x",
        "color": "#d98735",
    },
    {
        "id": "prevent_autoplay",
        "name": "Остановка автовоспроизведения",
        "description": "Приостанавливает видео и аудио, запущенные без действия пользователя.",
        "enabled": False,
        "glyph": "P",
        "color": "#64748b",
    },
    {
        "id": "youtube_insights",
        "name": "Grom YouTube Enhancer",
        "description": "Настраивает интерфейс YouTube и дополняет его локальным анализом заголовка, описания и ключевых слов.",
        "enabled": False,
        "glyph": "YT",
        "color": "#e53935",
    },
    {
        "id": "twitch_enhancer",
        "name": "Grom Twitch Enhancer",
        "description": "Автосбор бонусов, компактный интерфейс, очистка рекомендаций и улучшения чата Twitch.",
        "enabled": False,
        "glyph": "T",
        "color": "#9147ff",
    },
    {
        "id": "faceit_enhancer",
        "name": "Grom FACEIT Enhancer",
        "description": "Подсвечивает статистику матчей, упрощает карточки игроков и может автоматически принимать найденный матч.",
        "enabled": False,
        "glyph": "F",
        "color": "#ff5500",
    },
)


def default_builtin_extensions():
    return {item["id"]: bool(item["enabled"]) for item in BUILTIN_EXTENSION_DEFINITIONS}


class EqualizerCurve(QWidget):
    def __init__(self, color="#8ab4f8", parent=None):
        super().__init__(parent)
        self.values = [0] * 10
        self.color = QColor(color)
        self.setMinimumHeight(92)

    def set_values(self, values):
        self.values = [max(-12, min(12, float(value))) for value in values]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 22))
        painter.setPen(QPen(QColor(128, 132, 140, 90), 1))
        center = self.rect().center().y()
        painter.drawLine(8, center, self.width() - 8, center)
        if len(self.values) < 2:
            return
        path = QPainterPath()
        usable_width = max(1, self.width() - 16)
        usable_height = max(1, self.height() - 16)
        for index, value in enumerate(self.values):
            x = 8 + usable_width * index / (len(self.values) - 1)
            y = 8 + usable_height * (12 - value) / 24
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.setPen(QPen(self.color, 2.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)


class BuiltinExtensionsMixin:
    def builtin_extension_state(self):
        defaults = default_builtin_extensions()
        defaults["ad_blocker"] = bool(self.app_settings.get("ad_blocker", True))
        defaults["password_manager"] = bool(self.app_settings.get("password_manager", False))
        saved = self.app_settings.get("builtin_extensions", {})
        if isinstance(saved, dict):
            defaults.update({key: bool(value) for key, value in saved.items() if key in defaults})
        return defaults

    def builtin_extension_config(self):
        equalizer = []
        for frequency in (32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000):
            equalizer.append(max(-12, min(12, int(
                self.app_settings.get(f"audio_eq_{frequency}", 0)
            ))))
        return {
            "enabled": self.builtin_extension_state(),
            "ui": {
                "background": self.theme_colors["popup"],
                "surface": self.theme_colors["surface"],
                "text": self.theme_colors["text"],
                "muted": self.theme_colors["muted"],
                "accent": self.theme_colors["accent"],
                "border": self.theme_colors["border"],
            },
            "blocker": {
                "strict": bool(self.app_settings.get("blocker_strict", True)),
                "cleanLinks": bool(self.app_settings.get("blocker_clean_links", True)),
                "cookieBanners": bool(self.app_settings.get("blocker_cookie_banners", True)),
                "customFilters": [
                    value.strip().lower().lstrip(".")
                    for value in str(self.app_settings.get("blocker_custom_filters", "")).replace("\n", ",").split(",")
                    if value.strip()
                ],
                "allowlist": [
                    value.strip().lower().lstrip(".")
                    for value in str(self.app_settings.get("blocker_allowlist", "")).replace("\n", ",").split(",")
                    if value.strip()
                ],
            },
            "audio": {
                "volume": max(0, min(600, int(self.app_settings.get("audio_boost", 100)))),
                "equalizer": equalizer,
            },
            "videoSpeed": max(0.25, min(10.0, float(self.app_settings.get("video_speed", 1.0)))),
            "youtube": {
                "panel": bool(self.app_settings.get("youtube_insights_panel", True)),
                "hideShorts": bool(self.app_settings.get("youtube_hide_shorts", False)),
                "hideComments": bool(self.app_settings.get("youtube_hide_comments", False)),
                "hideLiveChat": bool(self.app_settings.get("youtube_hide_live_chat", False)),
                "hideRecommendations": bool(self.app_settings.get("youtube_hide_recommendations", False)),
                "hideEndScreens": bool(self.app_settings.get("youtube_hide_end_screens", False)),
            },
            "twitch": {
                "autoPoints": bool(self.app_settings.get("twitch_auto_points", True)),
                "compactChat": bool(self.app_settings.get("twitch_compact_chat", False)),
                "emoteSize": max(16, min(64, int(self.app_settings.get("twitch_emote_size", 28)))),
                "hideChat": bool(self.app_settings.get("twitch_hide_chat", False)),
                "hideSidebar": bool(self.app_settings.get("twitch_hide_sidebar", False)),
                "hideRecommendations": bool(self.app_settings.get("twitch_hide_recommendations", False)),
                "hideExtensions": bool(self.app_settings.get("twitch_hide_extensions", False)),
                "visibleChatters": bool(self.app_settings.get("twitch_visible_chatters", True)),
                "chatMedia": bool(self.app_settings.get("twitch_chat_media", True)),
                "pinStreamers": bool(self.app_settings.get("twitch_pin_streamers", True)),
                "channelTools": bool(self.app_settings.get("twitch_channel_tools", True)),
                "highlightMentions": bool(self.app_settings.get("twitch_highlight_mentions", True)),
                "streamLatency": bool(self.app_settings.get("twitch_stream_latency", True)),
                "vodTime": bool(self.app_settings.get("twitch_vod_time", True)),
                "clipDownload": bool(self.app_settings.get("twitch_clip_download", True)),
                "messageMenu": bool(self.app_settings.get("twitch_message_menu", True)),
                "localWatchtime": bool(self.app_settings.get("twitch_local_watchtime", True)),
            },
            "faceit": {
                "compact": bool(self.app_settings.get("faceit_compact_cards", True)),
                "highlightStats": bool(self.app_settings.get("faceit_highlight_stats", True)),
                "autoAccept": bool(self.app_settings.get("faceit_auto_accept", False)),
            },
        }

    def apply_builtin_extensions(self, browser):
        if not browser or browser.internal_page:
            return
        config = json.dumps(self.builtin_extension_config(), ensure_ascii=False)
        browser.runJavaScript(
            r"""
            (() => {
                window.__gromBuiltinsConfig = __CONFIG__;
                const config = () => window.__gromBuiltinsConfig || {enabled:{},audio:{},videoSpeed:1};
                const enabled = name => Boolean(config().enabled?.[name]);
                window.__gromBuiltinStats = window.__gromBuiltinStats || {ad_blocker:0,twitch_enhancer:0};
                const adPattern = /(?:^|[./-])(doubleclick|googlesyndication|googleadservices|adservice|adnxs|adsrvr|criteo|taboola|outbrain|amazon-adsystem|rubiconproject|pubmatic|openx|yieldmo|smartadserver|casalemedia|moatads|serving-sys|bidswitch|lijit|zedo|exoclick|popads|propellerads|trafficjunky)(?:[./-]|$)/i;
                const trackerPattern = /(?:^|[./-])(google-analytics|googletagmanager|analytics\.google|facebook\.net|connect\.facebook|clarity\.ms|hotjar|segment\.io|mixpanel|amplitude|matomo|metrika|mc\.yandex|pixel|scorecardresearch|quantserve|newrelic|sentry|fullstory|mouseflow|crazyegg|branch\.io|appsflyer)(?:[./-]|$)/i;
                const domainMatches = (host, rules) => (rules || []).some(rule => host === rule || host.endsWith('.' + rule));
                const blockerActive = () => enabled('ad_blocker') && !domainMatches(location.hostname.toLowerCase(), config().blocker?.allowlist);
                const blockedKind = value => {
                    const url = String(value || '');
                    if (!blockerActive()) return '';
                    let host = '';
                    try { host = new URL(url, location.href).hostname.toLowerCase(); } catch (_) {}
                    if (domainMatches(host, config().blocker?.customFilters) || adPattern.test(url) || (config().blocker?.strict && trackerPattern.test(url))) return 'ad_blocker';
                    return '';
                };
                const countBlock = kind => {
                    if (kind) window.__gromBuiltinStats[kind] = Number(window.__gromBuiltinStats[kind] || 0) + 1;
                    return Boolean(kind);
                };

                function cleanUrl(value) {
                    try {
                        const url = new URL(value, location.href);
                        ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','utm_id','utm_name','gclid','dclid','fbclid','yclid','msclkid','mc_cid','mc_eid','igshid','ref_src','ref_url']
                            .forEach(key => url.searchParams.delete(key));
                        return url.href;
                    } catch (_) { return value; }
                }

                function applyMedia(media) {
                    if (!(media instanceof HTMLMediaElement)) return;
                    if (enabled('prevent_autoplay') && media.autoplay && !media.dataset.gromUserStarted) {
                        media.autoplay = false;
                        media.pause();
                    }
                    if (enabled('video_speed')) media.playbackRate = Number(config().videoSpeed || 1);
                    else if (media.dataset.gromSpeedApplied) media.playbackRate = 1;
                    media.dataset.gromSpeedApplied = '1';

                    const audio = config().audio || {};
                    const shouldEnhance = enabled('audio_enhancer');
                    const existing = media.__gromAudioNodes;
                    if (existing) {
                        existing.gain.gain.value = shouldEnhance ? Number(audio.volume || 100) / 100 : 1;
                        existing.filters.forEach((filter, index) => {
                            filter.gain.value = shouldEnhance ? Number(audio.equalizer?.[index] || 0) : 0;
                        });
                        return;
                    }
                    if (!shouldEnhance) return;
                    try {
                        const Context = window.AudioContext || window.webkitAudioContext;
                        if (!Context) return;
                        const context = new Context();
                        const source = context.createMediaElementSource(media);
                        const gain = context.createGain();
                        const frequencies = [32,64,125,250,500,1000,2000,4000,8000,16000];
                        const filters = frequencies.map((frequency, index) => {
                            const filter = context.createBiquadFilter();
                            filter.type = index === 0 ? 'lowshelf' : index === frequencies.length - 1 ? 'highshelf' : 'peaking';
                            filter.frequency.value = frequency;
                            filter.Q.value = 1.05;
                            return filter;
                        });
                        let node = source;
                        filters.forEach(filter => { node.connect(filter); node = filter; });
                        node.connect(gain).connect(context.destination);
                        media.__gromAudioNodes = {context, source, filters, gain};
                        applyMedia(media);
                    } catch (_) {}
                }

                function applyDarkPages() {
                    const active = enabled('dark_pages');
                    const root = document.documentElement;
                    if (!root) return;
                    root.classList.toggle('__gromDarkPages', active);
                    let style = document.getElementById('__gromDarkPagesStyle');
                    if (!active) {
                        style?.remove();
                        const changed = window.__gromDarkPageElements;
                        if (style || changed?.size) {
                            for (const [element, saved] of (changed || [])) {
                                if (!element?.isConnected) continue;
                                element.style.backgroundColor = saved.backgroundColor;
                                element.style.color = saved.color;
                                element.style.borderColor = saved.borderColor;
                            }
                            window.__gromDarkPageElements = new Map();
                            window.__gromDarkInspected = new WeakSet();
                        }
                        return;
                    }
                    if (!style) {
                        style = document.createElement('style');
                        style.id = '__gromDarkPagesStyle';
                        style.textContent = `
                            html.__gromDarkPages { color-scheme:dark!important; background:#15171a!important }
                            html.__gromDarkPages body { background:#15171a!important; color:#e8eaed!important }
                            html.__gromDarkPages a { color:#8ab4f8 }
                            html.__gromDarkPages input,html.__gromDarkPages textarea,html.__gromDarkPages select,
                            html.__gromDarkPages button { color-scheme:dark }
                        `;
                        document.head?.append(style);
                    }
                    const saved = window.__gromDarkPageElements ||= new Map();
                    const inspected = window.__gromDarkInspected ||= new WeakSet();
                    const luminance = value => {
                        const match = String(value).match(/[\d.]+/g);
                        if (!match || match.length < 3) return -1;
                        const [r,g,b,a=1] = match.map(Number);
                        if (a === 0) return -1;
                        return (0.2126*r + 0.7152*g + 0.0722*b) / 255;
                    };
                    [...document.body.querySelectorAll('*')].slice(0, 3500).forEach(element => {
                        if (inspected.has(element)) return;
                        inspected.add(element);
                        if (element.closest('img,video,canvas,svg,picture')) return;
                        const computed = getComputedStyle(element);
                        const background = luminance(computed.backgroundColor);
                        const foreground = luminance(computed.color);
                        const border = luminance(computed.borderTopColor);
                        if (background < .72 && foreground > .28 && border < .72) return;
                        if (!saved.has(element)) saved.set(element, {
                            backgroundColor: element.style.backgroundColor,
                            color: element.style.color,
                            borderColor: element.style.borderColor
                        });
                        if (background >= .72) {
                            const shade = Math.max(18, Math.round(42 - (background - .72) * 35));
                            element.style.setProperty('background-color', `rgb(${shade},${shade + 1},${shade + 3})`, 'important');
                        }
                        if (foreground >= 0 && foreground < .42)
                            element.style.setProperty('color', '#e3e6eb', 'important');
                        if (border >= .72)
                            element.style.setProperty('border-color', '#4b4f56', 'important');
                    });
                }

                function applyYouTubeInsights() {
                    const active = enabled('youtube_insights') && /(^|\.)youtube\.com$/i.test(location.hostname);
                    if (window.__gromYouTubeInsightsUrl !== location.href) {
                        window.__gromYouTubeInsightsUrl = location.href;
                        window.__gromYouTubePanelDismissed = false;
                    }
                    document.getElementById('__gromYouTubeInsights')?.toggleAttribute('hidden', !active || !config().youtube?.panel || window.__gromYouTubePanelDismissed);
                    let style = document.getElementById('__gromYouTubeStyle');
                    if (!active) { style?.remove(); return; }
                    if (!style) {
                        style = document.createElement('style');
                        style.id = '__gromYouTubeStyle';
                        document.head?.append(style);
                    }
                    const rules = [];
                    if (config().youtube?.hideShorts) rules.push('ytd-rich-section-renderer,ytd-reel-shelf-renderer,ytd-guide-entry-renderer a[title="Shorts"],ytd-mini-guide-entry-renderer[aria-label*="Shorts" i]{display:none!important}');
                    if (config().youtube?.hideComments) rules.push('ytd-comments#comments,ytd-item-section-renderer#sections.ytd-comments{display:none!important}');
                    if (config().youtube?.hideLiveChat) rules.push('ytd-live-chat-frame#chat,#chat-container.ytd-watch-flexy{display:none!important}');
                    if (config().youtube?.hideRecommendations) rules.push('#related.ytd-watch-flexy,ytd-watch-next-secondary-results-renderer{display:none!important}');
                    if (config().youtube?.hideEndScreens) rules.push('.ytp-ce-element,.ytp-endscreen-content,.ytp-cards-teaser{display:none!important}');
                    style.textContent = rules.join('\n');
                    if (!config().youtube?.panel || !location.pathname.startsWith('/watch')) return;
                    let panel = document.getElementById('__gromYouTubeInsights');
                    if (!panel) {
                        panel = document.createElement('aside');
                        panel.id = '__gromYouTubeInsights';
                        panel.innerHTML = '<button data-grom-close title="Свернуть">×</button><b>Grom Insights</b><div data-grom-score></div><small data-grom-details></small><button data-grom-tags>Копировать ключевые слова</button>';
                        panel.style.cssText = 'position:fixed;right:18px;bottom:18px;z-index:2147483000;width:280px;padding:14px;color:#f5f7fa;background:#202124;border:1px solid #4f545c;border-radius:8px;box-shadow:0 12px 34px #0008;font:13px Segoe UI,sans-serif';
                        panel.querySelector('[data-grom-close]').style.cssText = 'float:right;border:0;background:transparent;color:#fff;font-size:18px;cursor:pointer';
                        panel.querySelector('[data-grom-tags]').style.cssText = 'margin-top:10px;padding:7px 9px;border:0;border-radius:5px;background:#8ab4f8;color:#111;cursor:pointer';
                        panel.querySelector('[data-grom-close]').onclick = () => { window.__gromYouTubePanelDismissed = true; panel.hidden = true; };
                        panel.querySelector('[data-grom-tags]').onclick = () => navigator.clipboard?.writeText(document.querySelector('meta[name="keywords"]')?.content || '');
                        document.documentElement.append(panel);
                    }
                    const title = document.querySelector('meta[name="title"]')?.content || document.title.replace(/\s*-\s*YouTube\s*$/, '');
                    const description = document.querySelector('meta[name="description"]')?.content || '';
                    const keywords = (document.querySelector('meta[name="keywords"]')?.content || '').split(',').filter(Boolean);
                    const thumbnail = Boolean(document.querySelector('meta[property="og:image"]')?.content);
                    const score = Math.min(100, (title.length >= 25 && title.length <= 70 ? 30 : 12) + (description.length >= 120 ? 25 : 10) + Math.min(30, keywords.length * 3) + (thumbnail ? 15 : 0));
                    panel.querySelector('[data-grom-score]').textContent = `Оценка оформления: ${score}/100`;
                    panel.querySelector('[data-grom-score]').style.cssText = 'margin:10px 0 5px;color:' + (score >= 75 ? '#77d693' : score >= 50 ? '#f7c566' : '#ff7b72') + ';font-weight:700';
                    panel.querySelector('[data-grom-details]').textContent = `Заголовок: ${title.length} зн. · Описание: ${description.length} зн. · Ключи: ${keywords.length}`;
                }

                function applyTwitchEnhancer() {
                    const twitch = /(^|\.)twitch\.tv$/i.test(location.hostname);
                    const kick = /(^|\.)kick\.com$/i.test(location.hostname);
                    const active = enabled('twitch_enhancer') && (twitch || kick);
                    let style = document.getElementById('__gromTwitchStyle');
                    let panel = document.getElementById('__gromStreamTools');
                    if (!active) { style?.remove(); panel?.remove(); return; }
                    if (!style) { style = document.createElement('style'); style.id = '__gromTwitchStyle'; document.head?.append(style); }
                    const options = config().twitch || {};
                    const ui = config().ui || {};
                    const rules = [];
                    if (options.compactChat) rules.push('.chat-line__message{padding-top:1px!important;padding-bottom:1px!important}.chat-scrollable-area__message-container{font-size:13px!important}');
                    const emoteSize = Math.max(16, Math.min(64, Number(options.emoteSize || 28)));
                    rules.push(`
                        .chat-line__message img.chat-image:not(.chat-badge),
                        [data-a-target="chat-line-message"] img.chat-image:not(.chat-badge),
                        [data-chat-entry] img[data-emote-id],
                        [data-chat-entry] img[class*="emote" i]{width:${emoteSize}px!important;height:${emoteSize}px!important;object-fit:contain!important}
                    `);
                    if (options.hideChat) rules.push('[data-a-target="right-column-chat-bar"],[data-test-selector="chat-room-component-layout"],.stream-chat,.chat-shell,.right-column{display:none!important}');
                    if (options.hideSidebar) rules.push('[data-a-target="side-nav-bar"],.side-nav{display:none!important}');
                    if (options.hideRecommendations) rules.push('[data-a-target="side-nav-card"],[data-test-selector="recommended-channels"]{display:none!important}');
                    if (options.hideExtensions) rules.push('.extension-view__iframe,.extensions-dock-card,[data-test-selector*="extension" i]{display:none!important}');
                    rules.push(`
                        .__gromMentionFocus{background:color-mix(in srgb, ${ui.accent || '#8ab4f8'} 22%, transparent)!important;border-left:3px solid ${ui.accent || '#8ab4f8'}!important}
                        .__gromChatAttachment{display:block;max-width:240px;max-height:150px;margin:6px 0;border-radius:6px;object-fit:contain;background:#111}
                        .__gromPinButton{width:24px;height:24px;margin-left:auto;border:0;border-radius:5px;background:transparent;color:inherit;cursor:pointer;opacity:.72}
                        .__gromPinButton:hover{background:rgba(127,127,127,.2);opacity:1}
                        [data-grom-pinned="1"]{order:-10!important}
                    `);
                    style.textContent = rules.join('\n');

                    const now = Date.now();
                    if (now - Number(window.__gromTwitchAppliedAt || 0) < 650) return;
                    window.__gromTwitchAppliedAt = now;
                    const parts = location.pathname.split('/').filter(Boolean);
                    const reserved = new Set(['directory','downloads','jobs','p','settings','subscriptions','videos','categories']);
                    const channel = parts[0] && !reserved.has(parts[0].toLowerCase()) ? parts[0] : '';
                    const messages = [...document.querySelectorAll('.chat-line__message,[data-a-target="chat-line-message"],[data-chat-entry]')].slice(-450);
                    const formatTime = seconds => {
                        seconds = Math.max(0, Math.floor(Number(seconds) || 0));
                        const hours = Math.floor(seconds / 3600);
                        const minutes = Math.floor(seconds % 3600 / 60);
                        const tail = String(seconds % 60).padStart(2, '0');
                        return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${tail}` : `${minutes}:${tail}`;
                    };

                    const visibleNames = new Set();
                    messages.forEach(message => {
                        const author = message.querySelector('[data-a-target="chat-message-username"],.chat-author__display-name,[data-chat-author]');
                        const name = String(author?.textContent || '').trim();
                        if (name) {
                            visibleNames.add(name.toLocaleLowerCase());
                            message.dataset.gromAuthor = name.toLocaleLowerCase();
                        }
                        if (options.highlightMentions && author && !author.dataset.gromMentionBound) {
                            author.dataset.gromMentionBound = '1';
                            author.addEventListener('mouseenter', () => {
                                const selected = String(author.textContent || '').trim().toLocaleLowerCase();
                                document.querySelectorAll('[data-grom-author]').forEach(row => row.classList.toggle('__gromMentionFocus', row.dataset.gromAuthor === selected));
                            });
                            author.addEventListener('mouseleave', () => document.querySelectorAll('.__gromMentionFocus').forEach(row => row.classList.remove('__gromMentionFocus')));
                        }
                        if (options.chatMedia) message.querySelectorAll('a[href]').forEach(anchor => {
                            if (anchor.dataset.gromMediaChecked) return;
                            anchor.dataset.gromMediaChecked = '1';
                            let source = '';
                            try { source = new URL(anchor.href, location.href).href; } catch (_) { return; }
                            if (/\.(?:png|jpe?g|gif|webp|avif)(?:[?#]|$)/i.test(source)) {
                                const image = document.createElement('img');
                                image.className = '__gromChatAttachment';
                                image.loading = 'lazy';
                                image.referrerPolicy = 'no-referrer';
                                image.src = source;
                                anchor.after(image);
                            } else if (/\.(?:mp4|webm)(?:[?#]|$)/i.test(source)) {
                                const video = document.createElement('video');
                                video.className = '__gromChatAttachment';
                                video.controls = true;
                                video.muted = true;
                                video.preload = 'metadata';
                                video.src = source;
                                anchor.after(video);
                            }
                        });
                    });

                    if (twitch && options.pinStreamers) {
                        let pinned = [];
                        try { pinned = JSON.parse(localStorage.getItem('__gromPinnedStreamers') || '[]'); } catch (_) {}
                        const sideCards = [...document.querySelectorAll('[data-a-target="side-nav-card"]')];
                        sideCards.forEach(card => {
                            const link = card.querySelector('a[href]');
                            const slug = String(link?.pathname || '').split('/').filter(Boolean)[0]?.toLowerCase();
                            if (!slug) return;
                            card.dataset.gromPinned = pinned.includes(slug) ? '1' : '0';
                            let button = card.querySelector('.__gromPinButton');
                            if (!button) {
                                button = document.createElement('button');
                                button.className = '__gromPinButton';
                                card.append(button);
                            }
                            button.title = 'Закрепить канал';
                            button.textContent = pinned.includes(slug) ? '●' : '○';
                            button.onclick = event => {
                                event.preventDefault(); event.stopPropagation();
                                let values = [];
                                try { values = JSON.parse(localStorage.getItem('__gromPinnedStreamers') || '[]'); } catch (_) {}
                                values = values.includes(slug) ? values.filter(value => value !== slug) : [...values, slug];
                                localStorage.setItem('__gromPinnedStreamers', JSON.stringify(values));
                                window.__gromTwitchAppliedAt = 0;
                                applyTwitchEnhancer();
                            };
                        });
                        const pinnedCards = pinned.map(slug => sideCards.find(card => {
                            const link = card.querySelector('a[href]');
                            return String(link?.pathname || '').split('/').filter(Boolean)[0]?.toLowerCase() === slug;
                        })).filter(Boolean);
                        if (pinnedCards.length) {
                            const parent = pinnedCards[0].parentElement;
                            const current = [...(parent?.children || [])].filter(card => sideCards.includes(card)).slice(0, pinnedCards.length);
                            if (parent && current.some((card, index) => card !== pinnedCards[index])) {
                                [...pinnedCards].reverse().forEach(card => parent.prepend(card));
                            }
                        }
                    }

                    const shouldShowPanel = Boolean(channel && options.channelTools);
                    if (!shouldShowPanel) { panel?.remove(); return; }
                    if (!panel) {
                        panel = document.createElement('aside');
                        panel.id = '__gromStreamTools';
                        panel.innerHTML = '<b>Grom Enhancer</b><button data-grom-close title="Скрыть">×</button><div data-grom-stream-stats></div><nav data-grom-stream-links></nav>';
                        document.documentElement.append(panel);
                        panel.querySelector('[data-grom-close]').onclick = () => { panel.hidden = true; };
                    }
                    panel.style.cssText = `position:fixed;left:14px;bottom:14px;z-index:2147483000;width:245px;padding:12px;color:${ui.text || '#f5f7fa'};background:${ui.background || '#202124'};border:1px solid ${ui.border || '#4f545c'};border-radius:7px;box-shadow:0 10px 30px #0007;font:12px Segoe UI,sans-serif`;
                    panel.querySelector('[data-grom-close]').style.cssText = `float:right;border:0;background:transparent;color:${ui.muted || '#aaa'};font-size:18px;cursor:pointer`;
                    const video = document.querySelector('video');
                    let latency = 0;
                    try { latency = video?.seekable?.length ? video.seekable.end(video.seekable.length - 1) - video.currentTime : 0; } catch (_) {}
                    let watched = Number(localStorage.getItem(`__gromWatchtime:${location.hostname}:${channel}`) || 0);
                    const stats = [];
                    if (options.visibleChatters) stats.push(`Видимых в чате: ${visibleNames.size}`);
                    if (options.streamLatency && video && !Number.isFinite(video.duration)) stats.push(`Задержка: ${Math.max(0, latency).toFixed(1)} с`);
                    if (options.vodTime && video && Number.isFinite(video.duration)) stats.push(`Видео: ${formatTime(video.currentTime)} / ${formatTime(video.duration)}`);
                    if (options.localWatchtime) stats.push(`Просмотрено здесь: ${formatTime(watched)}`);
                    panel.querySelector('[data-grom-stream-stats]').innerHTML = stats.map(value => `<div style="margin-top:5px;color:${ui.muted || '#bbb'}">${value}</div>`).join('');
                    const links = [];
                    if (twitch) {
                        links.push(`<a href="https://twitchtracker.com/${encodeURIComponent(channel)}" target="_blank">TwitchTracker</a>`);
                        links.push(`<a href="https://sullygnome.com/channel/${encodeURIComponent(channel)}" target="_blank">SullyGnome</a>`);
                    }
                    if (options.clipDownload && video && (location.pathname.includes('/clip/') || location.hostname.startsWith('clips.'))) links.push('<button data-grom-clip>Скачать клип</button>');
                    const navigation = panel.querySelector('[data-grom-stream-links]');
                    navigation.innerHTML = links.join('');
                    navigation.querySelectorAll('a,button').forEach(item => item.style.cssText = `display:inline-block;margin:9px 7px 0 0;padding:5px 7px;border:0;border-radius:5px;background:${ui.surface || '#303134'};color:${ui.text || '#fff'};text-decoration:none;cursor:pointer`);
                    const clipButton = navigation.querySelector('[data-grom-clip]');
                    if (clipButton) clipButton.onclick = () => {
                        const source = video.currentSrc || video.src;
                        if (!source) return;
                        const link = document.createElement('a');
                        link.href = source; link.download = `${channel || 'twitch-clip'}.mp4`; link.click();
                    };
                }

                function applyFaceitEnhancer() {
                    const active = enabled('faceit_enhancer') && /(^|\.)faceit\.com$/i.test(location.hostname);
                    let style = document.getElementById('__gromFaceitStyle');
                    if (!active) { style?.remove(); return; }
                    if (!style) { style = document.createElement('style'); style.id = '__gromFaceitStyle'; document.head?.append(style); }
                    style.textContent = config().faceit?.compact ? '[class*="Card"]{padding-top:8px!important;padding-bottom:8px!important}[class*="MatchCard"]{min-height:unset!important}' : '';
                    if (config().faceit?.highlightStats) {
                        const inspectedStats = window.__gromFaceitInspectedStats ||= new WeakSet();
                        document.querySelectorAll('span,div').forEach(node => {
                            if (inspectedStats.has(node)) return;
                            inspectedStats.add(node);
                            if (node.children.length || node.dataset.gromStat) return;
                            const text = node.textContent?.trim() || '';
                            const match = text.match(/^(?:ELO\s*)?(\d{3,4})$|^(\d{1,2}(?:\.\d+)?)%$/i);
                            if (!match) return;
                            const value = Number(match[1] || match[2]);
                            if (value >= 1800 || (text.endsWith('%') && value >= 55)) {
                                node.dataset.gromStat = '1';
                                node.style.setProperty('color', '#67d58b', 'important');
                                node.style.setProperty('font-weight', '700', 'important');
                            }
                        });
                    }
                    if (config().faceit?.autoAccept) {
                        const accept = [...document.querySelectorAll('button')].find(button => /^(accept|принять)$/i.test(button.textContent?.trim() || ''));
                        if (accept && !accept.dataset.gromAccepted) { accept.dataset.gromAccepted = '1'; accept.click(); }
                    }
                }

                function applyAll() {
                    document.querySelectorAll('video,audio').forEach(applyMedia);
                    applyDarkPages();
                    applyYouTubeInsights();
                    applyTwitchEnhancer();
                    applyFaceitEnhancer();
                    let blockerStyle = document.getElementById('__gromBuiltinBlockStyle');
                    if (blockerActive()) {
                        if (!blockerStyle) {
                            blockerStyle = document.createElement('style');
                            blockerStyle.id = '__gromBuiltinBlockStyle';
                            blockerStyle.textContent = `
                                ins.adsbygoogle,[data-ad-client],[data-ad-slot],[id^="google_ads"],
                                [class~="advertisement"],[class~="sponsored"],[class^="ad-container"],[class*=" ad-container"],
                                [id^="ad_container"],[data-testid^="ad-" i],[data-testid*="advertisement" i],[data-ad],[data-ad-unit],
                                iframe[src*="doubleclick"],iframe[src*="googlesyndication"],
                                [aria-label="Ads"],[aria-label="Advertisement"],[aria-label="Реклама"]{display:none!important}
                            `;
                            document.head?.append(blockerStyle);
                        }
                    } else blockerStyle?.remove();
                    if (blockerActive()) {
                        const filterRevision = `${Boolean(config().blocker?.strict)}|${(config().blocker?.customFilters || []).join(',')}`;
                        document.querySelectorAll('script[src],iframe[src],img[src],source[src],link[href]').forEach(node => {
                            const value = node.src || node.href || '';
                            const resourceKey = `${value}|${filterRevision}`;
                            if (node.__gromCheckedResource === resourceKey) return;
                            node.__gromCheckedResource = resourceKey;
                            const kind = blockedKind(value);
                            if (kind) { countBlock(kind); node.remove(); }
                        });
                    }
                    if (blockerActive() && config().blocker?.cookieBanners) {
                        document.querySelectorAll('[id*="cookie" i],[class*="cookie-banner" i],[class*="cookie-consent" i],[aria-label*="cookie" i]')
                            .forEach(node => {
                                const style = getComputedStyle(node);
                                if (style.position === 'fixed' || style.position === 'sticky' || node.getAttribute('role') === 'dialog') {
                                    node.style.setProperty('display', 'none', 'important');
                                }
                            });
                    }
                }

                if (!window.__gromBuiltinsInstalled) {
                    window.__gromBuiltinsInstalled = true;
                    const markMediaGesture = () => window.__gromLastMediaGesture = Date.now();
                    document.addEventListener('pointerdown', markMediaGesture, true);
                    document.addEventListener('keydown', markMediaGesture, true);
                    document.addEventListener('play', event => {
                        if (event.target instanceof HTMLMediaElement) {
                            const userStarted = Date.now() - Number(window.__gromLastMediaGesture || 0) < 1800;
                            if (enabled('prevent_autoplay') && !userStarted && !event.target.dataset.gromUserStarted) {
                                event.target.pause();
                                return;
                            }
                            if (userStarted) event.target.dataset.gromUserStarted = '1';
                            applyMedia(event.target);
                            event.target.__gromAudioNodes?.context?.resume?.();
                        }
                    }, true);
                    document.addEventListener('loadedmetadata', event => applyMedia(event.target), true);
                    document.addEventListener('click', event => {
                        const anchor = event.target?.closest?.('a[href]');
                        if (anchor && blockerActive() && config().blocker?.cleanLinks) anchor.href = cleanUrl(anchor.href);
                        const media = event.target?.closest?.('video,audio');
                        if (media) media.dataset.gromUserStarted = '1';
                    }, true);
                    const originalFetch = window.fetch?.bind(window);
                    if (originalFetch) window.fetch = (resource, options) => {
                        const url = typeof resource === 'string' ? resource : resource?.url || '';
                        const kind = blockedKind(url);
                        if (countBlock(kind)) return Promise.reject(new Error(`Blocked by Grom ${kind}`));
                        return originalFetch(resource, options);
                    };
                    const originalOpen = XMLHttpRequest.prototype.open;
                    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                        const kind = blockedKind(url);
                        if (countBlock(kind)) { this.__gromBlocked = true; return; }
                        return originalOpen.call(this, method, url, ...rest);
                    };
                    const originalSend = XMLHttpRequest.prototype.send;
                    XMLHttpRequest.prototype.send = function(...args) {
                        if (this.__gromBlocked) return;
                        return originalSend.apply(this, args);
                    };
                    const originalBeacon = navigator.sendBeacon?.bind(navigator);
                    if (originalBeacon) navigator.sendBeacon = (url, data) => {
                        const kind = blockedKind(url);
                        if (countBlock(kind)) return true;
                        return originalBeacon(url, data);
                    };
                    let observerPending = false;
                    new MutationObserver(() => {
                        if (document.hidden) return;
                        if (observerPending) return;
                        observerPending = true;
                        setTimeout(() => { observerPending = false; applyAll(); }, 240);
                    }).observe(document.documentElement, {childList:true,subtree:true});
                    document.addEventListener('visibilitychange', () => {
                        if (!document.hidden) applyAll();
                    });
                    window.__gromTwitchPointsTimer = setInterval(() => {
                        if (!enabled('twitch_enhancer') || !config().twitch?.autoPoints || !/(^|\.)twitch\.tv$/i.test(location.hostname)) return;
                        const target = document.querySelector('[data-test-selector="claimable-bonus__icon"]')
                            || document.querySelector('button[aria-label*="Claim Bonus" i]')
                            || document.querySelector('button[aria-label*="Получить бонус" i]');
                        const button = target?.closest?.('button') || (target?.matches?.('button') ? target : null);
                        if (button) { button.click(); window.__gromBuiltinStats.twitch_enhancer++; }
                    }, 12000);
                    window.__gromWatchtimeTimer = setInterval(() => {
                        if (!enabled('twitch_enhancer') || !config().twitch?.localWatchtime) return;
                        if (!/(^|\.)(?:twitch\.tv|kick\.com)$/i.test(location.hostname)) return;
                        const video = document.querySelector('video');
                        if (!video || video.paused || video.ended || document.hidden) return;
                        const channel = location.pathname.split('/').filter(Boolean)[0];
                        if (!channel) return;
                        const key = `__gromWatchtime:${location.hostname}:${channel}`;
                        localStorage.setItem(key, String(Number(localStorage.getItem(key) || 0) + 5));
                    }, 5000);
                    document.addEventListener('keydown', event => {
                        if (event.key !== 'Enter' || !enabled('twitch_enhancer') || !config().twitch?.localWatchtime) return;
                        const field = event.target?.closest?.('textarea,[contenteditable="true"]');
                        const value = String(field?.value ?? field?.textContent ?? '').trim().toLowerCase();
                        if (value !== '/watchtime') return;
                        event.preventDefault(); event.stopPropagation();
                        const channel = location.pathname.split('/').filter(Boolean)[0] || 'channel';
                        const seconds = Number(localStorage.getItem(`__gromWatchtime:${location.hostname}:${channel}`) || 0);
                        const minutes = Math.floor(seconds / 60);
                        const toast = document.createElement('div');
                        toast.textContent = `Grom: локальное время просмотра — ${Math.floor(minutes / 60)} ч ${minutes % 60} мин`;
                        toast.style.cssText = 'position:fixed;left:50%;bottom:70px;transform:translateX(-50%);z-index:2147483647;padding:10px 14px;border-radius:6px;background:#18181b;color:#efeff1;box-shadow:0 8px 28px #0008;font:13px Segoe UI,sans-serif';
                        document.documentElement.append(toast);
                        setTimeout(() => toast.remove(), 3200);
                        if ('value' in field) field.value = ''; else field.textContent = '';
                        field.dispatchEvent(new Event('input', {bubbles:true}));
                    }, true);
                    window.__gromBuiltinRefreshTimer = setInterval(() => {
                        if (!document.hidden) applyAll();
                    }, 6000);
                }
                window.__gromApplyBuiltins = applyAll;
                applyAll();
                return true;
            })();
            """.replace("__CONFIG__", config)
        )

    def apply_builtin_extensions_to_all(self):
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not hasattr(workspace, "primary_browser"):
                continue
            self.apply_builtin_extensions(workspace.primary_browser)
            if workspace.secondary_browser:
                self.apply_builtin_extensions(workspace.secondary_browser)

    def update_builtin_extension(self, extension_id, enabled):
        state = self.builtin_extension_state()
        state[extension_id] = bool(enabled)
        self.app_settings["builtin_extensions"] = state
        if extension_id == "ad_blocker":
            self.app_settings["ad_blocker"] = bool(enabled)
        elif extension_id == "password_manager":
            self.app_settings["password_manager"] = bool(enabled)
        self.save_app_settings()
        self.apply_builtin_extensions_to_all()

    def update_builtin_extension_value(self, key, value):
        self.app_settings[key] = value
        self.save_app_settings()
        self.apply_builtin_extensions_to_all()

    def builtin_extension_definition(self, extension_id):
        return next(
            (item for item in BUILTIN_EXTENSION_DEFINITIONS if item["id"] == extension_id),
            None,
        )

    def builtin_extension_icon(self, extension_id, size=36):
        definition = self.builtin_extension_definition(extension_id) or {
            "color": "#54708f", "name": str(extension_id)
        }
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_color = QColor(definition.get("color", "#54708f"))
        painter.setBrush(icon_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(1, 1, size - 2, size - 2, max(6, size // 4), max(6, size // 4))
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPixelSize(max(9, int(size * (0.36 if len(self.extension_initials(definition)) > 1 else 0.44))))
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.extension_initials(definition))
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def extension_initials(definition):
        words = [word for word in definition.get("name", "").replace("&", " ").split()
                 if word.casefold() not in {"grom", "and", "the", "и"}]
        return "".join(word[0] for word in words[:2]).upper() or "?"

    def extensions_toolbar_icon(self):
        path = (
            self.menu_icon_path("extensions.png")
            if hasattr(self, "menu_icon_path")
            else os.path.join(os.path.dirname(__file__), "menu_icons", "extensions.png")
        )
        if os.path.isfile(path):
            if hasattr(self, "themed_icon"):
                return self.themed_icon(path, self.theme_colors["icon"])
            return QIcon(path)
        return self.builtin_extension_icon("ad_blocker", 24)

    def extension_icon_data_uri(self, extension_id):
        path = os.path.join(
            os.path.dirname(__file__), "menu_icons", f"extension_{extension_id}.png"
        )
        if not os.path.isfile(path):
            return ""
        try:
            with open(path, "rb") as file:
                return "data:image/png;base64," + base64.b64encode(file.read()).decode("ascii")
        except OSError:
            return ""

    def extension_icon_markup(self, definition, css_class="extension-icon"):
        color = html_lib.escape(definition.get("color", "#54708f"))
        initials = html_lib.escape(self.extension_initials(definition))
        return f'<span class="{css_class} icon-placeholder" style="--icon-color:{color}">{initials}</span>'

    def extensions_popup_html(self, extension_id=None, stat_value=None):
        colors = self.theme_colors
        state = self.builtin_extension_state()
        selected = self.builtin_extension_definition(extension_id) if extension_id else None
        rows = []
        for index, definition in enumerate(BUILTIN_EXTENSION_DEFINITIONS):
            enabled = state.get(definition["id"], definition["enabled"])
            extension_key = definition["id"]
            rows.append(f"""
                <div class="extension-row" style="--delay:{index * 28}ms">
                    <button class="extension-main" onclick="send('extension_open',{{id:'{extension_key}'}})">
                        {self.extension_icon_markup(definition)}
                        <span class="extension-copy"><strong>{html_lib.escape(definition['name'])}</strong><small>{'Включено' if enabled else 'Выключено'} на всех сайтах</small></span>
                        <span class="chevron">›</span>
                    </button>
                    <label class="switch" title="Включить или выключить" onclick="event.stopPropagation()">
                        <input type="checkbox" {'checked' if enabled else ''} onchange="toggleExtension('{extension_key}',this)"><span></span>
                    </label>
                </div>
            """)

        content = f"""
            <header><div><h1>Расширения</h1><p>Встроенные инструменты Grom</p></div><button class="icon-button" onclick="send('extension_close')" aria-label="Закрыть">×</button></header>
            <main class="list">{''.join(rows)}</main>
            <footer><button onclick="send('extension_settings')"><span class="manage-icon"></span>Настройки браузера</button></footer>
        """
        if selected:
            enabled = state.get(selected["id"], selected["enabled"])
            control = "<p class='note'>Расширение работает автоматически на подходящих страницах.</p>"
            if selected["id"] == "audio_enhancer":
                controls = (
                    ("Громкость", "audio_boost", 100, 600, int(self.app_settings.get("audio_boost", 100)), "%"),
                    ("Низкие частоты", "audio_bass", -12, 12, int(self.app_settings.get("audio_bass", 0)), " dB"),
                    ("Высокие частоты", "audio_treble", -12, 12, int(self.app_settings.get("audio_treble", 0)), " dB"),
                )
                control = "".join(
                    f"<label class='range-row'><span><b>{title}</b><output id='out-{key}'>{value}{suffix}</output></span><input type='range' min='{minimum}' max='{maximum}' value='{value}' oninput=\"document.getElementById('out-{key}').textContent=this.value+'{suffix}'\" onchange=\"send('extension_value',{{key:'{key}',value:Number(this.value)}})\"></label>"
                    for title, key, minimum, maximum, value, suffix in controls
                )
            elif selected["id"] == "video_speed":
                value = float(self.app_settings.get("video_speed", 1.0))
                raw = round(value * 100)
                control = f"<label class='range-row'><span><b>Скорость видео</b><output id='out-speed'>{value:g}x</output></span><input type='range' min='50' max='300' value='{raw}' oninput=\"document.getElementById('out-speed').textContent=(this.value/100)+'x'\" onchange=\"send('extension_value',{{key:'video_speed',value:Number(this.value)/100}})\"></label>"
            elif selected["id"] in ("ad_blocker", "anti_tracker", "twitch_points"):
                label = "Заблокировано на странице" if selected["id"] != "twitch_points" else "Собрано на странице"
                control = f"<div class='stat'><strong>{int(stat_value or 0)}</strong><span>{label}</span></div><p class='note'>Счётчик начинается заново после перезагрузки страницы.</p>"
            elif selected["id"] == "password_manager":
                control = f"<div class='stat'><strong>{len(self.password_page_records())}</strong><span>Сохранённых учётных записей</span></div><button class='primary' onclick=\"send('extension_passwords')\">Открыть менеджер паролей</button>"
            content = f"""
                <header class="detail-header"><button class="icon-button back" onclick="send('extension_back')" aria-label="Назад">‹</button><div><h1>{html_lib.escape(selected['name'])}</h1><p>Настройка расширения</p></div><button class="icon-button" onclick="send('extension_close')" aria-label="Закрыть">×</button></header>
                <main class="detail">
                    <section class="hero" style="--hero:{html_lib.escape(selected['color'])}">{self.extension_icon_markup(selected, 'hero-icon')}<div><h2>{html_lib.escape(selected['name'])}</h2><p>{html_lib.escape(selected['description'])}</p></div></section>
                    <section class="enable-row"><div><b>Расширение</b><small id="extension-state">{'Включено' if enabled else 'Выключено'}</small></div><label class="switch large"><input type="checkbox" {'checked' if enabled else ''} onchange="toggleExtension('{selected['id']}',this)"><span></span></label></section>
                    <section class="controls">{control}</section>
                </main>
            """

        return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
            :root{{--bg:{colors['popup']};--surface:{colors['surface']};--hover:{colors['hover']};--border:{colors['border']};--text:{colors['text']};--muted:{colors['muted']};--accent:{colors['accent']}}}
            *{{box-sizing:border-box}}html,body{{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--text);font:14px "Segoe UI",Arial,sans-serif}}button,input{{font:inherit}}button{{color:inherit}}
            body{{display:grid;grid-template-rows:auto minmax(0,1fr) auto;border:1px solid var(--border)}}header{{height:74px;display:flex;align-items:center;justify-content:space-between;padding:13px 16px;border-bottom:1px solid var(--border);background:color-mix(in srgb,var(--bg) 88%,var(--surface))}}h1,h2,p{{margin:0}}h1{{font-size:18px}}header p{{margin-top:3px;color:var(--muted);font-size:12px}}
            .icon-button{{width:34px;height:34px;border:0;border-radius:50%;background:transparent;font-size:24px;line-height:1;cursor:pointer}}.icon-button:hover{{background:var(--hover)}}
            .list{{overflow-y:auto;padding:7px 7px 10px}}.list::-webkit-scrollbar,.detail::-webkit-scrollbar{{width:8px}}.list::-webkit-scrollbar-track,.detail::-webkit-scrollbar-track{{background:transparent}}.list::-webkit-scrollbar-thumb,.detail::-webkit-scrollbar-thumb{{background:#555a61;border-radius:999px;border:2px solid transparent;background-clip:content-box}}
            .extension-row{{position:relative;display:flex;align-items:center;min-height:64px;border-radius:7px;animation:rowIn .28s ease both;animation-delay:var(--delay)}}.extension-row:hover{{background:var(--hover)}}.extension-main{{width:100%;min-width:0;height:64px;display:grid;grid-template-columns:38px minmax(0,1fr) 18px;align-items:center;gap:11px;padding:7px 58px 7px 9px;border:0;background:transparent;text-align:left;cursor:pointer}}.extension-copy{{min-width:0}}.extension-copy strong,.extension-copy small{{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.extension-copy strong{{font-weight:600}}.extension-copy small{{margin-top:5px;color:var(--muted);font-size:12px}}.chevron{{font-size:22px;color:var(--muted)}}
            .extension-icon,.hero-icon{{width:34px;height:34px;object-fit:contain;border-radius:8px}}.icon-placeholder{{display:grid;place-items:center;background:var(--icon-color);color:#fff;font-size:11px;font-weight:750;letter-spacing:-.35px}}
            .switch{{position:absolute;right:12px;width:36px;height:21px}}.switch input{{display:none}}.switch span{{position:absolute;inset:0;border-radius:99px;background:var(--border);transition:.2s;cursor:pointer}}.switch span:after{{content:"";position:absolute;width:15px;height:15px;left:3px;top:3px;border-radius:50%;background:#fff;transition:.2s}}.switch input:checked+span{{background:var(--accent)}}.switch input:checked+span:after{{transform:translateX(15px)}}
            footer{{height:52px;padding:5px 8px;border-top:1px solid var(--border)}}footer button{{width:100%;height:40px;border:0;border-radius:6px;background:transparent;text-align:left;cursor:pointer}}footer button:hover{{background:var(--hover)}}.manage-icon{{display:inline-block;width:14px;height:14px;margin:0 12px 0 4px;border:2px solid currentColor;border-radius:4px;vertical-align:-2px}}
            .detail-header{{display:grid;grid-template-columns:38px 1fr 38px;gap:8px}}.detail{{overflow-y:auto;padding:15px;animation:pageIn .24s ease}}.hero{{display:grid;grid-template-columns:58px 1fr;gap:14px;align-items:center;padding:17px 0 20px;border-bottom:1px solid var(--border)}}.hero-icon{{width:52px;height:52px;border-radius:12px}}.hero h2{{font-size:18px}}.hero p,.note{{margin-top:6px;color:var(--muted);line-height:1.45}}.enable-row{{display:flex;align-items:center;justify-content:space-between;padding:18px 2px;border-bottom:1px solid var(--border)}}.enable-row small{{display:block;margin-top:4px;color:var(--muted)}}.switch.large{{position:relative;right:auto;width:42px;height:24px}}.switch.large span:after{{width:18px;height:18px}}.switch.large input:checked+span:after{{transform:translateX(18px)}}.controls{{display:grid;gap:20px;padding:21px 2px}}.range-row span{{display:flex;justify-content:space-between;margin-bottom:10px}}.range-row output{{color:var(--muted)}}input[type=range]{{width:100%;accent-color:var(--accent)}}.stat{{display:flex;align-items:baseline;gap:10px}}.stat strong{{font-size:32px;color:var(--accent)}}.stat span{{color:var(--muted)}}.primary{{height:40px;margin-top:14px;padding:0 14px;border:0;border-radius:6px;background:var(--accent);color:#fff;cursor:pointer}}
            @keyframes rowIn{{from{{opacity:0;transform:translateX(12px)}}to{{opacity:1;transform:none}}}}@keyframes pageIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
        </style></head><body>{content}<script>
            window.__gromCommandQueue=[];const send=(action,data={{}})=>window.__gromCommandQueue.push(Object.assign({{action}},data));
            function toggleExtension(id,input){{send('extension_toggle',{{id,enabled:input.checked}});const state=document.getElementById('extension-state');if(state)state.textContent=input.checked?'Включено':'Выключено';const row=input.closest('.extension-row');if(row)row.querySelector('small').textContent=(input.checked?'Включено':'Выключено')+' на всех сайтах'}}
            addEventListener('keydown',event=>{{if(event.key==='Escape')send('extension_close')}});
        </script></body></html>"""

    def show_builtin_extensions_popup(self, extension_id=None, force=False):
        existing = getattr(self, "builtin_extensions_popup", None)
        if existing:
            try:
                if existing.isVisible() and not force and extension_id is None:
                    existing.close()
                    return
            except RuntimeError:
                existing = None
                self.builtin_extensions_popup = None
        if existing:
            existing.close()
        from webview import BrowserWebView

        popup = QFrame(
            self,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        popup.setObjectName("builtinExtensionsPopup")
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.destroyed.connect(
            lambda _object=None, closed_popup=popup: self.clear_extensions_popup_reference(
                closed_popup
            )
        )
        popup.setFixedSize(430, 600)
        popup.setStyleSheet(f"QFrame#builtinExtensionsPopup{{background:{self.theme_colors['popup']};border:none}}")
        outer = QVBoxLayout(popup)
        outer.setContentsMargins(0, 0, 0, 0)
        view = BrowserWebView(parent=popup)
        view.force_qt_click_bridge = True
        view.set_placeholder_color(self.theme_colors["popup"])
        view.browserCommand.connect(
            lambda command, current_popup=popup, current_view=view: self.handle_extension_popup_command(
                command, current_popup, current_view
            )
        )
        outer.addWidget(view)
        self.builtin_extensions_popup = popup
        anchor = getattr(self, "extensions_btn", None)
        if anchor and anchor.isVisible():
            point = anchor.mapToGlobal(anchor.rect().bottomRight())
            popup.move(point.x() - popup.width(), point.y() + 6)
        else:
            self.position_popup(popup)
        popup.show()
        popup.raise_()
        popup.activateWindow()
        view.activate_native_view()
        view.web_view.requestActivate()
        QTimer.singleShot(
            0,
            lambda: view.load_internal_html(
                self.extensions_popup_html(extension_id), "grom://extensions"
            ),
        )
        QTimer.singleShot(250, view.activate_native_view)

    def clear_extensions_popup_reference(self, popup):
        if getattr(self, "builtin_extensions_popup", None) is popup:
            self.builtin_extensions_popup = None

    def handle_extension_popup_command(self, command, popup, view):
        action = str(command.get("action", ""))
        extension_id = str(command.get("id", ""))
        if action == "extension_close":
            popup.close()
        elif action == "extension_back":
            view.load_internal_html(self.extensions_popup_html(), "grom://extensions")
        elif action == "extension_toggle" and self.builtin_extension_definition(extension_id):
            self.update_builtin_extension(extension_id, bool(command.get("enabled", False)))
        elif action == "extension_value":
            key = str(command.get("key", ""))
            ranges = {
                "audio_boost": (100, 600), "audio_bass": (-12, 12),
                "audio_treble": (-12, 12), "video_speed": (0.5, 3.0),
            }
            if key in ranges:
                minimum, maximum = ranges[key]
                value = max(minimum, min(maximum, float(command.get("value", minimum))))
                self.update_builtin_extension_value(key, value)
        elif action in ("extension_settings", "extension_passwords"):
            popup.close()
            self.open_settings_tab()
        elif action == "extension_open" and self.builtin_extension_definition(extension_id):
            browser = self.current_browser()
            if extension_id in ("ad_blocker", "anti_tracker", "twitch_points") and browser and not browser.internal_page:
                browser.runJavaScript(
                    f"Number(window.__gromBuiltinStats?.[{json.dumps(extension_id)}] || 0)",
                    lambda value, current_id=extension_id: view.load_internal_html(
                        self.extensions_popup_html(current_id, value), "grom://extensions"
                    ),
                )
            else:
                view.load_internal_html(self.extensions_popup_html(extension_id), "grom://extensions")

    def show_builtin_extension_details(self, extension_id):
        self.show_builtin_extensions_popup(extension_id, force=True)
        return
        definition = self.builtin_extension_definition(extension_id)
        if not definition:
            return
        colors = self.theme_colors
        popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        popup.setObjectName("extensionDetailsPopup")
        popup.setFixedSize(480, 470)
        popup.setStyleSheet(f"""
            QFrame#extensionDetailsPopup {{ background:{colors['popup']}; border:1px solid {colors['border']}; }}
            QFrame#extensionHero,QFrame#extensionPanel {{ background:{colors['surface']}; border:none; border-radius:7px; }}
            QLabel {{ color:{colors['text']}; border:none; }}
            QLabel#description,QLabel#statHint {{ color:{colors['muted']}; }}
            QPushButton {{ color:{colors['text']}; background:transparent; border:none; border-radius:6px; padding:8px 12px; }}
            QPushButton:hover {{ background:{colors['hover']}; }}
            QLineEdit {{ color:{colors['text']}; background:{colors['background']}; border:1px solid {colors['border']}; border-radius:6px; padding:8px; }}
            QLineEdit:focus {{ border-color:{colors['accent']}; }}
            QSlider::groove:horizontal {{ height:4px; background:{colors['border']}; }}
            QSlider::handle:horizontal {{ width:14px; margin:-5px 0; border-radius:7px; background:{colors['accent']}; }}
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        back = QPushButton("Назад к расширениям")
        back.clicked.connect(
            lambda: (popup.close(), QTimer.singleShot(0, self.show_builtin_extensions_popup))
        )
        layout.addWidget(back, 0, Qt.AlignmentFlag.AlignLeft)
        hero = QFrame()
        hero.setObjectName("extensionHero")
        hero_layout = QHBoxLayout(hero)
        icon = QLabel()
        icon.setPixmap(self.builtin_extension_icon(extension_id, 52).pixmap(52, 52))
        copy = QVBoxLayout()
        title = QLabel(definition["name"])
        title.setStyleSheet("font-size:18px;font-weight:650;")
        description = QLabel(definition["description"])
        description.setObjectName("description")
        description.setWordWrap(True)
        copy.addWidget(title)
        copy.addWidget(description)
        toggle = QCheckBox("Включено")
        toggle.setChecked(self.builtin_extension_state().get(extension_id, definition["enabled"]))
        toggle.toggled.connect(
            lambda checked: (
                toggle.setText("Включено" if checked else "Выключено"),
                self.update_builtin_extension(extension_id, checked),
            )
        )
        hero_layout.addWidget(icon)
        hero_layout.addLayout(copy, 1)
        hero_layout.addWidget(toggle)
        layout.addWidget(hero)
        panel = QFrame()
        panel.setObjectName("extensionPanel")
        controls = QVBoxLayout(panel)
        controls.setContentsMargins(14, 12, 14, 12)
        if extension_id == "audio_enhancer":
            self._add_extension_slider(controls, "Громкость", "audio_boost", 100, 600, "%")
            self._add_extension_slider(controls, "Низкие", "audio_bass", -12, 12, " dB")
            self._add_extension_slider(controls, "Высокие", "audio_treble", -12, 12, " dB")
        elif extension_id == "video_speed":
            self._add_extension_slider(controls, "Скорость", "video_speed", 50, 300, "x", scale=100)
        elif extension_id in ("ad_blocker", "anti_tracker", "twitch_points"):
            stat = QLabel("Счётчик текущей страницы: …")
            stat.setStyleSheet("font-size:15px;font-weight:600;")
            hint = QLabel("Счётчик сбрасывается при перезагрузке страницы.")
            hint.setObjectName("statHint")
            controls.addWidget(stat)
            controls.addWidget(hint)
            browser = self.current_browser()
            if browser and not browser.internal_page:
                browser.runJavaScript(
                    f"Number(window.__gromBuiltinStats?.[{json.dumps(extension_id)}] || 0)",
                    lambda value, label=stat: label.setText(
                        f"На текущей странице: {int(value or 0)}"
                    ),
                )
        elif extension_id == "password_manager":
            add_option("Предлагать сохранение паролей", "offer_save_passwords", True)
            add_option("Автоматически заполнять формы", "autofill_passwords", True)
            count = len(self.password_page_records())
            summary = QLabel(f"Сохранено учётных записей: {count}")
            summary.setStyleSheet("font-size:15px;font-weight:600;")
            hint = QLabel("Пароли шифруются средствами Windows и не записываются в настройки Grom.")
            hint.setObjectName("statHint")
            hint.setWordWrap(True)
            open_settings = QPushButton("Открыть менеджер паролей")
            open_settings.clicked.connect(lambda: (popup.close(), self.open_settings_tab()))
            controls.addWidget(summary)
            controls.addWidget(hint)
            controls.addWidget(open_settings)
        else:
            hint = QLabel("Расширение работает автоматически на подходящих страницах.")
            hint.setObjectName("statHint")
            hint.setWordWrap(True)
            controls.addWidget(hint)
        controls.addStretch()
        layout.addWidget(panel, 1)
        self.builtin_extension_details_popup = popup
        self.position_popup(popup)
        popup.show()
        popup.raise_()

    def _add_extension_slider(
        self, layout, title, key, minimum, maximum, suffix, scale=1,
        step=1, tick_interval=0, on_change=None,
    ):
        container = QFrame()
        container.setObjectName("extensionSliderRow")
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QVBoxLayout(container)
        row.setContentsMargins(10, 8, 10, 9)
        row.setSpacing(5)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        value = QLabel()
        value.setMinimumWidth(64)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value.setObjectName("extensionSliderValue")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimumHeight(30)
        slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        slider.setRange(minimum, maximum)
        slider.setSingleStep(step)
        slider.setPageStep(max(step, tick_interval or step))
        if tick_interval:
            slider.setTickInterval(tick_interval)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        current = float(self.app_settings.get(key, 1.0 if key == "video_speed" else 100 if key == "audio_boost" else 0))
        slider.setValue(round(current * scale))

        def changed(raw):
            actual = raw / scale
            value.setText(f"{actual:g}{suffix}")
            if on_change:
                on_change(actual)

        def committed():
            raw = slider.value()
            actual = raw / scale
            self.update_builtin_extension_value(key, actual if scale != 1 else int(actual))

        changed(slider.value())
        slider.valueChanged.connect(changed)
        slider.sliderReleased.connect(committed)
        header.addWidget(label)
        header.addStretch()
        header.addWidget(value)
        row.addLayout(header)
        row.addWidget(slider)
        layout.addWidget(container)
        return slider

    # Native Qt implementation.  Keeping this panel out of a nested web view makes
    # opening, navigation and closing deterministic and removes the white flash.
    def builtin_extension_pins(self):
        state = self.builtin_extension_state()
        saved = self.app_settings.get("builtin_extension_pins", {})
        pins = {definition["id"]: bool(state.get(definition["id"], False))
                for definition in BUILTIN_EXTENSION_DEFINITIONS}
        if isinstance(saved, dict):
            pins.update({key: bool(value) for key, value in saved.items() if key in pins})
        return pins

    def update_builtin_extension_pin(self, extension_id, pinned):
        if not self.builtin_extension_definition(extension_id):
            return
        pins = self.builtin_extension_pins()
        pins[extension_id] = bool(pinned)
        self.app_settings["builtin_extension_pins"] = pins
        self.save_app_settings()
        self.refresh_extension_toolbar_buttons()

    def refresh_extension_toolbar_buttons(self):
        layout = getattr(self, "extension_pins_layout", None)
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        state = self.builtin_extension_state()
        pins = self.builtin_extension_pins()
        colors = self.theme_colors
        for definition in BUILTIN_EXTENSION_DEFINITIONS:
            extension_id = definition["id"]
            if not state.get(extension_id, False) or not pins.get(extension_id, False):
                continue
            button = QPushButton()
            button.setObjectName(f"pinnedExtension_{extension_id}")
            button.setFixedSize(28, 28)
            button.setIcon(self.builtin_extension_icon(extension_id, 20))
            button.setIconSize(QSize(20, 20))
            button.setToolTip(definition["name"])
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.setStyleSheet(f"""
                QPushButton {{ background:transparent; border:none; border-radius:14px; padding:0; }}
                QPushButton:hover {{ background:{colors['hover']}; }}
            """)
            button.clicked.connect(
                lambda _checked=False, current_id=extension_id:
                self.show_builtin_extensions_popup(current_id, force=True)
            )
            button.customContextMenuRequested.connect(
                lambda point, current_id=extension_id, current_button=button:
                self.show_pinned_extension_context_menu(
                    current_id, current_button.mapToGlobal(point)
                )
            )
            layout.addWidget(button)
        container = getattr(self, "extension_pins_widget", None)
        if container:
            container.setVisible(layout.count() > 0)

    def show_pinned_extension_context_menu(self, extension_id, global_pos):
        definition = self.builtin_extension_definition(extension_id)
        if not definition:
            return
        menu = QMenu(self)
        if hasattr(self, "context_menu_stylesheet"):
            menu.setStyleSheet(self.context_menu_stylesheet())
        settings_action = menu.addAction("Настроить расширение")
        hide_action = menu.addAction("Скрыть с панели")
        menu.addSeparator()
        disable_action = menu.addAction("Выключить")
        selected = menu.exec(global_pos)
        if selected == settings_action:
            self.show_builtin_extensions_popup(extension_id, force=True)
        elif selected == hide_action:
            self.update_builtin_extension_pin(extension_id, False)
        elif selected == disable_action:
            self.update_builtin_extension(extension_id, False)

    def _extensions_popup_stylesheet(self):
        colors = self.theme_colors
        return f"""
            QFrame#builtinExtensionsPopup {{
                background:{colors['popup']}; border:1px solid {colors['border']}; border-radius:12px;
            }}
            QWidget#extensionsPage, QWidget#extensionDetailsPage {{ background:{colors['popup']}; }}
            QLabel {{ color:{colors['text']}; background:transparent; border:none; }}
            QLabel#extensionsSubtitle, QLabel#extensionDescription, QLabel#extensionHint {{
                color:{colors['muted']};
            }}
            QFrame#extensionRow, QFrame#extensionHero, QFrame#extensionControlPanel {{
                background:{colors['surface']}; border:none; border-radius:7px;
            }}
            QFrame#extensionSliderRow {{
                background:{colors['background']}; border:1px solid {colors['border']}; border-radius:8px;
            }}
            QLabel#extensionSliderValue {{ color:{colors['accent']}; font-weight:600; }}
            QFrame#extensionRow:hover {{ background:{colors['hover']}; }}
            QPushButton {{
                color:{colors['text']}; background:transparent; border:none;
                border-radius:6px; padding:6px 9px; text-align:left;
            }}
            QPushButton:hover {{ background:{colors['hover']}; }}
            QPushButton#extensionOpenButton {{ padding:5px 2px; }}
            QPushButton#extensionCloseButton, QPushButton#extensionBackButton {{
                min-width:32px; max-width:32px; min-height:32px; max-height:32px;
                border-radius:16px; padding:0; text-align:center; font-size:18px;
            }}
            QLineEdit {{
                color:{colors['text']}; background:{colors['background']};
                border:1px solid {colors['border']}; border-radius:6px; padding:8px;
            }}
            QLineEdit:focus {{ border-color:{colors['accent']}; }}
            QCheckBox {{ color:{colors['text']}; spacing:8px; }}
            QCheckBox::indicator {{ width:34px; height:19px; }}
            QCheckBox::indicator:unchecked {{
                background:{colors['border']}; border:none; border-radius:9px;
            }}
            QCheckBox::indicator:checked {{
                background:{colors['accent']}; border:none; border-radius:9px;
            }}
            QSlider::groove:horizontal {{ height:6px; border-radius:3px; background:{colors['border']}; }}
            QSlider::sub-page:horizontal {{ background:{colors['accent']}; border-radius:3px; }}
            QSlider::handle:horizontal {{
                width:18px; margin:-6px 0; border-radius:9px; background:{colors['accent']};
            }}
            QScrollArea, QScrollArea::viewport {{ background:{colors['popup']}; border:none; }}
            QWidget#extensionRowsContainer {{ background:{colors['popup']}; }}
            QScrollBar:vertical {{ width:8px; margin:2px; background:transparent; }}
            QScrollBar::handle:vertical {{
                min-height:34px; background:#555a61; border-radius:4px;
            }}
            QScrollBar::handle:vertical:hover {{ background:#6a7078; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
        """

    def _build_extensions_list_page(self, popup, stack):
        page = QWidget()
        page.setObjectName("extensionsPage")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        page.setStyleSheet(f"background:{self.theme_colors['popup']};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 10, 10)
        layout.setSpacing(9)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("Расширения")
        title.setStyleSheet("font-size:18px;font-weight:650;")
        subtitle = QLabel("Встроенные инструменты Grom")
        subtitle.setObjectName("extensionsSubtitle")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        close_button = QPushButton("×")
        close_button.setObjectName("extensionCloseButton")
        close_button.setToolTip("Закрыть")
        close_button.clicked.connect(popup.close)
        header.addLayout(heading, 1)
        header.addWidget(close_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setAutoFillBackground(True)
        scroll.viewport().setAutoFillBackground(True)
        viewport_palette = scroll.viewport().palette()
        viewport_palette.setColor(QPalette.ColorRole.Window, QColor(self.theme_colors["popup"]))
        scroll.viewport().setPalette(viewport_palette)
        body = QWidget()
        body.setObjectName("extensionRowsContainer")
        body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body.setStyleSheet(f"background:{self.theme_colors['popup']};")
        rows = QVBoxLayout(body)
        rows.setContentsMargins(0, 2, 4, 2)
        rows.setSpacing(6)
        state = self.builtin_extension_state()
        for definition in BUILTIN_EXTENSION_DEFINITIONS:
            extension_id = definition["id"]
            row = QFrame()
            row.setObjectName("extensionRow")
            row.setFixedHeight(64)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(9, 6, 9, 6)
            row_layout.setSpacing(10)
            open_button = QPushButton()
            open_button.setObjectName("extensionOpenButton")
            open_button.setIcon(self.builtin_extension_icon(extension_id, 34))
            open_button.setIconSize(QSize(34, 34))
            open_button.setText(
                f"{definition['name']}\n"
                f"{'Включено' if state.get(extension_id, False) else 'Выключено'}"
            )
            open_button.setToolTip("Открыть настройки")
            open_button.clicked.connect(
                lambda _checked=False, current_id=extension_id:
                self._show_extension_details_in_popup(popup, stack, current_id)
            )
            toggle = QCheckBox()
            toggle.setObjectName(f"extensionToggle_{extension_id}")
            toggle.setToolTip("Включить или выключить")
            toggle.setChecked(state.get(extension_id, definition["enabled"]))

            def toggle_extension(checked, current_id=extension_id, current_button=open_button,
                                 current_name=definition["name"]):
                self.update_builtin_extension(current_id, checked)
                current_button.setText(
                    f"{current_name}\n{'Включено' if checked else 'Выключено'}"
                )

            toggle.toggled.connect(toggle_extension)
            row_layout.addWidget(open_button, 1)
            row_layout.addWidget(toggle)
            rows.addWidget(row)
        rows.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        return page

    def _show_extension_details_in_popup(self, popup, stack, extension_id):
        definition = self.builtin_extension_definition(extension_id)
        if not definition:
            return
        while stack.count() > 1:
            old_page = stack.widget(1)
            stack.removeWidget(old_page)
            old_page.deleteLater()

        page = QWidget()
        page.setObjectName("extensionDetailsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        back = QPushButton("‹")
        back.setObjectName("extensionBackButton")
        back.setToolTip("Назад")
        back.clicked.connect(lambda: stack.setCurrentIndex(0))
        title = QLabel(definition["name"])
        title.setStyleSheet("font-size:17px;font-weight:650;")
        close_button = QPushButton("×")
        close_button.setObjectName("extensionCloseButton")
        close_button.setToolTip("Закрыть")
        close_button.clicked.connect(popup.close)
        header.addWidget(back)
        header.addWidget(title, 1)
        header.addWidget(close_button)
        layout.addLayout(header)

        hero = QFrame()
        hero.setObjectName("extensionHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(13, 13, 13, 13)
        icon = QLabel()
        icon.setPixmap(self.builtin_extension_icon(extension_id, 48).pixmap(48, 48))
        description = QLabel(definition["description"])
        description.setObjectName("extensionDescription")
        description.setWordWrap(True)
        hero_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        hero_layout.addWidget(description, 1)
        layout.addWidget(hero)

        panel = QFrame()
        panel.setObjectName("extensionControlPanel")
        panel.setMinimumWidth(0)
        panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        controls = QVBoxLayout(panel)
        controls.setContentsMargins(14, 13, 14, 13)
        controls.setSpacing(14)
        state = self.builtin_extension_state()
        enabled = QCheckBox("Включено")
        enabled.setObjectName(f"extensionDetailToggle_{extension_id}")
        enabled.setChecked(state.get(extension_id, definition["enabled"]))
        enabled.toggled.connect(
            lambda checked, current_id=extension_id:
            self.update_builtin_extension(current_id, checked)
        )
        pinned = QCheckBox("Закрепить на панели")
        pinned.setObjectName(f"extensionPin_{extension_id}")
        pinned.setChecked(self.builtin_extension_pins().get(extension_id, False))
        pinned.toggled.connect(
            lambda checked, current_id=extension_id:
            self.update_builtin_extension_pin(current_id, checked)
        )
        controls.addWidget(enabled)
        controls.addWidget(pinned)

        def add_option(label, key, default=False):
            option = QCheckBox(label)
            option.setChecked(bool(self.app_settings.get(key, default)))
            option.toggled.connect(
                lambda checked, current_key=key:
                self.update_builtin_extension_value(current_key, checked)
            )
            controls.addWidget(option)
            return option

        if extension_id == "audio_enhancer":
            self._add_extension_slider(controls, "Громкость", "audio_boost", 100, 600, "%")
            curve = EqualizerCurve(self.theme_colors["accent"])
            curve_values = [int(self.app_settings.get(f"audio_eq_{frequency}", 0))
                            for frequency in (32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)]
            curve.set_values(curve_values)
            controls.addWidget(curve)
            for band_index, (frequency, label) in enumerate(zip(
                (32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000),
                ("32 Hz", "64 Hz", "125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz", "16 kHz"),
            )):
                def update_curve(value, index=band_index):
                    curve_values[index] = value
                    curve.set_values(curve_values)
                self._add_extension_slider(
                    controls, label, f"audio_eq_{frequency}", -12, 12, " dB",
                    on_change=update_curve,
                )
            reset_equalizer = QPushButton("Сбросить эквалайзер")
            def reset_curve():
                for frequency in (32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000):
                    self.app_settings[f"audio_eq_{frequency}"] = 0
                self.save_app_settings()
                self.apply_builtin_extensions_to_all()
                self._show_extension_details_in_popup(popup, stack, extension_id)
            reset_equalizer.clicked.connect(reset_curve)
            controls.addWidget(reset_equalizer)
        elif extension_id == "video_speed":
            self._add_extension_slider(
                controls, "Скорость", "video_speed", 25, 1000, "x",
                scale=100, step=25, tick_interval=100,
            )
            hint = QLabel("Шаг 0.25x. Отметки под шкалой соответствуют целым значениям скорости.")
            hint.setObjectName("extensionHint")
            hint.setWordWrap(True)
            controls.addWidget(hint)
        elif extension_id == "ad_blocker":
            add_option("Строгая защита от трекеров", "blocker_strict", True)
            add_option("Очищать ссылки от рекламных меток", "blocker_clean_links", True)
            add_option("Скрывать cookie-баннеры", "blocker_cookie_banners", True)
            custom_filters = QLineEdit(str(self.app_settings.get("blocker_custom_filters", "")))
            custom_filters.setMinimumWidth(0)
            custom_filters.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            custom_filters.setPlaceholderText("Блокировать домены: ads.example.com, tracker.example")
            custom_filters.setClearButtonEnabled(True)
            custom_filters.editingFinished.connect(
                lambda field=custom_filters:
                self.update_builtin_extension_value("blocker_custom_filters", field.text().strip())
            )
            allowlist = QLineEdit(str(self.app_settings.get("blocker_allowlist", "")))
            allowlist.setMinimumWidth(0)
            allowlist.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            allowlist.setPlaceholderText("Белый список: example.com, trusted.site")
            allowlist.setClearButtonEnabled(True)
            allowlist.editingFinished.connect(
                lambda field=allowlist:
                self.update_builtin_extension_value("blocker_allowlist", field.text().strip())
            )
            controls.addWidget(custom_filters)
            controls.addWidget(allowlist)
            stat = QLabel("На текущей странице: …")
            stat.setStyleSheet("font-size:15px;font-weight:600;")
            hint = QLabel("Заблокированные рекламные и отслеживающие запросы на текущей странице.")
            hint.setObjectName("extensionHint")
            controls.addWidget(stat)
            controls.addWidget(hint)
            browser = self.current_browser()
            if browser and not browser.internal_page:
                def update_stat(value, label=stat):
                    try:
                        label.setText(f"На текущей странице: {int(value or 0)}")
                    except RuntimeError:
                        pass
                browser.runJavaScript(
                    f"Number(window.__gromBuiltinStats?.[{json.dumps(extension_id)}] || 0)",
                    update_stat,
                )
        elif extension_id == "youtube_insights":
            add_option("Показывать панель анализа на видео", "youtube_insights_panel", True)
            add_option("Скрывать раздел Shorts", "youtube_hide_shorts", False)
            add_option("Скрывать комментарии", "youtube_hide_comments", False)
            add_option("Скрывать чат трансляций", "youtube_hide_live_chat", False)
            add_option("Скрывать рекомендации справа", "youtube_hide_recommendations", False)
            add_option("Скрывать конечные заставки видео", "youtube_hide_end_screens", False)
            hint = QLabel("Анализ выполняется локально по данным открытой страницы. Облачные метрики vidIQ и закрытые данные каналов без API недоступны.")
            hint.setObjectName("extensionHint")
            hint.setWordWrap(True)
            controls.addWidget(hint)
        elif extension_id == "twitch_enhancer":
            add_option("Автоматически собирать бонусные баллы", "twitch_auto_points", True)
            add_option("Компактный чат", "twitch_compact_chat", False)
            self._add_extension_slider(
                controls, "Размер смайликов", "twitch_emote_size",
                16, 64, " px", step=2, tick_interval=8,
            )
            add_option("Считать видимых участников чата", "twitch_visible_chatters", True)
            add_option("Показывать изображения и видео из ссылок чата", "twitch_chat_media", True)
            add_option("Закреплять любимые каналы в боковой панели", "twitch_pin_streamers", True)
            add_option("Показывать панель канала и ссылки аналитики", "twitch_channel_tools", True)
            add_option("Подсвечивать сообщения автора при наведении", "twitch_highlight_mentions", True)
            add_option("Показывать задержку трансляции", "twitch_stream_latency", True)
            add_option("Показывать реальное время VOD", "twitch_vod_time", True)
            add_option("Добавлять скачивание клипов", "twitch_clip_download", True)
            add_option("Контекстное меню сообщений чата", "twitch_message_menu", True)
            add_option("Считать локальное время просмотра и команду /watchtime", "twitch_local_watchtime", True)
            add_option("Полностью скрывать чат", "twitch_hide_chat", False)
            add_option("Скрывать левую панель каналов", "twitch_hide_sidebar", False)
            add_option("Скрывать рекомендации каналов", "twitch_hide_recommendations", False)
            add_option("Скрывать оверлеи расширений Twitch", "twitch_hide_extensions", False)
            stat = QLabel("Собрано бонусов на странице: …")
            controls.addWidget(stat)
            browser = self.current_browser()
            if browser and not browser.internal_page:
                browser.runJavaScript(
                    "Number(window.__gromBuiltinStats?.twitch_enhancer || 0)",
                    lambda value, label=stat: label.setText(f"Собрано бонусов на странице: {int(value or 0)}"),
                )
            hint = QLabel("Точный общий список чаттеров Twitch доступен только владельцу или модератору через OAuth. Grom показывает участников, сообщения которых уже видны в загруженном чате. Функции видео, медиа и локального времени работают также на Kick.")
            hint.setObjectName("extensionHint")
            hint.setWordWrap(True)
            controls.addWidget(hint)
        elif extension_id == "faceit_enhancer":
            add_option("Компактные карточки матчей", "faceit_compact_cards", True)
            add_option("Подсвечивать сильную статистику", "faceit_highlight_stats", True)
            add_option("Автоматически принимать найденный матч", "faceit_auto_accept", False)
            warning = QLabel("Автопринятие нажимает кнопку только при точном тексте «Accept» или «Принять».")
            warning.setObjectName("extensionHint")
            warning.setWordWrap(True)
            controls.addWidget(warning)
        elif extension_id == "password_manager":
            count = len(self.password_page_records())
            summary = QLabel(f"Сохранено учётных записей: {count}")
            summary.setStyleSheet("font-size:15px;font-weight:600;")
            open_passwords = QPushButton("Открыть менеджер паролей")
            open_passwords.clicked.connect(
                lambda: (popup.close(), self.open_settings_tab("privacy"))
            )
            controls.addWidget(summary)
            controls.addWidget(open_passwords)
        else:
            hint = QLabel("Расширение работает автоматически на подходящих страницах.")
            hint.setObjectName("extensionHint")
            hint.setWordWrap(True)
            controls.addWidget(hint)
        controls.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        layout.addWidget(scroll, 1)
        stack.addWidget(page)
        stack.setCurrentWidget(page)

    def show_builtin_extensions_popup(self, extension_id=None, force=False):
        if isinstance(extension_id, bool):
            extension_id = None
        if not extension_id and not force and hasattr(self, "begin_toggle_popup"):
            if not self.begin_toggle_popup(
                "builtin_extensions_popup", "extensions"
            ):
                return
        existing = getattr(self, "builtin_extensions_popup", None)
        if existing:
            try:
                if existing.isVisible():
                    if extension_id:
                        self._show_extension_details_in_popup(
                            existing, existing.extension_stack, extension_id
                        )
                        existing.raise_()
                        return
                    if not force:
                        existing.close()
                        return
            except RuntimeError:
                existing = None
                self.builtin_extensions_popup = None
        if existing:
            existing.close()

        popup = QFrame(
            self,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        popup.setObjectName("builtinExtensionsPopup")
        if hasattr(self, "register_toggle_popup"):
            self.register_toggle_popup(
                popup, "builtin_extensions_popup", "extensions"
            )
        else:
            popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup.setFixedSize(430, 600)
        popup.setStyleSheet(self._extensions_popup_stylesheet())
        outer = QVBoxLayout(popup)
        outer.setContentsMargins(0, 0, 0, 0)
        stack = QStackedWidget()
        popup.extension_stack = stack
        stack.addWidget(self._build_extensions_list_page(popup, stack))
        outer.addWidget(stack)
        popup.destroyed.connect(
            lambda _object=None, closed_popup=popup:
            self.clear_extensions_popup_reference(closed_popup)
        )
        self.builtin_extensions_popup = popup

        anchor = getattr(self, "extensions_btn", None)
        if anchor and anchor.isVisible():
            point = anchor.mapToGlobal(anchor.rect().bottomRight())
            screen = anchor.screen().availableGeometry()
            x = min(point.x(), screen.right()) - popup.width()
            x = max(screen.left(), x)
            y = min(point.y() + 6, screen.bottom() - popup.height() + 1)
            popup.move(x, max(screen.top(), y))
        else:
            self.position_popup(popup)
        if extension_id:
            self._show_extension_details_in_popup(popup, stack, extension_id)
        popup.show()
        popup.raise_()

    def show_builtin_extension_details(self, extension_id):
        self.show_builtin_extensions_popup(extension_id, force=True)

    def update_builtin_extension(self, extension_id, enabled):
        state = self.builtin_extension_state()
        state[extension_id] = bool(enabled)
        self.app_settings["builtin_extensions"] = state
        if extension_id == "ad_blocker":
            self.app_settings["ad_blocker"] = bool(enabled)
        elif extension_id == "password_manager":
            self.app_settings["password_manager"] = bool(enabled)
        self.save_app_settings()
        self.apply_builtin_extensions_to_all()
        self.refresh_extension_toolbar_buttons()
