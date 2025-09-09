import types


def test_interactive_quick_flow(monkeypatch, add_core_to_path):
    import roadnerd_client as client_mod

    # Dummy session to avoid network
    dummy_resp = types.SimpleNamespace(status_code=200, json=lambda: {
        'system': {'hostname': 'bee-link-ubuntu', 'distro': 'Ubuntu 24.04.3 LTS', 'platform': 'Linux'},
        'llm_backend': 'ollama'
    })

    class DummySession:
        def get(self, url, *a, **k):
            if url.endswith('/api/status'):
                return dummy_resp
            return types.SimpleNamespace(status_code=200, json=lambda: {})

        def post(self, url, json=None, *a, **k):
            if url.endswith('/api/diagnose'):
                return types.SimpleNamespace(status_code=200, json=lambda: {'llm_suggestion': 'stubbed suggestion'})
            if url.endswith('/api/execute'):
                return types.SimpleNamespace(status_code=200, json=lambda: {'executed': True, 'output': 'server-user'})
            return types.SimpleNamespace(status_code=200, json=lambda: {})

    # Patch requests.Session used inside client
    import requests
    monkeypatch.setattr(requests, 'Session', lambda: DummySession())

    c = client_mod.RoadNerdClient(server_url='http://dummy')
    assert c.check_connection() is True

    # Script a tiny interaction: status, a question, execute, quit
    inputs = iter([
        'status', '',
        'What version of Ubuntu is this?', '',
        'execute whoami', '',
        'quit', ''
    ])

    monkeypatch.setattr('builtins.input', lambda prompt='': next(inputs))
    c.interactive_mode()

