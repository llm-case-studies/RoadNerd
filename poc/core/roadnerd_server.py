#!/usr/bin/env python3
"""
RoadNerd Server - The "Smart Friend" Component
Run this on your BeeLink or second laptop with LLM installed
"""

import json
import subprocess
import platform
import os
from datetime import datetime
from typing import Dict, List, Optional
import socket
import shutil

# Try imports, fallback gracefully
try:
    from flask import Flask, request, jsonify, render_template_string
    from flask_cors import CORS
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask", "flask-cors"])
    from flask import Flask, request, jsonify, render_template_string
    from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configuration
CONFIG = {
    'llm_backend': 'ollama',  # or 'llamafile' or 'gpt4all'
    'model': 'llama3.2',
    'usb_network_ip': '192.168.42.1',  # Server IP on USB network
    'port': 8080,
    'safe_mode': True  # Don't execute commands automatically
}

# Knowledge base - embedded for portability
KNOWLEDGE_BASE = {
    'dns_issues': {
        'symptoms': ['cannot resolve', 'dns failure', 'name resolution'],
        'solutions': [
            {
                'name': 'Restart systemd-resolved',
                'commands': ['sudo systemctl restart systemd-resolved'],
                'check': 'systemctl status systemd-resolved'
            },
            {
                'name': 'Set Google DNS',
                'commands': ['echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf'],
                'check': 'nslookup google.com'
            }
        ]
    },
    'disk_space': {
        'symptoms': ['disk full', 'no space left', 'storage full'],
        'solutions': [
            {
                'name': 'Clean package cache',
                'commands': ['sudo apt-get clean', 'sudo apt-get autoremove'],
                'check': 'df -h /'
            },
            {
                'name': 'Remove old kernels',
                'commands': ['sudo apt-get remove --purge $(dpkg -l | grep "^rc" | awk "{print $2}")'],
                'check': 'dpkg --list | grep linux-image'
            }
        ]
    },
    'network_issues': {
        'symptoms': ['wifi down', 'no internet', 'connection failed'],
        'solutions': [
            {
                'name': 'Restart NetworkManager',
                'commands': ['sudo systemctl restart NetworkManager'],
                'check': 'nmcli dev status'
            },
            {
                'name': 'Reset network stack',
                'commands': [
                    'sudo ip link set dev wlan0 down',
                    'sudo ip link set dev wlan0 up'
                ],
                'check': 'ip addr show'
            }
        ]
    }
}

class SystemDiagnostics:
    """Gather system information safely"""
    
    @staticmethod
    def get_system_info() -> Dict:
        """Get basic system information"""
        info = {
            'platform': platform.system(),
            'hostname': socket.gethostname(),
            'kernel': platform.release(),
            'arch': platform.machine(),
            'python': platform.python_version()
        }
        
        # Add distro info for Linux
        if platform.system() == 'Linux':
            try:
                with open('/etc/os-release') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME'):
                            info['distro'] = line.split('=')[1].strip().strip('"')
                            break
            except:
                info['distro'] = 'Unknown Linux'
        
        return info
    
    @staticmethod
    def check_connectivity() -> Dict:
        """Check various connectivity aspects"""
        checks = {}
        
        # Check DNS
        try:
            socket.gethostbyname('google.com')
            checks['dns'] = 'working'
        except:
            checks['dns'] = 'failed'
        
        # Check default gateway
        try:
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
            checks['gateway'] = 'configured' if 'default' in result.stdout else 'missing'
        except:
            checks['gateway'] = 'unknown'
        
        # Check interfaces
        try:
            result = subprocess.run(['ip', 'link'], capture_output=True, text=True)
            checks['interfaces'] = result.stdout.count('state UP')
        except:
            checks['interfaces'] = 0
        
        return checks

class LLMInterface:
    """Interface to various LLM backends"""
    
    @staticmethod
    def query_ollama(prompt: str) -> str:
        """Query Ollama API"""
        try:
            import requests
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={'model': CONFIG['model'], 'prompt': prompt, 'stream': False}
            )
            return response.json().get('response', 'No response from Ollama')
        except Exception as e:
            return f"Ollama not available: {e}"
    
    @staticmethod
    def query_llamafile(prompt: str) -> str:
        """Query llamafile server"""
        try:
            import requests
            response = requests.post(
                'http://localhost:8080/completion',
                json={'prompt': prompt, 'n_predict': 200}
            )
            return response.json().get('content', 'No response from llamafile')
        except Exception as e:
            return f"Llamafile not available: {e}"
    
    @staticmethod
    def get_response(prompt: str) -> str:
        """Get response from configured LLM"""
        if CONFIG['llm_backend'] == 'ollama':
            return LLMInterface.query_ollama(prompt)
        elif CONFIG['llm_backend'] == 'llamafile':
            return LLMInterface.query_llamafile(prompt)
        else:
            return "No LLM backend configured"

class CommandExecutor:
    """Safely execute system commands"""
    
    @staticmethod
    def analyze_command(cmd: str) -> Dict:
        """Analyze a command for safety"""
        dangerous_patterns = ['rm -rf', 'dd if=', 'mkfs', '> /dev/', 'format']
        
        risk_level = 'low'
        warnings = []
        
        for pattern in dangerous_patterns:
            if pattern in cmd.lower():
                risk_level = 'high'
                warnings.append(f"Contains dangerous pattern: {pattern}")
        
        if 'sudo' in cmd:
            risk_level = 'medium' if risk_level == 'low' else 'high'
            warnings.append("Requires elevated privileges")
        
        return {
            'command': cmd,
            'risk_level': risk_level,
            'warnings': warnings,
            'requires_sudo': 'sudo' in cmd
        }
    
    @staticmethod
    def execute_safely(cmd: str) -> Dict:
        """Execute command with safety checks"""
        analysis = CommandExecutor.analyze_command(cmd)
        
        if analysis['risk_level'] == 'high' and CONFIG['safe_mode']:
            return {
                'executed': False,
                'output': 'Command blocked in safe mode',
                'analysis': analysis
            }
        
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return {
                'executed': True,
                'output': result.stdout or result.stderr,
                'return_code': result.returncode,
                'analysis': analysis
            }
        except subprocess.TimeoutExpired:
            return {
                'executed': False,
                'output': 'Command timed out',
                'analysis': analysis
            }
        except Exception as e:
            return {
                'executed': False,
                'output': str(e),
                'analysis': analysis
            }

# Flask Routes

@app.route('/')
def home():
    """Serve a simple web interface"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RoadNerd Server</title>
        <style>
            body { font-family: monospace; padding: 20px; background: #1a1a1a; color: #0f0; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #0f0; text-shadow: 0 0 10px #0f0; }
            .status { background: #000; padding: 20px; border: 1px solid #0f0; margin: 20px 0; }
            .endpoint { margin: 10px 0; padding: 10px; background: #111; }
            .online { color: #0f0; }
            .offline { color: #f00; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 RoadNerd Server Active</h1>
            <div class="status">
                <h2>System Status</h2>
                <div id="status">Loading...</div>
            </div>
            <div class="status">
                <h2>Available Endpoints</h2>
                <div class="endpoint">POST /api/diagnose - Analyze system issue</div>
                <div class="endpoint">POST /api/execute - Execute command</div>
                <div class="endpoint">GET /api/status - System status</div>
                <div class="endpoint">POST /api/llm - Query LLM directly</div>
            </div>
            <div class="status">
                <h2>USB Network Setup</h2>
                <pre>
1. Connect devices via USB cable
2. Enable USB tethering on this device
3. Client device should see network at 192.168.42.x
4. Access this server at: http://192.168.42.1:8080
                </pre>
            </div>
        </div>
        <script>
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status').innerHTML = JSON.stringify(data, null, 2);
                });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/status', methods=['GET'])
def api_status():
    """Return system status"""
    return jsonify({
        'server': 'online',
        'timestamp': datetime.now().isoformat(),
        'system': SystemDiagnostics.get_system_info(),
        'connectivity': SystemDiagnostics.check_connectivity(),
        'llm_backend': CONFIG['llm_backend'],
        'safe_mode': CONFIG['safe_mode']
    })

@app.route('/api/diagnose', methods=['POST'])
def api_diagnose():
    """Diagnose a system issue"""
    data = request.json
    issue = data.get('issue', '')
    
    # Check knowledge base first
    kb_solution = None
    for problem_type, details in KNOWLEDGE_BASE.items():
        for symptom in details['symptoms']:
            if symptom in issue.lower():
                kb_solution = details['solutions'][0]  # Get first solution
                break
    
    # Prepare context for LLM
    system_info = SystemDiagnostics.get_system_info()
    connectivity = SystemDiagnostics.check_connectivity()
    
    prompt = f"""
    System: {system_info['platform']} {system_info.get('distro', '')}
    Issue: {issue}
    Connectivity: DNS={connectivity['dns']}, Gateway={connectivity['gateway']}
    
    Provide a specific command to diagnose or fix this issue. Be concise.
    """
    
    llm_response = LLMInterface.get_response(prompt)
    
    return jsonify({
        'issue': issue,
        'kb_solution': kb_solution,
        'llm_suggestion': llm_response,
        'system_context': system_info,
        'connectivity': connectivity
    })

@app.route('/api/execute', methods=['POST'])
def api_execute():
    """Execute a command safely"""
    data = request.json
    command = data.get('command', '')
    force = data.get('force', False)
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    # Override safe mode if forced
    original_safe_mode = CONFIG['safe_mode']
    if force:
        CONFIG['safe_mode'] = False
    
    result = CommandExecutor.execute_safely(command)
    
    # Restore safe mode
    CONFIG['safe_mode'] = original_safe_mode
    
    return jsonify(result)

@app.route('/api/llm', methods=['POST'])
def api_llm():
    """Direct LLM query"""
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    response = LLMInterface.get_response(prompt)
    
    return jsonify({
        'prompt': prompt,
        'response': response,
        'model': CONFIG['model'],
        'backend': CONFIG['llm_backend']
    })

@app.route('/api/scan_network', methods=['GET'])
def api_scan_network():
    """Scan for network issues"""
    diagnostics = {}
    
    # Check each network interface
    try:
        result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
        diagnostics['interfaces'] = result.stdout
    except:
        diagnostics['interfaces'] = 'Could not scan interfaces'
    
    # Check routing table
    try:
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        diagnostics['routes'] = result.stdout
    except:
        diagnostics['routes'] = 'Could not get routes'
    
    # Check DNS
    try:
        result = subprocess.run(['cat', '/etc/resolv.conf'], capture_output=True, text=True)
        diagnostics['dns_config'] = result.stdout
    except:
        diagnostics['dns_config'] = 'Could not read DNS config'
    
    return jsonify(diagnostics)

def setup_usb_network():
    """Setup USB networking if not already configured"""
    print("\n" + "="*50)
    print("USB NETWORKING SETUP")
    print("="*50)
    print("\nOption 1: USB Tethering (Easiest)")
    print("1. Connect this device to patient laptop via USB")
    print("2. Enable 'USB Tethering' in network settings")
    print("3. Patient laptop will get IP automatically")
    print(f"4. Access server at: http://192.168.42.1:{CONFIG['port']}")
    
    print("\nOption 2: Direct USB Networking (Advanced)")
    print("1. modprobe g_ether  # On this device")
    print("2. ifconfig usb0 192.168.42.1")
    print("3. Patient laptop should see new network interface")
    
    print("\nOption 3: Ethernet Cable")
    print("1. Connect ethernet cable between devices")
    print("2. Set static IPs on both sides")
    print(f"3. This device: 192.168.1.1, Patient: 192.168.1.2")
    print("\n" + "="*50)

def start_llm_backend():
    """Ensure LLM backend is running"""
    print("\nChecking LLM backend...")
    
    if CONFIG['llm_backend'] == 'ollama':
        # Check if Ollama is running
        try:
            import requests
            requests.get('http://localhost:11434/api/tags')
            print("✓ Ollama is running")
        except:
            print("Starting Ollama...")
            subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✓ Ollama started")
            
            # Pull model if needed
            print(f"Ensuring {CONFIG['model']} is available...")
            subprocess.run(['ollama', 'pull', CONFIG['model']])
    
    elif CONFIG['llm_backend'] == 'llamafile':
        print("Please start llamafile manually:")
        print(f"  ./llamafile --server --nobrowser")

if __name__ == '__main__':
    print("""
    ╦═╗┌─┐┌─┐┌┬┐╔╗╔┌─┐┬─┐┌┬┐
    ╠╦╝│ │├─┤ ││║║║├┤ ├┬┘ ││
    ╩╚═└─┘┴ ┴─┴┘╝╚╝└─┘┴└──┴┘
    Your Portable System Assistant
    """)
    
    # Setup steps
    start_llm_backend()
    setup_usb_network()
    
    # Get local IP for display
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = '127.0.0.1'
    
    print(f"\n✓ Server starting on:")
    print(f"  • http://localhost:{CONFIG['port']}")
    print(f"  • http://{local_ip}:{CONFIG['port']}")
    print(f"  • http://192.168.42.1:{CONFIG['port']} (USB network)")
    print(f"\n✓ Safe mode: {CONFIG['safe_mode']}")
    print(f"✓ LLM backend: {CONFIG['llm_backend']}")
    print("\nPress Ctrl+C to stop\n")
    
    # Start server
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=CONFIG['port'],
        debug=False  # Set True for development
    )