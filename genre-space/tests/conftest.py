"""Shared test fixtures."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "discogs_sample.xml"


@pytest.fixture
def fixture_path() -> Path:
    return FIXTURE


@pytest.fixture
def load_datajs():
    """Return a helper that parses ``window.GENRE_DATA = {...};`` into a dict."""

    def _load(path: Path) -> dict:
        text = Path(path).read_text().strip()
        return json.loads(re.sub(r"^window\.GENRE_DATA = |;$", "", text))

    return _load
