import os
import sys
import types


def import_client_module():
    # Stub requests to avoid network/pip at import time
    dummy_response = types.SimpleNamespace(status_code=200, json=lambda: {})

    class DummySession:
        def get(self, *args, **kwargs):
            return dummy_response

        def post(self, *args, **kwargs):
            return dummy_response

    sys.modules['requests'] = types.SimpleNamespace(Session=lambda: DummySession())

    # Ensure we can import the client module by path
    here = os.path.dirname(__file__)
    core_dir = os.path.abspath(os.path.join(here, '..'))
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)

    import importlib
    return importlib.import_module('roadnerd_client')


def test_get_multiline_input_eof_no_content(monkeypatch):
    client_mod = import_client_module()
    c = client_mod.RoadNerdClient(server_url='http://dummy')

    # Simulate EOFError immediately
    def _raise_eof():
        raise EOFError

    monkeypatch.setattr('builtins.input', _raise_eof)
    assert c.get_multiline_input() is None


def test_get_multiline_input_blank_line_ends(monkeypatch):
    client_mod = import_client_module()
    c = client_mod.RoadNerdClient(server_url='http://dummy')

    lines = iter([
        'PRETTY_NAME="Ubuntu 24.04.3 LTS"',
        'VERSION_ID="24.04"',
        '',  # blank line ends
    ])
    monkeypatch.setattr('builtins.input', lambda: next(lines))

    out = c.get_multiline_input()
    assert 'Ubuntu 24.04.3' in out
    assert out.endswith('VERSION_ID="24.04"')


def test_get_multiline_input_fence_ends(monkeypatch):
    client_mod = import_client_module()
    c = client_mod.RoadNerdClient(server_url='http://dummy')

    lines = iter([
        'line 1',
        '```',  # fence ends
    ])
    monkeypatch.setattr('builtins.input', lambda: next(lines))
    out = c.get_multiline_input()
    assert out == 'line 1'


def test_analyze_user_intent_information():
    client_mod = import_client_module()
    c = client_mod.RoadNerdClient(server_url='http://dummy')

    text = 'PRETTY_NAME="Ubuntu 24.04.3 LTS"\nID=ubuntu\nVERSION_ID=24.04'
    info = c.analyze_user_intent(text)
    assert info['intent'] == 'information'


def test_analyze_user_intent_problem():
    client_mod = import_client_module()
    c = client_mod.RoadNerdClient(server_url='http://dummy')

    text = 'My wifi is not working and times out'
    info = c.analyze_user_intent(text)
    assert info['intent'] == 'problem'


def test_analyze_user_intent_question():
    client_mod = import_client_module()
    c = client_mod.RoadNerdClient(server_url='http://dummy')

    text = 'What OS am I running?'
    info = c.analyze_user_intent(text)
    assert info['intent'] == 'question'


def test_context_capacity_limit():
    client_mod = import_client_module()
    c = client_mod.RoadNerdClient(server_url='http://dummy')
    c.max_context_items = 3

    for i in range(6):
        info = {'intent': 'information', 'confidence': 1, 'info_score': 1, 'problem_score': 0}
        c.add_to_context(f'item {i}', info)

    assert len(c.conversation_context) == 3
    # Ensure only most recent kept
    assert c.conversation_context[0]['content'].endswith('item 3')
