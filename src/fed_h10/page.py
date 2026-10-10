"""The plugin's pages, under Manage alone: Connection and Datasets, each
also a read tool for agents on the deployment's MCP (`read_connection`,
`read_datasets`; plans/the-lake-prices-the-book, "v18's names").

A `dgm` shows its connectivity, its data subscriptions and how its
entitlements resolve, and no market data (the product owner, 2026-10-03:
"The data unit only cares for connectivity and data subscriptions and
entitlement resolution"). So:

- **Connection** (`/`): how the plugin reaches the Board's H.10 -- the site
  or synthetic mode, the last check, the latest release and when the Board
  published it, the next one expected, what the source needs (no key) and
  allows, and the responses kept.
- **Datasets** (`/datasets`): the one dataset the catalogue declares, as the
  deployment's Data sources page lists it; the standing wants it keeps
  current and the last want answered; and each currency H.10 publishes, how
  the Board quotes it, what its rate is the price of, and the deployment's
  instrument for its subject or why there is none -- one line a row, paged
  by the kit's om-pager to fit one screen.

Neither shows an account's data, since the plugin reaches none, nor a rate:
prices are the reading roles' to show. Each page is a view here and a
template under templates/ on the SDK's base, which links the kit the
dashboard serves; without the kit each is a plain table, and works.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import meridian

from . import records
from .board import BASE, CURRENT, release_days
from .currencies import USD
from .declaration import CADENCE, DAILY_DATASET, HISTORY, VENDOR, mode_name
from .feed import Feed, Status

TITLE = "Federal Reserve H.10"
# The kit these pages were built against: 0.10.0, every page one screen (one
# line a row, row-detail, om-pager).
KIT = "0.10.0"

pages = meridian.Pages(TITLE, templates=Path(__file__).parent / "templates", kit=KIT)

CONNECTION = "/"
DATASETS = "/datasets"

#: The longest search the Datasets tab reads.
MOST_QUERY = 100
#: How many wants the Datasets tab lists; read_datasets answers every one held.
SHOWN_WANTS = 3

_held: dict[str, Feed] = {}


def hold(feed: Feed) -> None:
    """The feed the pages read, once the plugin has registered."""
    _held["feed"] = feed


def _status() -> tuple[Status, Feed | None]:
    feed = _held.get("feed")
    return (feed.status if feed is not None else Status(), feed)


def _iso(moment: datetime | None) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds") if moment else ""


def _published(last_modified: str) -> str:
    try:
        moment = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
    except ValueError:
        return ""
    return moment.replace(tzinfo=UTC).isoformat(timespec="seconds")


def next_release(status: Status) -> str:
    """The day the next release is expected: the Monday after the latest's
    last day (or the next business day, when that is a holiday)."""
    if status.release is None:
        return ""
    return release_days(status.release.days[-1] + timedelta(days=7))[0].isoformat()


def _state(status: Status) -> tuple[str, str, str]:
    """The head's status: its state, what it means, and its detail."""
    misses = [c for c in status.currencies.values() if c.miss]
    if status.error and status.release is None:
        return "error", "The Board was not reached", status.error
    if status.error:
        return "warn", "The last check failed", status.error
    if status.release is None:
        return "busy", "Checking the Board", ""
    if misses:
        codes = ", ".join(sorted(c.code for c in misses))
        plural = "currency" if len(misses) == 1 else "currencies"
        return "warn", f"{len(misses)} {plural} not resolved", codes
    return "ok", "H.10 read", ""


def connection_read(status: Status, feed: Feed | None) -> records.ConnectionRead:
    state, said, _ = _state(status)
    release = status.release
    kept = feed.raw.keys() if feed is not None else []
    window = ""
    if feed is not None and feed.raw.granted:
        window = "in the storage the deployment grants, as its responses settings say"
    elif feed is not None:
        window = "in a directory of the plugin's own: this deployment grants no storage"
    return records.ConnectionRead(
        mode=status.mode,
        source=(
            "The responses recorded on 2026-10-10, committed with the plugin"
            if status.mode == "synthetic"
            else f"{BASE}{CURRENT}, and each past week's release by its date"
        ),
        state=state,
        said=said,
        checked_at=_iso(status.checked_at),
        error=status.error,
        latest_release=release.released.isoformat() if release else "",
        first_day=release.days[0].isoformat() if release else "",
        last_day=release.days[-1].isoformat() if release else "",
        published_at=_published(status.last_modified),
        next_release=next_release(status),
        pages_read=status.fetches,
        key="None: H.10 is public domain, and the Board asks for no key.",
        limits=(
            "The Board states no rate limit. The plugin asks one page at a time, at most "
            "one every two seconds, and checks for a new release every hour."
        ),
        responses_kept=len(kept),
        kept_for=window,
    )


def _quoted(per_dollar: bool, code: str, priced: int) -> tuple[str, str]:
    """How the Board quotes a currency, and what its rate is the price of."""
    if code == USD:
        return "the base of each rate per dollar", f"USD in {priced} currencies"
    if per_dollar:
        return f"{code} per US dollar", f"USD in {code}"
    return f"US dollars per {code}", f"{code} in USD"


def _want(answered: Any) -> records.WantRead:
    declined = ", ".join(f"{n} {reason.replace('_', ' ')}" for reason, n in answered.declined)
    return records.WantRead(
        want_id=answered.want_id,
        asked=answered.asked,
        subjects=answered.subjects,
        recorded=answered.recorded,
        declined=declined,
        at=_iso(answered.at),
        standing=answered.standing,
    )


def datasets_read(status: Status, feed: Feed | None) -> records.DatasetsRead:
    instance = feed.plugin.identity.instance_id if feed is not None else "fed-h10"
    entry = DAILY_DATASET
    currencies = sorted(status.currencies.values(), key=lambda c: (c.code != USD, c.code))
    priced = sum(1 for c in currencies if c.code != USD and c.per_dollar)
    return records.DatasetsRead(
        dataset=records.DatasetRead(
            dataset=f"{instance}:{entry.key}",
            vendor=VENDOR,
            data_types=list(entry.data_types),
            modes=[mode_name(m) for m in entry.modes],
            cadence="weekly" if entry.cadence == CADENCE else f"{entry.cadence} s",
            day="New York's, ending at noon (America/New_York, 12:00)",
            history_days=HISTORY,
            venue="None: the New York Fed's certified rates, no venue's",
            licence=(
                "Public domain: kept, with no limit on retention, derived use or display; "
                "not one person's terms"
            ),
        ),
        entitled_at_vendor="No key: every currency H.10 publishes is served.",
        currencies=[
            records.CurrencyRead(
                code=c.code,
                board_name=", ".join(part for part in (c.country, c.name) if part),
                quoted=_quoted(c.per_dollar, c.code, priced)[0],
                price_of=_quoted(c.per_dollar, c.code, priced)[1],
                instrument_id=c.instrument_id,
                miss=c.miss.replace("_", " "),
            )
            for c in currencies
        ],
        unconverted=[f"{name} ({n} reads)" for name, n in sorted(status.unconverted.items())],
        standing=[
            records.WantRead(want_id, "kept current", n, 0, "", _iso(since), True)
            for want_id, (n, since) in status.standing.items()
        ],
        wants=[_want(a) for a in status.wants],
    )


def _moment(value: str) -> str:
    """An ISO moment as a person reads it, to the minute in UTC."""
    if not value:
        return ""
    if len(value) == 10:
        return value
    return datetime.fromisoformat(value).astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _day(value: str) -> str:
    return date.fromisoformat(value).strftime("%a %d %b") if value else ""


def matching(query: str, *texts: str) -> bool:
    """Whether every word of a search is in one of `texts`, case aside."""
    words = query.lower().split()
    held = " ".join(texts).lower()
    return all(word in held for word in words)


pages.environment.filters["moment"] = _moment
pages.environment.filters["day"] = _day


@pages.page(
    CONNECTION,
    "Connection",
    levels="admin",
    answers=records.ConnectionRead,
    name="read_connection",
    description=(
        "How this plugin reaches the Federal Reserve Board's H.10 release: the Board's "
        "site or synthetic mode, the last check and why it failed if it did, the latest "
        "release and when the Board published it, the next expected, what the source "
        "needs (no key) and allows, and how many responses are kept. No rate."
    ),
)
async def connection(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    data = connection_read(status, feed)
    return pages.answer("connection.html", data, detail=_state(status)[2])


@pages.page(
    DATASETS,
    "Datasets",
    levels="admin",
    answers=records.DatasetsRead,
    name="read_datasets",
    description=(
        "What this plugin serves the lake: its one dataset as the catalogue declares it "
        "(weekly noon buying rates, New York's day ending at noon, public domain), each "
        "currency H.10 publishes with how the Board quotes it, what its rate is the price "
        "of and the deployment's instrument for it or why there is none, the standing "
        "wants it keeps current and the wants it answered lately. No rate."
    ),
)
async def datasets(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    data = datasets_read(status, feed)
    # A browser's search narrows the rows drawn; a tool answers them all.
    query = request.query.get("q", "").strip()[:MOST_QUERY]
    shown = [c for c in data.currencies if matching(query, c.code, c.board_name)]
    return pages.answer(
        "datasets.html",
        data,
        query=query,
        shown=shown,
        state=_state(status),
        checked_at=_iso(status.checked_at),
        shown_wants=data.wants[:SHOWN_WANTS],
    )
