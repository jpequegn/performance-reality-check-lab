import pytest

from reality_check.native import build_binary


@pytest.fixture(scope="session")
def native_binary():
    return build_binary()
