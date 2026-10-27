from __future__ import annotations

import base64
import ctypes
import json
import os
import re
import subprocess
import sys
import uuid
from ctypes import wintypes

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class WindowsCredentialStore:
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    def __init__(self, profile_id):
        self.profile_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(profile_id)) or "default"
        self.available = sys.platform == "win32"
        self.advapi = ctypes.WinDLL("Advapi32.dll") if self.available else None
        if self.advapi:
            pointer = ctypes.POINTER(self.CREDENTIALW)
            self.advapi.CredWriteW.argtypes = [pointer, wintypes.DWORD]
            self.advapi.CredWriteW.restype = wintypes.BOOL
            self.advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
            self.advapi.CredDeleteW.restype = wintypes.BOOL
            self.advapi.CredEnumerateW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.POINTER(ctypes.POINTER(pointer)),
            ]
            self.advapi.CredEnumerateW.restype = wintypes.BOOL
            self.advapi.CredFree.argtypes = [ctypes.c_void_p]

    def prefix(self):
        return f"GromBrowser:{self.profile_id}:"

    def target_name(self, origin, username):
        origin_key = base64.urlsafe_b64encode(str(origin).encode("utf-8")).decode("ascii")
        user_key = base64.urlsafe_b64encode(str(username).encode("utf-8")).decode("ascii")
        return f"{self.prefix()}{origin_key}:{user_key}"

    def save(self, origin, username, password):
        if not self.available or not origin or not username or not password:
            return False
        blob = str(password).encode("utf-16-le")
        if len(blob) > 2500:
            return False
        buffer = ctypes.create_string_buffer(blob)
        credential = self.CREDENTIALW()
        credential.Type = self.CRED_TYPE_GENERIC
        credential.TargetName = self.target_name(origin, username)
        credential.Comment = str(origin)
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        credential.Persist = self.CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = str(username)
        return bool(self.advapi.CredWriteW(ctypes.byref(credential), 0))

    def list(self):
        if not self.available:
            return []
        count = wintypes.DWORD()
        pointer = ctypes.POINTER(self.CREDENTIALW)
        credentials = ctypes.POINTER(pointer)()
        if not self.advapi.CredEnumerateW(self.prefix() + "*", 0, ctypes.byref(count), ctypes.byref(credentials)):
            return []
        result = []
        try:
            for index in range(count.value):
                item = credentials[index].contents
                blob = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
                result.append({
                    "target": item.TargetName or "",
                    "origin": item.Comment or "",
                    "username": item.UserName or "",
                    "password": blob.decode("utf-16-le", errors="ignore"),
                })
        finally:
            self.advapi.CredFree(credentials)
        return result

    def credential_for_origin(self, origin):
        return next((item for item in self.list() if item.get("origin") == origin), None)

    def delete(self, target):
        if not self.available or not str(target).startswith(self.prefix()):
            return False
        return bool(self.advapi.CredDeleteW(str(target), self.CRED_TYPE_GENERIC, 0))


class ProfilesMixin:
    def load_profile_registry(self):
        fallback = {
            "active": "default",
            "profiles": [{"id": "default", "name": "Профиль 1", "avatar": ""}],
        }
        try:
            with open(self.profiles_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            profiles = data.get("profiles", []) if isinstance(data, dict) else []
            profiles = [
                {
                    "id": re.sub(r"[^a-zA-Z0-9_-]", "", str(item.get("id", ""))),
                    "name": str(item.get("name", "Профиль"))[:50],
                    "avatar": str(item.get("avatar", "")),
                }
                for item in profiles
                if isinstance(item, dict) and re.sub(r"[^a-zA-Z0-9_-]", "", str(item.get("id", "")))
            ]
            if not any(item.get("id") == "default" for item in profiles):
                profiles.insert(0, fallback["profiles"][0])
            return {"active": str(data.get("active", "default")), "profiles": profiles}
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return fallback

    def save_profile_registry(self):
        with open(self.profiles_file, "w", encoding="utf-8") as file:
            json.dump(self.profile_registry, file, ensure_ascii=False, indent=2)

    def profile_page_records(self):
        records = []
        for profile in self.profile_registry.get("profiles", []):
            avatar_path = str(profile.get("avatar", ""))
            records.append({
                "id": str(profile.get("id", "")),
                "name": str(profile.get("name", "Профиль")),
                "avatar": self.file_data_uri(avatar_path) if avatar_path else "",
                "active": not self.guest_mode and profile.get("id") == self.profile_id,
                "deletable": profile.get("id") != "default" and profile.get("id") != self.profile_id,
            })
        return records

    def refresh_settings_pages(self):
        for index in range(self.tab_content.count()):
            workspace = self.tab_content.widget(index)
            if not isinstance(workspace, TabWorkspace):
                continue
            browser = workspace.primary_browser
            if browser.internal_page == "settings":
                browser.load_internal_html(self.settings_page_html(), "grom://settings/profiles")
                browser._icon = self.settings_icon()
                browser.iconChanged.emit(browser._icon)

    def create_profile(self, name):
        clean_name = str(name or "").strip()[:50]
        if not clean_name:
            return
        profile_id = uuid.uuid4().hex[:12]
        self.profile_registry["profiles"].append({"id": profile_id, "name": clean_name, "avatar": ""})
        self.save_profile_registry()
        self.refresh_settings_pages()

    def rename_profile(self, profile_id, name):
        clean_name = str(name or "").strip()[:50]
        if not clean_name:
            return
        for profile in self.profile_registry.get("profiles", []):
            if profile.get("id") == profile_id:
                profile["name"] = clean_name
                if profile_id == self.profile_id:
                    self.current_profile = profile
                    self.setWindowTitle(f"Grom Browser — {clean_name}")
                    self.profile_btn.setToolTip(clean_name)
                self.save_profile_registry()
                self.refresh_settings_pages()
                return

    def choose_profile_avatar(self, profile_id):
        profile = next((item for item in self.profile_registry.get("profiles", []) if item.get("id") == profile_id), None)
        if not profile:
            return
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "Выбрать аватар профиля",
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation),
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        avatar_dir = os.path.join(self.base_storage_path, "profile_avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        extension = os.path.splitext(path)[1].lower() or ".png"
        destination = os.path.join(avatar_dir, f"{profile_id}{extension}")
        if os.path.abspath(path) != os.path.abspath(destination):
            QFile.remove(destination)
            if not QFile.copy(path, destination):
                QMessageBox.warning(self, "Профиль", "Не удалось сохранить аватар профиля.")
                return
        profile["avatar"] = destination
        self.save_profile_registry()
        if profile_id == self.profile_id:
            self.current_profile = profile
            self.profile_btn.setIcon(self.profile_avatar_icon())
        self.refresh_settings_pages()

    def delete_profile(self, profile_id):
        if profile_id in ("default", self.profile_id):
            return
        profiles = self.profile_registry.get("profiles", [])
        profile = next((item for item in profiles if item.get("id") == profile_id), None)
        if not profile:
            return
        answer = QMessageBox.question(
            self,
            "Удалить профиль",
            f"Удалить профиль «{profile.get('name', 'Профиль')}» и его локальные данные?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        profiles_root = os.path.abspath(os.path.join(self.base_storage_path, "profiles"))
        target = os.path.abspath(os.path.join(profiles_root, profile_id))
        if os.path.commonpath([profiles_root, target]) == profiles_root and target != profiles_root:
            QDir(target).removeRecursively()
        avatar = str(profile.get("avatar", ""))
        avatar_root = os.path.abspath(os.path.join(self.base_storage_path, "profile_avatars"))
        if avatar:
            try:
                if os.path.commonpath([avatar_root, os.path.abspath(avatar)]) == avatar_root:
                    QFile.remove(avatar)
            except ValueError:
                pass
        self.profile_registry["profiles"] = [item for item in profiles if item.get("id") != profile_id]
        self.save_profile_registry()
        self.refresh_settings_pages()

    def switch_profile(self, profile_id=None, guest=False):
        if not guest and profile_id == self.profile_id and not self.guest_mode:
            return
        if not guest and not any(item.get("id") == profile_id for item in self.profile_registry.get("profiles", [])):
            return
        if not guest:
            self.profile_registry["active"] = profile_id
            self.save_profile_registry()
        executable = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.isfile(executable):
            executable = sys.executable
        arguments = [executable, os.path.abspath(__file__), "--guest" if guest else "--profile", "" if guest else profile_id]
        if guest:
            arguments.pop()
        subprocess.Popen(
            arguments,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        QApplication.quit()

    def launch_new_window(self):
        executable = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.isfile(executable):
            executable = sys.executable
        arguments = [executable, os.path.abspath(__file__)]
        if self.guest_mode:
            arguments.append("--guest")
        else:
            arguments.extend(("--profile", self.profile_id))
        subprocess.Popen(
            arguments,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
