"""The pages as synthetic mode shows them, each printed as one HTML file:
for looking at them without a deployment.

    python -m fed_h10.preview connection > preview/connection.html
    python -m fed_h10.preview datasets > preview/datasets.html

The plugin's work runs on the SDK's suite recorder in place of a sidecar --
every currency resolved to an instrument the recorder names, every batch
recorded -- against the responses committed under responses/, at 11:00 UTC
on 10 October 2026: the release of 5 October read, a want for 25 September
answered from the week before's, one for 8 October declined (not published
yet), and a standing want kept current. Each page links the kit where the
dashboard serves it, /.meridian/ui/<version>/: served beside the kit it is
styled (meridian-ui's `make serve`, or `make preview SHOTS=...`, which checks
each in a browser); opened on its own it is the page without the kit,
unstyled, which works too.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, date, datetime

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.suites import Recorder
from meridian.testing import PageClient

from .board import SyntheticBoard
from .feed import Feed
from .page import CONNECTION, DATASETS, hold, pages
from .raw import RawStore

AT = datetime(2026, 10, 10, 11, 0, tzinfo=UTC)
PAGES = {"connection": CONNECTION, "datasets": DATASETS}


def _want(want_id: str, subject: str, day: str = "", standing: bool = False) -> Heard:  # type: ignore[type-arg]
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset="fed-h10:daily",
            data_type="meridian.v1.Price",
            subjects=[ops.SubjectRef(entity_id=subject)],
            kinds=[ops.PRICE_KIND_CLOSE],
            business_date=day,
            standing=standing,
        ),
    )


async def synthetic_feed() -> Feed:
    """A feed as synthetic mode leaves it, on the recorder."""
    feed = Feed(Recorder("fed-h10"), SyntheticBoard(lambda: AT), RawStore(), now=lambda: AT)
    await feed.check()
    usd = feed.status.currencies["USD"].instrument_id
    await feed.on_want(_want("want-0925", usd, date(2026, 9, 25).isoformat()))
    await feed.on_want(_want("want-1008", usd, date(2026, 10, 8).isoformat()))
    await feed.on_want(_want("want-standing", usd, standing=True))
    return feed


def render(page: str) -> str:
    feed = asyncio.run(synthetic_feed())
    hold(feed)
    answer = PageClient(pages).get(PAGES[page], "admin")
    if answer.status != 200:
        raise SystemExit(f"{page} answered {answer.status}: {answer.text[:200]}")
    return answer.text


def main() -> None:
    page = sys.argv[1] if len(sys.argv) > 1 else "connection"
    if page not in PAGES:
        raise SystemExit(f"no page {page!r}: {', '.join(PAGES)}")
    sys.stdout.write(render(page))


if __name__ == "__main__":
    main()
