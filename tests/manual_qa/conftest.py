from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path() -> Path:
    base_dir = Path("artifacts") / "manual_qa_test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    yield Path(tempfile.mkdtemp(dir=base_dir))
