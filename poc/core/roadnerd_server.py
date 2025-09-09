#!/usr/bin/env python3
"""
RoadNerd Server - The "Smart Friend" Component
Run this on your BeeLink or second laptop with LLM installed
"""

import json
import sys
from pathlib import Path
import subprocess
import platform
import os
from datetime import datetime
from typing import Dict, List, Optional
import socket
import shutil
from pathlib import Path

# Imports (do not auto-install; fail with guidance)
try:
    from flask import Flask, request, jsonify, render_template_string, send_file, make_response
    from flask_cors import CORS
except ImportError:
    print("Missing dependencies for RoadNerd server: flask, flask-cors")
    print("Activate your venv (RN_VENV) and run: pip install flask flask-cors")
    sys.exit(1)

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configuration
CONFIG = {
    'llm_backend': 'ollama',  # or 'llamafile' or 'gpt4all'
    'model': 'llama3.2',
    'port': 8080,
    'safe_mode': True  # Don't execute commands automatically
}

# Environment overrides for easy experimentation
CONFIG['llm_backend'] = os.getenv('RN_LLM_BACKEND', CONFIG['llm_backend'])
CONFIG['model'] = os.getenv('RN_MODEL', CONFIG['model'])
try:
    CONFIG['port'] = int(os.getenv('RN_PORT', str(CONFIG['port'])))
except Exception:
    pass
sm = os.getenv('RN_SAFE_MODE', str(CONFIG['safe_mode']))
CONFIG['safe_mode'] = sm.lower() in ('1', 'true', 'yes', 'on')

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

    @staticmethod
    def ipv4_addresses() -> List[str]:
        """List IPv4 addresses for all non-loopback interfaces"""
        addrs: List[str] = []
        try:
            result = subprocess.run(['ip', '-4', '-o', 'addr', 'show'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[3].split('/')[0]
                    if ip != '127.0.0.1':
                        addrs.append(ip)
        except Exception:
            pass
        return addrs

class LLMInterface:
    """Interface to various LLM backends"""
    
    @staticmethod
    def query_ollama(prompt: str) -> str:
        """Query Ollama API"""
        try:
            import requests
            base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            # Deterministic-ish defaults for fast testing
            options = {
                'temperature': float(os.getenv('RN_TEMP', '0')),
                'num_predict': int(os.getenv('RN_NUM_PREDICT', '128'))
            }
            payload = {'model': CONFIG['model'], 'prompt': prompt, 'stream': False, 'options': options}
            response = requests.post(f'{base}/api/generate', json=payload)
            return response.json().get('response', 'No response from Ollama')
        except Exception as e:
            return f"Ollama not available: {e}"
    
    @staticmethod
    def query_llamafile(prompt: str) -> str:
        """Query llamafile server"""
        try:
            import requests
            base = os.getenv('LLAMAFILE_BASE_URL', 'http://localhost:8081')
            response = requests.post(f'{base}/completion', json={'prompt': prompt, 'n_predict': 200})
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

def _log_llm_run(record: Dict) -> None:
    """Append a single JSON record to logs/llm_runs/YYYYMMDD.jsonl (best-effort)."""
    try:
        # Prefer RN_LOG_DIR if set; otherwise use repo-root logs directory
        env_log_dir = os.getenv('RN_LOG_DIR')
        if env_log_dir:
            logs_dir = Path(env_log_dir)
        else:
            # Resolve repo root as .../RoadNerd from this file location
            repo_root = Path(__file__).resolve().parents[2]
            logs_dir = repo_root / 'logs' / 'llm_runs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime('%Y%m%d')
        out = logs_dir / f'{date}.jsonl'
        with out.open('a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as _:
        # Never break the API on logging errors
        pass


# BACKLOG++ Implementation: Brainstorm/Judge System
import uuid

class Idea:
    """Structured representation of a diagnostic/fix idea."""
    def __init__(self, hypothesis: str, category: str, why: str, 
                 checks: List[str] = None, fixes: List[str] = None, 
                 risk: str = "low", confidence: float = 0.5):
        self.id = str(uuid.uuid4())[:8]
        self.hypothesis = hypothesis
        self.category = category  # wifi, dns, network, performance, etc.
        self.why = why
        self.checks = checks or []
        self.fixes = fixes or []
        self.risk = risk  # low, medium, high
        self.confidence = confidence
        self.evidence = {}  # Will hold probe results
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'hypothesis': self.hypothesis,
            'category': self.category,
            'why': self.why,
            'checks': self.checks,
            'fixes': self.fixes,
            'risk': self.risk,
            'confidence': self.confidence,
            'evidence': self.evidence
        }

class BrainstormEngine:
    """Generate multiple structured ideas for a given issue."""
    
    @staticmethod
    def generate_ideas(issue: str, n: int = 5, creativity: int = 1) -> List[Idea]:
        """Generate N ideas with specified creativity level (0-3)."""
        
        # Adjust LLM parameters based on creativity
        temperature_map = {0: 0.0, 1: 0.3, 2: 0.7, 3: 1.0}
        temperature = temperature_map.get(creativity, 0.3)
        
        # Build brainstorming prompt
        system_info = SystemDiagnostics.get_system_info()
        connectivity = SystemDiagnostics.check_connectivity()
        
        prompt = f"""You are an expert system administrator brainstorming diagnostic approaches.

System: {system_info['platform']} {system_info.get('distro', '')}
Issue: {issue}
Connectivity: DNS={connectivity['dns']}, Gateway={connectivity['gateway']}

Generate {n} different diagnostic hypotheses. For each hypothesis, provide:
1. HYPOTHESIS: What might be causing this issue
2. CATEGORY: wifi/dns/network/performance/system/hardware
3. WHY: Brief reasoning for this hypothesis  
4. CHECKS: Specific read-only commands to test this hypothesis
5. FIXES: Potential solutions (if hypothesis is confirmed)
6. RISK: low/medium/high for the proposed fixes

Format each as JSON:
{{"hypothesis": "...", "category": "...", "why": "...", "checks": ["..."], "fixes": ["..."], "risk": "low"}}

Be creative and consider multiple angles. Include both common and uncommon causes."""

        # Get LLM response with higher creativity
        original_temp = os.getenv('RN_TEMP', '0')
        os.environ['RN_TEMP'] = str(temperature)
        
        try:
            llm_response = LLMInterface.get_response(prompt)
            ideas = BrainstormEngine._parse_ideas_response(llm_response, issue)
        finally:
            # Restore original temperature
            if original_temp:
                os.environ['RN_TEMP'] = original_temp
            else:
                os.environ.pop('RN_TEMP', None)
        
        return ideas[:n]  # Ensure we return exactly n ideas
    
    @staticmethod
    def _parse_ideas_response(response: str, issue: str) -> List[Idea]:
        """Parse LLM response into structured Idea objects."""
        ideas = []
        
        # Try to extract JSON objects from the response
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    idea_data = json.loads(line)
                    idea = Idea(
                        hypothesis=idea_data.get('hypothesis', 'Unknown hypothesis'),
                        category=idea_data.get('category', 'general'), 
                        why=idea_data.get('why', 'No reasoning provided'),
                        checks=idea_data.get('checks', []),
                        fixes=idea_data.get('fixes', []),
                        risk=idea_data.get('risk', 'medium')
                    )
                    ideas.append(idea)
                except json.JSONDecodeError:
                    continue
        
        # Fallback: if no valid JSON found, create a generic idea
        if not ideas:
            idea = Idea(
                hypothesis="Generic troubleshooting approach",
                category="general",
                why="LLM response could not be parsed into structured ideas",
                checks=["echo 'Manual analysis required'"],
                fixes=["Analyze the issue manually"],
                risk="low"
            )
            ideas.append(idea)
        
        return ideas

class JudgeEngine:
    """Score and rank ideas using deterministic criteria."""
    
    @staticmethod
    def judge_ideas(ideas: List[Idea], issue: str) -> List[Dict]:
        """Score and rank ideas, return ordered list with rationale."""
        
        scored_ideas = []
        system_info = SystemDiagnostics.get_system_info()
        
        for idea in ideas:
            scores = JudgeEngine._score_idea(idea, issue, system_info)
            
            # Calculate weighted total score
            total_score = (
                scores['safety'] * 0.3 +
                scores['success_likelihood'] * 0.4 +
                scores['cost'] * 0.2 +
                scores['determinism'] * 0.1
            )
            
            scored_ideas.append({
                'idea': idea.to_dict(),
                'scores': scores,
                'total_score': total_score,
                'rationale': JudgeEngine._generate_rationale(idea, scores)
            })
        
        # Sort by total score (descending)
        scored_ideas.sort(key=lambda x: x['total_score'], reverse=True)
        
        return scored_ideas
    
    @staticmethod
    def _score_idea(idea: Idea, issue: str, system_info: Dict) -> Dict:
        """Score an idea across multiple criteria (0.0 - 1.0)."""
        scores = {}
        
        # Safety score (higher = safer)
        risk_map = {'low': 0.9, 'medium': 0.6, 'high': 0.2}
        scores['safety'] = risk_map.get(idea.risk, 0.5)
        
        # Success likelihood (higher = more likely to work)
        likelihood = 0.5  # Default
        
        # Boost score for OS-appropriate suggestions
        if 'ubuntu' in system_info.get('distro', '').lower():
            if any('nmcli' in check.lower() for check in idea.checks):
                likelihood += 0.3
            if any('systemctl' in check.lower() for check in idea.checks):
                likelihood += 0.2
        
        # Boost for category match
        issue_lower = issue.lower()
        if (idea.category == 'wifi' and any(w in issue_lower for w in ['wifi', 'wireless'])) or \
           (idea.category == 'dns' and any(w in issue_lower for w in ['dns', 'resolution'])) or \
           (idea.category == 'network' and any(w in issue_lower for w in ['network', 'interface'])):
            likelihood += 0.2
            
        scores['success_likelihood'] = min(likelihood, 1.0)
        
        # Cost score (higher = cheaper/faster)
        cost = 0.8  # Default: most commands are cheap
        if any('reboot' in fix.lower() for fix in idea.fixes):
            cost = 0.3  # Reboots are expensive
        if any('reinstall' in fix.lower() for fix in idea.fixes):
            cost = 0.1  # Reinstalls are very expensive
            
        scores['cost'] = cost
        
        # Determinism score (higher = more predictable)  
        determinism = 0.7  # Default
        if len(idea.checks) > 0:
            determinism += 0.2  # Has diagnostic steps
        if len(idea.fixes) > 1:
            determinism -= 0.1  # Multiple fixes = less predictable
            
        scores['determinism'] = min(determinism, 1.0)
        
        return scores
    
    @staticmethod
    def _generate_rationale(idea: Idea, scores: Dict) -> str:
        """Generate human-readable rationale for the scoring."""
        rationale = f"Scored {scores.get('total_score', 0):.2f}/1.0. "
        
        if scores['safety'] < 0.5:
            rationale += "⚠️  High risk approach. "
        elif scores['safety'] > 0.8:
            rationale += "✅ Safe approach. "
            
        if scores['success_likelihood'] > 0.7:
            rationale += "Strong success indicators. "
        elif scores['success_likelihood'] < 0.4:
            rationale += "Low success probability. "
            
        if scores['cost'] < 0.5:
            rationale += "High cost/time investment."
        
        return rationale.strip()


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
            a { color: #7cf; }
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
                <div class="endpoint">GET <a href="/api-docs">/api-docs</a> - API Console (browser tests)</div>
            </div>
            <div class="status">
                <h2>Connection Info</h2>
                <div id="conn">Detecting local addresses...</div>
                <p>Recommended: direct Ethernet between Patient Box and this server. Common address: <code>10.55.0.1:8080</code>.</p>
            </div>
        </div>
        <script>
            fetch('/api/status')
              .then(r => r.json())
              .then(data => {
                document.getElementById('status').innerHTML = JSON.stringify(data, null, 2);
                const ips = (data.system && data.system.ips) ? data.system.ips : [];
                let html = '';
                if (ips.length) {
                  html += '<pre>Local IPv4 addresses:\n' + ips.map(ip => '  - ' + ip + ':8080').join('\n') + '</pre>';
                } else {
                  html += '<pre>No non-loopback IPv4 addresses detected.</pre>';
                }
                document.getElementById('conn').innerHTML = html;
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
        'system': {**SystemDiagnostics.get_system_info(), 'ips': SystemDiagnostics.ipv4_addresses()},
        'connectivity': SystemDiagnostics.check_connectivity(),
        'llm_backend': CONFIG['llm_backend'],
        'model': CONFIG['model'],
        'safe_mode': CONFIG['safe_mode']
    })

@app.route('/api-docs', methods=['GET'])
def api_docs():
    """Lightweight API console for browser testing"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>RoadNerd API Console</title>
      <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #0b1220; color: #e0e6f0; }
        h1, h2 { margin: 0 0 10px; }
        section { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        textarea, input { width: 100%; background: #0b1220; color: #e0e6f0; border: 1px solid #374151; border-radius: 6px; padding: 8px; }
        button { background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 8px 12px; cursor: pointer; }
        pre { background: #0b1220; padding: 12px; border-radius: 6px; overflow: auto; max-height: 320px; }
        label { display: block; margin: 6px 0; }
      </style>
    </head>
    <body>
      <h1>RoadNerd API Console</h1>
      <section>
        <h2>GET /api/status</h2>
        <button onclick="callStatus()">Call</button>
        <pre id="statusOut"></pre>
      </section>
      <section>
        <h2>POST /api/diagnose</h2>
        <label>Issue</label>
        <textarea id="issue" rows="4">My WiFi is not working</textarea>
        <button onclick="callDiagnose()">Diagnose</button>
        <pre id="diagOut"></pre>
      </section>
      <section>
        <h2>POST /api/execute</h2>
        <label>Command</label>
        <input id="cmd" value="whoami"/>
        <label><input id="force" type="checkbox"/> Force (override safe mode)</label>
        <button onclick="callExecute()">Execute</button>
        <pre id="execOut"></pre>
      </section>
      <section>
        <h2>POST /api/llm</h2>
        <label>Prompt</label>
        <textarea id="prompt" rows="3">What version of Ubuntu am I running?</textarea>
        <button onclick="callLLM()">Ask</button>
        <pre id="llmOut"></pre>
      </section>
      <script>
        function j(o){ return JSON.stringify(o, null, 2); }
        async function callStatus(){
          const r = await fetch('/api/status');
          document.getElementById('statusOut').textContent = j(await r.json());
        }
        async function callDiagnose(){
          const r = await fetch('/api/diagnose', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({issue: document.getElementById('issue').value})});
          document.getElementById('diagOut').textContent = j(await r.json());
        }
        async function callExecute(){
          const r = await fetch('/api/execute', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({command: document.getElementById('cmd').value, force: document.getElementById('force').checked})});
          document.getElementById('execOut').textContent = j(await r.json());
        }
        async function callLLM(){
          const r = await fetch('/api/llm', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prompt: document.getElementById('prompt').value})});
          document.getElementById('llmOut').textContent = j(await r.json());
        }
      </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/download/client.py', methods=['GET'])
def download_client():
    """Serve client file for patient bootstrap"""
    try:
        client_path = Path(__file__).parent / 'roadnerd_client.py'
        return send_file(str(client_path), as_attachment=True, download_name='roadnerd_client.py')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/download/ollama-models.tar.gz', methods=['GET'])  
def download_models():
    """Serve cached models for patient bootstrap"""
    try:
        from pathlib import Path
        models_path = Path.home() / '.roadnerd' / 'models' / 'ollama-models.tar.gz'
        if models_path.exists():
            return send_file(str(models_path), as_attachment=True, download_name='ollama-models.tar.gz')
        else:
            return jsonify({'error': 'Model cache not found. Run profile-machine.py --cache-models first'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/bootstrap.sh', methods=['GET'])
def bootstrap_script():
    """Serve bootstrap script for patient setup"""
    script = f'''#!/usr/bin/env bash
# RoadNerd Patient Bootstrap Script
set -euo pipefail

NERD_URL="${{1:-http://10.55.0.1:8080}}"
INSTALL_DIR="$HOME/.roadnerd"

echo "🤖 RoadNerd Patient Bootstrap"
echo "Connecting to Nerd at: $NERD_URL"

# Create installation directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download client
echo "📥 Downloading RoadNerd client..."
curl -fsSL "$NERD_URL/download/client.py" -o roadnerd_client.py
chmod +x roadnerd_client.py

# Check machine capability
TOTAL_RAM=$(free -m | awk 'NR==2{{printf "%.0f", $2}}')
echo "📊 Detected ${{TOTAL_RAM}}MB RAM"

if [ "$TOTAL_RAM" -gt 16000 ]; then
    echo "🚀 High-capacity machine - downloading model cache..."
    if curl -fsSL "$NERD_URL/download/ollama-models.tar.gz" -o ollama-models.tar.gz 2>/dev/null; then
        echo "🔧 Setting up Ollama..."
        if ! command -v ollama &> /dev/null; then
            echo "Installing Ollama..."
            curl -fsSL https://ollama.com/install.sh | sh
        fi
        
        echo "📦 Extracting models..."
        mkdir -p ~/.ollama
        tar xzf ollama-models.tar.gz -C ~/.ollama
        
        echo "🎯 Patient is now ready to be a Nerd!"
        echo "Run: ollama serve & && python3 roadnerd_server.py"
    else
        echo "⚠️  Model cache not available, will connect as client"
        python3 roadnerd_client.py "$NERD_URL"
    fi
else
    echo "💻 Standard machine - connecting as client"
    python3 roadnerd_client.py "$NERD_URL" 
fi
'''
    
    response = make_response(script)
    response.headers['Content-Type'] = 'text/x-shellscript'
    response.headers['Content-Disposition'] = 'attachment; filename="bootstrap.sh"'
    return response

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

    response_payload = {
        'issue': issue,
        'kb_solution': kb_solution,
        'llm_suggestion': llm_response,
        'system_context': system_info,
        'connectivity': connectivity
    }

    # Phase 0 logging (legacy mode)
    try:
        incoming = data if isinstance(data, dict) else {}
        _log_llm_run({
            'mode': 'legacy',
            'timestamp': datetime.now().isoformat(),
            'client': {
                'intent': incoming.get('intent'),
                'intent_analysis': incoming.get('intent_analysis'),
                'context_items': len(incoming.get('context', []) or [])
            },
            'issue_hash': str(hash(issue)) if issue else None,
            'issue': issue,
            'server': {
                'backend': CONFIG['llm_backend'],
                'model': CONFIG['model'],
                'safe_mode': CONFIG['safe_mode']
            },
            'system': system_info,
            'connectivity': connectivity,
            'result': {
                'has_kb': bool(kb_solution),
                'llm_tokens_est': len((llm_response or '').split()),
            }
        })
    except Exception:
        pass

    return jsonify(response_payload)

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


# BACKLOG++ API Endpoints

@app.route('/api/ideas/brainstorm', methods=['POST'])
def api_brainstorm():
    """Generate multiple structured diagnostic ideas (high creativity)."""
    data = request.get_json()
    
    if not data or 'issue' not in data:
        return jsonify({'error': 'Missing issue parameter'}), 400
    
    issue = data['issue']
    n = data.get('n', 5)  # Number of ideas to generate
    creativity = data.get('creativity', 2)  # 0-3 scale
    
    try:
        # Generate ideas with high exploration
        ideas = BrainstormEngine.generate_ideas(issue, n, creativity)
        
        # Log the brainstorming session
        _log_llm_run({
            'mode': 'brainstorm',
            'timestamp': datetime.now().isoformat(),
            'issue': issue,
            'creativity': creativity,
            'ideas_generated': len(ideas),
            'server': {
                'backend': CONFIG['llm_backend'],
                'model': CONFIG['model']
            },
            'ideas': [idea.to_dict() for idea in ideas]
        })
        
        return jsonify({
            'ideas': [idea.to_dict() for idea in ideas],
            'meta': {
                'count': len(ideas),
                'creativity': creativity,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Brainstorming failed: {str(e)}'}), 500

@app.route('/api/ideas/judge', methods=['POST']) 
def api_judge():
    """Score and rank ideas using deterministic criteria (temperature=0)."""
    data = request.get_json()
    
    if not data or 'ideas' not in data or 'issue' not in data:
        return jsonify({'error': 'Missing ideas or issue parameter'}), 400
    
    issue = data['issue']
    ideas_data = data['ideas']
    
    try:
        # Convert dict data back to Idea objects
        ideas = []
        for idea_dict in ideas_data:
            idea = Idea(
                hypothesis=idea_dict.get('hypothesis', ''),
                category=idea_dict.get('category', 'general'),
                why=idea_dict.get('why', ''),
                checks=idea_dict.get('checks', []),
                fixes=idea_dict.get('fixes', []),
                risk=idea_dict.get('risk', 'medium')
            )
            idea.id = idea_dict.get('id', idea.id)  # Preserve original ID
            ideas.append(idea)
        
        # Judge and rank ideas
        ranked = JudgeEngine.judge_ideas(ideas, issue)
        
        # Log the judging session
        _log_llm_run({
            'mode': 'judge',
            'timestamp': datetime.now().isoformat(),
            'issue': issue,
            'ideas_judged': len(ideas),
            'top_score': ranked[0]['total_score'] if ranked else 0,
            'server': {
                'backend': CONFIG['llm_backend'],
                'model': CONFIG['model']
            },
            'ranking': [r['idea']['id'] for r in ranked]
        })
        
        return jsonify({
            'ranked': ranked,
            'rationale': f"Judged {len(ideas)} ideas using safety, success likelihood, cost, and determinism criteria.",
            'meta': {
                'judged_count': len(ideas),
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Judging failed: {str(e)}'}), 500

@app.route('/api/ideas/probe', methods=['POST'])
def api_probe():
    """Run safe diagnostic checks and attach evidence to ideas.""" 
    data = request.get_json()
    
    if not data or 'ideas' not in data:
        return jsonify({'error': 'Missing ideas parameter'}), 400
    
    ideas_data = data['ideas']
    run_checks = data.get('run_checks', True)
    
    try:
        probed_ideas = []
        
        for idea_dict in ideas_data:
            idea = idea_dict.copy()
            
            if run_checks and 'checks' in idea:
                evidence = {}
                
                # Only run whitelisted read-only commands
                safe_commands = ['nmcli', 'ip addr', 'ip route', 'rfkill list', 
                               'systemctl status', 'journalctl', 'dig', 'nslookup']
                
                for check in idea['checks'][:3]:  # Limit to first 3 checks
                    if any(cmd in check.lower() for cmd in safe_commands):
                        try:
                            # Execute safe read-only command
                            analysis = CommandExecutor.analyze_command(check)
                            if analysis['risk_level'] == 'low':
                                result = subprocess.run(
                                    check, shell=True, 
                                    capture_output=True, text=True, 
                                    timeout=5
                                )
                                evidence[check] = {
                                    'stdout': result.stdout[:500],  # Truncate
                                    'stderr': result.stderr[:200],
                                    'returncode': result.returncode
                                }
                        except Exception as e:
                            evidence[check] = {'error': str(e)}
                
                idea['evidence'] = evidence
            
            probed_ideas.append(idea)
        
        # Log the probing session
        _log_llm_run({
            'mode': 'probe',
            'timestamp': datetime.now().isoformat(),
            'ideas_probed': len(probed_ideas),
            'checks_run': run_checks,
            'server': {
                'backend': CONFIG['llm_backend'], 
                'model': CONFIG['model']
            }
        })
        
        return jsonify({
            'probed_ideas': probed_ideas,
            'meta': {
                'probed_count': len(probed_ideas),
                'checks_executed': run_checks,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Probing failed: {str(e)}'}), 500


def print_connection_guidance():
    """Show connection guidance for direct Ethernet setups"""
    print("\n" + "="*50)
    print("CONNECTION GUIDANCE")
    print("="*50)
    print("- Recommended: direct Ethernet between this server and the Patient Box.")
    print("- Typical server address: 10.55.0.1 (port 8080).")
    print("- Client: run the RoadNerd client and it will auto-discover the server.")
    print("- Browser API Console: /api-docs on any of the local IPs shown below.")
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
    print_connection_guidance()
    
    # Get local IP for display
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = '127.0.0.1'
    
    print(f"\n✓ Server starting on:")
    print(f"  • http://localhost:{CONFIG['port']}")
    print(f"  • http://{local_ip}:{CONFIG['port']}")
    # Print all detected IPv4s
    ips = SystemDiagnostics.ipv4_addresses()
    if ips:
        print("  • Local IPv4s:")
        for ip in ips:
            print(f"    - http://{ip}:{CONFIG['port']}")
    print(f"\n✓ Safe mode: {CONFIG['safe_mode']}")
    print(f"✓ LLM backend: {CONFIG['llm_backend']}")
    print("\nPress Ctrl+C to stop\n")
    
    # Start server
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=CONFIG['port'],
        debug=False  # Set True for development
    )
