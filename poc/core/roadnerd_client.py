#!/usr/bin/env python3
"""
RoadNerd Client - Run this on the laptop that needs help
Connects to RoadNerd Server via USB network
"""

import sys
import os
import json
import time
import subprocess
from typing import Optional

try:
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    import requests

class RoadNerdClient:
    def __init__(self, server_url: str = None):
        """Initialize client with server URL"""
        # Try to auto-detect server
        if not server_url:
            server_url = self.find_server()
        
        self.server_url = server_url
        self.session = requests.Session()
        self.connected = False
        
    def find_server(self) -> str:
        """Auto-detect RoadNerd server on USB network"""
        print("🔍 Looking for RoadNerd server...")
        
        # Common USB tethering IPs
        possible_ips = [
            '10.55.0.1',         # Direct ethernet (current setup)
            '192.168.42.1',      # Android USB
            '192.168.42.129',    # Android alternate
            '172.20.10.1',       # iPhone USB
            '192.168.1.1',       # Direct ethernet alternate
            'localhost'          # Same machine
        ]
        
        for ip in possible_ips:
            for port in [8080, 8000, 5000]:
                url = f"http://{ip}:{port}"
                try:
                    response = requests.get(f"{url}/api/status", timeout=1)
                    if response.status_code == 200:
                        print(f"✓ Found server at {url}")
                        return url
                except:
                    continue
        
        # Manual entry
        print("\n❌ No server found automatically")
        print("\nMake sure:")
        print("1. USB cable is connected")
        print("2. USB tethering is enabled on server device")
        print("3. RoadNerd server is running")
        
        manual_ip = input("\nEnter server IP manually (or 'quit'): ")
        if manual_ip.lower() == 'quit':
            sys.exit(0)
        
        return f"http://{manual_ip}:8080"
    
    def check_connection(self) -> bool:
        """Verify connection to server"""
        try:
            response = self.session.get(f"{self.server_url}/api/status", timeout=5)
            if response.status_code == 200:
                self.connected = True
                status = response.json()
                print(f"✓ Connected to {status['system']['hostname']}")
                print(f"  Running: {status['system'].get('distro', status['system']['platform'])}")
                print(f"  LLM: {status['llm_backend']}")
                return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.connected = False
        
        return False
    
    def diagnose(self, issue: str) -> dict:
        """Send issue to server for diagnosis"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/diagnose",
                json={'issue': issue}
            )
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def execute_command(self, command: str, force: bool = False) -> dict:
        """Execute command via server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/execute",
                json={'command': command, 'force': force}
            )
            return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    def query_llm(self, prompt: str) -> str:
        """Query LLM directly"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/llm",
                json={'prompt': prompt}
            )
            data = response.json()
            return data.get('response', 'No response')
        except Exception as e:
            return f"Error: {e}"
    
    def interactive_mode(self):
        """Interactive troubleshooting session"""
        print("\n" + "="*50)
        print("🚀 RoadNerd Interactive Mode")
        print("="*50)
        print("\nCommands:")
        print("  help - Show this help")
        print("  status - Check server status")
        print("  scan - Scan network configuration")
        print("  execute <cmd> - Run a command")
        print("  quit - Exit")
        print("\nOr just describe your problem!\n")
        
        while True:
            try:
                user_input = input("🤖 RoadNerd> ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() == 'quit':
                    print("Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    self.interactive_mode()  # Show help again
                
                elif user_input.lower() == 'status':
                    response = self.session.get(f"{self.server_url}/api/status")
                    print(json.dumps(response.json(), indent=2))
                
                elif user_input.lower() == 'scan':
                    response = self.session.get(f"{self.server_url}/api/scan_network")
                    data = response.json()
                    for key, value in data.items():
                        print(f"\n[{key.upper()}]")
                        print(value)
                
                elif user_input.startswith('execute '):
                    cmd = user_input[8:]
                    print(f"Executing: {cmd}")
                    result = self.execute_command(cmd)
                    
                    if result.get('executed'):
                        print(f"Output:\n{result['output']}")
                    else:
                        print(f"Failed: {result.get('output', 'Unknown error')}")
                        if result.get('analysis', {}).get('warnings'):
                            print("Warnings:", ', '.join(result['analysis']['warnings']))
                
                else:
                    # Treat as a problem description
                    print("🔍 Analyzing issue...")
                    
                    # Get diagnosis
                    diagnosis = self.diagnose(user_input)
                    
                    # Show KB solution if found
                    if diagnosis.get('kb_solution'):
                        print(f"\n📚 Known Solution: {diagnosis['kb_solution']['name']}")
                        for cmd in diagnosis['kb_solution']['commands']:
                            print(f"  $ {cmd}")
                    
                    # Show LLM suggestion
                    if diagnosis.get('llm_suggestion'):
                        print(f"\n🤖 AI Suggestion:")
                        print(diagnosis['llm_suggestion'])
                    
                    # Show system context
                    if diagnosis.get('connectivity'):
                        conn = diagnosis['connectivity']
                        print(f"\n📊 System State:")
                        print(f"  DNS: {conn.get('dns', 'unknown')}")
                        print(f"  Gateway: {conn.get('gateway', 'unknown')}")
                        print(f"  Active interfaces: {conn.get('interfaces', 0)}")
                    
                    # Offer to execute suggested commands
                    if diagnosis.get('kb_solution'):
                        response = input("\n⚡ Execute suggested fix? (y/n): ")
                        if response.lower() == 'y':
                            for cmd in diagnosis['kb_solution']['commands']:
                                print(f"\nRunning: {cmd}")
                                # For safety, we're not auto-executing
                                # In production, would run: self.execute_command(cmd)
                                print("(In production, this would execute)")
                    
            except KeyboardInterrupt:
                print("\n\nUse 'quit' to exit")
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue

def main():
    """Main entry point"""
    print("""
    ╦═╗┌─┐┌─┐┌┬┐╔╗╔┌─┐┬─┐┌┬┐  ╔═╗┬  ┬┌─┐┌┐┌┌┬┐
    ╠╦╝│ │├─┤ ││║║║├┤ ├┬┘ ││  ║  │  │├┤ │││ │ 
    ╩╚═└─┘┴ ┴─┴┘╝╚╝└─┘┴└──┴┘  ╚═╝┴─┘┴└─┘┘└┘ ┴ 
    Connecting to your portable system assistant...
    """)
    
    # Parse arguments
    server_url = None
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('http'):
            server_url = sys.argv[1]
        else:
            server_url = f"http://{sys.argv[1]}:8080"
    
    # Create client
    client = RoadNerdClient(server_url)
    
    # Check connection
    if not client.check_connection():
        print("\n❌ Could not connect to server")
        print("\nTroubleshooting:")
        print("1. Check USB cable connection")
        print("2. Enable USB tethering on server device")
        print("3. Make sure server.py is running")
        print("4. Try: ping 192.168.42.1")
        sys.exit(1)
    
    # Start interactive mode
    client.interactive_mode()

if __name__ == "__main__":
    main()