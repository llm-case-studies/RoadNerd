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
import re
from datetime import datetime

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
        self.conversation_context = []  # New: conversation memory
        self.max_context_items = 10     # Limit memory usage
        
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
    
    def diagnose(self, issue: str, intent_info: dict) -> dict:
        """Send issue with context and intent to server"""
        try:
            payload = {
                'issue': issue,
                'intent': intent_info['intent'],
                'context': self.get_context_for_api(),
                'intent_analysis': {
                    'confidence': intent_info['confidence'],
                    'info_score': intent_info['info_score'],
                    'problem_score': intent_info['problem_score']
                }
            }
            
            response = self.session.post(
                f"{self.server_url}/api/diagnose",
                json=payload
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
    
    def get_multiline_input(self, prompt: str = "🤖 RoadNerd> ") -> Optional[str]:
        """
        Collect multi-line input until blank line or closing fence.
        Handles paste operations naturally.
        """
        print(prompt, end="", flush=True)
        lines = []
        seen_content = False
        
        while True:
            try:
                line = input()
            except EOFError:
                # If stdin is closed and nothing was entered, signal caller to exit
                if not lines and not seen_content:
                    return None
                # Otherwise, treat EOF as end of multi-line block
                break
                
            stripped = line.strip()
            
            # Explicit end markers
            if stripped in ("```", "EOF", "END"):
                break
                
            # Empty line after content ends input
            if stripped == "" and seen_content:
                break
                
            if stripped:
                seen_content = True
                
            lines.append(line)
        
        return "\n".join(lines).strip()

    def print_help(self) -> None:
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

    def analyze_user_intent(self, text: str) -> dict:
        """Classify user input intent with pattern matching"""
        
        # Information indicators
        info_patterns = [
            r"cat /etc/\w+",                    # Command output
            r"^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+:.*\$",  # Shell prompt
            r"^[A-Z_]+=.*",                     # Environment variables
            r"PRETTY_NAME=|VERSION_ID=|ID=",    # OS release keys
            r"^#|^\$ ",                         # Commented/prompt lines
            r"Here is.*:|Like that:|Output:",   # User presenting info
            r"^====.*====",                     # Delimiter patterns
        ]
        
        # Problem indicators
        problem_patterns = [
            r"not working|broken|fail(ed)?|error|timeout",
            r"how (do|to)|why is|can't|cannot|won't",
            r"help me|fix|diagnose|troubleshoot",
            r"issue|problem|stuck|confused",
        ]
        
        info_score = sum(bool(re.search(p, text, re.IGNORECASE | re.MULTILINE)) 
                        for p in info_patterns)
        problem_score = sum(bool(re.search(p, text, re.IGNORECASE | re.MULTILINE)) 
                           for p in problem_patterns)
        
        # Default to question if no strong indicators
        intent = ("information" if info_score > problem_score 
                 else ("problem" if problem_score > 0 else "question"))
        
        return {
            "intent": intent,
            "confidence": max(info_score, problem_score),
            "info_score": info_score,
            "problem_score": problem_score
        }

    def add_to_context(self, user_input: str, intent_info: dict, response: dict = None):
        """Store interaction in conversation context"""
        context_item = {
            'type': intent_info['intent'],
            'content': user_input[:200],  # Truncate long content
            'timestamp': datetime.now().isoformat(),
            'intent_scores': {
                'info': intent_info['info_score'],
                'problem': intent_info['problem_score']
            }
        }
        
        # Add response summary if available
        if response:
            context_item['response_summary'] = response.get('llm_suggestion', '')[:100]
        
        self.conversation_context.append(context_item)
        
        # Keep only recent context
        if len(self.conversation_context) > self.max_context_items:
            self.conversation_context = self.conversation_context[-self.max_context_items:]

    def get_context_for_api(self) -> list:
        """Format context for API transmission"""
        return [
            {
                'type': item['type'],
                'content': item['content'],
                'timestamp': item['timestamp']
            }
            for item in self.conversation_context[-5:]  # Send last 5 items
        ]

    def interactive_mode(self):
        """Interactive troubleshooting session"""
        self.print_help()
        
        while True:
            try:
                user_input = self.get_multiline_input()
                
                # Handle closed stdin to avoid busy-looping and spamming prompts
                if user_input is None:
                    print("\nInput closed (EOF). Exiting.")
                    break
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() == 'quit':
                    print("Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    self.print_help()  # Show help text without recursion
                
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
                    # Intent analysis
                    intent_info = self.analyze_user_intent(user_input)
                    
                    # Information handling
                    if intent_info['intent'] == 'information':
                        print(f"📝 Information noted ({intent_info['confidence']} confidence)")
                        self.add_to_context(user_input, intent_info)
                        
                        # Ask if they need help with anything
                        if len(user_input.split('\n')) > 3:  # Multi-line info
                            print("What would you like me to help you with regarding this information?")
                        continue

                    # Problem/Question processing
                    print("🔍 Analyzing issue...")
                    
                    # Get diagnosis with context
                    diagnosis = self.diagnose(user_input, intent_info)
                    
                    # Store in context
                    self.add_to_context(user_input, intent_info, diagnosis)
                    
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
