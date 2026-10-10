"""The plugin's settings, declared to the SDK, and what it makes of them.

H.10 needs no key and no choice: the plugin reads the Board's public pages.
It declares one setting of its own, synthetic mode, a developer's setting
(shown and accepted only on a deployment installed for development): the
real responses committed under responses/ in place of the Board's site, for
the e2e and for trying the plugin offline. The name is SnapTrade's, reused
for the same thing.

The SDK declares the storage's two settings from the declaration's kind
(declaration.py): `responses_window_days`, how long a response is kept in
storage, ten years by default, and `responses_past_window`, what is done
with it after -- archived, kept or deleted. Their names are the SDK's, and
read here only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import meridian

from .raw import DEFAULT_WINDOW_DAYS, RESPONSES

SYNTHETIC = "synthetic"
WINDOW = f"{RESPONSES}_window_days"
PAST_WINDOW = f"{RESPONSES}_past_window"

DECLARED = (
    meridian.Setting(
        SYNTHETIC,
        bool,
        label="Synthetic mode",
        default=False,
        developer=True,
        description=(
            "Serve the Board's responses recorded on 2026-10-10, committed with the plugin, "
            "instead of reading the Board's site: the release of 5 October 2026 as the "
            "current one, and the weeks it holds."
        ),
    ),
)


@dataclass(frozen=True)
class Config:
    synthetic: bool = False
    window_days: int = DEFAULT_WINDOW_DAYS
    past_window: str = "kept"


def config_from(values: Mapping[str, object]) -> Config:
    """The configuration a delivery of the settings says."""
    window = values.get(WINDOW)
    past = values.get(PAST_WINDOW)
    return Config(
        synthetic=values.get(SYNTHETIC) is True,
        window_days=window if isinstance(window, int) and window > 0 else DEFAULT_WINDOW_DAYS,
        past_window=past if isinstance(past, str) and past else "kept",
    )
