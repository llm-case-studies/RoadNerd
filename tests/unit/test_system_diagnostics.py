from types import SimpleNamespace


def test_ipv4_addresses_parsing(monkeypatch, add_core_to_path):
    import roadnerd_server as srv

    sample = (
        "2: enp58s0    inet 10.55.0.1/24 brd 10.55.0.255 scope global enp58s0\n"
        "3: wlp59s0f0  inet 172.20.4.96/16 brd 172.20.255.255 scope global dyn wlp59s0f0\n"
        "1: lo         inet 127.0.0.1/8 scope host lo\n"
    )

    def fake_run(cmd, capture_output=False, text=False):
        return SimpleNamespace(stdout=sample, returncode=0)

    monkeypatch.setattr(srv.subprocess, 'run', fake_run)
    ips = srv.SystemDiagnostics.ipv4_addresses()
    assert '10.55.0.1' in ips
    assert '172.20.4.96' in ips
    assert '127.0.0.1' not in ips


def test_check_connectivity_resilient(monkeypatch, add_core_to_path):
    import roadnerd_server as srv

    # Make socket.gethostbyname fail to simulate DNS issue
    class Boom(Exception):
        pass

    def fail_dns(host):
        raise Boom('dns fail')

    monkeypatch.setattr(srv.socket, 'gethostbyname', fail_dns)

    # Simulate gateway check failing
    def fake_run(cmd, capture_output=False, text=False):
        return SimpleNamespace(stdout='default via 10.55.0.1 dev enp58s0\n', returncode=0)

    monkeypatch.setattr(srv.subprocess, 'run', fake_run)
    chk = srv.SystemDiagnostics.check_connectivity()
    assert chk.get('dns') in ('failed', 'working')  # resilient path
    assert 'gateway' in chk
    assert 'interfaces' in chk

