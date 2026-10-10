"""The catalogue, from code, as the deployment approves it."""

from __future__ import annotations

from fed_h10.declaration import DAILY_DATASET, DECLARATION, mode_name


def test_one_daily_dataset_of_prices() -> None:
    assert [d.key for d in DECLARATION.catalogue] == ["daily"]
    assert list(DAILY_DATASET.data_types) == ["meridian.v1.Price"]
    assert [mode_name(m) for m in DAILY_DATASET.modes] == ["push", "pull"]
    assert DAILY_DATASET.day_time_zone == "America/New_York"
    assert DAILY_DATASET.day_end_minute == 720
    assert DAILY_DATASET.cadence == 7 * 86_400 and DAILY_DATASET.history == 3650
    assert not DAILY_DATASET.venue_id


def test_public_domain_is_not_one_persons_terms() -> None:
    licence = DAILY_DATASET.licence_default
    assert licence is not None
    assert licence.kept and licence.derived_use and licence.display
    assert not licence.personal_use and licence.retention_days == 0


def test_the_responses_are_kept_in_storage() -> None:
    assert DECLARATION.storage is not None
    assert [k.name for k in DECLARATION.storage.kinds] == ["responses"]
