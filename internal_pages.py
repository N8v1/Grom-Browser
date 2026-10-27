from __future__ import annotations

import json
import os

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class InternalPagesMixin:
    def welcome_page_html(self):
        colors = json.dumps(self.theme_colors, ensure_ascii=False)
        state = json.dumps(
            {
                "theme": self.app_settings.get("theme", "light"),
                "show_forward": self.app_settings.get("show_forward", True),
                "show_home_button": self.app_settings.get("show_home_button", False),
                "interface_language": self.app_settings.get("interface_language", "en"),
            },
            ensure_ascii=False,
        )
        logo = self.file_data_uri(os.path.join(os.path.dirname(__file__), "Grom.png"))
        icon = self.brand_icon_data_uri()
        html = r"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Добро пожаловать</title>
<style>
:root{--background:#17181a;--surface:#35363a;--toolbar:#292a2d;--input:#202124;--border:#5f6368;--text:#f1f3f4;--muted:#bdc1c6;--accent:#8ab4f8;--hover:#45474c}*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:var(--background);color:var(--text);font-family:"Segoe UI",Arial,sans-serif}button{font:inherit;cursor:pointer}.stage{position:relative;width:100%;height:100%;overflow:hidden}.ambient{position:absolute;inset:0;opacity:.36;pointer-events:none}.line{position:absolute;height:1px;background:var(--border);animation:travel 10s linear infinite}.line:nth-child(1){top:17%;left:-20%;width:52%;animation-delay:-2s}.line:nth-child(2){top:42%;right:-18%;width:44%;animation-delay:-7s;animation-direction:reverse}.line:nth-child(3){bottom:18%;left:-12%;width:36%;animation-delay:-4s}@keyframes travel{50%{transform:translateX(46vw);opacity:.75}}.top{position:absolute;z-index:3;top:24px;left:30px;right:30px;display:flex;align-items:center;justify-content:space-between}.mini-brand{display:flex;align-items:center;gap:10px;font-weight:650}.mini-brand img{width:28px;height:28px;object-fit:contain}.progress{display:flex;gap:7px}.progress span{width:36px;height:3px;background:var(--border);transition:.35s}.progress span.active{background:var(--accent)}.slides{height:100%;display:flex;transition:transform .65s cubic-bezier(.2,.75,.2,1)}.slide{position:relative;flex:0 0 100%;height:100%;display:grid;place-items:center;padding:82px 7vw 72px}.content{width:min(920px,100%);text-align:center}.hero-icon{width:94px;height:94px;object-fit:contain;opacity:0;transform:scale(.72) rotate(-7deg);animation:iconIn .85s .15s cubic-bezier(.2,.8,.2,1) forwards}.hero-logo{display:block;width:min(360px,62vw);height:150px;object-fit:contain;margin:5px auto -12px;opacity:0;transform:translateY(18px);animation:rise .75s .45s ease forwards}.hero-title{margin:0;font-size:clamp(34px,6vw,72px);font-weight:720;letter-spacing:0;opacity:0;animation:rise .75s .7s ease forwards}.lead{width:min(650px,100%);margin:18px auto 0;color:var(--muted);font-size:17px;line-height:1.55}.slide h2{margin:0 0 10px;font-size:34px;letter-spacing:0}.swatches{display:flex;flex-wrap:wrap;justify-content:center;gap:15px;margin:32px auto 0}.swatch{width:48px;height:48px;padding:0;border:2px solid transparent;border-radius:50%;background:var(--swatch);box-shadow:0 0 0 1px var(--border)}.swatch:hover{transform:translateY(-3px)}.swatch.active{border-color:var(--text);box-shadow:0 0 0 3px var(--accent)}.preferences{width:min(720px,100%);margin:30px auto 0;text-align:left;border-top:1px solid var(--border)}.preference{display:flex;align-items:center;justify-content:space-between;gap:30px;padding:20px 4px;border-bottom:1px solid var(--border)}.preference strong{display:block;font-size:15px}.preference small{display:block;margin-top:5px;color:var(--muted);font-size:13px}.switch{position:relative;width:48px;height:27px;flex:0 0 auto}.switch input{opacity:0;width:0;height:0}.slider{position:absolute;inset:0;border-radius:14px;background:var(--border);transition:.2s}.slider:after{content:"";position:absolute;left:4px;top:4px;width:19px;height:19px;border-radius:50%;background:#fff;transition:.2s}.switch input:checked+.slider{background:var(--accent)}.switch input:checked+.slider:after{transform:translateX(21px)}.feature-row{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin:32px auto 0;background:var(--border);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}.feature{min-height:120px;padding:24px;background:var(--background);text-align:left}.feature b{display:block;margin-bottom:8px}.feature span{color:var(--muted);font-size:13px;line-height:1.45}.controls{position:absolute;z-index:4;left:0;right:0;bottom:24px;display:flex;justify-content:center;gap:10px}.primary,.secondary{height:44px;padding:0 22px;border:0;border-radius:8px}.primary{color:#fff;background:var(--accent);font-weight:650}.primary:hover{filter:brightness(1.08)}.secondary{color:var(--text);background:var(--surface)}.secondary:hover{background:var(--hover)}@keyframes iconIn{to{opacity:1;transform:scale(1) rotate(0)}}@keyframes rise{to{opacity:1;transform:translateY(0)}}@media(max-width:700px){.top{left:16px;right:16px}.slide{padding-inline:18px}.hero-title{font-size:38px}.feature-row{grid-template-columns:1fr}.feature{min-height:auto}.lead{font-size:15px}.progress span{width:22px}}
</style></head><body><div class="stage"><div class="ambient"><span class="line"></span><span class="line"></span><span class="line"></span></div><header class="top"><div class="mini-brand"><img src="__ICON__" alt=""><span>Grom Browser</span></div><div id="progress" class="progress"><span></span><span></span><span></span><span></span></div></header><div id="slides" class="slides">
<section class="slide"><div class="content"><img class="hero-icon" src="__ICON__" alt=""><img class="hero-logo" src="__LOGO__" alt="Grom"><h1 class="hero-title">Добро пожаловать в Grom</h1><p class="lead">Быстрый браузер с рабочими пространствами, разделением экрана, профилями и инструментами приватности. Настроим главное за минуту.</p></div></section>
<section class="slide"><div class="content"><h2>Выберите настроение</h2><p class="lead">Тема применяется сразу ко всему браузеру. Позже её всегда можно поменять в настройках.</p><div class="swatches"><button class="swatch" title="Светлая" data-theme="light" style="--swatch:#e8eaed"></button><button class="swatch" title="Тёмная" data-theme="dark" style="--swatch:#202124"></button><button class="swatch" title="Тёмно-серая" data-theme="dark_gray" style="--swatch:#3c4043"></button><button class="swatch" title="Фиолетовая" data-theme="purple" style="--swatch:#493267"></button><button class="swatch" title="Тёмно-зелёная" data-theme="dark_green" style="--swatch:#1d4037"></button><button class="swatch" title="Синяя" data-theme="blue" style="--swatch:#1f4f82"></button><button class="swatch" title="Бирюзовая" data-theme="cyan" style="--swatch:#176b72"></button><button class="swatch" title="Розовая" data-theme="rose" style="--swatch:#7b3f57"></button><button class="swatch" title="Красная" data-theme="red" style="--swatch:#7a2830"></button><button class="swatch" title="Оранжевая" data-theme="orange" style="--swatch:#8a4c20"></button></div></div></section>
<section class="slide"><div class="content"><h2>Панель под ваш сценарий</h2><p class="lead">Оставьте только те кнопки, которыми действительно пользуетесь.</p><div class="preferences"><label class="preference"><span><strong>Кнопка «Вперёд»</strong><small>Возвращает к следующей странице в истории вкладки.</small></span><span class="switch"><input id="welcomeForward" type="checkbox"><span class="slider"></span></span></label><label class="preference"><span><strong>Кнопка «Главная»</strong><small>Быстрый переход на стартовую страницу Grom.</small></span><span class="switch"><input id="welcomeHome" type="checkbox"><span class="slider"></span></span></label></div></div></section>
<section class="slide"><div class="content"><h2>Всё готово</h2><p class="lead">Главная страница уже открыта в соседней вкладке. В ней доступны умный поиск, быстрые ссылки и собственный фон.</p><div class="feature-row"><div class="feature"><b>Контроль памяти</b><span>Неактивные вкладки могут засыпать и восстанавливаться по вашему запросу.</span></div><div class="feature"><b>Два сайта рядом</b><span>Разделяйте вкладку на две части для сравнения и параллельной работы.</span></div><div class="feature"><b>Личные профили</b><span>Раздельные настройки, история, закладки и гостевой режим.</span></div></div></div></section>
</div><nav class="controls"><button id="back" class="secondary">Назад</button><button id="next" class="primary">Продолжить</button></nav></div>
<script>const colors=__COLORS__,state=__STATE__;window.__gromCommandQueue=[];let page=0;const slides=document.getElementById('slides'),back=document.getElementById('back'),next=document.getElementById('next'),steps=[...document.querySelectorAll('#progress span')],forward=document.getElementById('welcomeForward'),home=document.getElementById('welcomeHome');function send(action,data={}){window.__gromCommandQueue.push(Object.assign({action},data))}function setCss(value){const root=document.documentElement.style;Object.entries(value).forEach(([key,item])=>typeof item==='string'&&root.setProperty(`--${key}`,item))}window.applyThemeFromHost=setCss;setCss(colors);forward.checked=Boolean(state.show_forward);home.checked=Boolean(state.show_home_button);function render(){slides.style.transform=`translateX(${-page*100}%)`;steps.forEach((step,index)=>step.classList.toggle('active',index<=page));back.style.visibility=page?'visible':'hidden';next.textContent=page===3?'Начать работу':'Продолжить'}back.onclick=()=>{page=Math.max(0,page-1);render()};next.onclick=()=>{if(page===3){send('finish_welcome');return}page++;render()};document.querySelectorAll('.swatch').forEach(button=>{button.classList.toggle('active',button.dataset.theme===state.theme);button.onclick=()=>{state.theme=button.dataset.theme;document.querySelectorAll('.swatch').forEach(item=>item.classList.toggle('active',item===button));send('welcome_preferences',{theme:state.theme,show_forward:forward.checked,show_home_button:home.checked})}});function preferences(){send('welcome_preferences',{theme:state.theme,show_forward:forward.checked,show_home_button:home.checked})}forward.onchange=preferences;home.onchange=preferences;render();</script></body></html>"""
        html = html.replace(
            '<h1 class="hero-title">Добро пожаловать в Grom</h1>',
            '<h1 class="hero-title">Добро пожаловать</h1>',
        )
        html = html.replace(
            '.controls{position:absolute;z-index:4;left:0;right:0;bottom:24px;display:flex;justify-content:center;gap:10px}',
            '.controls{position:absolute;z-index:4;left:0;right:0;bottom:24px;display:grid;grid-template-columns:120px 180px 120px;justify-content:center;gap:10px}.controls #back{grid-column:1}.controls #next{grid-column:2}',
        )
        html = html.replace(
            "</style></head>",
            ".language-switcher{padding:7px 10px;color:var(--text);background:var(--surface);border:1px solid var(--border);border-radius:7px;font:13px 'Segoe UI',Arial,sans-serif}</style></head>",
            1,
        )
        html = html.replace(
            '<div id="progress" class="progress">',
            '<select id="gromLanguage" class="language-switcher" aria-label="Выбор языка"><option value="ru">Русский</option><option value="en">English</option></select><div id="progress" class="progress">',
            1,
        )
        html = html.replace(
            "forward.onchange=preferences;home.onchange=preferences;render();",
            "forward.onchange=preferences;home.onchange=preferences;const languageSelect=document.getElementById('gromLanguage');languageSelect.value=state.interface_language||'en';languageSelect.addEventListener('change',()=>send('set_interface_language',{language:languageSelect.value}));render();",
            1,
        )
        html = html.replace(
            '</style></head>',
            '.waves{position:absolute;z-index:1;left:0;bottom:-2px;width:200%;height:155px;opacity:.58;animation:waveTravel 13s linear infinite;pointer-events:none}.waves path{fill:none;stroke:var(--accent);stroke-width:2}.waves path:nth-child(2){stroke:var(--border);stroke-width:3}.waves path:nth-child(3){stroke:var(--text);stroke-width:1;opacity:.34}@keyframes waveTravel{to{transform:translateX(-50%)}}</style></head>',
        )
        html = html.replace(
            '<div class="ambient"><span class="line"></span><span class="line"></span><span class="line"></span></div>',
            '<div class="ambient"><span class="line"></span><span class="line"></span><span class="line"></span></div><svg class="waves" viewBox="0 0 2400 180" preserveAspectRatio="none" aria-hidden="true"><path d="M0 108 C180 28 360 168 540 92 S900 28 1080 104 S1440 166 1620 84 S1980 24 2160 102 S2340 158 2400 110"/><path d="M0 136 C210 70 390 174 600 118 S990 58 1200 130 S1590 174 1800 110 S2190 52 2400 132"/><path d="M0 82 C160 142 350 20 520 90 S870 146 1040 76 S1390 18 1560 88 S1910 148 2080 76 S2310 38 2400 82"/></svg>',
        )
        return html.replace("__ICON__", icon).replace("__LOGO__", logo).replace(
            "__COLORS__", colors
        ).replace("__STATE__", state)

    def home_page_html(self):
        use_theme = self.app_settings.get("home_use_theme", True)
        home_color = self.app_settings.get("home_color", "#202124")
        page_colors = self.theme_colors if use_theme else self.build_theme_colors(home_color)
        background = ""
        background_path = self.app_settings.get("home_background_path", "")
        if background_path:
            background = self.file_data_uri(background_path)
        if not background:
            candidate = self.app_settings.get("home_background_url", "")
            if QUrl(candidate).scheme() in ("http", "https"):
                background = candidate
        config = {
            "use_theme": bool(use_theme),
            "color": home_color,
            "background_url": self.app_settings.get("home_background_url", ""),
            "background": background,
            "search_engine": self.app_settings.get("search_engine", "google"),
            "interface_language": self.app_settings.get("interface_language", "en"),
            "shortcuts_limit": self.app_settings.get("home_shortcuts_limit", 16),
            "popular_queries": [
                "погода сегодня", "новости сегодня", "курс валют",
                "переводчик", "карты", "музыка", "фильмы онлайн",
            ],
        }
        logo = self.file_data_uri(os.path.join(os.path.dirname(__file__), "Grom.png"))
        app_icon = self.brand_icon_data_uri()
        html = r"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Grom</title>
<style>.brand-lockup{display:flex;align-items:center;justify-content:center;gap:18px;margin-bottom:30px}.app-icon{width:76px;height:76px;object-fit:contain;flex:0 0 auto}.logo{width:280px!important;height:140px!important;margin:0!important}.name{display:none!important}@media(max-width:600px){.brand-lockup{gap:10px}.app-icon{width:56px;height:56px}.logo{width:210px!important;height:105px!important}}</style>
<style>
:root{--background:#17181a;--surface:#35363a;--toolbar:#292a2d;--input:#202124;--border:#5f6368;--text:#f1f3f4;--muted:#bdc1c6;--accent:#8ab4f8;--hover:#45474c;--wallpaper:none}*{box-sizing:border-box}html,body{margin:0;width:100%;min-height:100%;font-family:"Segoe UI",Arial,sans-serif;color:var(--text);background:var(--background)}body{min-height:100vh;background-image:linear-gradient(rgba(0,0,0,.28),rgba(0,0,0,.28)),var(--wallpaper);background-size:cover;background-position:center;background-attachment:fixed}.home{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:42px 24px 15vh}.center{width:min(720px,100%);text-align:center}.logo{width:132px;height:132px;object-fit:contain;margin-bottom:20px}.name{margin:0 0 30px;font-size:34px;font-weight:650}.search-wrap{position:relative}.search{width:100%;height:54px;padding:0 58px 0 20px;color:var(--text);background:color-mix(in srgb,var(--input) 94%,transparent);border:1px solid var(--border);border-radius:27px;outline:none;font-size:16px;box-shadow:0 8px 24px rgba(0,0,0,.22);backdrop-filter:blur(12px)}.search:focus{border-color:var(--accent)}.submit{position:absolute;right:8px;top:7px;width:40px;height:40px;border:0;border-radius:50%;color:var(--text);background:var(--surface);font-size:18px}.submit:hover{background:var(--hover)}.suggestions{display:none;position:absolute;z-index:4;top:61px;left:12px;right:12px;max-height:330px;overflow:auto;padding:6px;background:var(--toolbar);border:1px solid var(--border);border-radius:10px;text-align:left;box-shadow:0 14px 30px rgba(0,0,0,.3)}.suggestions.visible{display:block}.suggestion{display:block;width:100%;padding:10px 12px;color:var(--text);background:transparent;border:0;border-radius:7px;text-align:left}.suggestion:hover,.suggestion.active{background:var(--hover)}.suggestion small{display:block;margin-top:3px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.customize{position:fixed;right:22px;bottom:22px;padding:10px 14px;color:var(--text);background:var(--toolbar);border:1px solid var(--border);border-radius:8px}.customize:hover{background:var(--hover)}.panel{display:none;position:fixed;right:22px;bottom:72px;width:340px;padding:18px;background:var(--toolbar);border:1px solid var(--border);border-radius:10px;box-shadow:0 16px 34px rgba(0,0,0,.3);text-align:left}.panel.visible{display:block}.panel h2{margin:0 0 16px;font-size:16px}.row{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:12px 0}.row input[type=color]{width:42px;height:32px;padding:0;border:1px solid var(--border);background:transparent}.url{width:100%;height:38px;padding:0 10px;color:var(--text);background:var(--input);border:1px solid var(--border);border-radius:6px;outline:none}.buttons{display:flex;gap:8px;margin-top:10px}.buttons button{flex:1;padding:9px;color:var(--text);background:var(--surface);border:0;border-radius:6px}.buttons button:hover{background:var(--hover)}@media(max-width:600px){.logo{width:96px;height:96px}.name{font-size:28px}.panel{left:14px;right:14px;width:auto}.home{padding-inline:14px}}
 .quick-links{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:18px}.quick-link{height:78px;display:flex;align-items:center;gap:11px;padding:12px 14px;color:var(--text);background:color-mix(in srgb,var(--toolbar) 92%,transparent);border:1px solid var(--border);border-radius:14px;text-align:left;overflow:hidden;backdrop-filter:blur(12px)}.quick-link:hover{background:var(--hover);border-color:var(--accent)}.quick-icon{width:38px;height:38px;display:grid;place-items:center;flex:0 0 auto;border-radius:10px;background:var(--surface);color:var(--text);font-size:17px;font-weight:600}.quick-icon img{width:24px;height:24px;object-fit:contain}.quick-title{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.quick-add{justify-content:center;text-align:center}.quick-add .quick-icon{font-size:25px;font-weight:400}.quick-menu{display:none;position:fixed;z-index:20;width:170px;padding:5px;background:var(--toolbar);border:1px solid var(--border);border-radius:8px;box-shadow:0 12px 28px rgba(0,0,0,.32)}.quick-menu.visible{display:block}.quick-menu button{display:block;width:100%;padding:9px 11px;color:var(--text);background:transparent;border:0;border-radius:6px;text-align:left}.quick-menu button:hover{background:var(--hover)}@media(max-width:650px){.quick-links{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style></head><body><main class="home"><div class="center"><div class="brand-lockup"><img class="app-icon" src="__ICON__" alt=""><img class="logo" src="__LOGO__" alt="Grom"></div><h1 class="name">Grom</h1><div class="search-wrap"><input id="search" class="search" autocomplete="off" placeholder="Поиск или адрес"><button id="submit" class="submit" title="Открыть">→</button><div id="suggestions" class="suggestions"></div></div><div id="quickLinks" class="quick-links"></div></div></main><div id="quickMenu" class="quick-menu"><button id="renameQuick">Переименовать</button><button id="deleteQuick">Удалить</button></div><button id="customize" class="customize">Настроить</button><section id="panel" class="panel"><h2>Главная страница</h2><label class="row"><span>Цвета темы браузера</span><input id="useTheme" type="checkbox"></label><label class="row"><span>Основной цвет</span><input id="homeColor" type="color"></label><div class="row" style="display:block"><span>Ссылка на изображение</span><input id="backgroundUrl" class="url" type="url" placeholder="https://example.com/background.jpg"></div><div class="buttons"><button id="apply">Применить</button><button id="upload">Загрузить</button><button id="clear">Убрать фон</button></div></section>
<script>
const config=__CONFIG__,items=__SUGGESTIONS__,quickLinkItems=__QUICK_LINKS__;window.__gromCommandQueue=[];let active=-1;
function setCss(colors){const root=document.documentElement.style;Object.entries(colors).forEach(([key,value])=>{if(typeof value==='string')root.setProperty(`--${key}`,value)})}window.applyThemeFromHost=colors=>{if(config.use_theme)setCss(colors)};setCss(__COLORS__);if(config.background)document.documentElement.style.setProperty('--wallpaper',`url(${JSON.stringify(config.background)})`);
const search=document.getElementById('search'),suggestions=document.getElementById('suggestions');
function send(action,data={}){window.__gromCommandQueue.push(Object.assign({action},data))}function openValue(value){if(value.trim())send('navigate_home',{value:value.trim()})}
const quickMenu=document.getElementById('quickMenu');let selectedQuick=null;
function hideQuickMenu(){quickMenu.classList.remove('visible');selectedQuick=null}
function showQuickMenu(event,item){event.preventDefault();selectedQuick=item;quickMenu.classList.add('visible');const width=170,height=82;quickMenu.style.left=`${Math.max(8,Math.min(event.clientX,innerWidth-width-8))}px`;quickMenu.style.top=`${Math.max(8,Math.min(event.clientY,innerHeight-height-8))}px`}
function renderQuickLinks(){const target=document.getElementById('quickLinks');target.textContent='';quickLinkItems.forEach(item=>{const button=document.createElement('button');button.className='quick-link';const icon=document.createElement('span');icon.className='quick-icon';if(item.icon){const image=document.createElement('img');image.src=item.icon;image.alt='';icon.append(image)}else icon.textContent=(item.title||'?').trim().slice(0,1).toUpperCase();const title=document.createElement('span');title.className='quick-title';title.textContent=item.title;button.append(icon,title);button.title=item.url;button.onclick=()=>openValue(item.url);button.oncontextmenu=event=>showQuickMenu(event,item);target.append(button)});const add=document.createElement('button');add.className='quick-link quick-add';add.innerHTML='<span class="quick-icon">+</span><span class="quick-title">Добавить сайт</span>';add.onclick=()=>{const url=prompt('Ссылка на сайт','https://');if(!url?.trim())return;const name=prompt('Название сайта','')||'';send('add_home_shortcut',{url:url.trim(),name:name.trim()})};target.append(add)}renderQuickLinks();
document.getElementById('renameQuick').onclick=()=>{if(!selectedQuick)return;const name=prompt('Новое название',selectedQuick.title)||'';if(name.trim())send('rename_home_shortcut',{url:selectedQuick.url,name:name.trim()});hideQuickMenu()};document.getElementById('deleteQuick').onclick=()=>{if(selectedQuick)send('delete_home_shortcut',{url:selectedQuick.url});hideQuickMenu()};
function normalized(value){return String(value||'').trim().toLocaleLowerCase('ru-RU')}
function suggestionButton(title,subtitle,value){const button=document.createElement('button');button.className='suggestion';const label=document.createElement('span');label.textContent=title;const detail=document.createElement('small');detail.textContent=subtitle;button.append(label,detail);button.onclick=()=>openValue(value);suggestions.append(button)}
const keyboardEnglish="qwertyuiop[]asdfghjkl;'zxcvbnm,.",keyboardRussian='\u0439\u0446\u0443\u043a\u0435\u043d\u0433\u0448\u0449\u0437\u0445\u044a\u0444\u044b\u0432\u0430\u043f\u0440\u043e\u043b\u0434\u0436\u044d\u044f\u0447\u0441\u043c\u0438\u0442\u044c\u0431\u044e';
function keyboardSwap(value,from,to){return [...value].map(letter=>{const index=from.indexOf(letter);return index<0?letter:to[index]}).join('')}
function queryVariants(value){const query=normalized(value);return [...new Set([query,keyboardSwap(query,keyboardEnglish,keyboardRussian),keyboardSwap(query,keyboardRussian,keyboardEnglish)])]}
function editDistance(left,right){const row=[...Array(right.length+1).keys()];for(let i=1;i<=left.length;i++){let previous=row[0];row[0]=i;for(let j=1;j<=right.length;j++){const saved=row[j];row[j]=Math.min(row[j]+1,row[j-1]+1,previous+(left[i-1]===right[j-1]?0:1));previous=saved}}return row[right.length]}
function textScore(text,query){const words=normalized(text).split(/\s+/).filter(Boolean);let best=-1;for(const variant of queryVariants(query)){if(words.includes(variant))best=Math.max(best,1000);if(words.some(word=>word.startsWith(variant)))best=Math.max(best,700);if(words.join(' ').includes(variant))best=Math.max(best,450);if(variant.length>=3&&words.some(word=>editDistance(variant,word)<=Math.max(1,Math.floor(variant.length/4))))best=Math.max(best,360)}return best}
function matchScore(item,query){const title=normalized(item.title),host=normalized(new URL(item.url).hostname.replace(/^www\./,'')),aliases=normalized(item.aliases);return textScore(`${title} ${host} ${aliases}`,query)}
function render(){const raw=search.value.trim(),query=normalized(raw);suggestions.textContent='';active=-1;if(!query){suggestions.classList.remove('visible');return}suggestionButton(`Искать «${raw}»`,config.search_engine,raw);(config.popular_queries||[]).map(value=>({value,score:textScore(value,query)})).filter(item=>item.score>=360&&normalized(item.value)!==query).sort((a,b)=>b.score-a.score).slice(0,2).forEach(({value})=>suggestionButton(value,'Популярный запрос',value));items.map(item=>{const match=matchScore(item,query);return{item,match,score:match+Number(item.score||0)}}).filter(result=>result.match>=0).sort((a,b)=>b.score-a.score).slice(0,7).forEach(({item})=>suggestionButton(item.title,new URL(item.url).hostname.replace(/^www\./,''),item.url));suggestions.classList.add('visible')}
search.addEventListener('input',render);search.addEventListener('keydown',event=>{const buttons=[...suggestions.querySelectorAll('.suggestion')];if(event.key==='ArrowDown'){event.preventDefault();active=Math.min(buttons.length-1,active+1)}else if(event.key==='ArrowUp'){event.preventDefault();active=Math.max(0,active-1)}else if(event.key==='Enter'){event.preventDefault();if(active>=0&&buttons[active])buttons[active].click();else openValue(search.value);return}else return;buttons.forEach((button,index)=>button.classList.toggle('active',index===active))});document.getElementById('submit').onclick=()=>openValue(search.value);
const panel=document.getElementById('panel'),useTheme=document.getElementById('useTheme'),homeColor=document.getElementById('homeColor'),backgroundUrl=document.getElementById('backgroundUrl');useTheme.checked=config.use_theme;homeColor.value=config.color||'#202124';backgroundUrl.value=config.background_url||'';document.getElementById('customize').onclick=()=>panel.classList.toggle('visible');document.getElementById('apply').onclick=()=>send('set_home_customization',{use_theme:useTheme.checked,color:homeColor.value,background_url:backgroundUrl.value.trim()});document.getElementById('upload').onclick=()=>send('choose_home_background');document.getElementById('clear').onclick=()=>send('clear_home_background');document.addEventListener('pointerdown',event=>{if(!event.target.closest('.search-wrap'))suggestions.classList.remove('visible');if(!event.target.closest('.quick-menu'))hideQuickMenu()});requestAnimationFrame(()=>search.focus());
</script></body></html>"""
        html = html.replace(
            ".center{width:min(720px,100%);text-align:center}",
            ".center{width:min(1080px,100%);text-align:center}",
        ).replace(
            ".search-wrap{position:relative}",
            ".search-wrap{position:relative;width:min(720px,100%);margin-inline:auto}",
        ).replace(
            "grid-template-columns:repeat(4,minmax(0,1fr))",
            "grid-template-columns:repeat(5,minmax(0,1fr))",
        ).replace(
            "@media(max-width:650px){.quick-links",
            "@media(max-width:900px){.quick-links{grid-template-columns:repeat(4,minmax(0,1fr))}}@media(max-width:650px){.quick-links",
        )
        html = html.replace(
            '<div class="buttons"><button id="apply">',
            '<label class="row"><span>Максимум быстрых сайтов</span><input id="shortcutLimit" class="limit-input" type="number" min="4" max="40" step="1"></label><div class="buttons"><button id="apply">',
        ).replace(
            ".buttons{display:flex;gap:8px;margin-top:10px}",
            ".limit-input{width:78px;height:34px;padding:0 8px;color:var(--text);background:var(--input);border:1px solid var(--border);border-radius:6px}.buttons{display:flex;gap:8px;margin-top:10px}",
        ).replace(
            "backgroundUrl=document.getElementById('backgroundUrl');",
            "backgroundUrl=document.getElementById('backgroundUrl'),shortcutLimit=document.getElementById('shortcutLimit');",
        ).replace(
            "backgroundUrl.value=config.background_url||'';",
            "backgroundUrl.value=config.background_url||'';shortcutLimit.value=config.shortcuts_limit||16;",
        ).replace(
            "background_url:backgroundUrl.value.trim()});",
            "background_url:backgroundUrl.value.trim(),shortcuts_limit:Math.max(4,Math.min(40,Number(shortcutLimit.value)||16))});",
        )
        html = html.replace(
            "</style></head>",
            ".interface-language{position:fixed;z-index:5;top:22px;right:22px;padding:8px 11px;color:var(--text);background:var(--toolbar);border:1px solid var(--border);border-radius:8px;font:13px 'Segoe UI',Arial,sans-serif}</style></head>",
            1,
        )
        html = html.replace(
            '<button id="customize" class="customize">',
            '<select id="interfaceLanguage" class="interface-language" aria-label="Выбор языка"><option value="ru">Русский</option><option value="en">English</option></select><button id="customize" class="customize">',
            1,
        )
        html = html.replace(
            "renderQuickLinks();",
            "renderQuickLinks();const interfaceLanguage=document.getElementById('interfaceLanguage');interfaceLanguage.value=config.interface_language||'en';interfaceLanguage.addEventListener('change',()=>send('set_interface_language',{language:interfaceLanguage.value}));",
            1,
        )
        return html.replace("__LOGO__", logo).replace("__ICON__", app_icon).replace(
            "__CONFIG__", json.dumps(config, ensure_ascii=False)
        ).replace(
            "__SUGGESTIONS__", json.dumps(self.home_suggestions(), ensure_ascii=False)
        ).replace(
            "__QUICK_LINKS__", json.dumps(self.home_quick_links(), ensure_ascii=False)
        ).replace("__COLORS__", json.dumps(page_colors, ensure_ascii=False))

    def downloads_page_html(self):
        records = []
        for task in reversed(self.download_tasks):
            records.append({
                "id": str(task.get("id", "")),
                "name": str(task.get("name", "download")),
                "url": str(task.get("url", "")),
                "status": str(task.get("status", "")),
                "date": str(task.get("date", "")),
                "category": str(task.get("category", "Другое")),
                "source_host": str(task.get("source_host", "")),
                "checksum": str(task.get("checksum", "")),
                "security_status": str(task.get("security_status", "")),
                "exists": bool(task.get("path") and os.path.exists(task.get("path", ""))),
            })
        data = json.dumps(records, ensure_ascii=False)
        colors = json.dumps(self.theme_colors, ensure_ascii=False)
        html = r"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Загрузки</title>
<style>
:root{--background:#17181a;--surface:#35363a;--toolbar:#292a2d;--input:#202124;--border:#5f6368;--text:#f1f3f4;--muted:#bdc1c6;--accent:#8ab4f8;--hover:#45474c}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--background);color:var(--text);font-family:"Segoe UI",Arial,sans-serif}button,input{font:inherit}
.page{width:min(960px,calc(100% - 48px));margin:0 auto;padding:34px 0 70px}.header{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:24px}h1{margin:0;font-size:25px}.clear{color:var(--text);background:transparent;border:1px solid var(--border);padding:9px 14px;border-radius:7px}.clear:hover{background:var(--hover)}
.search{width:100%;height:42px;margin-bottom:18px;padding:0 15px;color:var(--text);background:var(--input);border:1px solid var(--border);border-radius:9px;outline:none}.search:focus{border-color:var(--accent)}
.list{border-top:1px solid var(--border)}.item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center;padding:16px 6px;border-bottom:1px solid var(--border)}.name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px;font-weight:600}.meta{margin-top:5px;color:var(--muted);font-size:12px}.actions{display:flex;gap:6px}.actions button{padding:8px 12px;color:var(--text);background:var(--surface);border:0;border-radius:6px}.actions button:hover{background:var(--hover)}.actions button:disabled{opacity:.45;cursor:default}.empty{padding:70px 0;text-align:center;color:var(--muted)}
@media(max-width:620px){.page{width:calc(100% - 28px);padding-top:24px}.header{align-items:flex-start}.item{grid-template-columns:1fr}.actions{justify-content:flex-start}}
</style></head><body><main class="page"><div class="header"><h1>Загрузки</h1><button id="clear" class="clear">Удалить все</button></div><input id="search" class="search" type="search" placeholder="Поиск загрузок"><div id="list" class="list"></div></main>
<script>
const records=__DOWNLOADS__;window.__gromCommandQueue=[];
function setCss(colors){const root=document.documentElement.style;Object.entries(colors).forEach(([name,value])=>{if(typeof value==='string')root.setProperty(`--${name}`,value)})}window.applyThemeFromHost=setCss;setCss(__COLORS__);
function send(action,id=''){window.__gromCommandQueue.push({action,id})}
 function render(query=''){const list=document.getElementById('list');list.textContent='';const needle=query.trim().toLowerCase();const visible=records.filter(item=>`${item.name} ${item.url} ${item.category} ${item.source_host}`.toLowerCase().includes(needle));if(!visible.length){const empty=document.createElement('div');empty.className='empty';empty.textContent=records.length?'Ничего не найдено':'Загрузок пока нет';list.append(empty);return}visible.forEach(item=>{const row=document.createElement('div');row.className='item';const copy=document.createElement('div');const name=document.createElement('div');name.className='name';name.textContent=item.name;const meta=document.createElement('div');meta.className='meta';meta.textContent=[item.status,item.category,item.source_host?`с сайта ${item.source_host}`:'',item.security_status,item.checksum?`SHA-256 ${item.checksum.slice(0,16)}…`:'',item.date].filter(Boolean).join(' · ');if(item.checksum)meta.title=item.checksum;copy.append(name,meta);const actions=document.createElement('div');actions.className='actions';const open=document.createElement('button');if(item.status==='Загрузка'){open.textContent='Пауза';open.onclick=()=>send('pause_download',item.id)}else if(item.status==='Приостановлено'){open.textContent='Продолжить';open.onclick=()=>send('resume_download',item.id)}else if(item.status==='Ошибка'){open.textContent='Повторить';open.onclick=()=>send('retry_download',item.id)}else{open.textContent='Открыть';open.disabled=!item.exists||item.status!=='Готово';open.onclick=()=>send('open_download',item.id)}const remove=document.createElement('button');remove.textContent='Удалить';remove.onclick=()=>send('delete_download',item.id);actions.append(open,remove);row.append(copy,actions);list.append(row)})}
document.getElementById('search').addEventListener('input',event=>render(event.target.value));document.getElementById('clear').onclick=()=>send('clear_downloads');render();
</script></body></html>"""
        return html.replace("__DOWNLOADS__", data).replace("__COLORS__", colors)

    def _legacy_settings_page_html(self):
        initial = json.dumps(self.app_settings, ensure_ascii=False)
        colors = json.dumps(self.theme_colors, ensure_ascii=False)
        html = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Настройки</title>
<style>
    :root {
        --background: #17181a;
        --surface: #35363a;
        --toolbar: #292a2d;
        --border: #5f6368;
        --text: #f1f3f4;
        --muted: #bdc1c6;
        --accent: #8ab4f8;
        --hover: #3c4043;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; background: var(--background); color: var(--text); font-family: "Segoe UI", Arial, sans-serif; }
    body { display: grid; grid-template-columns: 220px minmax(0, 1fr); }
    aside { min-height: 100vh; background: var(--toolbar); border-right: 1px solid var(--border); padding: 24px 14px; }
    .brand { font-size: 18px; font-weight: 600; padding: 0 12px 22px; }
    .nav-item { width: 100%; border: 0; border-left: 3px solid var(--accent); background: var(--hover); color: var(--text); padding: 11px 14px; text-align: left; font-size: 14px; }
    main { width: min(820px, calc(100% - 56px)); margin: 0 auto; padding: 36px 0 70px; }
    h1 { font-size: 24px; font-weight: 600; margin: 0 0 28px; }
    section { padding: 22px 0; border-bottom: 1px solid var(--border); }
    h2 { font-size: 16px; font-weight: 600; margin: 0 0 6px; }
    p { color: var(--muted); margin: 0 0 18px; line-height: 1.45; font-size: 13px; }
    .themes { display: grid; grid-template-columns: repeat(3, minmax(130px, 1fr)); gap: 10px; }
    .theme-button { border: 1px solid var(--border); background: transparent; color: var(--text); min-height: 50px; padding: 8px 10px; display: flex; align-items: center; gap: 10px; text-align: left; }
    .theme-button:hover { background: var(--hover); }
    .theme-button.active { border: 2px solid var(--accent); padding: 7px 9px; }
    .swatch { width: 24px; height: 24px; border: 1px solid var(--border); flex: 0 0 auto; }
    .custom-color { width: 24px; height: 28px; padding: 0; border: 0; background: transparent; }
    .setting-row { display: flex; align-items: center; justify-content: space-between; gap: 30px; min-height: 44px; }
    .setting-copy h2 { margin-bottom: 4px; }
    .setting-copy p { margin: 0; }
    .switch { position: relative; width: 42px; height: 24px; flex: 0 0 auto; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; inset: 0; background: var(--border); transition: .15s; border-radius: 12px; }
    .slider::before { content: ""; position: absolute; width: 18px; height: 18px; left: 3px; top: 3px; background: white; border-radius: 50%; transition: .15s; }
    .switch input:checked + .slider { background: var(--accent); }
    .switch input:checked + .slider::before { transform: translateX(18px); }
    .zoom-control { display: flex; align-items: center; gap: 14px; width: min(390px, 100%); }
    input[type="range"] { flex: 1; accent-color: var(--accent); }
    output { width: 54px; color: var(--text); text-align: right; }
    @media (max-width: 720px) {
        body { grid-template-columns: 1fr; }
        aside { min-height: auto; border-right: 0; border-bottom: 1px solid var(--border); padding: 16px; }
        .brand { padding-bottom: 12px; }
        main { width: calc(100% - 32px); padding-top: 24px; }
        .themes { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    }
</style>
</head>
<body>
<aside>
    <div class="brand">Настройки Grom</div>
    <button class="nav-item">Внешний вид</button>
</aside>
<main>
    <h1>Внешний вид</h1>
    <section>
        <h2>Цветовая тема</h2>
        <p>Основной цвет задаёт фон, панели, меню и контраст текста. Остальные оттенки создаются автоматически.</p>
        <div class="themes">
            <button class="theme-button" data-theme="light" data-color="#e8eaed"><span class="swatch" style="background:#e8eaed"></span>Светлая</button>
            <button class="theme-button" data-theme="dark" data-color="#202124"><span class="swatch" style="background:#202124"></span>Тёмная</button>
            <button class="theme-button" data-theme="dark_gray" data-color="#3c4043"><span class="swatch" style="background:#3c4043"></span>Тёмно-серая</button>
            <button class="theme-button" data-theme="purple" data-color="#493267"><span class="swatch" style="background:#493267"></span>Фиолетовая</button>
            <button class="theme-button" data-theme="dark_green" data-color="#1d4037"><span class="swatch" style="background:#1d4037"></span>Тёмно-зелёная</button>
            <button class="theme-button" data-theme="custom"><input id="customColor" class="custom-color" type="color"><span>Свой цвет</span></button>
        </div>
    </section>
    <section>
        <div class="setting-row">
            <div class="setting-copy">
                <h2>Кнопка «Вперёд»</h2>
                <p>Показывать кнопку перехода к следующей странице рядом с кнопкой «Назад».</p>
            </div>
            <label class="switch"><input id="forwardToggle" type="checkbox"><span class="slider"></span></label>
        </div>
    </section>
    <section>
        <div class="setting-copy">
            <h2>Масштаб страниц</h2>
            <p>Этот масштаб применяется к открытым и новым страницам.</p>
        </div>
        <div class="zoom-control">
            <input id="zoomRange" type="range" min="25" max="300" step="10">
            <output id="zoomValue"></output>
        </div>
    </section>
</main>
<script>
    const settings = __INITIAL__;
    window.__gromSettingsRevision = 0;
    window.__gromSettingsState = JSON.stringify(settings);

    const customColor = document.getElementById('customColor');
    const forwardToggle = document.getElementById('forwardToggle');
    const zoomRange = document.getElementById('zoomRange');
    const zoomValue = document.getElementById('zoomValue');

    customColor.value = settings.custom_color || '#3f4652';
    forwardToggle.checked = Boolean(settings.show_forward);
    zoomRange.value = settings.default_zoom || 100;
    zoomValue.value = `${zoomRange.value}%`;

    function setCss(colors) {
        const root = document.documentElement.style;
        for (const [name, value] of Object.entries(colors)) {
            if (typeof value === 'string') root.setProperty(`--${name}`, value);
        }
    }
    window.applyThemeFromHost = setCss;
    setCss(__COLORS__);

    function markActive() {
        document.querySelectorAll('.theme-button').forEach(button => {
            button.classList.toggle('active', button.dataset.theme === settings.theme);
        });
    }
    function commit() {
        window.__gromSettingsState = JSON.stringify(settings);
        window.__gromSettingsRevision++;
        markActive();
    }
    document.querySelectorAll('.theme-button').forEach(button => {
        button.addEventListener('click', event => {
            if (event.target === customColor) return;
            settings.theme = button.dataset.theme;
            if (settings.theme === 'custom') settings.custom_color = customColor.value;
            commit();
        });
    });
    customColor.addEventListener('input', () => {
        settings.theme = 'custom';
        settings.custom_color = customColor.value;
        commit();
    });
    forwardToggle.addEventListener('change', () => {
        settings.show_forward = forwardToggle.checked;
        commit();
    });
    zoomRange.addEventListener('input', () => {
        settings.default_zoom = Number(zoomRange.value);
        zoomValue.value = `${zoomRange.value}%`;
        commit();
    });
    markActive();
</script>
</body>
</html>"""
        return html.replace("__INITIAL__", initial).replace("__COLORS__", colors)

    def settings_page_html(self):
        settings_state = json.loads(json.dumps(self.app_settings))
        permission_overrides = settings_state.setdefault("site_permission_overrides", {})
        for origin, values in getattr(self, "session_permission_overrides", {}).items():
            current = permission_overrides.setdefault(origin, {})
            for key, value in values.items():
                if value == "allow":
                    current[key] = "allow_once"
        initial = json.dumps(settings_state, ensure_ascii=False)
        colors = json.dumps(self.theme_colors, ensure_ascii=False)
        profiles = json.dumps(self.profile_page_records(), ensure_ascii=False)
        passwords = json.dumps(self.password_page_records(), ensure_ascii=False)
        profile_state = json.dumps({
            "guest": self.guest_mode,
            "name": self.current_profile.get("name", "Профиль"),
        }, ensure_ascii=False)
        html = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Настройки</title>
<style>
    :root { --background:#17181a; --surface:#35363a; --toolbar:#292a2d; --input:#202124; --border:#5f6368; --text:#f1f3f4; --muted:#bdc1c6; --accent:#8ab4f8; --hover:#45474c; }
    * { box-sizing:border-box; }
    html,body { margin:0; min-height:100%; background:var(--background); color:var(--text); font-family:"Segoe UI",Arial,sans-serif; }
    body { display:grid; grid-template-columns:240px minmax(0,1fr); }
    aside { min-height:100vh; padding:28px 18px; background:var(--background); border-right:1px solid var(--border); }
    .brand { padding:0 10px 16px; font-size:17px; font-weight:650; }
    .settings-search { width:100%; height:40px; margin:0 0 22px; padding:0 12px; color:var(--text); background:var(--input); border:1px solid var(--border); border-radius:8px; outline:none; font:inherit; }
    .settings-search:focus { border-color:var(--accent); }
    .nav-label { padding:0 10px 8px; color:var(--muted); font-size:11px; text-transform:uppercase; }
    .nav-item { width:100%; margin:2px 0; padding:11px 12px; color:var(--text); background:transparent; border:0; border-radius:8px; text-align:left; font-size:14px; }
    .nav-item:hover { background:var(--hover); }
    .nav-item.active { background:var(--surface); }
    main { width:min(900px,calc(100% - 48px)); margin:0 auto; padding:32px 0 64px; }
    h1 { margin:0 0 24px; font-size:24px; font-weight:650; }
    h2 { margin:0; font-size:15px; font-weight:650; }
    p { margin:5px 0 0; color:var(--muted); font-size:13px; line-height:1.45; }
    .theme-panel { padding:18px; background:var(--surface); border:1px solid var(--border); border-radius:22px; box-shadow:0 10px 26px rgba(0,0,0,.14); }
    .theme-head { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:20px; }
    .theme-label { color:var(--text); font-size:14px; font-weight:600; }
    button { cursor:pointer; }
    .reset-link { padding:9px 12px; color:var(--text); background:transparent; border:0; border-radius:8px; font:inherit; }
    .reset-link:hover { background:var(--hover); }
    .swatches { display:flex; flex-wrap:wrap; gap:14px; align-items:center; padding:2px 8px 20px; }
    .theme-button { position:relative; width:38px; height:38px; padding:0; border:2px solid transparent; border-radius:50%; background:var(--swatch); box-shadow:inset 0 -5px 0 rgba(0,0,0,.16),0 0 0 1px var(--border); }
    .theme-button:hover { transform:translateY(-1px); filter:brightness(1.12); }
    .theme-button.active { border-color:var(--text); box-shadow:0 0 0 2px var(--accent); }
    .theme-button.custom { display:grid; place-items:center; color:var(--text); background:var(--input); font-size:20px; overflow:hidden; }
    #customColor { position:absolute; inset:-8px; width:54px; height:54px; opacity:0; cursor:pointer; }
    .preview { height:250px; padding:10px; overflow:hidden; background:var(--background); border:8px solid var(--toolbar); border-radius:12px; }
    .preview-tabs { height:36px; display:flex; align-items:end; gap:4px; }
    .preview-tab { width:160px; height:30px; background:var(--active_tab,var(--surface)); border-radius:8px 8px 0 0; }
    .preview-plus { padding:0 8px 6px; color:var(--text); font-size:22px; }
    .preview-bar { height:31px; padding:5px 10px; background:var(--toolbar); }
    .preview-url { height:21px; background:var(--address,var(--input)); border:1px solid var(--border); border-radius:11px; }
    .theme-actions { display:flex; flex-wrap:wrap; gap:9px; margin:0 8px 18px; }
    .theme-image-note { align-self:center; color:var(--muted); font-size:12px; }
    .color-role-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:18px; }
    .color-role { min-width:0; display:flex; align-items:center; justify-content:space-between; gap:14px; padding:12px 13px; background:var(--surface); border:1px solid var(--border); border-radius:8px; }
    .color-role-copy { min-width:0; }
    .color-role strong { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; }
    .color-role small { display:block; margin-top:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--muted); }
    .theme-role { width:42px; height:32px; flex:0 0 auto; padding:2px; background:var(--input); border:1px solid var(--border); border-radius:7px; cursor:pointer; }
    .menu-command-label { min-width:0; display:flex; align-items:center; gap:11px; }
    .menu-command-label img { width:20px; height:20px; object-fit:contain; flex:0 0 auto; }
    .settings-section { padding:24px 4px; border-bottom:1px solid var(--border); }
    .settings-page { display:none; }
    .settings-page.active { display:block; }
    .search-hidden { display:none !important; }
    .no-results { display:none; padding:42px 4px; color:var(--muted); font-size:14px; }
    .setting-row { display:flex; align-items:center; justify-content:space-between; gap:28px; min-height:48px; }
    .switch { position:relative; width:44px; height:25px; flex:0 0 auto; }
    .switch input { opacity:0; width:0; height:0; }
    .slider { position:absolute; inset:0; background:var(--border); border-radius:13px; transition:.16s; }
    .slider:before { content:""; position:absolute; width:19px; height:19px; left:3px; top:3px; background:#fff; border-radius:50%; transition:.16s; }
    .switch input:checked+.slider { background:var(--accent); }
    .switch input:checked+.slider:before { transform:translateX(19px); }
    .zoom-control { display:flex; align-items:center; gap:14px; width:min(430px,100%); margin-top:16px; }
    input[type=range] { flex:1; accent-color:var(--accent); }
    output { width:55px; text-align:right; }
    .control { min-width:210px; height:38px; padding:0 11px; color:var(--text); background:var(--input); border:1px solid var(--border); border-radius:7px; outline:none; }
    .control:focus { border-color:var(--accent); }
    .stack { display:grid; gap:12px; margin-top:16px; }
    .form-row { display:flex; align-items:center; justify-content:space-between; gap:24px; }
    .permission-grid { display:grid; grid-template-columns:1fr 220px; gap:10px 24px; align-items:center; margin-top:16px; }
    .permission-sites { display:grid; gap:8px; margin-top:16px; }
    .permission-site { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px; align-items:center; padding:11px 12px; background:var(--surface); border:1px solid var(--border); border-radius:7px; }
    .permission-site small { display:block; margin-top:4px; color:var(--muted); overflow-wrap:anywhere; }
    .permission-site button { padding:7px 10px; color:var(--text); background:var(--input); border:1px solid var(--border); border-radius:6px; }
    .restart-note { color:var(--accent); font-size:12px; }
    .danger-row { padding-top:26px; }
    .reset-button { padding:10px 16px; color:var(--text); background:var(--surface); border:1px solid var(--border); border-radius:8px; font:inherit; }
    .reset-button:hover { background:var(--hover); }
    .profile-list { display:grid; gap:10px; margin-top:16px; }
    .profile-card { display:grid; grid-template-columns:46px minmax(0,1fr) auto; gap:12px; align-items:center; padding:12px; background:var(--surface); border:1px solid var(--border); border-radius:8px; }
    .profile-avatar { width:46px; height:46px; display:grid; place-items:center; overflow:hidden; border-radius:50%; background:var(--accent); color:#fff; font-size:18px; font-weight:700; }
    .profile-avatar img { width:100%; height:100%; object-fit:cover; }
    .profile-name { font-weight:650; }
    .profile-status { margin-top:3px; color:var(--muted); font-size:12px; }
    .profile-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:5px; }
    .profile-actions button, .profile-create { padding:8px 10px; color:var(--text); background:var(--input); border:1px solid var(--border); border-radius:6px; }
    .profile-actions button:hover, .profile-create:hover { background:var(--hover); }
    .profile-tools { display:flex; gap:8px; margin-top:16px; }
    .password-list { display:grid; gap:8px; margin-top:16px; }
    .password-item { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px; align-items:center; padding:11px 12px; background:var(--surface); border:1px solid var(--border); border-radius:7px; }
    .password-origin { font-weight:600; }
    .password-user { margin-top:3px; color:var(--muted); font-size:12px; }
    .password-actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:5px; }
    .password-item button,.password-form button { padding:7px 10px; color:var(--text); background:var(--input); border:1px solid var(--border); border-radius:6px; }
    .password-form { display:grid; grid-template-columns:1fr 1fr 1fr auto; gap:8px; margin-top:16px; }
    @media(max-width:720px){ body{grid-template-columns:1fr} aside{min-height:auto;border-right:0;border-bottom:1px solid var(--border)} main{width:calc(100% - 28px);padding-top:22px}.theme-head{align-items:flex-start;flex-direction:column}.preview{height:190px}.color-role-grid{grid-template-columns:1fr}.password-form{grid-template-columns:1fr} }
</style>
</head>
<body>
<aside><div class="brand">Настройки Grom</div><input id="settingsSearch" class="settings-search" type="search" autocomplete="off" placeholder="Поиск настроек"><div class="nav-label">Браузер</div><button class="nav-item active" data-page="general">Общие</button><button class="nav-item" data-page="menu">Меню</button><button class="nav-item" data-page="profiles">Профили</button><button class="nav-item" data-page="appearance">Внешний вид</button><button class="nav-item" data-page="performance">Производительность</button><button class="nav-item" data-page="privacy">Приватность</button></aside>
<main>
  <div class="settings-page" data-page-content="appearance"><h1>Внешний вид</h1>
    <section class="settings-section">
        <h2 style="margin-bottom:12px">Тема</h2>
        <div class="theme-panel">
            <div class="theme-head">
                <div class="theme-label">Цветовая тема</div>
                <button id="restoreTheme" class="reset-link">↶&nbsp;&nbsp;Восстановить по умолчанию</button>
            </div>
            <div class="swatches">
                <button class="theme-button" title="Светлая" data-theme="light" style="--swatch:#e8eaed"></button>
                <button class="theme-button" title="Тёмная" data-theme="dark" style="--swatch:#202124"></button>
                <button class="theme-button" title="Тёмно-серая" data-theme="dark_gray" style="--swatch:#3c4043"></button>
                <button class="theme-button" title="Фиолетовая" data-theme="purple" style="--swatch:#493267"></button>
                <button class="theme-button" title="Тёмно-зелёная" data-theme="dark_green" style="--swatch:#1d4037"></button>
                <button class="theme-button" title="Синяя" data-theme="blue" style="--swatch:#1f4f82"></button>
                <button class="theme-button" title="Бирюзовая" data-theme="cyan" style="--swatch:#176b72"></button>
                <button class="theme-button" title="Розовая" data-theme="rose" style="--swatch:#7b3f57"></button>
                <button class="theme-button" title="Красная" data-theme="red" style="--swatch:#7a2830"></button>
                <button class="theme-button" title="Оранжевая" data-theme="orange" style="--swatch:#8a4c20"></button>
                <button class="theme-button" title="Графитовая" data-theme="graphite" style="--swatch:#282d35"></button>
                <button class="theme-button" title="Индиго" data-theme="indigo" style="--swatch:#343b73"></button>
                <button class="theme-button custom" title="Свой цвет" data-theme="custom">⌕<input id="customColor" type="color"></button>
            </div>
            <div class="theme-actions"><button id="themeFromImage" class="reset-button">Создать тему из изображения</button><span class="theme-image-note">Grom выделит основные цвета и соберёт согласованную палитру.</span></div>
            <div class="preview"><div class="preview-tabs"><div class="preview-tab"></div><span class="preview-plus">+</span></div><div class="preview-bar"><div class="preview-url"></div></div></div>
        </div>
    </section>
    <section class="settings-section"><h2>Детальные цвета интерфейса</h2><p>Каждый цвет можно изменить независимо. Пустые настройки автоматически наследуют выбранную тему.</p><div class="color-role-grid">
      <label class="color-role"><span class="color-role-copy"><strong>Фон браузера</strong><small>Область вокруг страниц</small></span><input class="theme-role" data-role="background" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Панель вкладок</strong><small>Фон верхней полосы</small></span><input class="theme-role" data-role="tabs" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Активная вкладка</strong><small>Выбранная вкладка</small></span><input class="theme-role" data-role="active_tab" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Панель навигации</strong><small>Кнопки и адресная строка</small></span><input class="theme-role" data-role="toolbar" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Панель закладок</strong><small>Закреплённые сайты</small></span><input class="theme-role" data-role="bookmarks" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Адресная строка</strong><small>Поле URL и поиска</small></span><input class="theme-role" data-role="address" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Всплывающие меню</strong><small>Меню, история и профили</small></span><input class="theme-role" data-role="popup" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Панели и карточки</strong><small>Вторичные поверхности</small></span><input class="theme-role" data-role="surface" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Наведение на кнопки</strong><small>Подсветка действий</small></span><input class="theme-role" data-role="button_hover" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Границы</strong><small>Разделители и обводки</small></span><input class="theme-role" data-role="border" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Основной текст</strong><small>Названия и подписи</small></span><input class="theme-role" data-role="text" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Вторичный текст</strong><small>Подсказки и неактивные подписи</small></span><input class="theme-role" data-role="muted" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Иконки</strong><small>Активные кнопки панели</small></span><input class="theme-role" data-role="icon" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Неактивные иконки</strong><small>Недоступные действия</small></span><input class="theme-role" data-role="disabled_icon" type="color"></label>
      <label class="color-role"><span class="color-role-copy"><strong>Акцент</strong><small>Переключатели и фокус</small></span><input class="theme-role" data-role="accent" type="color"></label>
    </div><div class="theme-actions" style="margin:16px 0 0"><button id="clearThemeOverrides" class="reset-button">Сбросить детальные цвета</button></div></section>
    <section class="settings-section"><h2>Масштаб страниц</h2><p>Ползунок фиксируется на стандартных значениях масштаба.</p><div class="zoom-control"><input id="zoomRange" type="range" min="25" max="300" step="1" list="zoomStops"><datalist id="zoomStops"><option value="50"><option value="75"><option value="100"><option value="120"><option value="150"><option value="200"><option value="250"><option value="300"></datalist><output id="zoomValue"></output></div></section>
    <section class="settings-section"><h2>Размер шрифта</h2><p>Изменяет размер текста на веб-страницах независимо от масштаба.</p><div class="zoom-control"><input id="fontScale" type="range" min="50" max="200" step="5"><output id="fontScaleValue"></output></div><div class="setting-row" style="margin-top:16px"><span>Применять также к странице настроек</span><label class="switch"><input id="fontScaleSettings" type="checkbox"><span class="slider"></span></label></div></section>
    <section class="settings-section"><h2>Размер текста в режиме чтения</h2><p>Размер основного текста очищенной статьи.</p><div class="zoom-control"><input id="readerFontSize" type="range" min="14" max="28" step="1"><output id="readerFontValue"></output></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Панель закладок</h2><p>Показывать сохранённые сайты под адресной строкой.</p></div><label class="switch"><input id="bookmarksBar" type="checkbox"><span class="slider"></span></label></div></section>
  </div>
  <div class="settings-page active" data-page-content="general"><h1>Общие настройки</h1>
    <section class="settings-section"><div class="setting-row"><div><h2>Кнопка «Вперёд»</h2><p>Показывать переход к следующей странице рядом с кнопкой «Назад».</p></div><label class="switch"><input id="forwardToggle" type="checkbox"><span class="slider"></span></label></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Кнопка «Главная»</h2><p>Открывать домашнюю страницу Grom из панели навигации.</p></div><label class="switch"><input id="homeButtonToggle" type="checkbox"><span class="slider"></span></label></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Кнопка расширений</h2><p>Показывать значок встроенных расширений справа от меню браузера.</p></div><label class="switch"><input id="extensionsButtonToggle" type="checkbox"><span class="slider"></span></label></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Поисковая система</h2><p>Используется для запросов из адресной строки и главной страницы.</p></div><select id="searchEngine" class="control"><option value="google">Google</option><option value="bing">Bing</option><option value="duckduckgo">DuckDuckGo</option><option value="yandex">Яндекс</option><option value="brave">Brave Search</option><option value="startpage">Startpage</option><option value="ecosia">Ecosia</option><option value="qwant">Qwant</option><option value="yahoo">Yahoo</option><option value="mojeek">Mojeek</option></select></div></section>
    <section class="settings-section"><h2>Новая вкладка</h2><p>Страница, которая открывается в новых вкладках.</p><div class="stack"><div class="form-row"><span>Стартовая страница</span><select id="startPage" class="control"><option value="grom">Главная Grom</option><option value="google">Google</option><option value="blank">Пустая страница</option><option value="custom">Свой адрес</option></select></div><div class="form-row"><span>Адрес</span><input id="startPageUrl" class="control" type="url" placeholder="https://example.com"></div></div></section>
    <section class="settings-section"><h2>Перевод страниц</h2><p>Язык страницы определяется автоматически после загрузки.</p><div class="stack"><div class="form-row"><span>Переводить на</span><select id="translationLanguage" class="control"><option value="ru">Русский</option><option value="en">English</option><option value="de">Deutsch</option><option value="fr">Français</option><option value="es">Español</option><option value="it">Italiano</option><option value="zh-CN">中文</option><option value="ja">日本語</option><option value="ko">한국어</option></select></div><div class="setting-row"><div><h2>Предлагать перевод</h2><p>Показывать предложение, если язык страницы отличается от выбранного.</p></div><label class="switch"><input id="offerTranslation" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><div><h2>Автоматический перевод</h2><p>Переводить страницу сразу, не показывая предложение.</p></div><label class="switch"><input id="autoTranslate" type="checkbox"><span class="slider"></span></label></div></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Вертикальные вкладки</h2><p>Показывать список вкладок слева. Автоматически этот режим больше не включается.</p></div><label class="switch"><input id="verticalTabs" type="checkbox"><span class="slider"></span></label></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Восстановление сессии</h2><p>Предлагать вернуть вкладки после неожиданного завершения.</p></div><label class="switch"><input id="restoreSessionPrompt" type="checkbox"><span class="slider"></span></label></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Браузер Windows по умолчанию</h2><p>Добавить Grom в список браузеров и приложений для HTML, PDF и изображений.</p></div><button id="registerDefaultBrowser" class="reset-button">Открыть настройки Windows</button></div></section>
    <div class="danger-row"><button id="resetAll" class="reset-button">Сбросить все настройки</button></div>
  </div>
  <div class="settings-page" data-page-content="profiles"><h1>Профили</h1>
    <section class="settings-section"><h2>Профили Grom</h2><p>У каждого профиля свои настройки, история, закладки, загрузки и восстановление вкладок.</p><div id="profilesList" class="profile-list"></div><div class="profile-tools"><button id="createProfile" class="profile-create">Создать профиль</button><button id="guestProfile" class="profile-create">Открыть гостевой режим</button></div></section>
  </div>
  <div class="settings-page" data-page-content="menu"><h1>Меню управления</h1>
    <section class="settings-section"><h2>Команды меню</h2><p>Редкие функции остаются в разделе «Дополнительные инструменты». Здесь можно вынести их в основное меню.</p><div class="stack"><div class="setting-row"><span class="menu-command-label"><img src="__ICON_TAB_SEARCH__" alt="">Поиск по вкладкам</span><label class="switch"><input class="menu-command" data-command="tab_search" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><span class="menu-command-label"><img src="__ICON_FIND__" alt="">Найти на странице</span><label class="switch"><input class="menu-command" data-command="find_page" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><span class="menu-command-label"><img src="__ICON_SCREENSHOT__" alt="">Сделать скриншот</span><label class="switch"><input class="menu-command" data-command="screenshot" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><span class="menu-command-label"><img src="__ICON_SPLIT__" alt="">Разделить экран</span><label class="switch"><input class="menu-command" data-command="split_screen" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><span class="menu-command-label"><img src="__ICON_DEVTOOLS__" alt="">Инструменты разработчика</span><label class="switch"><input class="menu-command" data-command="developer_tools" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><span class="menu-command-label"><img src="__ICON_INSTALL__" alt="">Установить текущий сайт как приложение</span><label class="switch"><input class="menu-command" data-command="install_site" type="checkbox"><span class="slider"></span></label></div></div></section>
    <section class="settings-section"><h2>Установить сайт</h2><p>Откройте нужный сайт и нажмите кнопку ниже. Grom создаст отдельный ярлык приложения без вкладок и панели навигации.</p><button id="installCurrentSite" class="reset-button">Установить текущий сайт</button></section>
  </div>
  <div class="settings-page" data-page-content="performance"><h1>Производительность</h1>
    <section class="settings-section"><div class="stack"><div class="setting-row"><div><h2>Экономия памяти</h2><p>Неактивные вкладки освобождают страницу и восстанавливаются при открытии.</p></div><label class="switch"><input id="memorySaver" type="checkbox"><span class="slider"></span></label></div><div class="form-row"><span>Переводить в сон через</span><select id="sleepMinutes" class="control"><option value="1">1 минуту</option><option value="5">5 минут</option><option value="15">15 минут</option><option value="30">30 минут</option><option value="60">1 час</option></select></div><div class="setting-row"><div><h2>Аппаратное ускорение</h2><p>Использовать видеокарту для отображения страниц.</p><span class="restart-note">Изменение применяется после перезапуска браузера.</span></div><label class="switch"><input id="hardwareAcceleration" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><div><h2>Плавные анимации вкладок</h2><p>Анимировать появление и закрытие вкладок.</p></div><label class="switch"><input id="smoothAnimations" type="checkbox"><span class="slider"></span></label></div></div></section>
    <section class="settings-section"><h2>Менеджер загрузок</h2><p>Ограничение скорости применяется к каждой активной загрузке. Ноль означает без ограничения.</p><div class="stack"><div class="form-row"><span>Одновременных загрузок</span><select id="maxConcurrentDownloads" class="control"><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="6">6</option><option value="8">8</option></select></div><div class="form-row"><span>Скорость, КБ/с</span><input id="downloadSpeedLimit" class="control" type="number" min="0" max="1048576" step="64" placeholder="0"></div></div></section>
  </div>
  <div class="settings-page" data-page-content="privacy"><h1>Приватность</h1>
    <section class="settings-section"><h2>Защита от опасных сайтов</h2><p>Grom проверяет подозрительные признаки локально. Для проверки по базе Google Safe Browsing можно указать собственный API-ключ.</p><div class="stack"><div class="setting-row"><span>Предупреждать об опасных адресах</span><label class="switch"><input id="safeBrowsingEnabled" type="checkbox"><span class="slider"></span></label></div><div class="form-row"><span>Safe Browsing API key</span><input id="safeBrowsingApiKey" class="control" type="password" autocomplete="off" placeholder="Необязательно"></div></div></section>
    <section class="settings-section"><div class="setting-row"><div><h2>Блокировщик рекламы</h2><p>Скрывает рекламные блоки и останавливает известные рекламные запросы внутри страниц.</p></div><label class="switch"><input id="adBlocker" type="checkbox"><span class="slider"></span></label></div></section>
    <section class="settings-section"><h2>Менеджер паролей Windows</h2><p>Пароли хранятся в Windows Credential Manager и не записываются в файлы Grom.</p><div class="stack"><div class="setting-row"><span>Использовать менеджер паролей</span><label class="switch"><input id="passwordManager" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><span>Предлагать сохранение</span><label class="switch"><input id="offerPasswords" type="checkbox"><span class="slider"></span></label></div><div class="setting-row"><span>Автоматически заполнять формы</span><label class="switch"><input id="autofillPasswords" type="checkbox"><span class="slider"></span></label></div></div><div class="password-form"><input id="passwordOrigin" class="control" placeholder="https://example.com"><input id="passwordUsername" class="control" autocomplete="off" placeholder="Логин"><input id="passwordValue" class="control" type="password" autocomplete="new-password" placeholder="Пароль"><button id="addPassword">Добавить</button></div><div id="passwordList" class="password-list"></div><div class="setting-row" style="margin-top:18px"><div><h2>Сайты без предложений</h2><p id="neverSaveSummary"></p></div><button id="clearNeverSave" class="reset-button">Очистить список</button></div><div id="neverSaveList" class="password-list"></div></section>
    <section class="settings-section"><h2>Разрешения сайтов</h2><p>Задайте поведение по умолчанию. Индивидуальные и временные решения доступны в паспорте сайта.</p><div class="permission-grid"><span>Камера</span><select class="control permission" data-permission="camera"><option value="ask">Спрашивать</option><option value="block">Блокировать</option></select><span>Микрофон</span><select class="control permission" data-permission="microphone"><option value="ask">Спрашивать</option><option value="block">Блокировать</option></select><span>Уведомления</span><select class="control permission" data-permission="notifications"><option value="ask">Спрашивать</option><option value="block">Блокировать</option></select><span>Геолокация</span><select class="control permission" data-permission="geolocation"><option value="ask">Спрашивать</option><option value="block">Блокировать</option></select><span>Автозапуск видео</span><select class="control permission" data-permission="autoplay"><option value="ask">Разрешать</option><option value="block">Блокировать</option></select><span>Буфер обмена</span><select class="control permission" data-permission="clipboard"><option value="ask">Спрашивать</option><option value="block">Блокировать</option></select><span>Всплывающие окна</span><select class="control permission" data-permission="popups"><option value="ask">Разрешать</option><option value="block">Блокировать</option></select></div></section>
    <section class="settings-section"><h2>Сайты с индивидуальными разрешениями</h2><p>Здесь собраны все постоянные исключения.</p><div id="permissionSitesList" class="permission-sites"></div></section>
    <section class="settings-section"><h2>Приватные вкладки</h2><p>Страницы, открытые через Ctrl+Shift+N, не добавляются в историю и не сохраняются в сессии браузера.</p></section>
  </div>
  <div id="settingsNoResults" class="no-results">Ничего не найдено. Попробуйте другое слово.</div>
</main>
<script>
    const profiles=__PROFILES__,profileState=__PROFILE_STATE__,savedPasswords=__PASSWORDS__;window.__gromCommandQueue=[];
    function browserCommand(action,data={}){window.__gromCommandQueue.push(Object.assign({action},data))}
    const defaults={theme:'light',custom_color:'#3f4652',theme_overrides:{},show_forward:true,show_home_button:false,show_extensions_button:true,default_zoom:100,font_scale:100,font_scale_settings:false,search_engine:'google',start_page:'grom',start_page_url:'',home_shortcuts_limit:16,hardware_acceleration:true,memory_saver:true,sleep_minutes:15,max_concurrent_downloads:3,download_speed_limit_kbps:0,vertical_tabs:false,reader_font_size:18,restore_session_prompt:true,smooth_tab_animations:true,show_bookmarks_bar:true,ad_blocker:true,password_manager:false,offer_save_passwords:true,autofill_passwords:true,translation_language:'ru',offer_translation:true,auto_translate:false,safe_browsing_enabled:true,safe_browsing_api_key:'',password_never_save:[],menu_commands:{tab_search:true,find_page:true,screenshot:false,split_screen:false,developer_tools:false,install_site:false},site_permissions:{camera:'ask',microphone:'ask',notifications:'ask',geolocation:'ask',autoplay:'ask',clipboard:'ask',popups:'ask'},site_permission_overrides:{}};
    const settings=Object.assign({},defaults,__INITIAL__);
    settings.site_permissions=Object.assign({},defaults.site_permissions,settings.site_permissions||{});
    settings.menu_commands=Object.assign({},defaults.menu_commands,settings.menu_commands||{});
    settings.theme_overrides=Object.assign({},settings.theme_overrides||{});
    window.__gromSettingsRevision=0;
    window.__gromSettingsState=JSON.stringify(settings);
    const customColor=document.getElementById('customColor');
    const forwardToggle=document.getElementById('forwardToggle');
    const homeButtonToggle=document.getElementById('homeButtonToggle');
    const extensionsButtonToggle=document.getElementById('extensionsButtonToggle');
    const zoomRange=document.getElementById('zoomRange');
    const zoomValue=document.getElementById('zoomValue');
    const fontScale=document.getElementById('fontScale');
    const fontScaleValue=document.getElementById('fontScaleValue');
    const fontScaleSettings=document.getElementById('fontScaleSettings');
    const searchEngine=document.getElementById('searchEngine');
    const startPage=document.getElementById('startPage');
    const startPageUrl=document.getElementById('startPageUrl');
    const hardwareAcceleration=document.getElementById('hardwareAcceleration');
    const memorySaver=document.getElementById('memorySaver');
    const sleepMinutes=document.getElementById('sleepMinutes');
    const maxConcurrentDownloads=document.getElementById('maxConcurrentDownloads');
    const downloadSpeedLimit=document.getElementById('downloadSpeedLimit');
    const verticalTabs=document.getElementById('verticalTabs');
    const readerFontSize=document.getElementById('readerFontSize');
    const readerFontValue=document.getElementById('readerFontValue');
    const restoreSessionPrompt=document.getElementById('restoreSessionPrompt');
    const smoothAnimations=document.getElementById('smoothAnimations');
    const bookmarksBar=document.getElementById('bookmarksBar');
    const adBlocker=document.getElementById('adBlocker');
    const passwordManager=document.getElementById('passwordManager');
    const offerPasswords=document.getElementById('offerPasswords');
    const autofillPasswords=document.getElementById('autofillPasswords');
    const translationLanguage=document.getElementById('translationLanguage');
    const offerTranslation=document.getElementById('offerTranslation');
    const autoTranslate=document.getElementById('autoTranslate');
    const safeBrowsingEnabled=document.getElementById('safeBrowsingEnabled');
    const safeBrowsingApiKey=document.getElementById('safeBrowsingApiKey');
    function setCss(colors){const root=document.documentElement.style;Object.entries(colors).forEach(([name,value])=>{if(typeof value==='string')root.setProperty(`--${name}`,value)})}
    window.applyThemeFromHost=setCss;setCss(__COLORS__);
    const zoomStops=[25,50,67,75,80,90,100,110,120,125,150,175,200,250,300];
    function sync(){customColor.value=settings.custom_color;forwardToggle.checked=Boolean(settings.show_forward);homeButtonToggle.checked=Boolean(settings.show_home_button);extensionsButtonToggle.checked=Boolean(settings.show_extensions_button);zoomRange.value=settings.default_zoom;zoomValue.value=`${settings.default_zoom}%`;fontScale.value=settings.font_scale;fontScaleValue.value=`${settings.font_scale}%`;fontScaleSettings.checked=Boolean(settings.font_scale_settings);searchEngine.value=settings.search_engine;startPage.value=settings.start_page;startPageUrl.value=settings.start_page_url||'';startPageUrl.disabled=settings.start_page!=='custom';hardwareAcceleration.checked=Boolean(settings.hardware_acceleration);memorySaver.checked=Boolean(settings.memory_saver);sleepMinutes.value=String(settings.sleep_minutes);maxConcurrentDownloads.value=String(settings.max_concurrent_downloads);downloadSpeedLimit.value=String(settings.download_speed_limit_kbps||0);verticalTabs.checked=Boolean(settings.vertical_tabs);readerFontSize.value=settings.reader_font_size;readerFontValue.value=`${settings.reader_font_size}px`;restoreSessionPrompt.checked=Boolean(settings.restore_session_prompt);smoothAnimations.checked=Boolean(settings.smooth_tab_animations);bookmarksBar.checked=Boolean(settings.show_bookmarks_bar);adBlocker.checked=Boolean(settings.ad_blocker);passwordManager.checked=Boolean(settings.password_manager);offerPasswords.checked=Boolean(settings.offer_save_passwords);autofillPasswords.checked=Boolean(settings.autofill_passwords);translationLanguage.value=settings.translation_language;offerTranslation.checked=Boolean(settings.offer_translation);autoTranslate.checked=Boolean(settings.auto_translate);safeBrowsingEnabled.checked=Boolean(settings.safe_browsing_enabled);safeBrowsingApiKey.value=settings.safe_browsing_api_key||'';document.querySelectorAll('.permission').forEach(select=>select.value=settings.site_permissions[select.dataset.permission]||'ask');document.querySelectorAll('.menu-command').forEach(input=>input.checked=Boolean(settings.menu_commands[input.dataset.command]));document.querySelectorAll('.theme-role').forEach(input=>input.value=settings.theme_overrides[input.dataset.role]||getComputedStyle(document.documentElement).getPropertyValue(`--${input.dataset.role}`).trim()||'#808080');document.querySelectorAll('.theme-button').forEach(b=>b.classList.toggle('active',b.dataset.theme===settings.theme));document.getElementById('neverSaveSummary').textContent=(settings.password_never_save||[]).length?`${settings.password_never_save.length} сайт(ов) не показывают предложение`:'Список пуст';renderNeverSave()}
    function commit(){window.__gromSettingsState=JSON.stringify(settings);window.__gromSettingsRevision++;sync()}
    document.querySelectorAll('.theme-button').forEach(button=>button.addEventListener('click',event=>{if(event.target===customColor)return;settings.theme=button.dataset.theme;settings.theme_overrides={};if(settings.theme==='custom')settings.custom_color=customColor.value;commit()}));
    customColor.addEventListener('input',()=>{settings.theme='custom';settings.custom_color=customColor.value;settings.theme_overrides={};commit()});
    document.querySelectorAll('.theme-role').forEach(input=>input.addEventListener('input',()=>{settings.theme_overrides[input.dataset.role]=input.value;commit()}));
    document.getElementById('themeFromImage').addEventListener('click',()=>browserCommand('choose_theme_image'));
    document.getElementById('clearThemeOverrides').addEventListener('click',()=>{settings.theme_overrides={};commit()});
    forwardToggle.addEventListener('change',()=>{settings.show_forward=forwardToggle.checked;commit()});
    homeButtonToggle.addEventListener('change',()=>{settings.show_home_button=homeButtonToggle.checked;commit()});
    extensionsButtonToggle.addEventListener('change',()=>{settings.show_extensions_button=extensionsButtonToggle.checked;commit()});
    zoomRange.addEventListener('input',()=>{zoomValue.value=`${zoomRange.value}%`});
    zoomRange.addEventListener('change',()=>{const raw=Number(zoomRange.value);settings.default_zoom=zoomStops.reduce((best,value)=>Math.abs(value-raw)<Math.abs(best-raw)?value:best,zoomStops[0]);commit()});
    fontScale.addEventListener('input',()=>{settings.font_scale=Number(fontScale.value);commit()});
    fontScaleSettings.addEventListener('change',()=>{settings.font_scale_settings=fontScaleSettings.checked;commit()});
    searchEngine.addEventListener('change',()=>{settings.search_engine=searchEngine.value;commit()});
    startPage.addEventListener('change',()=>{settings.start_page=startPage.value;commit()});
    startPageUrl.addEventListener('change',()=>{settings.start_page_url=startPageUrl.value.trim();commit()});
    hardwareAcceleration.addEventListener('change',()=>{settings.hardware_acceleration=hardwareAcceleration.checked;commit()});
    memorySaver.addEventListener('change',()=>{settings.memory_saver=memorySaver.checked;commit()});
    sleepMinutes.addEventListener('change',()=>{settings.sleep_minutes=Number(sleepMinutes.value);commit()});
    maxConcurrentDownloads.addEventListener('change',()=>{settings.max_concurrent_downloads=Number(maxConcurrentDownloads.value);commit()});
    downloadSpeedLimit.addEventListener('change',()=>{settings.download_speed_limit_kbps=Math.max(0,Number(downloadSpeedLimit.value)||0);commit()});
    verticalTabs.addEventListener('change',()=>{settings.vertical_tabs=verticalTabs.checked;commit()});
    readerFontSize.addEventListener('input',()=>{settings.reader_font_size=Number(readerFontSize.value);commit()});
    restoreSessionPrompt.addEventListener('change',()=>{settings.restore_session_prompt=restoreSessionPrompt.checked;commit()});
    smoothAnimations.addEventListener('change',()=>{settings.smooth_tab_animations=smoothAnimations.checked;commit()});
    bookmarksBar.addEventListener('change',()=>{settings.show_bookmarks_bar=bookmarksBar.checked;commit()});
    adBlocker.addEventListener('change',()=>{settings.ad_blocker=adBlocker.checked;commit()});
    passwordManager.addEventListener('change',()=>{settings.password_manager=passwordManager.checked;commit()});
    offerPasswords.addEventListener('change',()=>{settings.offer_save_passwords=offerPasswords.checked;commit()});
    autofillPasswords.addEventListener('change',()=>{settings.autofill_passwords=autofillPasswords.checked;commit()});
    translationLanguage.addEventListener('change',()=>{settings.translation_language=translationLanguage.value;commit()});
    offerTranslation.addEventListener('change',()=>{settings.offer_translation=offerTranslation.checked;commit()});
    autoTranslate.addEventListener('change',()=>{settings.auto_translate=autoTranslate.checked;commit()});
    safeBrowsingEnabled.addEventListener('change',()=>{settings.safe_browsing_enabled=safeBrowsingEnabled.checked;commit()});
    safeBrowsingApiKey.addEventListener('change',()=>{settings.safe_browsing_api_key=safeBrowsingApiKey.value.trim();commit()});
    document.querySelectorAll('.permission').forEach(select=>select.addEventListener('change',()=>{settings.site_permissions[select.dataset.permission]=select.value;commit()}));
    document.querySelectorAll('.menu-command').forEach(input=>input.addEventListener('change',()=>{settings.menu_commands[input.dataset.command]=input.checked;commit()}));
    document.getElementById('restoreTheme').addEventListener('click',()=>{settings.theme=defaults.theme;settings.custom_color=defaults.custom_color;settings.theme_overrides={};commit()});
    document.getElementById('resetAll').addEventListener('click',()=>{Object.assign(settings,defaults);settings.theme_overrides={};settings.site_permissions=Object.assign({},defaults.site_permissions);commit()});
    document.getElementById('registerDefaultBrowser').addEventListener('click',()=>browserCommand('register_default_browser'));
    document.getElementById('installCurrentSite').addEventListener('click',()=>browserCommand('install_current_site'));
    function renderProfiles(){const list=document.getElementById('profilesList');list.textContent='';profiles.forEach(profile=>{const card=document.createElement('div');card.className='profile-card';const avatar=document.createElement('div');avatar.className='profile-avatar';if(profile.avatar){const image=document.createElement('img');image.src=profile.avatar;image.alt='';avatar.append(image)}else avatar.textContent=(profile.name||'П').trim().slice(0,1).toUpperCase();const copy=document.createElement('div');const name=document.createElement('div');name.className='profile-name';name.textContent=profile.name;const status=document.createElement('div');status.className='profile-status';status.textContent=profile.active?'Текущий профиль':'Отдельные локальные данные';copy.append(name,status);const actions=document.createElement('div');actions.className='profile-actions';if(!profile.active){const open=document.createElement('button');open.textContent='Открыть';open.onclick=()=>browserCommand('switch_profile',{profile_id:profile.id});actions.append(open)}const avatarButton=document.createElement('button');avatarButton.textContent='Аватар';avatarButton.onclick=()=>browserCommand('profile_avatar',{profile_id:profile.id});const rename=document.createElement('button');rename.textContent='Переименовать';rename.onclick=()=>{const value=prompt('Название профиля',profile.name);if(value?.trim())browserCommand('rename_profile',{profile_id:profile.id,name:value.trim()})};actions.append(avatarButton,rename);if(profile.deletable){const remove=document.createElement('button');remove.textContent='Удалить';remove.onclick=()=>browserCommand('delete_profile',{profile_id:profile.id});actions.append(remove)}card.append(avatar,copy,actions);list.append(card)});if(profileState.guest){const note=document.createElement('p');note.textContent='Сейчас открыт гостевой режим. Его локальные данные будут удалены после закрытия браузера.';list.prepend(note)}}
    function renderPasswords(){const list=document.getElementById('passwordList');list.textContent='';if(!savedPasswords.length){const empty=document.createElement('p');empty.textContent=profileState.guest?'В гостевом режиме пароли не сохраняются.':'Сохранённых паролей пока нет.';list.append(empty);return}savedPasswords.forEach(record=>{const row=document.createElement('div');row.className='password-item';const copy=document.createElement('div');const origin=document.createElement('div');origin.className='password-origin';origin.textContent=record.origin;const user=document.createElement('div');user.className='password-user';user.textContent=record.username;copy.append(origin,user);const actions=document.createElement('div');actions.className='password-actions';const copyUser=document.createElement('button');copyUser.textContent='Копировать логин';copyUser.onclick=()=>navigator.clipboard?.writeText(record.username);const copyPassword=document.createElement('button');copyPassword.textContent='Копировать пароль';copyPassword.onclick=()=>browserCommand('copy_password',{target:record.target});const remove=document.createElement('button');remove.textContent='Удалить';remove.onclick=()=>browserCommand('delete_password',{target:record.target});actions.append(copyUser,copyPassword,remove);row.append(copy,actions);list.append(row)})}
    function renderNeverSave(){const list=document.getElementById('neverSaveList');list.textContent='';(settings.password_never_save||[]).forEach(origin=>{const row=document.createElement('div');row.className='password-item';const name=document.createElement('div');name.className='password-origin';name.textContent=origin;const allow=document.createElement('button');allow.textContent='Снова спрашивать';allow.onclick=()=>browserCommand('allow_password_origin',{origin});row.append(name,allow);list.append(row)})}
    function renderPermissionSites(){const list=document.getElementById('permissionSitesList');list.textContent='';const entries=Object.entries(settings.site_permission_overrides||{});if(!entries.length){const empty=document.createElement('p');empty.textContent='Индивидуальных разрешений пока нет';list.append(empty);return}const names={camera:'камера',microphone:'микрофон',notifications:'уведомления',geolocation:'геолокация',autoplay:'автозапуск',clipboard:'буфер обмена',popups:'всплывающие окна'};entries.forEach(([origin,values])=>{const row=document.createElement('div');row.className='permission-site';const copy=document.createElement('div');const title=document.createElement('strong');title.textContent=origin;const details=document.createElement('small');details.textContent=Object.entries(values).map(([key,value])=>`${names[key]||key}: ${value==='allow_once'?'только сейчас':value==='allow'?'разрешено':'заблокировано'}`).join(' · ');copy.append(title,details);const remove=document.createElement('button');remove.textContent='Сбросить';remove.onclick=()=>browserCommand('clear_site_permissions',{origin});row.append(copy,remove);list.append(row)})}
    document.getElementById('addPassword').addEventListener('click',()=>{const origin=document.getElementById('passwordOrigin').value.trim(),username=document.getElementById('passwordUsername').value.trim(),password=document.getElementById('passwordValue').value;if(origin&&username&&password)browserCommand('add_password',{origin,username,password})});
    document.getElementById('clearNeverSave').addEventListener('click',()=>browserCommand('clear_password_never'));
    document.getElementById('createProfile').addEventListener('click',()=>{const name=prompt('Название нового профиля',`Профиль ${profiles.length+1}`);if(name?.trim())browserCommand('create_profile',{name:name.trim()})});
    document.getElementById('guestProfile').addEventListener('click',()=>browserCommand('guest_profile'));
    const settingsSearch=document.getElementById('settingsSearch'),settingsPages=[...document.querySelectorAll('.settings-page')],settingsNav=[...document.querySelectorAll('.nav-item')],noSettingsResults=document.getElementById('settingsNoResults');let activeSettingsPage='general';
    const synonymGroups=[['тема','цвет','палитра','оформление','дизайн','внешний вид'],['масштаб','зум','увеличение','уменьшение','размер страницы'],['шрифт','текст','буквы','размер текста'],['пароль','логин','автозаполнение','учетные данные','учётные данные'],['камера','вебкамера','микрофон','геолокация','местоположение','уведомления','разрешения'],['память','сон','спящие','производительность','скорость','экономия'],['главная','домашняя','стартовая','новая вкладка'],['профиль','аккаунт','пользователь','гость','аватар'],['реклама','блокировщик','баннер','adblock'],['перевод','язык','translate'],['вкладки','вертикальные','панель вкладок'],['закладки','избранное','favorites'],['сброс','по умолчанию','восстановить настройки'],['ускорение','видеокарта','gpu','аппаратное']];
    const normalize=value=>String(value||'').toLowerCase().replaceAll('ё','е').trim();
    function showSettingsPage(name){activeSettingsPage=name;settingsPages.forEach(page=>{page.style.display='';page.classList.toggle('active',page.dataset.pageContent===name);page.querySelectorAll('.search-hidden').forEach(item=>item.classList.remove('search-hidden'))});settingsNav.forEach(item=>item.classList.toggle('active',item.dataset.page===name));noSettingsResults.style.display='none';window.scrollTo(0,0)}
    function alternatives(word){const values=new Set([word]);synonymGroups.forEach(group=>{const normalized=group.map(normalize);if(normalized.some(term=>term.includes(word)||word.includes(term)))normalized.forEach(term=>values.add(term))});return [...values]}
    function searchSettings(){const query=normalize(settingsSearch.value);if(!query){showSettingsPage(activeSettingsPage);return}const wordGroups=query.split(/\s+/).map(alternatives);let total=0;settingsNav.forEach(item=>item.classList.remove('active'));settingsPages.forEach(page=>{let pageMatches=0;const pageAliases=normalize(page.dataset.pageContent+' '+page.querySelector('h1')?.textContent);[...page.querySelectorAll(':scope > .settings-section,:scope > section,:scope > .danger-row')].forEach(section=>{const haystack=normalize(section.textContent+' '+pageAliases);const match=wordGroups.every(words=>words.some(word=>haystack.includes(word)));section.classList.toggle('search-hidden',!match);if(match)pageMatches++});page.classList.add('active');page.style.display=pageMatches?'block':'none';total+=pageMatches});noSettingsResults.style.display=total?'none':'block';window.scrollTo(0,0)}
    settingsSearch.addEventListener('input',searchSettings);settingsSearch.addEventListener('keydown',event=>{if(event.key==='Escape'){settingsSearch.value='';showSettingsPage(activeSettingsPage)}});settingsNav.forEach(button=>button.addEventListener('click',()=>{settingsSearch.value='';showSettingsPage(button.dataset.page)}));
    renderProfiles();renderPasswords();renderNeverSave();renderPermissionSites();sync();
</script>
</body></html>"""
        icon_tokens = {
            "__ICON_TAB_SEARCH__": "Поиск по вкладкам",
            "__ICON_FIND__": "Найти на странице",
            "__ICON_SCREENSHOT__": "Сделать скриншот",
            "__ICON_SPLIT__": "Разделить экран",
            "__ICON_DEVTOOLS__": "Инструменты разработчика",
            "__ICON_INSTALL__": "Установить сайт",
        }
        result = html.replace("__INITIAL__", initial).replace("__COLORS__", colors).replace("__PROFILES__", profiles).replace("__PROFILE_STATE__", profile_state).replace("__PASSWORDS__", passwords)
        for token, label in icon_tokens.items():
            result = result.replace(token, self.icon_data_uri(self.popup_action_icon(label), 20))
        return result
