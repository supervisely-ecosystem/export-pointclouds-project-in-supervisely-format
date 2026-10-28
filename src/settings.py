"""Export options from the modal window, parsed once at startup."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

import supervisely as sly

_TRUE = {"1", "true", "yes", "on", "y", "t"}
_FALSE = {"0", "false", "no", "off", "n", "f"}


@dataclass(frozen=True)
class Settings:
    download_items: bool  # False: annotations (and photo context) only

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> Settings:
        raw = env.get("modal.state.items")
        if raw is None:
            sly.logger.warning("Option 'items' is not set: point clouds are downloaded with annotations")
            return cls(download_items=True)
        return cls(download_items=_parse_bool(raw))


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ValueError(f"modal.state.items must be True or False, got {value!r}")
