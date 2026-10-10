"""What the Board answered, kept as received, in the plugin's own storage.

A `dgm` keeps its source's raw records in the storage the deployment grants
an edge plugin (decisions/028, `meridian.edge.storage_dir()`), and every row
it records names the one it was converted from (`ObservationMeta.raw`). Here
that is each response of the Board's: its address, status, the Date and
Last-Modified headers, when it was received, and the page itself, one gzipped
JSON file each, kept before anything is read from it.

One kind of raw record, `responses` (declaration.py), in units of a month
of receipt: `responses/<YYYY-MM>/`, each file `<received>-<page>.json.gz`,
its key that path. A month's unit is written to only in that month, so once
its last record is past the kind's window it is moved whole, as the SDK's
`responses_past_window` setting says: archived (`plugin.archive_unit`),
deleted (`plugin.delete_unit`, which a deployment's hold refuses, keeping
it) or kept. H.10 is public domain and small (about 13 kB a week gzipped),
so the window defaults to ten years.

A rate read again -- the same release on the next check, or after a restart
-- names the response it was first read from, not the newest copy: the lake
compares a row's raw record too, so a new reference would restate every rate
unchanged. Which response first held a release's rates is noted in
`responses-first.json` at the storage's root, keyed by the release's date and
a digest of its rates, and rebuilt from the responses if it is lost (a
release read again then names the copy read that day, once).

Where no storage is granted -- a test, a preview -- the store keeps its
records in a directory of its own and moves nothing.
"""

from __future__ import annotations

import gzip
import json
import logging
import re
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import meridian
from meridian import edge

from .board import Fetched

log = logging.getLogger("fed_h10")

#: The kind of raw record, and its default window: ten years.
RESPONSES = "responses"
DEFAULT_WINDOW_DAYS = 3650
#: The longest a window may be set to, which the storage declaration states.
MOST_WINDOW_DAYS = 36500

_PAGE = re.compile(r"[^a-z0-9]+")
#: Which response first held each release's rates, at the storage's root.
FIRSTS = "responses-first.json"


def _ns(moment: datetime) -> int:
    return int(moment.timestamp() * 1_000_000) * 1000


def page_name(path: str) -> str:
    """A short name for the page a path is: `current`, or the release's date."""
    parts = [p for p in path.split("/") if p and p not in ("releases", "h10", "default.htm")]
    return _PAGE.sub("-", "-".join(parts).lower()).strip("-") or "page"


@dataclass(frozen=True)
class Unit:
    """A month of responses: its path in storage, and what it holds."""

    unit: str
    records: int
    first_ns: int
    last_ns: int


class RawStore:
    """Responses kept under `root`: the granted storage, or a directory of
    the store's own where none is granted (`granted` False)."""

    def __init__(self, root: Path | None = None) -> None:
        granted = root if root is not None else edge.storage_dir()
        self.granted = granted is not None
        self.root = (
            Path(granted) if granted is not None else Path(tempfile.mkdtemp(prefix="fed-h10-"))
        )

    def keep(self, fetched: Fetched) -> str:
        """Keep a response before anything is read from it; its key."""
        at = fetched.fetched_at.astimezone(UTC)
        unit = f"{RESPONSES}/{at:%Y-%m}"
        key = f"{unit}/{at:%Y%m%dT%H%M%S%fZ}-{page_name(fetched.path)}.json.gz"
        document = {
            "url": fetched.url,
            "status": fetched.status,
            "date": fetched.date,
            "last_modified": fetched.last_modified,
            "received_at": at.isoformat(),
            "body": fetched.text,
        }
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".partial")
        partial.write_bytes(gzip.compress(json.dumps(document).encode(), mtime=0))
        partial.replace(target)
        return key

    def first(self, release: str) -> str | None:
        """The key of the response a release's rates were first read from,
        by the release's date and its rates' digest; None if none is noted
        or storage no longer holds it."""
        key = self._firsts().get(release)
        return key if key and (self.root / key).is_file() else None

    def note_first(self, release: str, key: str) -> str:
        """Note `key` as the first response of `release`, unless one is noted
        and held already; the key the release's rows name."""
        held = self.first(release)
        if held is not None:
            return held
        firsts = self._firsts()
        firsts[release] = key
        target = self.root / FIRSTS
        partial = target.with_suffix(".partial")
        partial.write_text(json.dumps(firsts, sort_keys=True, indent=0))
        partial.replace(target)
        return key

    def _firsts(self) -> dict[str, str]:
        try:
            held: dict[str, str] = json.loads((self.root / FIRSTS).read_text())
        except (OSError, ValueError):
            return {}
        return held

    def read(self, key: str) -> dict[str, Any] | None:
        """A kept response by its key, or None where storage no longer holds it."""
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            return None
        document: dict[str, Any] = json.loads(gzip.decompress(path.read_bytes()))
        return document

    def keys(self) -> list[str]:
        """Every kept response's key, oldest first."""
        held = self.root / RESPONSES
        if not held.is_dir():
            return []
        return sorted(str(p.relative_to(self.root)) for p in held.glob("*/*.json.gz"))

    def units(self) -> Iterator[Unit]:
        """Each month of responses in storage, oldest first."""
        held = self.root / RESPONSES
        if not held.is_dir():
            return
        for month in sorted(p for p in held.iterdir() if p.is_dir()):
            read = (_received(p.name) for p in month.glob("*.json.gz"))
            stamps = sorted(s for s in read if s is not None)
            if stamps:
                yield Unit(
                    str(month.relative_to(self.root)), len(stamps), _ns(stamps[0]), _ns(stamps[-1])
                )

    async def tend(
        self, plugin: meridian.Plugin, window_days: int, past_window: str, now: datetime
    ) -> dict[str, int]:
        """Move each month past the window as `past_window` says, and say on
        the heartbeat what storage holds; what it came to."""
        done = {"archived": 0, "deleted": 0, "kept": 0, "refused": 0}
        if not self.granted:
            return done
        cut = _ns(now - timedelta(days=window_days))
        this_month = f"{RESPONSES}/{now.astimezone(UTC):%Y-%m}"
        for unit in list(self.units()):
            if unit.last_ns >= cut or unit.unit == this_month:
                continue
            if past_window not in ("archived", "deleted"):
                done["kept"] += 1
                continue
            move = plugin.archive_unit if past_window == "archived" else plugin.delete_unit
            try:
                await move(
                    RESPONSES,
                    unit.unit,
                    record_count=unit.records,
                    first_received_ns=unit.first_ns,
                    last_received_ns=unit.last_ns,
                )
                done[past_window] += 1
            except meridian.MeridianError as refused:
                log.warning("%s: %s refused, kept: %s", unit.unit, past_window, refused)
                done["refused"] += 1
        plugin.stored = [self.span()]
        return done

    def span(self) -> Any:
        """What storage holds of the kind, for the heartbeat."""
        from meridian.v1 import sidecar_pb2

        units = list(self.units())
        return sidecar_pb2.StoredSpan(
            record_kind=RESPONSES,
            record_count=sum(u.records for u in units),
            first_received_ns=units[0].first_ns if units else 0,
            last_received_ns=units[-1].last_ns if units else 0,
        )


def _received(name: str) -> datetime | None:
    try:
        return datetime.strptime(name.split("-", 1)[0], "%Y%m%dT%H%M%S%fZ").replace(tzinfo=UTC)
    except ValueError:
        return None
