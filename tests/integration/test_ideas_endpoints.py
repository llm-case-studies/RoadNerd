import json
from types import SimpleNamespace


def stub_llm_response_array():
    return json.dumps([
        {
            "hypothesis": "DNS misconfiguration",
            "category": "dns",
            "why": "resolv.conf points to wrong server",
            "checks": ["cat /etc/resolv.conf", "dig example.com"],
            "fixes": ["sudo systemctl restart systemd-resolved"],
            "risk": "low"
        },
        {
            "hypothesis": "NetworkManager glitch",
            "category": "network",
            "why": "service stuck",
            "checks": ["nmcli dev status"],
            "fixes": ["sudo systemctl restart NetworkManager"],
            "risk": "medium"
        }
    ])


def test_brainstorm_parses_array(flask_client, monkeypatch):
    import roadnerd_server as srv
    monkeypatch.setattr(srv.LLMInterface, 'get_response', staticmethod(lambda *a, **k: stub_llm_response_array()))

    r = flask_client.post('/api/ideas/brainstorm', json={'issue': 'DNS failing', 'n': 5, 'creativity': 2})
    assert r.status_code == 200
    data = r.get_json()
    assert 'ideas' in data and isinstance(data['ideas'], list)
    assert len(data['ideas']) >= 2
    first = data['ideas'][0]
    assert 'hypothesis' in first and 'category' in first and 'checks' in first


def test_brainstorm_parses_fenced_json(flask_client, monkeypatch):
    import roadnerd_server as srv
    fenced = """
```json
[{"hypothesis":"WiFi radio blocked","category":"wifi","why":"rfkill shows blocked","checks":["rfkill list"],"fixes":["rfkill unblock all"],"risk":"low"}]
```
"""
    monkeypatch.setattr(srv.LLMInterface, 'get_response', staticmethod(lambda *a, **k: fenced))
    r = flask_client.post('/api/ideas/brainstorm', json={'issue': 'wifi down', 'n': 3, 'creativity': 3})
    assert r.status_code == 200
    ideas = r.get_json()['ideas']
    assert len(ideas) == 1
    assert ideas[0]['category'] == 'wifi'


def test_probe_whitelist_and_limits(flask_client, monkeypatch):
    import roadnerd_server as srv

    # Fake subprocess.run to avoid real commands
    def fake_run(cmd, shell=False, capture_output=False, text=False, timeout=None):
        return SimpleNamespace(stdout=f"out:{cmd}", stderr="", returncode=0)

    monkeypatch.setattr(srv.subprocess, 'run', fake_run)
    payload = {
        'ideas': [{
            'hypothesis': 'test', 'category': 'dns', 'why': 'x',
            'checks': ['nmcli dev status', 'ip addr', 'cat /etc/shadow']
        }]
    }
    r = flask_client.post('/api/ideas/probe', json=payload)
    assert r.status_code == 200
    out = r.get_json()
    probed = out['probed_ideas'][0]
    ev = probed.get('evidence', {})
    # Only safe commands should have evidence; forbidden ones omitted
    assert any('nmcli dev status' in k or 'ip addr' in k for k in ev.keys())
    assert not any('/etc/shadow' in k for k in ev.keys())


def test_judge_succeeds(flask_client):
    ideas = [{
        'hypothesis': 'DNS misconfig', 'category': 'dns', 'why': 'x',
        'checks': [], 'fixes': [], 'risk': 'low'
    }, {
        'hypothesis': 'dangerous fix', 'category': 'dns', 'why': 'y',
        'checks': [], 'fixes': [], 'risk': 'high'
    }]
    r = flask_client.post('/api/ideas/judge', json={'issue': 'dns', 'ideas': ideas})
    assert r.status_code == 200
    ranked = r.get_json()['ranked']
    assert isinstance(ranked, list) and len(ranked) == 2
    # Top idea should be safer one typically
    assert ranked[0]['idea']['risk'] in ('low', 'medium')

