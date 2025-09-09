import sys


def test_analyze_command_risk_levels(add_core_to_path):
    import roadnerd_server as srv
    CE = srv.CommandExecutor

    low = CE.analyze_command('whoami')
    assert low['risk_level'] == 'low'

    med = CE.analyze_command('sudo systemctl restart NetworkManager')
    assert med['risk_level'] in ('medium', 'high')
    assert 'Requires elevated privileges' in med['warnings']

    high = CE.analyze_command('rm -rf /')
    assert high['risk_level'] == 'high'
    assert any('dangerous pattern' in w for w in high['warnings'])


def test_execute_safely_respects_safe_mode(add_core_to_path):
    import roadnerd_server as srv
    srv.CONFIG['safe_mode'] = True
    res = srv.CommandExecutor.execute_safely('rm -rf /tmp/danger')
    assert res['executed'] is False
    assert 'blocked' in res.get('output', '').lower() or res['analysis']['risk_level'] == 'high'

