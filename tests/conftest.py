"""Shared pytest setup.

Integration tests (@pytest.mark.db) DROP and reload tables, so they must never touch the real
database. They run only against TEST_DATABASE_URL and are skipped when it is not set.
"""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Must run before `src.config` is imported anywhere: point the app at the test database.
load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["READONLY_DATABASE_URL"] = ""

FIXTURES = Path(__file__).parent / "fixtures"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests cleanly if no test database is configured."""
    if TEST_DATABASE_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def loaded_db() -> None:
    """Create schemas and load every fixture dataset into the TEST database."""
    from scripts import check_setup
    from scripts.load_all import LOADERS

    check_setup.main()
    for name, loader in LOADERS.items():
        loader.main(FIXTURES / name)
