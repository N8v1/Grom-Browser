# Grom Browser

A Windows desktop browser built with Python, PySide6, Qt WebView, and Microsoft Edge WebView2. The interface is available in English and Russian. The first-run setup opens in English; choose the interface language on the welcome screen.

**Current release:** 1.1.1  
**Developer:** Ilyin Nikita Nikolaevich N8

## Features

- English and Russian interface, including the first-run welcome screen
- Tabs, bookmarks, browsing history, downloads, and browser profiles
- Customizable start page and browser appearance
- Built-in privacy and content controls
- Windows application icon and version information

## Download and install

Open the [Releases](https://github.com/N8v1/Grom-Browser/releases) page and download the latest `Grom-Setup-*.exe` installer. Run it and follow the setup steps.

Grom Browser requires Windows 10/11 (64-bit) and the Microsoft Edge WebView2 Runtime. If WebView2 is missing, install the [Evergreen WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).

## Build from source

The source build is intended for Windows. Install Python 3.10 or newer and open PowerShell in this repository directory (the directory containing `build_gui.py`).

Install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the graphical builder:

```powershell
pythonw build_gui.py
```

Click **Build application**. The portable application folder is created at `dist/Grom/`; run `dist/Grom/Grom.exe`. Copy the whole `dist/Grom` folder when moving the app to another computer.

### Create the Setup installer

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then open `GromInstaller.iss` in Inno Setup Compiler and choose **Compile**. The installer is written to `installer_output/Grom-Setup-1.1.1.exe`.

Alternatively, compile it from PowerShell:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\GromInstaller.iss
```

The builder includes the browser's image assets, translation data, Qt WebView plug-ins, application icon, and Windows version metadata.

## Project layout

- `grom_browser.py` - application entry point and main browser window
- `webview.py`, `tabs.py`, `downloads.py` - browser components
- `internal_pages.py` - welcome, start, settings, and other internal pages
- `i18n.py`, `ui_translations_en.json` - interface localization
- `build_gui.py` - graphical PyInstaller builder
- `GromInstaller.iss` - Inno Setup installer definition

## License

No license has been selected for this repository yet. Until a license is added, the source remains under the default copyright rules; public visibility alone does not grant permission to reuse or redistribute it. Check the licenses of included dependencies and image assets before choosing a license for the whole project.
