"""The typed records the pages answer, for a person's page and an agent's
tool alike (contract v12; spec/a-deployment-serves-its-mcp): the Connection
tab is `read_connection`, the Datasets tab `read_datasets`, each answering
what its page shows, as data.

A `dgm`'s pages show its connection and its datasets, never a price
(plans/the-lake-prices-the-book, ruled 2026-10-03): prices are the reading
roles'. So neither record holds a rate; each says how the Board was reached
and what the plugin serves of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConnectionRead:
    """How the plugin reaches the Board's H.10, and how it last went."""

    #: `live` (the Board's site) or `synthetic` (the responses committed).
    mode: str
    #: Where it reads H.10 from.
    source: str
    #: The head's status: `ok`, `busy`, `warn` or `error`, and what it means.
    state: str
    said: str
    #: The last check of the current release, ISO 8601; empty before the first.
    checked_at: str
    #: Why the last check failed; empty when it did not.
    error: str
    #: The latest release read: the date it came out, and its first and last day.
    latest_release: str
    first_day: str
    last_day: str
    #: When the Board's server says the latest release's page was last
    #: modified, ISO 8601: its publication.
    published_at: str
    #: The next release expected: the Monday after the latest's last day, at
    #: 16:15 New York, or the next business day.
    next_release: str
    #: Pages asked of the Board since the plugin started.
    pages_read: int
    #: What the source needs and allows.
    key: str
    limits: str
    #: The Board's responses kept in the plugin's storage, and for how long.
    responses_kept: int
    kept_for: str


@dataclass(frozen=True)
class DatasetRead:
    """The dataset the catalogue declares, as the deployment sees it."""

    dataset: str
    vendor: str
    data_types: list[str]
    modes: list[str]
    cadence: str
    day: str
    history_days: int
    venue: str
    licence: str


@dataclass(frozen=True)
class CurrencyRead:
    """One currency H.10 publishes: how the Board names and quotes it, what
    its rate is a price of, and the deployment's instrument resolved for its
    subject, or why there is none."""

    code: str
    board_name: str
    quoted: str
    price_of: str
    instrument_id: str
    miss: str


@dataclass(frozen=True)
class WantRead:
    """A want the lake sent, and what the plugin did with it."""

    want_id: str
    asked: str
    subjects: int
    recorded: int
    declined: str
    at: str
    standing: bool


@dataclass(frozen=True)
class DatasetsRead:
    """What the plugin serves: its dataset, the currencies it covers, the
    standing wants it keeps current and the wants it answered lately."""

    dataset: DatasetRead
    #: What the source entitles the plugin to: no key, every currency.
    entitled_at_vendor: str
    currencies: list[CurrencyRead] = field(default_factory=list)
    #: The Board's rows the plugin could not name, each with how often seen.
    unconverted: list[str] = field(default_factory=list)
    standing: list[WantRead] = field(default_factory=list)
    wants: list[WantRead] = field(default_factory=list)
