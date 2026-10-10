"""The two pages under Manage, and their read tools: what each shows, to
whom, and that a tool answers what its page shows."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from meridian.testing import PageClient

from fed_h10 import page as page_module
from fed_h10.page import CONNECTION, DATASETS, hold, pages

from conftest import feed, want


@pytest.fixture
def client(tmp_path: Path) -> PageClient:
    work = feed(tmp_path)

    async def run() -> None:
        await work.check()
        usd = work.status.currencies["USD"].instrument_id
        await work.on_want(want("w-0925", [usd], day="2026-09-25"))
        await work.on_want(want("w-standing", [usd], standing=True))

    asyncio.run(run())
    hold(work)
    return PageClient(pages)


def test_each_page_is_managed_alone(client: PageClient) -> None:
    served = {(r.page.path, r.level): r.response.status for r in client.every_page()}
    assert served == {
        (CONNECTION, "admin"): 200,
        (CONNECTION, "write"): 403,
        (CONNECTION, "read"): 403,
        (DATASETS, "admin"): 200,
        (DATASETS, "write"): 403,
        (DATASETS, "read"): 403,
    }
    # No rate on any page: the Board's figures are the reading roles' to show.
    client.assert_no_account_data("0.8293", "1.1259", "1359.7800")


def test_connection_says_how_the_board_is_reached(client: PageClient) -> None:
    text = client.get(CONNECTION, "admin").text
    assert 'state="ok"' in text and "H.10 read" in text
    assert "Synthetic mode" in text
    assert "Mon 05 Oct" in text  # the latest release
    assert "Mon 12 Oct" in text  # the next one expected
    assert "public domain" in text
    assert 'href="/.meridian/ui/0.10.0/meridian.css"' in text


def test_datasets_lists_the_dataset_and_every_currency(client: PageClient) -> None:
    text = client.get(DATASETS, "admin").text
    assert "fed-h10:daily" in text and "Public domain" in text
    assert text.count("<tr data-code=") == 24
    assert "<om-pager>" in text
    assert "1 standing" in text and "2026-09-25: 19 recorded" in text
    # No rate: prices are the reading roles' to show.
    assert "0.8293" not in text and "1.1259" not in text


def test_the_tools_answer_what_the_pages_show(client: PageClient) -> None:
    names = {t.name for t in pages.tools}
    assert names == {"read_connection", "read_datasets"}
    connection = client.call_tool("read_connection")
    assert connection.outcome == "unchanged", connection.json
    assert connection.data["latest_release"] == "2026-10-05"
    assert connection.data["first_day"] == "2026-09-28" and connection.data["mode"] == "synthetic"
    assert connection.data["next_release"] == "2026-10-12"
    assert connection.data["published_at"] == "2026-10-05T20:15:04+00:00"
    datasets = client.call_tool("read_datasets")
    assert datasets.outcome == "unchanged"
    data = datasets.data
    assert data["dataset"]["dataset"] == "fed-h10:daily"
    assert data["dataset"]["modes"] == ["push", "pull"]
    codes = [c["code"] for c in data["currencies"]]
    assert codes[0] == "USD" and len(codes) == 24
    euro = next(c for c in data["currencies"] if c["code"] == "EUR")
    assert euro["quoted"] == "US dollars per EUR" and euro["price_of"] == "EUR in USD"
    page = client.get(DATASETS, "admin").text
    assert all(c["instrument_id"] in page for c in data["currencies"])
    assert [w["want_id"] for w in data["standing"]] == ["w-standing"]


def test_before_the_first_check(tmp_path: Path) -> None:
    page_module._held.clear()
    text = PageClient(pages).get(CONNECTION, "admin").text
    assert "Checking the Board" in text
    empty = PageClient(pages).get(DATASETS, "admin").text
    assert "No release read yet" in empty


def test_the_board_not_reached(tmp_path: Path) -> None:
    work = feed(tmp_path)
    work.status.error = (
        "https://www.federalreserve.gov/releases/h10/current/default.htm: ConnectionRefusedError"
    )
    hold(work)
    text = PageClient(pages).get(CONNECTION, "admin").text
    assert 'state="error"' in text and "The Board was not reached" in text
    assert "ConnectionRefusedError" in text
