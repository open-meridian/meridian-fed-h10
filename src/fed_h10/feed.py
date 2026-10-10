"""H.10 into the lake: each weekly release pushed when it appears, and any
past week recorded when the lake wants it (W10.4, W10.7).

**Push.** The current release is read at start and every hour. A release
not recorded yet in this process -- a new week, or the first read after a
start -- is recorded whole: every rate of its five days, in batches of at
most 500. A restart records the same week again, and the lake answers each
row unchanged, so nothing is kept between starts but the responses in
storage (decisions/028: a plugin's process holds nothing it cannot lose).

**Subjects.** Before anything is recorded, every currency the release names
is resolved to the deployment's cash instrument by its ISO 4217 code (W3.1);
one that does not resolve, or resolves to two records, is reported missing
(W3.2) with why, its rates left out until it does, and tried again on the
next release. The dollar's instrument is the subject of every rate quoted
per dollar; the euro's, the pound's, the Australian and the New Zealand
dollar's, of their own (convert.py).

**Wants.** The lake asks for what a reader read and it does not hold
(ObservationsWanted): a business date, a range, or the latest. The plugin
covers a subject it resolved itself -- the dollar's cash instrument, or a
currency quoted in dollars per unit -- and declines any other per subject,
`not_covered` (the lake never inverts a rate, and neither does the plugin).
For each day asked it reads the release that holds it, by the date that
release came out (board.release_days), and records that week's rates for the
subjects asked against the want. A day the Board has not published yet is
declined `source_silent`; one before the history the catalogue declares,
`beyond_history`. A standing want asks the subjects kept current, which the
weekly push does; it is listed until it is withdrawn (WantWithdrawn).
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import meridian
from meridian.plugin.v1 import operations_pb2 as ops

from .board import CURRENT, Board, BoardUnreachable, Fetched, dated, release_days, utc_now
from .convert import NEW_YORK, codes, quoted, to_prices
from .currencies import USD, code_of
from .declaration import DAILY, HISTORY
from .raw import RawStore
from .release import NotARelease, Release, last_modified_ns, parse

log = logging.getLogger("fed_h10")

#: The source this plugin names on what it reports missing.
SOURCE = "fed-h10"
#: The most rows one RecordPrices carries (the row's bound).
BATCH = 500
#: The most days one want is answered for: a quarter.
MOST_DAYS = 92
#: How many wants the Datasets page lists.
RECENT = 12


def _ns(moment: datetime) -> int:
    return int(moment.timestamp() * 1_000_000) * 1000


@dataclass
class Currency:
    """One currency as the plugin last saw it: how the Board names and quotes
    it, and the deployment's instrument for it, or why there is none."""

    code: str
    country: str
    name: str
    per_dollar: bool
    instrument_id: str = ""
    miss: str = ""


@dataclass(frozen=True)
class Answered:
    """What became of one want."""

    want_id: str
    asked: str
    subjects: int
    recorded: int
    declined: tuple[tuple[str, int], ...]
    at: datetime
    standing: bool = False


@dataclass
class Status:
    """What the plugin last did, for its pages; held in memory, lost on a
    restart and read again by the first check."""

    mode: str = "live"
    started_at: datetime | None = None
    checked_at: datetime | None = None
    answered_at: datetime | None = None
    error: str = ""
    release: Release | None = None
    release_key: str = ""
    last_modified: str = ""
    recorded: int = 0
    restated: int = 0
    unchanged: int = 0
    currencies: dict[str, Currency] = field(default_factory=dict)
    unconverted: dict[str, int] = field(default_factory=dict)
    wants: list[Answered] = field(default_factory=list)
    standing: dict[str, tuple[int, datetime]] = field(default_factory=dict)
    fetches: int = 0


@dataclass(frozen=True)
class Outcome:
    recorded: int = 0
    restated: int = 0
    unchanged: int = 0
    unresolved: tuple[str, ...] = ()

    def __add__(self, other: Outcome) -> Outcome:
        return Outcome(
            self.recorded + other.recorded,
            self.restated + other.restated,
            self.unchanged + other.unchanged,
            tuple(dict.fromkeys(self.unresolved + other.unresolved)),
        )


class Feed:
    """The plugin's work, on its typed operations -- `plugin` is the
    connected `meridian.Plugin`, or the suite's `Recorder` in its tests --
    reading the Board, resolving, recording, answering wants."""

    def __init__(
        self,
        plugin: Any,
        board: Board,
        raw: RawStore,
        now: Callable[[], datetime] = utc_now,
    ) -> None:
        self.plugin = plugin
        self.board = board
        self.raw = raw
        self.now = now
        self.status = Status(mode=board.mode, started_at=now())
        self._recorded_digest = ""

    @property
    def dataset(self) -> str:
        return f"{self.plugin.identity.instance_id}:{DAILY}"

    def use(self, board: Board) -> None:
        """Read from `board` from now on: synthetic mode turned on or off."""
        if board.mode != self.board.mode:
            self.board = board
            self.status.mode = board.mode
            self._recorded_digest = ""

    # ── Reading the Board ───────────────────────────────────────────────

    async def fetch(self, path: str) -> tuple[Fetched, str]:
        """A page of the Board's, kept before it is read: the response and
        its key in storage."""
        fetched = await self.board.get(path)
        self.status.fetches += 1
        return fetched, self.raw.keep(fetched)

    async def read_release(self, path: str) -> tuple[Release, Fetched, str] | None:
        """The release at `path`, or None where the Board answers none there
        (404); BoardUnreachable or NotARelease otherwise."""
        fetched, key = await self.fetch(path)
        if fetched.status == 404:
            return None
        if fetched.status != 200:
            raise BoardUnreachable(f"{fetched.url} answered {fetched.status}")
        return parse(fetched.text), fetched, key

    # ── Resolving ───────────────────────────────────────────────────────

    def _note_currencies(self, release: Release) -> None:
        for country, name, per_dollar in release.currencies:
            code = code_of(country, name)
            if code is None:
                label = f"{country} {name}"
                self.status.unconverted[label] = self.status.unconverted.get(label, 0) + 1
                continue
            held = self.status.currencies.get(code)
            if held is None:
                self.status.currencies[code] = Currency(code, country, name, per_dollar)
            else:
                held.per_dollar = per_dollar
        self.status.currencies.setdefault(USD, Currency(USD, "UNITED STATES", "DOLLAR", True))

    async def resolve(self, wanted: Iterable[str]) -> dict[str, str]:
        """Each ISO code's cash instrument, resolved now where not yet; a
        code that does not resolve reported missing, with why."""
        for code in wanted:
            held = self.status.currencies.setdefault(code, Currency(code, "", "", True))
            if held.instrument_id:
                continue
            identifier = ops.Identifier(scheme="iso4217", value=code)
            found = await self.plugin.resolve_identifier(
                identifiers=[identifier],
                stated_asset_class="cash",
                stated_currency=code,
                stated_description=f"{code} cash",
            )
            if found.found and found.instrument_id:
                held.instrument_id, held.miss = found.instrument_id, ""
                continue
            reason = found.miss_reason or ops.MISS_REASON_NOT_FOUND
            held.miss = ops.MissReason.Name(reason).removeprefix("MISS_REASON_").lower()
            await self.plugin.report_missing_instrument(
                source=SOURCE,
                asset_class="cash",
                identifiers=[identifier],
                reason=reason,
                observed_at_ns=_ns(self.now()),
            )
        return self.instruments()

    def instruments(self) -> dict[str, str]:
        return {c.code: c.instrument_id for c in self.status.currencies.values() if c.instrument_id}

    def covered(self) -> dict[str, str]:
        """Each subject the plugin can price, by its instrument: the dollar,
        and each currency quoted in dollars per unit."""
        out: dict[str, str] = {}
        for currency in self.status.currencies.values():
            if currency.instrument_id and (currency.code == USD or not currency.per_dollar):
                out[currency.instrument_id] = currency.code
        return out

    # ── Recording ───────────────────────────────────────────────────────

    async def record(
        self,
        release: Release,
        fetched: Fetched,
        key: str,
        *,
        want_id: str = "",
        days: Sequence[date] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> Outcome:
        """Record `release`'s rates -- on `days` and for `subjects` where
        given -- in batches, against `want_id` where given."""
        self._note_currencies(release)
        instruments = await self.resolve(codes(release))
        # The response these rates were first read from: a new copy of the
        # same rates would otherwise restate each one, unchanged (raw.py).
        first = self.raw.note_first(f"{release.released}:{digest_of(release)}", key)
        converted = to_prices(
            release,
            instruments,
            dataset=self.dataset,
            raw=self.plugin.raw_record(first),
            published_ns=last_modified_ns(fetched.last_modified),
            days=days,
        )
        prices = list(converted.prices)
        if subjects is not None:
            keep = set(subjects)
            prices = [
                p for p in prices if p.meta is not None and p.meta.subjects[0].entity_id in keep
            ]
        outcome = Outcome(unresolved=converted.unresolved)
        for start in range(0, len(prices), BATCH):
            done = await self.plugin.record_prices(
                prices=prices[start : start + BATCH], want_id=want_id
            )
            outcome = outcome + Outcome(done.recorded, done.restated, done.unchanged)
        self.status.recorded += outcome.recorded
        self.status.restated += outcome.restated
        self.status.unchanged += outcome.unchanged
        return outcome

    async def check(self) -> Outcome | None:
        """Read the current release; record it where this process has not
        recorded it as it reads now. None where nothing was recorded."""
        self.status.checked_at = self.now()
        try:
            read = await self.read_release(CURRENT)
        except (BoardUnreachable, NotARelease) as failed:
            self.status.error = str(failed)
            log.warning("the current release was not read: %s", failed)
            return None
        if read is None:
            self.status.error = f"the Board answered no current release at {CURRENT}"
            return None
        release, fetched, key = read
        self.status.error = ""
        self.status.release, self.status.release_key = release, key
        self.status.last_modified = fetched.last_modified
        digest = digest_of(release)
        if digest == self._recorded_digest:
            return None
        outcome = await self.record(release, fetched, key)
        if not outcome.unresolved:
            self._recorded_digest = digest
        log.info(
            "the release of %s: %d rates recorded, %d restated, %d unchanged%s",
            release.released,
            outcome.recorded,
            outcome.restated,
            outcome.unchanged,
            f"; not resolved: {', '.join(outcome.unresolved)}" if outcome.unresolved else "",
        )
        return outcome

    # ── Wants ───────────────────────────────────────────────────────────

    def _days(self, want: ops.ObservationsWantedEvent) -> list[date]:
        if want.business_date:
            return [date.fromisoformat(want.business_date)]
        if want.valid_from_ns or want.valid_until_ns:
            start = datetime.fromtimestamp(want.valid_from_ns // 10**9, NEW_YORK).date()
            end_ns = want.valid_until_ns or _ns(self.now())
            end = datetime.fromtimestamp(end_ns // 10**9, NEW_YORK).date()
            days = [start + timedelta(days=n) for n in range((end - start).days + 1)]
            return [d for d in days if d.weekday() < 5][-MOST_DAYS:]
        release = self.status.release
        return list(release.days) if release is not None else []

    async def _decline(
        self, want_id: str, subjects: Sequence[str], reason: str, declined: dict[str, int]
    ) -> None:
        if not subjects:
            return
        await self.plugin.decline_want(
            want_id=want_id,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            reason=reason,
        )
        declined[reason] = declined.get(reason, 0) + len(subjects)

    async def on_want(self, heard: meridian.Heard[ops.ObservationsWantedEvent]) -> None:
        """Record what the lake wants of the plugin's dataset, or decline it."""
        want = heard.message
        if want.dataset and want.dataset != self.dataset:
            return
        asked = [s.entity_id for s in want.subjects]
        declined: dict[str, int] = {}
        recorded = 0
        kinds = set(want.kinds)
        price = want.data_type in ("", "meridian.v1.Price")
        if not price or (kinds and ops.PRICE_KIND_CLOSE not in kinds):
            await self._decline(want.want_id, asked, "not_covered", declined)
            self._answered(want, asked, recorded, declined)
            return
        if not self.covered():
            await self.check()
        covered = self.covered()
        await self._decline(
            want.want_id, [s for s in asked if s not in covered], "not_covered", declined
        )
        mine = [s for s in asked if s in covered]
        if want.standing:
            self.status.standing[want.want_id] = (len(mine), self.now())
        if mine:
            recorded = await self._answer(want, mine, declined)
        self._answered(want, asked, recorded, declined)

    async def _answer(
        self, want: ops.ObservationsWantedEvent, mine: list[str], declined: dict[str, int]
    ) -> int:
        today = self.now().date()
        days = self._days(want)
        oldest = today - timedelta(days=HISTORY)
        if days and all(d < oldest for d in days):
            await self._decline(want.want_id, mine, "beyond_history", declined)
            return 0
        days = [d for d in days if d >= oldest]
        by_release: dict[date, list[date]] = {}
        for day in days:
            by_release.setdefault(release_days(day)[0], []).append(day)
        recorded = 0
        silent = False
        for monday, its_days in sorted(by_release.items()):
            read = await self._release_out_on(monday, today)
            if read is None:
                silent = True
                continue
            release, fetched, key = read
            done = await self.record(
                release, fetched, key, want_id=want.want_id, days=its_days, subjects=mine
            )
            recorded += done.recorded + done.restated + done.unchanged
        if recorded == 0 and (silent or days):
            await self._decline(want.want_id, mine, "source_silent", declined)
        return recorded

    async def _release_out_on(
        self, monday: date, today: date
    ) -> tuple[Release, Fetched, str] | None:
        """The release that came out on `monday` or the days after it, or
        None where none has (yet), or it could not be read."""
        current = self.status.release
        for day in [monday + timedelta(days=n) for n in range(4)]:
            if day > today:
                return None
            if current is not None and current.released == day and self.status.release_key:
                kept = self.raw.read(self.status.release_key)
                if kept is not None:
                    fetched = Fetched(
                        "/releases/h10/current/default.htm",
                        200,
                        kept["body"].encode(),
                        self.now(),
                        last_modified=kept.get("last_modified", ""),
                    )
                    return current, fetched, self.status.release_key
            try:
                read = await self.read_release(dated(day))
            except (BoardUnreachable, NotARelease) as failed:
                log.warning("the release of %s was not read: %s", day, failed)
                return None
            if read is not None:
                return read
        return None

    def _answered(
        self,
        want: ops.ObservationsWantedEvent,
        asked: Sequence[str],
        recorded: int,
        declined: dict[str, int],
    ) -> None:
        what = want.business_date or ("a range" if want.valid_from_ns else "the latest")
        self.status.answered_at = self.now()
        self.status.wants.insert(
            0,
            Answered(
                want.want_id,
                what,
                len(asked),
                recorded,
                tuple(sorted(declined.items())),
                self.now(),
                want.standing,
            ),
        )
        del self.status.wants[RECENT:]
        log.info(
            "want %s for %s: %d rows recorded, declined %s",
            want.want_id,
            what,
            recorded,
            dict(declined) or "none",
        )

    async def on_withdrawn(self, heard: meridian.Heard[ops.WantWithdrawnEvent]) -> None:
        """A standing want withdrawn: no longer listed as kept current."""
        if heard.message.dataset and heard.message.dataset != self.dataset:
            return
        self.status.standing.pop(heard.message.want_id, None)
        log.info("standing want %s withdrawn", heard.message.want_id)


def digest_of(release: Release) -> str:
    """What a release states, as a short digest: its rates and its days with
    no rate, never the page's other bytes, which change on every read."""
    stated = repr((release.released, release.rates, release.no_data)).encode()
    return hashlib.sha256(stated).hexdigest()[:16]


__all__ = ["Feed", "Outcome", "Status", "quoted"]
