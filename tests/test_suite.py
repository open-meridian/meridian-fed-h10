"""The `dgm` suite (meridian.suites, contract v18), each case H.10 presents
mapped to the plugin's own conversion of the Board's recorded responses.

H.10 presents eight of the suite's thirteen cases. Five ask for what the
Board never states, and the plugin has no conversion for them, so they have
no producer here:

- `a-daily-bar`: H.10 is one rate a day, no open, high, low or volume;
- `a-stablecoin-quote`: H.10 quotes currencies against the US dollar, no
  crypto asset and no stablecoin;
- `a-venue-resolved` and `a-venue-not-held`: the rates are the New York
  Fed's certified noon buying rates, no venue's, so the dataset declares no
  venue and no row names one.

The SDK's runner lets only a closed-list case be "not presented", and none
of these is one, so by the runner's rule the plugin is short of the suite
and not verified: the test below holds it to exactly the eight it presents
and to those five failing for want of a producer, never for a wrong answer.
That the suite has no way for a source to say it states no bars, no tokens,
no venue and no security is a question for the suite's owner (meridian-design
matrix/boundaries/suites/dgm.yaml), raised with this build.

`the-forming-day-restated`: H.10's day is never forming once published, but
the Board does correct a published rate; the plugin records the corrected
rate under the same row key, which the lake keeps as the row's next version.
That is the case's outcome, and the producer gives the plugin a correction.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.suites import Recorder, names, run

from fed_h10.board import CURRENT, Fetched
from fed_h10.feed import Feed
from fed_h10.raw import RawStore

from conftest import AT, DATASET, response, want

NOT_PRESENTED = {
    "a-daily-bar": "H.10 states one rate a day: no open, high, low or volume",
    "a-stablecoin-quote": "H.10 quotes currencies against the US dollar: no token",
    "a-venue-resolved": "H.10's rates are the New York Fed's, no venue's",
    "a-venue-not-held": "H.10's rates are the New York Fed's, no venue's",
    "a-subject-another-source-resolved": "H.10 rates currencies: no security another source named",
}


class Corrected:
    """The Board's site, the current release read twice: as received, then
    with one rate corrected."""

    mode = "synthetic"

    def __init__(self) -> None:
        self.reads = 0

    async def get(self, path: str) -> Fetched:
        self.reads += 1
        page = response("20261005")
        if self.reads > 1:
            page = page.replace("0.8293", "0.8294")
        return Fetched(path, 200, page.encode(), AT, last_modified="Mon, 05 Oct 2026 20:15:04 GMT")


def _resolving(recorder: Recorder, ambiguous: str = "") -> None:
    """Each ISO code resolved to `LCL-<code>`; `ambiguous` to two records."""

    def answer(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
        code = params.identifiers[0].value
        if code == ambiguous:
            return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_AMBIGUOUS)
        return ops.ResolveIdentifierResult(found=True, instrument_id=f"LCL-{code}")

    recorder.answer("ResolveIdentifier", answer)


def producers(tmp: Path) -> dict[str, Callable[[Recorder], Awaitable[None]]]:
    from fed_h10.board import SyntheticBoard

    def work(recorder: Recorder, board: Any = None) -> Feed:
        return Feed(recorder, board or SyntheticBoard(lambda: AT), RawStore(tmp), now=lambda: AT)

    async def a_release_read(recorder: Recorder) -> None:
        _resolving(recorder)
        await work(recorder).check()

    async def the_rate_corrected(recorder: Recorder) -> None:
        _resolving(recorder)
        feed = work(recorder, Corrected())
        await feed.check()
        await feed.check()
        keys = [[p.meta.row_key for p in b.prices] for b in recorder.on("RecordPrices")]
        assert len(keys) == 2 and keys[0] == keys[1]

    async def two_records(recorder: Recorder) -> None:
        _resolving(recorder, ambiguous="GBP")
        await work(recorder).check()

    def wanted(message: Any) -> Callable[[Recorder], Awaitable[None]]:
        async def produce(recorder: Recorder) -> None:
            _resolving(recorder)
            feed = work(recorder)
            recorder.answer("ObservationsWanted", lambda _: message)
            await recorder.receive(observations_wanted=feed.on_want)

        return produce

    async def withdrawn(recorder: Recorder) -> None:
        _resolving(recorder)
        feed = work(recorder)
        recorder.answer(
            "WantWithdrawn",
            lambda _: ops.WantWithdrawnEvent(want_id="w-standing", dataset=DATASET),
        )
        await recorder.receive(want_withdrawn=feed.on_withdrawn)

    return {
        "a-daily-close": a_release_read,
        "the-forming-day-restated": the_rate_corrected,
        "an-exact-price": a_release_read,
        "an-fx-rate": a_release_read,
        "an-asset-that-does-not-resolve": two_records,
        "a-want-recorded-against": wanted(want("w-1", ["LCL-USD"], day="2026-09-25").message),
        "a-subject-declined": wanted(want("w-2", ["LCL-CHF"], day="2026-10-02").message),
        "a-standing-want-withdrawn": withdrawn,
    }


def test_the_dgm_suite(tmp_path: Path) -> None:
    report = run("dgm", producers(tmp_path), instance_id="fed-h10")
    presented = [name for name in names("dgm") if name not in NOT_PRESENTED]
    assert report.passed_cases == presented, report.failures
    assert set(report.failures) == set(NOT_PRESENTED)
    assert all(why.startswith("no producer") for why in report.failures.values()), report.failures


def test_an_exact_price_never_passes_through_a_float(tmp_path: Path) -> None:
    recorder = Recorder("fed-h10")
    _resolving(recorder)
    import asyncio

    from fed_h10.board import SyntheticBoard

    feed = Feed(recorder, SyntheticBoard(lambda: AT), RawStore(tmp_path), now=lambda: AT)
    asyncio.run(feed.check())
    from meridian.operations import as_decimal

    amounts = {
        p.meta.row_key: str(as_decimal(p.price.amount))
        for p in recorder.on("RecordPrices")[0].prices
    }
    assert amounts["KRW:2026-09-28"] == "1359.7800"
    assert amounts["CHF:2026-10-02"] == "0.8293"
    assert CURRENT.endswith("default.htm")
