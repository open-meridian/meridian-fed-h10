"""Shared stand-ins: the Board's recorded responses, a fixed clock, and the
lake's wants as the sidecar delivers them."""

from __future__ import annotations

import gzip
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder

from fed_h10.board import SyntheticBoard
from fed_h10.feed import Feed
from fed_h10.raw import RawStore

#: When the responses were recorded, and the clock the tests run at.
AT = datetime(2026, 10, 10, 11, 0, tzinfo=UTC)
INSTANCE = "fed-h10"
DATASET = f"{INSTANCE}:daily"


def response(name: str) -> str:
    """A recorded response's page, by its file's name under responses/."""
    held = resources.files("fed_h10").joinpath("responses", f"{name}.htm.gz")
    return gzip.decompress(held.read_bytes()).decode()


def feed(tmp: Path, plugin: Recorder | None = None, at: datetime = AT) -> Feed:
    """The plugin's work on the suite's recorder and the recorded responses,
    at `at`."""
    return Feed(
        plugin or Recorder(INSTANCE), SyntheticBoard(lambda: at), RawStore(tmp), now=lambda: at
    )


def want(
    want_id: str,
    subjects: list[str],
    *,
    day: str = "",
    standing: bool = False,
    kinds: tuple[Any, ...] = (ops.PRICE_KIND_CLOSE,),
    data_type: str = "meridian.v1.Price",
    dataset: str = DATASET,
) -> Heard:  # type: ignore[type-arg]
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset=dataset,
            data_type=data_type,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            kinds=list(kinds),
            business_date=day,
            standing=standing,
        ),
    )
