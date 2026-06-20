"""End-to-end simulation tests for LAN and WebDAV sharing paths.

Tests run without external dependencies (no requests/cryptography).
Encryption roundtrip is tested via the pure-crypto section.
LAN server test uses stdlib http only.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import unittest
import urllib.request
from typing import Any
from unittest.mock import patch

try:
    import requests as _requests_mod
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
    HAS_CRYPTOGRAPHY = True
except Exception:
    HAS_CRYPTOGRAPHY = False

_skip_crypto = unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography DLL not available")
_skip_requests = unittest.skipUnless(HAS_REQUESTS, "requests not installed")

from sharing.history_package import (
    build_history_package,
    dumps_package,
    merge_history_package,
    parse_history_package,
)
from sharing.lan_share_server import LanShareServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_desktop_history(n: int = 5) -> tuple[list[str], dict, dict, dict]:
    history = [f"\\frac{{{i}}}{{{i+1}}}" for i in range(n)]
    names = {h: f"formula_{i}" for i, h in enumerate(history)}
    types = {h: "mathcraft" for h in history}
    tags = {h: "latex" for h in history}
    return history, names, types, tags


def _make_mobile_records(n: int = 3) -> list[dict]:
    return [
        {"latex": f"\\sum_{{k=0}}^{{{i}}} {i}", "confidence": 0.95, "type": "formula", "source": "mobile"}
        for i in range(1, n + 1)
    ]


def _build_mobile_package(records: list[dict]) -> dict[str, Any]:
    seen: set[str] = set()
    entries: list[dict] = []
    now = int(time.time() * 1000)
    for r in records:
        latex = str(r.get("latex", "")).strip()
        if not latex or latex in seen:
            continue
        seen.add(latex)
        entries.append({
            "id": hashlib.sha256(latex.encode()).hexdigest()[:16],
            "latex": latex,
            "title": r.get("title", ""),
            "contentType": r.get("type", "formula"),
            "renderTag": "latex",
            "favorite": False,
            "confidence": r.get("confidence", 1),
            "source": r.get("source", "mobile"),
            "createdAt": now,
        })
    return {
        "schema": "latexsnipper.share.history.v1",
        "version": 1,
        "source": "mobile",
        "exportedAt": now,
        "entries": entries,
    }


# ---------------------------------------------------------------------------
# Test 1: Package format compatibility
# ---------------------------------------------------------------------------

class TestPackageCompatibility(unittest.TestCase):

    def test_desktop_package_schema(self):
        history, names, types, tags = _make_desktop_history(5)
        pkg = build_history_package(history, names, types, tags, source="desktop")
        self.assertEqual(pkg["schema"], "latexsnipper.share.history.v1")
        self.assertEqual(len(pkg["entries"]), 5)
        for entry in pkg["entries"]:
            self.assertIn("id", entry)
            self.assertIn("latex", entry)

    def test_mobile_package_parseable_by_desktop(self):
        records = _make_mobile_records(3)
        pkg = _build_mobile_package(records)
        parsed = parse_history_package(pkg)
        self.assertEqual(len(parsed["entries"]), 3)

    def test_serialization_roundtrip(self):
        history, names, types, tags = _make_desktop_history(3)
        pkg = build_history_package(history, names, types, tags)
        raw = dumps_package(pkg)
        self.assertIsInstance(raw, bytes)
        restored = parse_history_package(raw)
        self.assertEqual(len(restored["entries"]), 3)

    def test_bytes_roundtrip(self):
        records = _make_mobile_records(2)
        pkg = _build_mobile_package(records)
        raw = json.dumps(pkg, ensure_ascii=False).encode("utf-8")
        restored = parse_history_package(raw)
        self.assertEqual(len(restored["entries"]), 2)


# ---------------------------------------------------------------------------
# Test 2: Merge logic
# ---------------------------------------------------------------------------

class TestMergeLogic(unittest.TestCase):

    def test_merge_new_entries(self):
        history, names, types, tags = _make_desktop_history(3)
        pkg = _build_mobile_package(_make_mobile_records(3))
        added, updated = merge_history_package(pkg, history, names, types, tags)
        self.assertGreater(added, 0)
        self.assertEqual(len(history), 6)

    def test_merge_deduplicates(self):
        history, names, types, tags = _make_desktop_history(3)
        pkg = _build_mobile_package([{"latex": history[0], "type": "formula", "source": "mobile"}])
        added, updated = merge_history_package(pkg, history, names, types, tags)
        self.assertEqual(added, 0)
        self.assertEqual(len(history), 3)

    def test_merge_updates_metadata(self):
        history, names, types, tags = _make_desktop_history(2)
        pkg = _build_mobile_package([{"latex": history[0], "title": "new_name", "type": "mathcraft_mixed", "source": "mobile"}])
        added, updated = merge_history_package(pkg, history, names, types, tags)
        self.assertEqual(names[history[0]], "new_name")
        self.assertEqual(types[history[0]], "mathcraft_mixed")

    def test_merge_truncates_to_max(self):
        history, names, types, tags = _make_desktop_history(5)
        records = [{"latex": f"\\alpha_{{{i}}}", "type": "formula", "source": "mobile"} for i in range(20)]
        pkg = _build_mobile_package(records)
        added, updated = merge_history_package(pkg, history, names, types, tags, max_history=10)
        self.assertEqual(len(history), 10)

    def test_merge_bidirectional(self):
        h1, n1, t1, tg1 = _make_desktop_history(3)
        pkg1 = build_history_package(h1, n1, t1, tg1, source="desktop")
        records = _make_mobile_records(2)
        pkg2 = _build_mobile_package(records)
        h2, n2, t2, tg2 = _make_desktop_history(0)
        a1, _ = merge_history_package(pkg1, h2, n2, t2, tg2)
        a2, _ = merge_history_package(pkg2, h2, n2, t2, tg2)
        self.assertEqual(a1, 3)
        self.assertGreater(a2, 0)
        self.assertEqual(len(h2), 3 + a2)


# ---------------------------------------------------------------------------
# Test 3: LAN server API
# ---------------------------------------------------------------------------

class TestLanServerSimulation(unittest.TestCase):

    def _start_server(self):
        history, names, types, tags = _make_desktop_history(3)

        def provider():
            return build_history_package(history, names, types, tags, source="desktop")

        def importer(package):
            return merge_history_package(package, history, names, types, tags)

        server = LanShareServer(provider, importer, host="127.0.0.1", port=0)
        server.start()
        return server, history

    def test_info_endpoint(self):
        server, _ = self._start_server()
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{server.port}/api/v1/info", timeout=5)
            data = json.loads(resp.read())
            self.assertTrue(data["ok"])
            self.assertEqual(data["app"], "LaTeXSnipper")
        finally:
            server.stop()

    def test_history_get_with_pin(self):
        server, _ = self._start_server()
        try:
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{server.port}/api/v1/history?pin={server.pin}", timeout=5
            )
            data = parse_history_package(resp.read())
            self.assertEqual(data["schema"], "latexsnipper.share.history.v1")
            self.assertEqual(len(data["entries"]), 3)
        finally:
            server.stop()

    def test_history_get_wrong_pin(self):
        server, _ = self._start_server()
        try:
            with self.assertRaises(Exception):
                urllib.request.urlopen(
                    f"http://127.0.0.1:{server.port}/api/v1/history?pin=000000", timeout=5
                )
        finally:
            server.stop()

    def test_history_post_import(self):
        server, hist = self._start_server()
        try:
            pkg = _build_mobile_package(_make_mobile_records(3))
            body = json.dumps(pkg, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.port}/api/v1/history/import?pin={server.pin}",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            self.assertTrue(data["ok"])
            self.assertEqual(data["added"], 3)
            self.assertEqual(len(hist), 6)
        finally:
            server.stop()

    def test_full_lan_roundtrip(self):
        """Simulate: desktop starts server -> mobile pulls -> mobile pushes -> desktop merges."""
        server, hist = self._start_server()
        try:
            # Mobile pulls desktop history
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{server.port}/api/v1/history?pin={server.pin}", timeout=5
            )
            desktop_pkg = parse_history_package(resp.read())
            self.assertEqual(len(desktop_pkg["entries"]), 3)

            # Mobile builds its own package
            mobile_pkg = _build_mobile_package(_make_mobile_records(3))

            # Mobile pushes to desktop
            body = json.dumps(mobile_pkg, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.port}/api/v1/history/import?pin={server.pin}",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=5)
            result = json.loads(resp.read())
            self.assertTrue(result["ok"])
            self.assertEqual(result["added"], 3)
            self.assertEqual(len(hist), 6)
        finally:
            server.stop()


# ---------------------------------------------------------------------------
# Test 4: WebDAV URL normalization
# ---------------------------------------------------------------------------

class TestWebdavUrlNormalization(unittest.TestCase):

    def _normalize(self, url: str) -> str:
        """Import and test normalize_webdav_url."""
        from sharing.webdav_sync import normalize_webdav_url
        return normalize_webdav_url(url)

    def test_bare_server_root(self):
        result = self._normalize("https://dav.example.com/")
        self.assertIn("latexsnipper/history.json", result)

    def test_bare_server_no_slash(self):
        result = self._normalize("https://dav.example.com")
        self.assertIn("latexsnipper/history.json", result)

    def test_server_with_path(self):
        result = self._normalize("https://dav.example.com/user/dav")
        self.assertIn("latexsnipper/history.json", result)
        self.assertIn("/user/dav/", result)

    def test_full_json_url_kept(self):
        url = "https://dav.example.com/mydir/history.json"
        result = self._normalize(url)
        self.assertEqual(result, url)

    def test_existing_json_at_subfolder(self):
        url = "https://dav.example.com/latexsnipper/history.json"
        result = self._normalize(url)
        self.assertEqual(result, url)

    def test_empty_url(self):
        result = self._normalize("")
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# Test 5: WebDAV credential storage
# ---------------------------------------------------------------------------

@_skip_crypto
class TestCredentialStorage(unittest.TestCase):

    def setUp(self):
        from sharing.webdav_sync import clear_webdav_credentials
        clear_webdav_credentials()

    def tearDown(self):
        from sharing.webdav_sync import clear_webdav_credentials
        clear_webdav_credentials()

    def test_save_and_load(self):
        from sharing.webdav_sync import save_webdav_credentials, load_webdav_credentials, has_saved_webdav_credentials
        save_webdav_credentials("https://dav.example.com/test.json", "user1", "pass123", "enc-key-456")
        self.assertTrue(has_saved_webdav_credentials())
        creds = load_webdav_credentials()
        self.assertIsNotNone(creds)
        self.assertEqual(creds["url"], "https://dav.example.com/test.json")
        self.assertEqual(creds["username"], "user1")

    def test_overwrite(self):
        from sharing.webdav_sync import save_webdav_credentials, load_webdav_credentials
        save_webdav_credentials("https://old.example.com/a.json", "old", "old", "old")
        save_webdav_credentials("https://new.example.com/b.json", "new", "new", "new")
        creds = load_webdav_credentials()
        self.assertEqual(creds["url"], "https://new.example.com/b.json")

    def test_no_saved(self):
        from sharing.webdav_sync import has_saved_webdav_credentials, load_webdav_credentials
        self.assertFalse(has_saved_webdav_credentials())
        self.assertIsNone(load_webdav_credentials())

    def test_clear(self):
        from sharing.webdav_sync import save_webdav_credentials, clear_webdav_credentials, has_saved_webdav_credentials
        save_webdav_credentials("https://x.com", "u", "p", "e")
        clear_webdav_credentials()
        self.assertFalse(has_saved_webdav_credentials())


# ---------------------------------------------------------------------------
# Test 6: WebDAV encrypt/decrypt simulation (via requests mock)
# ---------------------------------------------------------------------------

@_skip_crypto
class TestWebdavSyncSimulation(unittest.TestCase):
    """Simulate full WebDAV sync by mocking the requests calls."""

    def test_desktop_encrypts_mobile_decrypts(self):
        from sharing.webdav_sync import encrypt_package, decrypt_package

        history, names, types, tags = _make_desktop_history(4)
        pkg = build_history_package(history, names, types, tags, source="desktop")
        passphrase = "shared-secret-12345"

        encrypted = encrypt_package(pkg, passphrase)
        self.assertEqual(encrypted["schema"], "latexsnipper.share.encrypted.v1")
        self.assertEqual(encrypted["cipher"], "AES-256-GCM")

        file_content = json.dumps(encrypted, ensure_ascii=False).encode("utf-8")
        stored = json.loads(file_content.decode("utf-8"))
        decrypted = decrypt_package(stored, passphrase)
        self.assertEqual(len(decrypted["entries"]), 4)

    def test_wrong_password_fails(self):
        from sharing.webdav_sync import encrypt_package, decrypt_package

        history, _, _, _ = _make_desktop_history(2)
        pkg = build_history_package(history, source="desktop")
        encrypted = encrypt_package(pkg, "correct-password-12345")
        with self.assertRaises(Exception):
            decrypt_package(encrypted, "wrong-password-xxxxx")

    def test_tampered_payload_fails(self):
        from sharing.webdav_sync import encrypt_package, decrypt_package

        history, _, _, _ = _make_desktop_history(2)
        pkg = build_history_package(history, source="desktop")
        encrypted = encrypt_package(pkg, "test-pass-12345")
        encrypted["payload"] = encrypted["payload"][:-4] + "XXXX"
        with self.assertRaises(Exception):
            decrypt_package(encrypted, "test-pass-12345")

    def test_bidirectional_webdav_sync(self):
        from sharing.webdav_sync import encrypt_package, decrypt_package

        h_a, n_a, t_a, tg_a = _make_desktop_history(3)
        passphrase = "sync-password-999"

        # A encrypts and uploads
        pkg_a = build_history_package(h_a, n_a, t_a, tg_a, source="desktop")
        encrypted_a = encrypt_package(pkg_a, passphrase)
        file_a = json.dumps(encrypted_a, ensure_ascii=False).encode("utf-8")

        # B: mobile with 2 formulas
        records_b = _make_mobile_records(2)
        pkg_b = _build_mobile_package(records_b)

        # B decrypts A's package
        stored_a = json.loads(file_a.decode("utf-8"))
        decrypted_a = decrypt_package(stored_a, passphrase)
        h_b, n_b, t_b, tg_b = _make_desktop_history(0)
        added_b, _ = merge_history_package(decrypted_a, h_b, n_b, t_b, tg_b)
        self.assertEqual(added_b, 3)

        # B adds its own records and encrypts
        merge_history_package(pkg_b, h_b, n_b, t_b, tg_b)
        pkg_b_merged = build_history_package(h_b, n_b, t_b, tg_b, source="mobile")
        encrypted_b = encrypt_package(pkg_b_merged, passphrase)
        file_b = json.dumps(encrypted_b, ensure_ascii=False).encode("utf-8")

        # A decrypts B's package
        stored_b = json.loads(file_b.decode("utf-8"))
        decrypted_b = decrypt_package(stored_b, passphrase)
        added_a, _ = merge_history_package(decrypted_b, h_a, n_a, t_a, tg_a)
        self.assertGreater(added_a, 0)
        self.assertEqual(len(h_a), 3 + added_a)

    def test_upload_download_via_mock(self):
        from sharing.webdav_sync import upload_package, download_package

        history, names, types, tags = _make_desktop_history(3)
        pkg = build_history_package(history, names, types, tags, source="desktop")
        passphrase = "mock-test-pass-123"

        captured: dict[str, Any] = {}

        class FakeResponse:
            status_code = 201

            def __init__(self, body=None):
                self._body = body

            def raise_for_status(self):
                pass

            def json(self):
                return self._body

            @property
            def ok(self):
                return 200 <= self.status_code < 300

        def fake_put(url, **kwargs):
            captured["url"] = url
            captured["data"] = kwargs.get("data")
            captured["auth"] = kwargs.get("auth")
            return FakeResponse()

        def fake_get(url, **kwargs):
            captured["url_get"] = url
            return FakeResponse(json.loads(captured["data"]))

        with patch("sharing.webdav_sync.requests.put", side_effect=fake_put), \
             patch("sharing.webdav_sync.requests.get", side_effect=fake_get):

            upload_package("https://dav.example.com/", "user", "pass", passphrase, pkg)
            self.assertIn("latexsnipper/history.json", captured["url"])
            self.assertEqual(captured["auth"], ("user", "pass"))

            result = download_package("https://dav.example.com/", "user", "pass", passphrase)
            self.assertEqual(result["schema"], "latexsnipper.share.history.v1")
            self.assertEqual(len(result["entries"]), 3)

    def test_combined_lan_then_webdav(self):
        """Phase 1: LAN quick share. Phase 2: WebDAV backup. Phase 3: Mobile restores from WebDAV."""
        from sharing.webdav_sync import encrypt_package, decrypt_package

        # Phase 1: LAN
        history, names, types, tags = _make_desktop_history(3)

        def provider():
            return build_history_package(history, names, types, tags, source="desktop")

        def importer(package):
            return merge_history_package(package, history, names, types, tags)

        server = LanShareServer(provider, importer, host="127.0.0.1", port=0)
        server.start()
        try:
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{server.port}/api/v1/history?pin={server.pin}", timeout=5
            )
            initial_pkg = parse_history_package(resp.read())
            self.assertEqual(len(initial_pkg["entries"]), 3)
        finally:
            server.stop()

        # Phase 2: WebDAV backup
        pkg = build_history_package(history, names, types, tags, source="desktop")
        passphrase = "long-term-key"
        encrypted = encrypt_package(pkg, passphrase)
        file_content = json.dumps(encrypted, ensure_ascii=False).encode("utf-8")

        # Phase 3: Mobile restores from WebDAV
        stored = json.loads(file_content.decode("utf-8"))
        decrypted = decrypt_package(stored, passphrase)
        self.assertEqual(decrypted["schema"], "latexsnipper.share.history.v1")
        self.assertEqual(len(decrypted["entries"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
