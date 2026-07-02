"""
Duplicate detection for the Marrakech Daily agent.

Uses two complementary strategies:
1. URL fingerprinting — exact match on source URL (catches exact reprints)
2. Title fingerprint — normalised title hash (catches near-identical stories
   even from different sources)

The hash store is persisted to _data/published_hashes.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

from config import HASHES_FILE, MAX_HASH_HISTORY

log = logging.getLogger(__name__)


# ── Normalisation ──────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, remove accents, strip punctuation, collapse whitespace."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest()[:24]


def _title_hash(title: str) -> str:
    return hashlib.sha256(_normalise(title).encode()).hexdigest()[:24]


# ── Store loading / saving ─────────────────────────────────────────────────────

def _load_store() -> dict:
    if HASHES_FILE.exists():
        try:
            return json.loads(HASHES_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not load hash store: %s", exc)
    return {"url_hashes": [], "title_hashes": []}


def _save_store(store: dict) -> None:
    # Trim to max history to keep file size manageable
    store["url_hashes"]   = store["url_hashes"][-MAX_HASH_HISTORY:]
    store["title_hashes"] = store["title_hashes"][-MAX_HASH_HISTORY:]
    HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASHES_FILE.write_text(
        json.dumps(store, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── Public API ─────────────────────────────────────────────────────────────────

class Deduplicator:
    """
    Maintains an in-memory + on-disk set of seen URLs and title hashes.
    Call `is_duplicate()` before publishing an article, and `mark_published()`
    after it has been saved.
    """

    def __init__(self) -> None:
        store = _load_store()
        self._url_hashes:   set[str] = set(store.get("url_hashes", []))
        self._title_hashes: set[str] = set(store.get("title_hashes", []))
        log.debug(
            "Deduplicator loaded: %d URL hashes, %d title hashes",
            len(self._url_hashes),
            len(self._title_hashes),
        )

    def is_duplicate(self, source_url: str, title: str) -> bool:
        """Return True if this article has already been published."""
        if source_url and _url_hash(source_url) in self._url_hashes:
            log.info("DUPLICATE (URL): %s", source_url[:80])
            return True
        if _title_hash(title) in self._title_hashes:
            log.info("DUPLICATE (title): %s", title[:80])
            return True
        return False

    def mark_published(self, source_url: str, title: str) -> None:
        """Record that this article has been published."""
        if source_url:
            self._url_hashes.add(_url_hash(source_url))
        self._title_hashes.add(_title_hash(title))

    def save(self) -> None:
        """Persist the current state to disk."""
        store = {
            "url_hashes":   list(self._url_hashes),
            "title_hashes": list(self._title_hashes),
        }
        _save_store(store)
        log.debug("Hash store saved (%d URLs, %d titles)",
                  len(self._url_hashes), len(self._title_hashes))
