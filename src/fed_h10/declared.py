"""What this version declares beside its role, `data` (W8.1, W4.1; the
catalogue from contract v18), built from code and used twice: `__main__`
registers with it, and `meridian plugin upload` reads it from the built image
(pyproject.toml's `[tool.meridian] declaration`).

**The catalogue: one dataset, `daily`** (the plan's Q21: a daily dataset per
plugin; H.10 has no live one). The Board's H.10, a week's noon buying rates
pushed when it is released, and any past week pulled when the lake wants it:

- `vendor` the Board; no aggregator, since the plugin reads the Board itself;
- `data_types` prices alone: an FX rate is the price of a currency's cash
  instrument (convert.py);
- `modes` `push` (each weekly release recorded when it appears) and `pull`
  (a past week, on a want);
- `cadence` a week, in seconds: the Board releases weekly;
- `history` ten years, in days: every release since 2013 is in the layout
  the plugin reads (release.py);
- its day New York's, ending at noon (`America/New_York`, 720): the rates
  are noon buying rates, so a rate's date is its business date;
- no venue: the rates are the New York Fed's certified rates, no venue's;
- the licence the Board's terms give: public domain, so kept, with no limit
  on retention, derived use or display, and not one person's terms
  (`personal_use` false). A deployment's licence confirms or replaces it on
  the Data sources page; the plugin says nothing of whether a deployment
  meets anyone's terms.

**Storage:** the Board's responses (raw.py), archivable, ten years by
default.
"""

from __future__ import annotations

from meridian import DatasetDeclaration, DatasetLicence
from meridian.declaration import RecordKind
from meridian.plugin.v1 import operations_pb2 as ops

from .convert import DAY_END_MINUTE, DAY_TIME_ZONE
from .raw import DEFAULT_WINDOW_DAYS, RESPONSES

#: The dataset's key: its rows name `<instance>:daily`.
DAILY = "daily"
VENDOR = "Board of Governors of the Federal Reserve System"
#: A week, in seconds.
CADENCE = 7 * 86_400
#: Ten years, in days.
HISTORY = 3650

DAILY_DATASET = DatasetDeclaration(
    key=DAILY,
    vendor=VENDOR,
    data_types=["meridian.v1.Price"],
    modes=["push", "pull"],
    cadence=CADENCE,
    history=HISTORY,
    licence_default=DatasetLicence(kept=True, derived_use=True, display=True),
    day_time_zone=DAY_TIME_ZONE,
    day_end_minute=DAY_END_MINUTE,
)

RESPONSES_KIND = RecordKind(RESPONSES, "Raw responses", window_days=DEFAULT_WINDOW_DAYS)


def mode_name(mode: int | str) -> str:
    """A mode as the catalogue's words say it (`push`), however it is held."""
    if isinstance(mode, str):
        return mode
    return str(ops.ObservationMode.Name(mode)).removeprefix("OBSERVATION_MODE_").lower()
