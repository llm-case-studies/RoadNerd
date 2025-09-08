import os
import sys
import types
import importlib


class DummyResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


class DummySession:
    def get(self, url, *args, **kwargs):
        if url.endswith('/api/status'):
            return DummyResponse(200, {
                'system': {
                    'hostname': 'bee-link-ubuntu',
                    'distro': 'Ubuntu 24.04.3 LTS',
                    'platform': 'Linux'
                },
                'llm_backend': 'ollama'
            })
        if url.endswith('/api/scan_network'):
            return DummyResponse(200, {
                'dns': '1.1.1.1',
                'gateway': '10.55.0.1',
                'interfaces': 2
            })
        return DummyResponse(404, {'error': 'not found'})

    def post(self, url, json=None, *args, **kwargs):
        if url.endswith('/api/diagnose'):
            issue = (json or {}).get('issue', '')
            if 'wifi' in issue.lower():
                return DummyResponse(200, {
                    'kb_solution': {
                        'name': 'Reset NetworkManager',
                        'commands': [
                            'sudo systemctl restart NetworkManager',
                            'nmcli r wifi off && sleep 1 && nmcli r wifi on'
                        ]
                    },
                    'llm_suggestion': 'Check rfkill and kernel modules for wifi adapter.',
                    'connectivity': {
                        'dns': '1.1.1.1',
                        'gateway': '10.55.0.1',
                        'interfaces': 2
                    }
                })
            else:
                return DummyResponse(200, {
                    'llm_suggestion': 'Ubuntu 24.04 (Noble Numbat)',
                    'connectivity': {
                        'dns': '1.1.1.1',
                        'gateway': '10.55.0.1',
                        'interfaces': 2
                    }
                })
        if url.endswith('/api/execute'):
            cmd = (json or {}).get('command', '')
            if cmd == 'whoami':
                return DummyResponse(200, {'executed': True, 'output': 'server-user\n'})
            if cmd == 'id':
                return DummyResponse(200, {'executed': True, 'output': 'uid=1000(server-user) gid=1000(server-user)\n'})
            if cmd.startswith('ping'):
                return DummyResponse(200, {'executed': True, 'output': '1 packets transmitted, 1 received'})
            return DummyResponse(200, {'executed': False, 'output': 'Command blocked by policy', 'analysis': {'warnings': ['blocked']}})
        if url.endswith('/api/llm'):
            return DummyResponse(200, {'response': 'stubbed response'})
        return DummyResponse(404, {'error': 'not found'})


def main():
    # Stub requests for the client module before import
    sys.modules['requests'] = types.SimpleNamespace(Session=lambda: DummySession())

    # Import client module from sibling directory
    here = os.path.dirname(__file__)
    core_dir = os.path.abspath(os.path.join(here, '..'))
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    client = importlib.import_module('roadnerd_client')

    # Build client and check connection (uses DummySession)
    c = client.RoadNerdClient(server_url='http://dummy')
    assert c.check_connection()

    # Build scripted input stream covering key flows
    scripted_inputs = iter([
        # status
        'status', '',
        # paste OS info
        'PRETTY_NAME="Ubuntu 24.04.3 LTS"', 'VERSION_ID="24.04"', '',
        # follow-up question
        'What version of Ubuntu is this?', '',
        # problem triggers kb solution and execute prompt (we answer 'n')
        'My WiFi is not working', '', 'n',
        # manual execute
        'execute whoami', '',
        # exit
        'quit', ''
    ])

    # Patch builtins.input globally for the duration
    import builtins
    original_input = builtins.input
    builtins.input = lambda prompt='': next(scripted_inputs)

    try:
        c.interactive_mode()
    finally:
        builtins.input = original_input


if __name__ == '__main__':
    main()

