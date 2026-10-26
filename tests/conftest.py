import pytest
import os
import tempfile
from src.db import init_db, DEFAULT_DB_PATH
from data.generate_synthetic_aml_data import generate_synthetic_data

@pytest.fixture(scope="session")
def seeded_db():
    """Provides path to the seeded database."""
    if not os.path.exists(DEFAULT_DB_PATH):
        generate_synthetic_data(DEFAULT_DB_PATH)
    return DEFAULT_DB_PATH

@pytest.fixture
def temp_db():
    """Provides a fresh isolated temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    generate_synthetic_data(path, num_customers=10)
    yield path
    if os.path.exists(path):
        os.remove(path)
