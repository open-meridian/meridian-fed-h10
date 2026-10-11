"""The typed records the pages answer, for a person's page and an agent's
tool alike (contract v12; spec/a-deployment-serves-its-mcp): the data role's
common records (`meridian.roles.data`, spec/plugin-pages-follow-their-role),
each extended with H.10's own fields. The Connection tab is
`read_connection`, the Datasets tab `read_datasets`, each answering what its
page shows, as data, under the role's names.

A data plugin's pages show its connection and its datasets, never a price
(plans/the-lake-prices-the-book, ruled 2026-10-03): prices are the reading
roles'. So neither record holds a rate; each says how the Board was reached
and what the plugin serves of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meridian.roles import data


@dataclass(frozen=True)
class ConnectionRead(data.ConnectionRead):
    """Connection's common fields, then H.10's: the head's status and what it
    means, the source read, the last check, the release calendar -- the
    latest release, its first and last day, when the Board published it, the
    next expected -- and the responses kept."""

    #: The head's status: `ok`, `busy`, `warn` or `error`, and what it means.
    state: str = ""
    said: str = ""
    source: str = ""
    checked_at: str = ""
    latest_release: str = ""
    first_day: str = ""
    last_day: str = ""
    #: When the Board's server says the latest release's page was last
    #: modified, ISO 8601: its publication.
    published_at: str = ""
    #: The next release expected: the Monday after the latest's last day, at
    #: 16:15 New York, or the next business day.
    next_release: str = ""
    responses_kept: int = 0
    kept_for: str = ""


@dataclass(frozen=True)
class Served(data.Served):
    """The one dataset as "Served" shows it, then H.10's: its cadence, its
    history in days, its venue (none: the New York Fed's certified rates),
    and what it restated and kept unchanged since the plugin started."""

    cadence: str = ""
    history_days: int = 0
    venue: str = ""
    restated: int = 0
    unchanged: int = 0


@dataclass(frozen=True)
class Want(data.Want):
    """One want as "Wants" shows it, then H.10's: its ID, when, whether it
    stands, and what it declined, by reason."""

    want_id: str = ""
    at: str = ""
    standing: bool = False
    declined_as: str = ""


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
class DatasetsRead(data.DatasetsRead):
    """Datasets' common fields, then H.10's: each currency it publishes, and
    the Board's rows it could not name. Its rows are H.10's, each extending
    the role's."""

    served: list[Served] = field(default_factory=list)  # type: ignore[assignment]
    wants: list[Want] = field(default_factory=list)  # type: ignore[assignment]
    currencies: list[CurrencyRead] = field(default_factory=list)
    #: The Board's rows the plugin could not name, each with how often seen.
    unconverted: list[str] = field(default_factory=list)
