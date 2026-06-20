"""Encrypted WebDAV sync for shared history packages."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
from typing import Any

from sharing.history_package import parse_history_package

ENCRYPTED_SCHEMA = "latexsnipper.share.encrypted.v1"
ITERATIONS = 210000
WEBDAV_SUBFOLDER = "latexsnipper"
WEBDAV_FILENAME = "history.json"


def _require_crypto():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.hashes import SHA256
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    return AESGCM, SHA256, PBKDF2HMAC


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase or "") < 8:
        raise ValueError("encryption password must be at least 8 characters")
    _aesgcm, sha256, pbkdf2 = _require_crypto()
    kdf = pbkdf2(algorithm=sha256(), length=32, salt=salt, iterations=ITERATIONS)
    return kdf.derive(passphrase.encode("utf-8"))


def normalize_webdav_url(url: str) -> str:
    """Ensure the WebDAV URL targets the latexsnipper subfolder.

    - Bare server root (e.g. ``https://dav.example.com/``) -> appends
      ``latexsnipper/history.json``.
    - URL already ending with ``.json`` is kept as-is (user provided full path).
    - URL ending with ``/`` -> appends ``latexsnipper/history.json``.
    - URL pointing elsewhere (e.g. ``https://dav.example.com/mydir/notes.txt``)
      is kept as-is.
    """
    from urllib.parse import urljoin, urlparse

    url = (url or "").strip().rstrip("/")
    if not url:
        return url

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    # Already points to a .json file -> keep as-is
    if path.endswith(".json"):
        return url

    # Points to a directory (or bare host) -> append subfolder + filename
    if not path or not "." in path.split("/")[-1]:
        return f"{parsed.scheme}://{parsed.netloc}/{path}/{WEBDAV_SUBFOLDER}/{WEBDAV_FILENAME}".replace("//", "/").replace(":///", "://")

    return url


def encrypt_package(package: dict[str, Any], passphrase: str) -> dict[str, Any]:
    """Encrypt a history package in the same format as the mobile app."""
    parse_history_package(package)
    aesgcm_cls, _sha256, _pbkdf2 = _require_crypto()
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = _derive_key(passphrase, salt)
    cipher = aesgcm_cls(key).encrypt(iv, json.dumps(package, ensure_ascii=False).encode("utf-8"), None)
    return {
        "schema": ENCRYPTED_SCHEMA,
        "version": 1,
        "kdf": "PBKDF2-SHA256",
        "iterations": ITERATIONS,
        "cipher": "AES-256-GCM",
        "salt": base64.b64encode(salt).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "payload": base64.b64encode(cipher).decode("ascii"),
    }


def decrypt_package(envelope: dict[str, Any], passphrase: str) -> dict[str, Any]:
    """Decrypt an encrypted history package from WebDAV."""
    if not isinstance(envelope, dict) or envelope.get("schema") != ENCRYPTED_SCHEMA:
        raise ValueError("unsupported encrypted package")
    aesgcm_cls, _sha256, _pbkdf2 = _require_crypto()
    salt = base64.b64decode(str(envelope.get("salt", "")))
    iv = base64.b64decode(str(envelope.get("iv", "")))
    payload = base64.b64decode(str(envelope.get("payload", "")))
    key = _derive_key(passphrase, salt)
    plain = aesgcm_cls(key).decrypt(iv, payload, None)
    return parse_history_package(json.loads(plain.decode("utf-8")))


def upload_package(url: str, username: str, password: str, passphrase: str, package: dict[str, Any]) -> None:
    import requests

    encrypted = encrypt_package(package, passphrase)
    url = normalize_webdav_url(url)
    response = requests.put(
        url,
        data=json.dumps(encrypted, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        auth=(username, password) if username or password else None,
        timeout=20,
    )
    response.raise_for_status()


def download_package(url: str, username: str, password: str, passphrase: str) -> dict[str, Any]:
    import requests

    url = normalize_webdav_url(url)
    response = requests.get(
        url,
        auth=(username, password) if username or password else None,
        timeout=20,
    )
    response.raise_for_status()
    return decrypt_package(response.json(), passphrase)


def _device_key() -> bytes:
    raw = f"{platform.node()}:{os.getuid() if hasattr(os, 'getuid') else platform.machine()}"
    return hashlib.sha256(raw.encode()).digest()[:32]


def save_webdav_credentials(url: str, username: str, password: str, encrypt_password: str) -> None:
    """Encrypt and persist WebDAV credentials locally. Cannot be read back, only overwritten."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _device_key()
    iv = os.urandom(12)
    plaintext = json.dumps({
        "url": url,
        "username": username,
        "password": password,
        "encrypt_password": encrypt_password,
    }, ensure_ascii=False).encode("utf-8")
    ct = AESGCM(key).encrypt(iv, plaintext, None)
    blob = base64.b64encode(iv + ct).decode("ascii")

    from runtime.config_manager import ConfigManager
    cfg = ConfigManager()
    cfg.set("webdav_credentials", blob)


def load_webdav_credentials() -> dict[str, str] | None:
    """Load encrypted WebDAV credentials. Returns None if not found or corrupted."""
    from runtime.config_manager import ConfigManager

    cfg = ConfigManager()
    blob = cfg.get("webdav_credentials", "")
    if not blob:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        raw = base64.b64decode(blob)
        iv, ct = raw[:12], raw[12:]
        key = _device_key()
        plaintext = AESGCM(key).decrypt(iv, ct, None)
        return json.loads(plaintext.decode("utf-8"))
    except Exception:
        return None


def has_saved_webdav_credentials() -> bool:
    """Check if saved credentials exist (without decrypting)."""
    from runtime.config_manager import ConfigManager
    return bool(ConfigManager().get("webdav_credentials", ""))


def clear_webdav_credentials() -> None:
    """Remove saved WebDAV credentials."""
    from runtime.config_manager import ConfigManager
    cfg = ConfigManager()
    cfg.set("webdav_credentials", "")
