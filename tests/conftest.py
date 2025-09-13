import importlib.util
import sys
from pathlib import Path
import pytest


@pytest.fixture()
def template_client():
    # Load the Flask app from the script file without relying on package layout
    server_path = Path(__file__).resolve().parents[2] / 'poc' / 'core' / 'roadnerd_server.py'
    spec = importlib.util.spec_from_file_location('roadnerd_server', server_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['roadnerd_server'] = mod
    spec.loader.exec_module(mod)  # type: ignore
    app = mod.app  # type: ignore
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

