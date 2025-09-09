import os
import sys
import types
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def core_dir(repo_root: Path) -> Path:
    return repo_root / 'poc' / 'core'


@pytest.fixture(scope="session")
def add_core_to_path(core_dir: Path):
    sys.path.insert(0, str(core_dir))
    yield
    try:
        sys.path.remove(str(core_dir))
    except ValueError:
        pass


@pytest.fixture(scope="session")
def server_module(add_core_to_path):
    flask = pytest.importorskip('flask')
    try:
        import roadnerd_server as srv
    except Exception as e:
        pytest.skip(f"Cannot import server module: {e}")
    return srv


@pytest.fixture()
def flask_client(server_module):
    # Stub LLM to avoid external calls
    server_module.LLMInterface.get_response = staticmethod(lambda prompt: 'stubbed-llm-response')
    return server_module.app.test_client()

