"""Encrypted WebDAV sync for shared history packages."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import requests

from sharing.history_package import parse_history_package

ENCRYPTED_SCHEMA = "latexsnipper.share.encrypted.v1"
ITERATIONS = 210000


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
    encrypted = encrypt_package(package, passphrase)
    response = requests.put(
        url,
        data=json.dumps(encrypted, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        auth=(username, password) if username or password else None,
        timeout=20,
    )
    response.raise_for_status()


def download_package(url: str, username: str, password: str, passphrase: str) -> dict[str, Any]:
    response = requests.get(
        url,
        auth=(username, password) if username or password else None,
        timeout=20,
    )
    response.raise_for_status()
    return decrypt_package(response.json(), passphrase)
