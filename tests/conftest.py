import pytest
from pathlib import Path


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Return a temporary directory suitable for use as an ICM workspace."""
    return tmp_path
