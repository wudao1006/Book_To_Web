from __future__ import annotations

from pathlib import Path

import pytest

INTEGRATION_FILES = {
    "test_parser.py",
    "test_reader.py",
    "test_creator.py",
    "test_engineer.py",
    "test_director.py",
    "test_db.py",
    "test_error_contract.py",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = Path(str(item.fspath))
        file_name = path.name
        if "/tests/api/" in str(path):
            item.add_marker(pytest.mark.e2e_smoke)
            continue
        if file_name in INTEGRATION_FILES or "/tests/storage/" in str(path):
            item.add_marker(pytest.mark.integration)
            continue
        item.add_marker(pytest.mark.unit)
