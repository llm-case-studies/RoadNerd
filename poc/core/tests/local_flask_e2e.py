#!/usr/bin/env python3
"""
Local Flask e2e using test_client (no sockets).
Calls server endpoints in-process. Stubs LLM if not available.
"""
import os
import sys
from pathlib import Path
import json


def main():
    # Import server module
    core_dir = Path(__file__).resolve().parent.parent
    if str(core_dir) not in sys.path:
        sys.path.insert(0, str(core_dir))
    import roadnerd_server as srv

    # Optionally stub LLM to avoid external deps
    if os.getenv('RN_STUB_LLM', '1') in ('1', 'true', 'yes', 'on'):
        srv.LLMInterface.get_response = staticmethod(lambda prompt: 'stubbed-llm-response')

    app = srv.app
    client = app.test_client()

    print("== GET /api/status ==")
    r = client.get('/api/status')
    print(json.dumps(r.get_json(), indent=2))

    print("\n== POST /api/diagnose (info+question) ==")
    payload = {
        'issue': 'What version of Ubuntu is this?\nPRETTY_NAME="Ubuntu 24.04.3 LTS"'
    }
    r = client.post('/api/diagnose', json=payload)
    print(json.dumps(r.get_json(), indent=2))

    print("\n== POST /api/diagnose (wifi problem) ==")
    r = client.post('/api/diagnose', json={'issue': 'My WiFi is not working'})
    print(json.dumps(r.get_json(), indent=2))

    print("\n== POST /api/execute (whoami) ==")
    r = client.post('/api/execute', json={'command': 'whoami'})
    print(json.dumps(r.get_json(), indent=2))

    print("\nDone.")


if __name__ == '__main__':
    main()

