#!/usr/bin/env python3
"""
RoadNerd Real-Server Integration Tests (non-interactive)

Runs a set of conversational and execution flows against a live server.
Usage:
  python3 RoadNerd/poc/core/real_server_integration.py [http://10.55.0.1:8080]
"""

import sys
import json
from typing import Optional


def print_section(title: str):
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)


def show(name: str, data):
    print(f"\n-- {name} --")
    try:
        print(json.dumps(data, indent=2))
    except Exception:
        print(data)


def scenario_status_and_scan(client):
    print_section("Status & Scan")
    s = client.session.get(f"{client.server_url}/api/status").json()
    show("/api/status", s)
    try:
        scan = client.session.get(f"{client.server_url}/api/scan_network").json()
        show("/api/scan_network", scan)
    except Exception as e:
        print(f"scan_network not available: {e}")


def scenario_context_question(client):
    print_section("Context → Question")
    info_text = 'PRETTY_NAME="Ubuntu 24.04.3 LTS"\nNAME="Ubuntu"\nVERSION_ID="24.04"'
    info = client.analyze_user_intent(info_text)
    show("intent(info)", info)
    client.add_to_context(info_text, info)

    question = "What version of Ubuntu is this?"
    qinfo = client.analyze_user_intent(question)
    show("intent(question)", qinfo)
    diag = client.diagnose(question, qinfo)
    show("diagnosis", diag)


def scenario_wifi_problem(client):
    print_section("Problem: WiFi not working")
    issue = "My WiFi is not working on this laptop."
    pinfo = client.analyze_user_intent(issue)
    show("intent(problem)", pinfo)
    diag = client.diagnose(issue, pinfo)
    show("diagnosis", diag)


def scenario_execute_commands(client):
    print_section("Execute Commands")
    for cmd in ["whoami", "id", "ping -c 1 1.1.1.1"]:
        res = client.execute_command(cmd)
        show(f"execute {cmd}", res)


def main():
    # Resolve server URL from arg or default
    server_url: Optional[str] = None
    if len(sys.argv) > 1:
        server_url = sys.argv[1]

    # Import after sys.path update
    from pathlib import Path
    core_dir = Path(__file__).resolve().parent
    if str(core_dir) not in sys.path:
        sys.path.insert(0, str(core_dir))
    import roadnerd_client as client_mod

    c = client_mod.RoadNerdClient(server_url)
    if not c.check_connection():
        print("Failed to connect to server. Aborting.")
        sys.exit(2)

    scenario_status_and_scan(c)
    scenario_context_question(c)
    scenario_wifi_problem(c)
    scenario_execute_commands(c)

    print("\nAll scenarios completed.")


if __name__ == "__main__":
    main()

