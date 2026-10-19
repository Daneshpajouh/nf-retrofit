from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def data_dir() -> Path:
    return ROOT / "tests" / "data"
