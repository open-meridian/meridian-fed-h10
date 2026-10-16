"""The plugin's pages, under Manage alone: the data role's common pages
(spec/plugin-pages-follow-their-role), Connection and Datasets, in its
order, each also a read tool for agents on the deployment's MCP under the
role's names (`read_connection`, `read_datasets`). Each record is the
role's (`meridian.roles.data`), extended with H.10's fields; each template
is the role's, with H.10's nuance at its blocks only.

A data plugin shows its connectivity, its data subscriptions and how its
entitlements resolve, and no market data (the product owner, 2026-10-03:
"The data unit only cares for connectivity and data subscriptions and
entitlement resolution"). So:

- **Connection** (`/`): "Key" -- the mode (Live or Sample data), "No key
  needed", what the Board serves; "Limits and use" -- the Board states no
  limit, the pages asked, the last check and error; "Stream": it does not
  stream. Then H.10's: the source, the responses kept, and the release
  calendar (the latest release, when the Board published it, the next).
- **Datasets** (`/datasets`): "Served", "Wants" and "Subjects", then each
  currency H.10 publishes, how the Board quotes it, what its rate is the
  price of, and the deployment's instrument for its subject or why there is
  none -- one line a row, searched and paged by the kit's om-pager to fit
  one screen.

Neither shows an account's data, since the plugin reaches none, nor a rate:
prices are the reading roles' to show.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import meridian
from meridian.roles import data

from . import records
from .board import BASE, CURRENT, release_days
from .currencies import USD
from .declared import CADENCE, DAILY_DATASET, HISTORY, mode_name
from .feed import Feed, Status

TITLE = "Federal Reserve H.10"
#: The kit these pages are built on: 0.12.0's "Facts" and "Next step".
KIT = "0.12.0"

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
        return "error", "Not answering", status.error
    if status.error:
        return "warn", "Answering", status.error
    if status.release is None:
        return "busy", "Checking the Board", ""
    if misses:
        codes = ", ".join(sorted(c.code for c in misses))
        plural = "currency" if len(misses) == 1 else "currencies"
        return "warn", f"{len(misses)} {plural} not resolved", codes
    if status.mode == "synthetic":
        return "ok", "Sample data", ""
    return "ok", "Answering", ""


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
        mode="Sample data" if status.mode == "synthetic" else "Live",
        credentials=[],
        entitled_at_vendor=(
            "Every currency H.10 publishes: no key, public domain"
            if status.release is not None or status.mode == "synthetic"
            else ""
        ),
        limit=(
            "The Board states none; the plugin asks one page at a time, at most one every "
            "two seconds, and checks for a new release every hour"
        ),
        calls=status.fetches,
        last_call_at=_iso(status.checked_at),
        last_error=status.error,
        sessions=None,
        state=state,
        said=said,
        source=(
            "The responses recorded on 2026-10-10, committed with the plugin"
            if status.mode == "synthetic"
            else f"{BASE}{CURRENT}, and each past week's release by its date"
        ),
        checked_at=_iso(status.checked_at),
        latest_release=release.released.isoformat() if release else "",
        first_day=release.days[0].isoformat() if release else "",
        last_day=release.days[-1].isoformat() if release else "",
        published_at=_published(status.last_modified),
        next_release=next_release(status),
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


def _want(answered: Any, dataset: str) -> records.Want:
    declined = ", ".join(f"{n} {reason.replace('_', ' ')}" for reason, n in answered.declined)
    return records.Want(
        dataset=dataset,
        asked=answered.asked,
        subjects=answered.subjects,
        recorded=answered.recorded,
        declined=sum(n for _, n in answered.declined),
        state="Answered, standing" if answered.standing else "Answered",
        want_id=answered.want_id,
        at=_iso(answered.at),
        standing=answered.standing,
        declined_as=declined,
    )


def datasets_read(status: Status, feed: Feed | None) -> records.DatasetsRead:
    instance = feed.plugin.identity.instance_id if feed is not None else "fed-h10"
    entry = DAILY_DATASET
    dataset = f"{instance}:{entry.key}"
    currencies = sorted(status.currencies.values(), key=lambda c: (c.code != USD, c.code))
    priced = sum(1 for c in currencies if c.code != USD and c.per_dollar)
    answered = status.release is not None or status.mode == "synthetic"
    served = [
        records.Served(
            dataset=dataset,
            data="noon buying rates",
            arrives=", ".join(mode_name(m) for m in entry.modes),
            day="New York's, to noon",
            default_terms="kept; public domain",
            entitled_at_vendor="Yes: no key needed" if answered else "Not asked yet",
            recorded=status.recorded,
            declined=status.declined,
            last_recorded=_iso(status.last_recorded_at),
            licensed=dataset in status.licensed,
            cadence="weekly" if entry.cadence == CADENCE else f"{entry.cadence} s",
            history_days=HISTORY,
            venue="none: the New York Fed's certified rates, no venue's",
            restated=status.restated,
            unchanged=status.unchanged,
        )
    ]
    standing = [
        records.Want(
            dataset=dataset,
            asked="prices",
            subjects=n,
            state="Kept current",
            want_id=want_id,
            at=_iso(since),
            standing=True,
        )
        for want_id, (n, since) in status.standing.items()
    ]
    return records.DatasetsRead(
        served=served,
        wants=standing + [_want(a, dataset) for a in status.wants],
        reads_instruments=True,
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
    )


def figures(status: Status, feed: Feed | None) -> list[meridian.Figure]:
    """The data role's figures, in its order (`meridian.roles.data`); H.10
    reports none of its own."""
    state, said, why = _state(status)
    if status.mode == "synthetic" and state == "ok":
        connection: Any = "Sample data"
    elif said == "Not answering":
        connection = meridian.Figure("", said, state="error", why=why[:200])
    else:
        connection = meridian.Figure(
            "", "Answering", state="warn" if status.error else None, why=status.error[:200]
        )
    return data.figures(
        connection=connection,
        entitled_at_vendor="1 of 1 datasets",
        stream="Does not stream",
        last_recorded=status.last_recorded_at,
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
        "How this plugin reaches the Federal Reserve Board's H.10 release, as every data "
        "plugin's Connection answers it: the mode (Live or Sample data), no key needed, "
        "what the Board serves, its limits (none stated) and the pages asked, the last "
        "check and why it failed if it did; it does not stream. Then H.10's own: the "
        "source, the latest release and when the Board published it, the next expected, "
        "and how many responses are kept. No rate."
    ),
)
async def connection(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = connection_read(status, feed)
    return pages.answer("connection.html", read, detail=_state(status)[2])


@pages.page(
    DATASETS,
    "Datasets",
    levels="admin",
    answers=records.DatasetsRead,
    name="read_datasets",
    description=(
        "What this plugin serves the lake, as every data plugin's Datasets answers it: its "
        "one dataset as the catalogue declares it (weekly noon buying rates, New York's "
        "day ending at noon, public domain), whether a deployment admin has licensed it, "
        "what it recorded and declined; the standing wants it keeps current and the wants "
        "it answered. Then H.10's own: each currency H.10 publishes, how the Board quotes "
        "it, what its rate is the price of and the deployment's instrument for it or why "
        "there is none. No rate."
    ),
)
async def datasets(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = datasets_read(status, feed)
    # A browser's search narrows the currencies drawn, and it is drawn the
    # latest wants; a tool answers them all.
    query = request.query.get("q", "").strip()[:MOST_QUERY]
    shown = [c for c in read.currencies if matching(query, c.code, c.board_name)]
    drawn = read if request.tool_name else replace(read, wants=read.wants[:SHOWN_WANTS])
    return pages.answer(
        "datasets.html",
        drawn,
        query=query,
        shown=shown,
        state=_state(status),
        checked_at=_iso(status.checked_at),
        wants=len(read.wants),
    )
