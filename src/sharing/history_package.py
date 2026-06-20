"""Portable history package format shared with LaTeXSnipper Mobile."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from runtime.config_manager import normalize_content_type

SCHEMA = "latexsnipper.share.history.v1"


def _entry_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def build_history_package(
    history: list[str],
    formula_names: dict[str, str] | None = None,
    formula_types: dict[str, str] | None = None,
    render_tags: dict[str, str] | None = None,
    *,
    source: str = "desktop",
) -> dict[str, Any]:
    """Build a JSON-serializable package for LAN/WebDAV sharing."""
    names = formula_names or {}
    types = formula_types or {}
    tags = render_tags or {}
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    now_ms = int(time.time() * 1000)

    for index, raw_text in enumerate(history):
        text = str(raw_text or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        tag = str(tags.get(text, "") or "").lower()
        entries.append(
            {
                "id": _entry_id(text),
                "latex": text,
                "title": str(names.get(text, "") or ""),
                "contentType": normalize_content_type(types.get(text)),
                "renderTag": tag if tag in ("latex", "typst") else "",
                "favorite": False,
                "createdAt": now_ms - (len(history) - index),
            }
        )

    return {
        "schema": SCHEMA,
        "version": 1,
        "source": source,
        "exportedAt": now_ms,
        "entries": entries,
    }


def parse_history_package(data: bytes | str | dict[str, Any]) -> dict[str, Any]:
    """Parse and validate a shared history package."""
    if isinstance(data, bytes):
        payload = json.loads(data.decode("utf-8"))
    elif isinstance(data, str):
        payload = json.loads(data)
    else:
        payload = data

    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("unsupported history package")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("history package entries must be a list")
    return payload


def merge_history_package(
    package: dict[str, Any],
    history: list[str],
    formula_names: dict[str, str],
    formula_types: dict[str, str],
    render_tags: dict[str, str],
    *,
    max_history: int = 200,
) -> tuple[int, int]:
    """Merge package entries into desktop history and metadata."""
    parsed = parse_history_package(package)
    added = 0
    updated = 0
    known = set(history)

    for item in parsed.get("entries", []):
        if not isinstance(item, dict):
            continue
        text = str(item.get("latex", "") or "").strip()
        if not text:
            continue
        if text not in known:
            history.append(text)
            known.add(text)
            added += 1

        title = str(item.get("title", "") or "").strip()
        if title and formula_names.get(text) != title:
            formula_names[text] = title
            updated += 1

        content_type = normalize_content_type(str(item.get("contentType", "") or ""))
        if formula_types.get(text) != content_type:
            formula_types[text] = content_type
            updated += 1

        tag = str(item.get("renderTag", "") or "").strip().lower()
        if tag in ("latex", "typst") and render_tags.get(text) != tag:
            render_tags[text] = tag
            updated += 1

    if len(history) > max_history:
        del history[:-max_history]
    return added, updated


def dumps_package(package: dict[str, Any]) -> bytes:
    """Serialize a shared package as UTF-8 JSON bytes."""
    parse_history_package(package)
    return json.dumps(package, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
