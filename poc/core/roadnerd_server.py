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

# Ensure local imports (classify.py, retrieval.py) resolve when running as a script
try:
    if str(Path(__file__).parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).parent))
except Exception:
    pass

# Import modular components
from modules.system_diagnostics import SystemDiagnostics
from modules.command_executor import CommandExecutor

# Configuration
CONFIG = {
    'llm_backend': 'ollama',  # or 'llamafile' or 'gpt4all'
    'model': 'llama3.2',
    'port': 8080,
    'safe_mode': True,  # Don't execute commands automatically
    'bind_host': '0.0.0.0'  # Default bind host (override via RN_BIND or RN_BIND_HOST)
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
# Bind host: explicit env takes precedence; RN_PROD defaults to 10.55.0.1
CONFIG['bind_host'] = os.getenv('RN_BIND', os.getenv('RN_BIND_HOST', CONFIG['bind_host']))
if os.getenv('RN_PROD', '0').lower() in ('1', 'true', 'yes', 'on') and not os.getenv('RN_BIND') and not os.getenv('RN_BIND_HOST'):
    CONFIG['bind_host'] = '10.55.0.1'

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


class LLMInterface:
    """Interface to various LLM backends"""
    
    @staticmethod
    def query_ollama(prompt: str, options_overrides: Optional[Dict] = None) -> str:
        """Query Ollama API - automatically selects chat vs generate based on model"""
        try:
            import requests
            base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            
            # Check if we should use chat mode (auto-detect GPT-OSS models or force via env)
            use_chat_mode = os.getenv('RN_USE_CHAT_MODE', 'auto').lower()
            force_chat = (use_chat_mode == 'force') or (use_chat_mode == 'auto' and CONFIG['model'].startswith('gpt-oss'))
            
            # Defaults from environment with GPT-OSS specific settings
            if force_chat:
                # GPT-OSS needs temperature=1.0, top_p=1.0 by default
                options = {
                    'temperature': float(os.getenv('RN_TEMP', '1.0')),
                    'top_p': float(os.getenv('RN_TOP_P', '1.0')),
                    'num_predict': int(os.getenv('RN_NUM_PREDICT', '128')),
                    'num_ctx': int(os.getenv('RN_NUM_CTX', '2048')),
                }
            else:
                # Standard models use previous defaults
                options = {
                    'temperature': float(os.getenv('RN_TEMP', '0')),
                    'num_predict': int(os.getenv('RN_NUM_PREDICT', '128')),
                    'num_ctx': int(os.getenv('RN_NUM_CTX', '2048')),
                }
            
            if options_overrides:
                options.update({k: v for k, v in options_overrides.items() if v is not None})
            
            if force_chat:
                # Use chat API for GPT-OSS models
                payload = {
                    'model': CONFIG['model'],
                    'messages': [
                        {'role': 'system', 'content': 'You are a helpful diagnostic assistant.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'stream': False,
                    'options': options,
                }
                response = requests.post(f'{base}/api/chat', json=payload)
                result = response.json()
                if 'message' in result and 'content' in result['message']:
                    return result['message']['content']
                else:
                    return result.get('response', 'No response from Ollama chat API')
            else:
                # Use generate API for standard models
                payload = {
                    'model': CONFIG['model'],
                    'prompt': prompt,
                    'stream': False,
                    'options': options,
                }
                response = requests.post(f'{base}/api/generate', json=payload)
                return response.json().get('response', 'No response from Ollama')
        except Exception as e:
            return f"Ollama not available: {e}"
    
    @staticmethod
    def query_llamafile(prompt: str, options_overrides: Optional[Dict] = None) -> str:
        """Query llamafile server"""
        try:
            import requests
            base = os.getenv('LLAMAFILE_BASE_URL', 'http://localhost:8081')
            response = requests.post(f'{base}/completion', json={'prompt': prompt, 'n_predict': 200})
            return response.json().get('content', 'No response from llamafile')
        except Exception as e:
            return f"Llamafile not available: {e}"
    
    @staticmethod
    def get_response(prompt: str, *, temperature: Optional[float] = None, num_predict: Optional[int] = None, top_p: Optional[float] = None) -> str:
        """Get response from configured LLM with optional per-request options."""
        overrides = {'temperature': temperature, 'num_predict': num_predict, 'top_p': top_p}
        if CONFIG['llm_backend'] == 'ollama':
            return LLMInterface.query_ollama(prompt, options_overrides=overrides)
        elif CONFIG['llm_backend'] == 'llamafile':
            return LLMInterface.query_llamafile(prompt, options_overrides=overrides)
        else:
            return "No LLM backend configured"


# Prompt loader and simple templating
def _load_template(kind: str, category_hint: Optional[str] = None) -> str:
    base_dir = os.getenv('RN_PROMPT_DIR')
    search_dirs = []
    if base_dir:
        search_dirs.append(Path(base_dir))
    search_dirs.append(Path(__file__).parent / 'prompts')

    names = []
    if category_hint:
        names.append(f"{kind}.{category_hint}.txt")
    names.append(f"{kind}.base.txt")

    for d in search_dirs:
        for name in names:
            p = d / name
            if p.exists():
                try:
                    return p.read_text(encoding='utf-8')
                except Exception:
                    continue
    # Fallback minimal template
    return "Issue: {{ISSUE}}\nSystem: {{SYSTEM}}\nChecks and fixes please."


def _render_template(tpl: str, ctx: Dict[str, str]) -> str:
    # Very small mustache-like rendering for optional blocks
    def toggle_block(text: str, key: str, value: str) -> str:
        start = f"{{{{#{key}}}}}"
        end = f"{{{{/{key}}}}}"
        while True:
            i = text.find(start)
            if i == -1:
                break
            j = text.find(end, i)
            if j == -1:
                break
            inner = text[i + len(start): j]
            replacement = inner if value else ''
            text = text[:i] + replacement + text[j + len(end):]
        return text

    out = tpl
    # Optional blocks
    out = toggle_block(out, 'CATEGORY_HINT', ctx.get('CATEGORY_HINT') or '')
    out = toggle_block(out, 'RETRIEVAL', ctx.get('RETRIEVAL') or '')
    # Simple replacements
    for k, v in ctx.items():
        out = out.replace(f"{{{{{k}}}}}", v or '')
    return out



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

def _logs_dir() -> Path:
    """Resolve the logs directory honoring RN_LOG_DIR, else repo logs/llm_runs."""
    env_log_dir = os.getenv('RN_LOG_DIR')
    if env_log_dir:
        d = Path(env_log_dir)
        d.mkdir(parents=True, exist_ok=True)
        return d
    repo_root = Path(__file__).resolve().parents[2]
    d = repo_root / 'logs' / 'llm_runs'
    d.mkdir(parents=True, exist_ok=True)
    return d


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
    def generate_ideas(issue: str, n: int = 5, creativity: int = 1, category_hint: Optional[str] = None, retrieval_text: str = "") -> List[Idea]:
        """Generate N ideas with specified creativity level (0-3)."""
        
        # Adjust LLM parameters based on creativity
        temperature_map = {0: 0.0, 1: 0.3, 2: 0.7, 3: 1.0}
        temperature = temperature_map.get(creativity, 0.3)
        
        # Build brainstorming prompt (template, optional category hint)
        system_info = SystemDiagnostics.get_system_info()
        connectivity = SystemDiagnostics.check_connectivity()
        tpl = _load_template('brainstorm', category_hint=category_hint)
        ctx = {
            'SYSTEM': json.dumps(system_info, ensure_ascii=False),
            'CONNECTIVITY': json.dumps(connectivity, ensure_ascii=False),
            'ISSUE': issue,
            'CATEGORY_HINT': category_hint or '',
            'N': str(n),
            'RETRIEVAL': retrieval_text or '',
        }
        prompt = _render_template(tpl, ctx)

        # Get LLM response with per-request creativity
        # Each JSON idea ~100-200 tokens, so scale appropriately
        num_predict = max(512, n * 120)  # At least 120 tokens per idea
        llm_response = LLMInterface.get_response(
            prompt,
            temperature=temperature,
            num_predict=num_predict,
        )
        ideas = BrainstormEngine._parse_ideas_response(llm_response, issue)
        
        return ideas[:n]  # Ensure we return exactly n ideas
    
    @staticmethod
    def _parse_ideas_response(response: str, issue: str) -> List[Idea]:
        """Parse LLM response into structured Idea objects (tolerant of arrays, fences)."""
        def to_idea(obj: Dict) -> Idea:
            return Idea(
                hypothesis=obj.get('hypothesis', 'Unknown hypothesis'),
                category=obj.get('category', 'general'),
                why=obj.get('why', 'No reasoning provided'),
                checks=obj.get('checks', []),
                fixes=obj.get('fixes', []),
                risk=obj.get('risk', 'medium')
            )

        ideas: List[Idea] = []

        text = response or ''

        # 1) Direct JSON parse (array or object)
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        ideas.append(to_idea(item))
            elif isinstance(data, dict):
                # Possibly {"ideas": [...]}
                if isinstance(data.get('ideas'), list):
                    for item in data['ideas']:
                        if isinstance(item, dict):
                            ideas.append(to_idea(item))
                else:
                    ideas.append(to_idea(data))
        except Exception:
            pass

        # 2) Parse fenced code blocks ```json ... ```
        if not ideas:
            import re
            fence_pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
            for block in fence_pattern.findall(text):
                block = block.strip()
                try:
                    blk = json.loads(block)
                    if isinstance(blk, list):
                        for item in blk:
                            if isinstance(item, dict):
                                ideas.append(to_idea(item))
                    elif isinstance(blk, dict):
                        if isinstance(blk.get('ideas'), list):
                            for item in blk['ideas']:
                                if isinstance(item, dict):
                                    ideas.append(to_idea(item))
                        else:
                            ideas.append(to_idea(blk))
                except Exception:
                    continue

        # 3) Parse numbered JSON list format (1. {...}, 2. {...})
        if not ideas:
            import re
            # Match numbered items with JSON objects
            numbered_pattern = re.compile(r'^\d+\.\s*(\{.*?\})', re.MULTILINE | re.DOTALL)
            for match in numbered_pattern.findall(text):
                try:
                    obj = json.loads(match)
                    if isinstance(obj, dict):
                        ideas.append(to_idea(obj))
                except Exception:
                    continue

        # 4) Curly-brace balanced objects found in text
        if not ideas:
            buf = []
            depth = 0
            for ch in text:
                if ch == '{':
                    depth += 1
                if depth > 0:
                    buf.append(ch)
                if ch == '}':
                    depth -= 1
                    if depth == 0 and buf:
                        candidate = ''.join(buf)
                        buf = []
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict):
                                ideas.append(to_idea(obj))
                        except Exception:
                            continue

        # 5) Fallback
        if not ideas:
            ideas.append(Idea(
                hypothesis="Generic troubleshooting approach",
                category="general",
                why="LLM response could not be parsed into structured ideas",
                checks=["echo 'Manual analysis required'"],
                fixes=["Analyze the issue manually"],
                risk="low"
            ))

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

@app.route('/api/model/switch', methods=['POST'])
def api_model_switch():
    """Switch to a different model"""
    data = request.get_json() or {}
    new_model = data.get('model')
    
    if not new_model:
        return jsonify({'error': 'Model name required'}), 400
    
    # Verify model exists in Ollama
    try:
        import requests
        base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        response = requests.get(f'{base}/api/tags')
        if response.status_code == 200:
            available_models = [m['name'] for m in response.json().get('models', [])]
            if new_model not in available_models:
                return jsonify({
                    'error': f'Model {new_model} not found',
                    'available_models': available_models
                }), 400
        else:
            return jsonify({'error': 'Could not connect to Ollama'}), 500
    except Exception as e:
        return jsonify({'error': f'Ollama error: {str(e)}'}), 500
    
    # Switch the model
    old_model = CONFIG['model']
    CONFIG['model'] = new_model
    
    # Test the new model
    try:
        test_response = LLMInterface.get_response("Hello", temperature=0.1, num_predict=10)
        if "not available" in test_response or "error" in test_response.lower():
            # Revert if test fails
            CONFIG['model'] = old_model
            return jsonify({'error': f'Model {new_model} failed test: {test_response}'}), 500
    except Exception as e:
        # Revert if test fails
        CONFIG['model'] = old_model
        return jsonify({'error': f'Model test failed: {str(e)}'}), 500
    
    return jsonify({
        'success': True,
        'previous_model': old_model,
        'current_model': CONFIG['model'],
        'test_response': test_response[:100] + '...' if len(test_response) > 100 else test_response
    })

@app.route('/api/model/list', methods=['GET'])
def api_model_list():
    """Get list of available models"""
    try:
        import requests
        base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        response = requests.get(f'{base}/api/tags')
        if response.status_code == 200:
            models = response.json().get('models', [])
            return jsonify({
                'current_model': CONFIG['model'],
                'available_models': [
                    {
                        'name': m['name'],
                        'size': m.get('size', 'unknown'),
                        'modified': m.get('modified_at', ''),
                        'current': m['name'] == CONFIG['model']
                    }
                    for m in models
                ]
            })
        else:
            return jsonify({'error': 'Could not connect to Ollama'}), 500
    except Exception as e:
        return jsonify({'error': f'Ollama error: {str(e)}'}), 500

@app.route('/api/profile/standard', methods=['POST'])
def api_profile_standard():
    """Run standard profiling test on CURRENT model only"""
    try:
        import time
        import psutil
        import requests
        import os
        
        # Use the challenging 5-idea stress test
        test_issue = "My laptop turned dark green all over sudden... what happened?"
        
        # Get baseline system metrics
        process = psutil.Process()
        cpu_before = psutil.cpu_percent(interval=1)
        memory_before = psutil.virtual_memory()
        
        payload = {
            'issue': test_issue,
            'n': 5,  # The challenging 5-idea test  
            'creativity': 2,
            'debug': True
        }
        
        # Time the request
        start_time = time.time()
        
        # Call our own brainstorm endpoint
        response = requests.post(
            'http://localhost:8080/api/ideas/brainstorm',
            json=payload,
            timeout=120  # Increased timeout for large models like 34B
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code != 200:
            raise Exception(f"Brainstorm API call failed: {response.status_code}")
            
        result = response.json()
        
        # Get post-test system metrics  
        cpu_after = psutil.cpu_percent(interval=1)
        memory_after = psutil.virtual_memory()
        
        # Calculate performance metrics
        model = CONFIG['model']
        
        # Estimate tokens (rough approximation)
        response_text = str(result)
        estimated_tokens = len(response_text.split()) * 1.3  # ~1.3 tokens per word
        tokens_per_sec = estimated_tokens / response_time if response_time > 0 else 0
        
        # Get model size info from Ollama
        try:
            ollama_response = requests.get(f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags", timeout=5)
            model_info = {}
            if ollama_response.status_code == 200:
                models = ollama_response.json().get('models', [])
                for m in models:
                    if m['name'] == model:
                        # Size is in bytes, convert to GB
                        size_gb = int(m.get('size', 0)) / (1024**3)
                        model_info = {
                            'size_gb': round(size_gb, 1),
                            'modified': m.get('modified_at', 'unknown')
                        }
                        break
        except:
            model_info = {'size_gb': 'unknown', 'modified': 'unknown'}
        
        # Performance metrics
        performance_metrics = {
            'response_time_sec': round(response_time, 2),
            'tokens_per_second': round(tokens_per_sec, 1),
            'estimated_tokens': round(estimated_tokens),
            'cpu_usage_percent': round((cpu_before + cpu_after) / 2, 1),
            'ram_usage_percent': round(memory_after.percent, 1),
            'ram_used_gb': round(memory_after.used / (1024**3), 1),
            'model_size_disk_gb': model_info.get('size_gb', 'unknown'),
            'model_modified': model_info.get('modified', 'unknown')
        }
        
        # Analyze results
        ideas_count = len(result.get('ideas', []))
        success = ideas_count >= 3  # Success if 3+ ideas generated
        n_idea_success = ideas_count >= 5  # Perfect if all 5 ideas
        
        # Categorize model size
        model = CONFIG['model']
        if '1b' in model.lower():
            size_category = 'tiny'
        elif '3b' in model.lower():
            size_category = 'small' 
        elif '7b' in model.lower() or '8b' in model.lower():
            size_category = 'medium'
        elif '13b' in model.lower():
            size_category = 'large'
        elif '20b' in model.lower() or '34b' in model.lower():
            size_category = 'xlarge'
        else:
            size_category = 'unknown'
            
        # More stringent production readiness criteria  
        production_ready = (
            success and 
            ideas_count >= 4 and
            tokens_per_sec >= 5.0 and  # At least 5 tokens/sec
            response_time <= 30.0 and  # Under 30 seconds
            memory_after.percent <= 85  # RAM usage under 85%
        )
        
        return jsonify({
            'model': model,
            'test_issue': test_issue,
            'result': result,
            'performance_metrics': performance_metrics,
            'analysis': {
                'ideas_generated': ideas_count,
                'success': success,
                'n_idea_generation_success': n_idea_success,
                'model_size_category': size_category,
                'production_ready': production_ready,
                'performance_tier': 'excellent' if ideas_count >= 5 else 'good' if ideas_count >= 3 else 'poor',
                'speed_rating': 'fast' if tokens_per_sec >= 15 else 'medium' if tokens_per_sec >= 5 else 'slow'
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Standard profile test failed: {str(e)}'}), 500

@app.route('/api/test-presets', methods=['GET'])
def api_test_presets():
    """Get predefined test issues for profiling"""
    presets = {
        'hardware': [
            "My laptop turned dark green all over sudden... what happened?",
            "Computer won't boot, just shows black screen",
            "Laptop gets extremely hot and shuts down randomly",
            "USB ports stopped working after Windows update"
        ],
        'network': [
            "DNS resolution is failing on Ubuntu", 
            "WiFi keeps disconnecting every few minutes",
            "Can't connect to work VPN from home",
            "Internet is slow but only on this computer"
        ],
        'system': [
            "System randomly freezes during video calls",
            "Dual boot time is wrong between Windows and Linux",
            "Getting blue screen errors with MEMORY_MANAGEMENT",
            "Audio crackling and popping through headphones"
        ],
        'stress_tests': [
            "My laptop turned dark green all over sudden... what happened?", # The 5-idea challenge
            "Complex network issue with multiple symptoms: DNS fails, VPN won't connect, and WiFi drops randomly", # JSON parsing challenge
            "Generate comprehensive troubleshooting for enterprise server that won't boot" # Large response test
        ]
    }
    
    return jsonify(presets)

@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Return JSONL logs for a given date with optional filtering."""
    try:
        import json as _json
        logs_dir = _logs_dir()
        date = request.args.get('date')
        mode = request.args.get('mode')
        limit = int(request.args.get('limit', '200'))

        files = sorted(logs_dir.glob('*.jsonl'))
        if not files:
            return jsonify({'date': None, 'count': 0, 'entries': []})

        target = None
        if date:
            cand = logs_dir / f"{date}.jsonl"
            target = cand if cand.exists() else None
        if target is None:
            target = files[-1]

        entries = []
        with target.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = _json.loads(line)
                    if mode and obj.get('mode') != mode:
                        continue
                    entries.append(obj)
                except Exception:
                    continue
        # Keep only the last N entries
        if limit and len(entries) > limit:
            entries = entries[-limit:]

        return jsonify({
            'date': target.stem,
            'count': len(entries),
            'files': [p.name for p in files],
            'entries': entries
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logs', methods=['GET'])
def logs_view():
    """Simple browser viewer for JSONL logs with filters."""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>RoadNerd Logs</title>
      <style>
        body { font-family: system-ui, sans-serif; background: #0b1220; color: #e0e6f0; padding: 20px; }
        header { margin-bottom: 12px; }
        select, input { background: #111827; color: #e0e6f0; border: 1px solid #374151; border-radius: 6px; padding: 6px; }
        button { background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 6px 10px; cursor: pointer; }
        pre { background: #0b1220; border: 1px solid #1f2937; border-radius: 8px; padding: 10px; max-height: 60vh; overflow: auto; }
        .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
      </style>
    </head>
    <body>
      <h1>RoadNerd Logs</h1>
      <div class="row">
        <label>Date <input id="date" placeholder="YYYYMMDD (optional)"/></label>
        <label>Mode
          <select id="mode">
            <option value="">(any)</option>
            <option>legacy</option>
            <option>prompt_suite</option>
            <option>brainstorm</option>
            <option>probe</option>
            <option>judge</option>
            <option>disambiguation</option>
          </select>
        </label>
        <label>Limit <input id="limit" value="200" size="4"/></label>
        <button onclick="loadLogs()">Load</button>
      </div>
      <pre id="out">(no data)</pre>
      <script>
        function j(o){ return JSON.stringify(o, null, 2); }
        async function loadLogs(){
          const d = document.getElementById('date').value.trim();
          const m = document.getElementById('mode').value;
          const l = document.getElementById('limit').value;
          const qs = new URLSearchParams();
          if (d) qs.set('date', d);
          if (m) qs.set('mode', m);
          if (l) qs.set('limit', l);
          const r = await fetch('/api/logs?' + qs.toString());
          const data = await r.json();
          document.getElementById('out').textContent = j(data);
        }
        loadLogs();
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
        <h2>Token (optional)</h2>
        <label>Authorization: Bearer <input id="token" placeholder="token for gated endpoints"/></label>
      </section>
      <section>
        <h2>GET /api/status</h2>
        <button onclick="callStatus()">Call</button>
        <pre id="statusOut"></pre>
      </section>
      <section>
        <h2>POST /api/diagnose</h2>
        <label>Issue</label>
        <textarea id="issue" rows="4">My WiFi is not working</textarea>
        <label><input id="diagDebug" type="checkbox"/> Debug</label>
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
        <h2>POST /api/ideas/brainstorm</h2>
        <label>Issue</label>
        <textarea id="issueIdeas" rows="3">DNS resolution is failing on Ubuntu.</textarea>
        <label>N ideas</label>
        <input id="nIdeas" value="5"/>
        <label>Creativity (0-3)</label>
        <input id="creativity" value="2"/>
        <label><input id="brainDebug" type="checkbox"/> Debug</label>
        <button onclick="callBrainstorm()">Brainstorm</button>
        <pre id="brainOut"></pre>
      </section>
      <section>
        <h2>POST /api/ideas/probe</h2>
        <label>Ideas JSON (array)</label>
        <textarea id="ideasJSON" rows="5">[{"hypothesis":"DNS misconfiguration","category":"dns","why":"resolv.conf wrong","checks":["cat /etc/resolv.conf","dig example.com"]}]</textarea>
        <label><input id="runChecks" type="checkbox" checked/> Run checks</label>
        <button onclick="callProbe()">Probe</button>
        <pre id="probeOut"></pre>
      </section>
      <section>
        <h2>POST /api/ideas/judge</h2>
        <label>Issue</label>
        <input id="issueJudge" value="DNS resolution is failing"/>
        <label>Ideas JSON (array)</label>
        <textarea id="ideasJudge" rows="5">[{"hypothesis":"DNS misconfiguration","category":"dns","why":"resolv.conf wrong","checks":["cat /etc/resolv.conf"],"fixes":["sudo systemctl restart systemd-resolved"],"risk":"low"}]</textarea>
        <button onclick="callJudge()">Judge</button>
        <pre id="judgeOut"></pre>
      </section>
      <section>
        <h2>POST /api/llm</h2>
        <label>Prompt</label>
        <textarea id="prompt" rows="3">What version of Ubuntu am I running?</textarea>
        <button onclick="callLLM()">Ask</button>
        <pre id="llmOut"></pre>
      </section>
      <section>
        <h2>Standard Profiling Suite</h2>
        <button onclick="loadTestPresets()">📋 Load Test Issue Presets</button>
        <button onclick="runStandardProfile()" style="background: #059669; margin-left: 10px;">🧪 Run Standard Profile</button>
        <br><br>
        <label>Test Categories:</label>
        <select id="presetCategory" onchange="loadCategoryIssues()" style="width: 200px; margin: 5px;">
          <option value="">Select category...</option>
          <option value="hardware">Hardware Issues</option>
          <option value="network">Network Issues</option>
          <option value="system">System Issues</option>
          <option value="stress_tests">Stress Tests</option>
        </select>
        <br>
        <label>Select Test Issue:</label>
        <select id="presetIssue" onchange="usePresetIssue()" style="width: 100%; margin: 5px 0;">
          <option value="">Choose an issue to auto-fill...</option>
        </select>
        <pre id="presetOut">Standard profiling will test N-idea generation across multiple models with predefined diagnostic scenarios</pre>
      </section>
      <section>
        <h2>Model Switching</h2>
        <button onclick="getModel()">🔄 List Available Models</button>
        <br><br>
        <label>Select Model:</label>
        <select id="modelSelect" style="width: 300px; margin: 5px 0;">
          <option value="">Loading models...</option>
        </select>
        <br>
        <label>Or enter manually:</label>
        <input id="newModel" placeholder="e.g., llama3.2:3b or gpt-oss:20b" style="width: 300px;"/>
        <br><br>
        <button onclick="setModel()" style="background: #007acc; color: white; padding: 8px 16px;">🔄 Switch Model</button>
        <pre id="modelOut">Click "List Available Models" to see all models</pre>
      </section>
      <script>
        function j(o){ return JSON.stringify(o, null, 2); }
        function headers(){
          const t = document.getElementById('token').value.trim();
          const h = {'Content-Type':'application/json'};
          if (t) h['Authorization'] = 'Bearer ' + t;
          return h;
        }
        async function callStatus(){
          const r = await fetch('/api/status');
          document.getElementById('statusOut').textContent = j(await r.json());
        }
        async function callDiagnose(){
          const body = {issue: document.getElementById('issue').value};
          if (document.getElementById('diagDebug').checked) body.debug = true;
          const r = await fetch('/api/diagnose', {method:'POST', headers: headers(), body: JSON.stringify(body)});
          document.getElementById('diagOut').textContent = j(await r.json());
        }
        async function callExecute(){
          const r = await fetch('/api/execute', {method:'POST', headers: headers(), body: JSON.stringify({command: document.getElementById('cmd').value, force: document.getElementById('force').checked})});
          document.getElementById('execOut').textContent = j(await r.json());
        }
        async function callBrainstorm(){
          showProgress('brainOut', '🧠 Generating ideas... (may take 15-30s for larger models)');
          const body = {issue: document.getElementById('issueIdeas').value, n: parseInt(document.getElementById('nIdeas').value||'5'), creativity: parseInt(document.getElementById('creativity').value||'2')};
          if (document.getElementById('brainDebug').checked) body.debug = true;
          const r = await fetch('/api/ideas/brainstorm', {method:'POST', headers: headers(), body: JSON.stringify(body)});
          document.getElementById('brainOut').textContent = j(await r.json());
        }
        async function callProbe(){
          const ideas = JSON.parse(document.getElementById('ideasJSON').value || '[]');
          const body = {ideas: ideas, run_checks: document.getElementById('runChecks').checked};
          const r = await fetch('/api/ideas/probe', {method:'POST', headers: headers(), body: JSON.stringify(body)});
          document.getElementById('probeOut').textContent = j(await r.json());
        }
        async function callJudge(){
          const ideas = JSON.parse(document.getElementById('ideasJudge').value || '[]');
          const body = {issue: document.getElementById('issueJudge').value, ideas: ideas};
          const r = await fetch('/api/ideas/judge', {method:'POST', headers: headers(), body: JSON.stringify(body)});
          document.getElementById('judgeOut').textContent = j(await r.json());
        }
        async function callLLM(){
          showProgress('llmOut', '🧠 LLM processing...');
          const r = await fetch('/api/llm', {method:'POST', headers: headers(), body: JSON.stringify({prompt: document.getElementById('prompt').value})});
          document.getElementById('llmOut').textContent = j(await r.json());
        }
        async function getModel(){
          document.getElementById('modelOut').textContent = '🔄 Loading available models...';
          const r = await fetch('/api/model/list', {headers: headers()});
          const data = await r.json();
          document.getElementById('modelOut').textContent = j(data);
          
          // Auto-populate dropdown if models available
          if (data.available_models) {
            const select = document.getElementById('modelSelect');
            if (select) {
              select.innerHTML = '<option value="">Choose model...</option>';
              data.available_models.forEach(m => {
                const option = document.createElement('option');
                option.value = m.name;
                option.textContent = `${m.name} (${m.size})${m.current ? ' [CURRENT]' : ''}`;
                option.selected = m.current;
                select.appendChild(option);
              });
            }
          }
        }
        async function setModel(){
          const m = document.getElementById('newModel').value || document.getElementById('modelSelect')?.value;
          if (!m) {
            document.getElementById('modelOut').textContent = 'Please enter or select a model name';
            return;
          }
          
          document.getElementById('modelOut').textContent = `🔄 Switching to ${m}... (testing model)`;
          const r = await fetch('/api/model/switch', {method:'POST', headers: headers(), body: JSON.stringify({model: m})});
          const data = await r.json();
          document.getElementById('modelOut').textContent = j(data);
          
          // Refresh model list if successful
          if (data.success) {
            setTimeout(getModel, 500);
          }
        }
        
        // Add progress indicators for LLM calls
        function showProgress(elementId, message = '🧠 LLM thinking...') {
          document.getElementById(elementId).textContent = message;
        }
        
        // Standard Profiling Functions
        let testPresets = {};
        
        async function loadTestPresets() {
          try {
            const r = await fetch('/api/test-presets');
            testPresets = await r.json();
            document.getElementById('presetOut').textContent = 'Test presets loaded! Select a category to see available issues.';
          } catch (e) {
            document.getElementById('presetOut').textContent = 'Error loading presets: ' + e.message;
          }
        }
        
        function loadCategoryIssues() {
          const category = document.getElementById('presetCategory').value;
          const select = document.getElementById('presetIssue');
          select.innerHTML = '<option value="">Choose an issue to auto-fill...</option>';
          
          if (category && testPresets[category]) {
            testPresets[category].forEach(issue => {
              const option = document.createElement('option');
              option.value = issue;
              option.textContent = issue;
              select.appendChild(option);
            });
          }
        }
        
        function usePresetIssue() {
          const issue = document.getElementById('presetIssue').value;
          if (issue) {
            document.getElementById('issueIdeas').value = issue;
            document.getElementById('presetOut').textContent = `Selected: "${issue}" - Ready to test brainstorming!`;
          }
        }
        
        async function runStandardProfile() {
          document.getElementById('presetOut').textContent = '🧪 Running 5-idea stress test on current model... (may take 15-30s)';
          
          try {
            const r = await fetch('/api/profile/standard', {method: 'POST', headers: headers()});
            const data = await r.json();
            
            if (data.error) {
              document.getElementById('presetOut').textContent = 'Error: ' + data.error;
              return;
            }
            
            const analysis = data.analysis;
            const metrics = data.performance_metrics;
            let output = `STANDARD PROFILE RESULTS\\n\\n`;
            output += `Model: ${data.model}\\n`;
            output += `Test: "${data.test_issue}"\\n\\n`;
            
            // Performance metrics
            output += `PERFORMANCE METRICS:\\n`;
            output += `• Response Time: ${metrics.response_time_sec}s\\n`;
            output += `• Tokens/Second: ${metrics.tokens_per_second} (${analysis.speed_rating})\\n`;
            output += `• Estimated Tokens: ${metrics.estimated_tokens}\\n`;
            output += `• CPU Usage: ${metrics.cpu_usage_percent}%\\n`;
            output += `• RAM Usage: ${metrics.ram_usage_percent}% (${metrics.ram_used_gb}GB)\\n`;
            output += `• Model Size: ${metrics.model_size_disk_gb}GB on disk\\n\\n`;
            
            // Quality analysis
            output += `QUALITY ANALYSIS:\\n`;
            output += `• Ideas Generated: ${analysis.ideas_generated}/5\\n`;
            output += `• Success: ${analysis.success ? '✅ PASS' : '❌ FAIL'}\\n`;
            output += `• N-Idea Generation: ${analysis.n_idea_generation_success ? '✅ PASS' : '❌ FAIL'}\\n`;
            output += `• Model Size Category: ${analysis.model_size_category}\\n`;
            output += `• Performance Tier: ${analysis.performance_tier.toUpperCase()}\\n`;
            output += `• Production Ready: ${analysis.production_ready ? '✅ YES' : '❌ NO'}\\n\\n`;
            
            // Show actual ideas if available
            if (data.result && data.result.ideas) {
              output += `IDEAS GENERATED:\\n`;
              data.result.ideas.forEach((idea, i) => {
                output += `${i+1}. ${idea.hypothesis} (${idea.category})\\n`;
              });
            }
            
            output += `\\n💡 Use model switching above to test different models with this same stress test!`;
            
            document.getElementById('presetOut').textContent = output;
            
          } catch (e) {
            document.getElementById('presetOut').textContent = 'Error: ' + e.message;
          }
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
    debug_flag = bool(data.get('debug')) if isinstance(data, dict) else False
    # Classification and retrieval (Phase A scaffolding)
    try:
        import classify as _clf  # local directory
    except Exception:  # pragma: no cover
        import poc.core.classify as _clf  # fallback for different sys.path layouts
    try:
        import retrieval as _ret
    except Exception:  # pragma: no cover
        import poc.core.retrieval as _ret

    detector = _clf.InputDetector()
    dtype = detector.detect(issue)
    classifier = _clf.CategoryClassifier()
    pred = classifier.classify(issue)
    retriever = _ret.HybridRetriever()
    snippets = retriever.search(issue, category_hint=pred.label, k=3)
    retrieval_text = '\n'.join(f"- {s.text[:300]} (source: {Path(s.source).name})" for s in snippets)
    
    # Check knowledge base first
    kb_solution = None
    for problem_type, details in KNOWLEDGE_BASE.items():
        for symptom in details['symptoms']:
            if symptom in issue.lower():
                kb_solution = details['solutions'][0]  # Get first solution
                break
    
    # Prepare context for LLM (prompt template)
    system_info = SystemDiagnostics.get_system_info()
    connectivity = SystemDiagnostics.check_connectivity()
    tpl = _load_template('diagnose', category_hint=pred.label)
    ctx = {
        'SYSTEM': json.dumps(system_info, ensure_ascii=False),
        'CONNECTIVITY': json.dumps(connectivity, ensure_ascii=False),
        'ISSUE': issue,
        'CATEGORY_HINT': pred.label,
        'RETRIEVAL': retrieval_text,
    }
    prompt = _render_template(tpl, ctx)
    
    llm_response = LLMInterface.get_response(prompt, temperature=0.0, num_predict=192)

    response_payload = {
        'issue': issue,
        'kb_solution': kb_solution,
        'llm_suggestion': llm_response,
        'system_context': system_info,
        'connectivity': connectivity,
        'classification': {
            'input_type': {'label': dtype.label, 'confidence': dtype.confidence},
            'category': {'label': pred.label, 'confidence': pred.confidence, 'candidates': pred.candidates},
        }
    }

    if debug_flag:
        response_payload['debug'] = {
            'retrieval_snippets': [
                {'source': str(s.source), 'text': s.text[:300], 'score': s.score}
                for s in snippets
            ],
            'prompt_excerpt': prompt[:600],
            'llm_options': {'temperature': 0.0, 'num_predict': 192}
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
    
    # Force execution is disabled unless explicitly allowed via RN_ALLOW_FORCE
    original_safe_mode = CONFIG['safe_mode']
    if force:
        allow_force = os.getenv('RN_ALLOW_FORCE', '0').lower() in ('1', 'true', 'yes', 'on')
        if not allow_force:
            return jsonify({'executed': False, 'error': 'Force execution disabled. Set RN_ALLOW_FORCE=1 to enable explicitly.'}), 403
        CONFIG['safe_mode'] = False
    
    result = CommandExecutor.execute_safely(command, safe_mode=CONFIG['safe_mode'])
    
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

@app.route('/api/model', methods=['GET', 'POST'])
def api_model():
    """Get or set the active LLM model (dynamic). POST {model}."""
    if request.method == 'GET':
        return jsonify({'backend': CONFIG['llm_backend'], 'model': CONFIG['model']})

    data = request.get_json() or {}
    new_model = data.get('model')
    if not new_model:
        return jsonify({'error': 'Missing model'}), 400

    old = CONFIG['model']
    CONFIG['model'] = new_model

    pulled = False
    pull_error = None
    if CONFIG['llm_backend'] == 'ollama' and os.getenv('RN_PULL_MODEL', '1').lower() in ('1', 'true', 'yes', 'on'):
        try:
            # Attempt a non-blocking pull to warm the cache
            subprocess.Popen(['ollama', 'pull', new_model], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pulled = True
        except Exception as e:
            pull_error = str(e)

    return jsonify({'ok': True, 'previous': old, 'model': CONFIG['model'], 'pull_started': pulled, 'pull_error': pull_error})

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
    category_hint = data.get('category_hint')
    debug = data.get('debug', False)  # Include diagnostic info

    # If no category_hint provided, attempt classification
    classification = None
    if not category_hint:
        try:
            import classify as _clf
        except Exception:  # pragma: no cover
            import poc.core.classify as _clf
        classifier = _clf.CategoryClassifier()
        pred = classifier.classify(issue)
        category_hint = pred.label
        classification = {'label': pred.label, 'confidence': pred.confidence, 'candidates': pred.candidates}
    else:
        classification = {'label': category_hint, 'confidence': None, 'candidates': []}

    # Retrieval snippets for prompt grounding
    retrieval_text = ''
    try:
        import retrieval as _ret
    except Exception:  # pragma: no cover
        import poc.core.retrieval as _ret
    try:
        retriever = _ret.HybridRetriever()
        snippets = retriever.search(issue, category_hint=category_hint, k=3)
        retrieval_text = '\n'.join(f"- {s.text[:300]} (source: {Path(s.source).name})" for s in snippets)
    except Exception:
        pass
    
    try:
        # Generate ideas with high exploration
        ideas = BrainstormEngine.generate_ideas(issue, n, creativity, category_hint=category_hint, retrieval_text=retrieval_text)
        
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
            'ideas': [idea.to_dict() for idea in ideas],
            'classification': classification
        })

        response = {
            'ideas': [idea.to_dict() for idea in ideas],
            'meta': {
                'count': len(ideas),
                'creativity': creativity,
                'timestamp': datetime.now().isoformat(),
                'category_hint': category_hint,
            }
        }
        
        # Add debug information if requested
        if debug:
            response['debug'] = {
                'steps': {
                    '1_classification': {
                        'method': 'automatic' if not data.get('category_hint') else 'provided',
                        'result': classification,
                        'confidence_level': 'high' if classification and classification.get('confidence', 0) > 0.7 else 'medium' if classification and classification.get('confidence', 0) > 0.4 else 'low',
                        'ambiguous': classification and classification.get('confidence', 0) < 0.6 if classification else False
                    },
                    '2_retrieval': {
                        'snippets_found': len(retrieval_text.splitlines()) if retrieval_text else 0,
                        'used_category': category_hint
                    },
                    '3_brainstorming': {
                        'template_used': f"brainstorm.{category_hint}.txt" if category_hint else "brainstorm.base.txt",
                        'model': CONFIG['model'],
                        'num_predict': max(512, n * 120),
                        'temperature': {0: 0.0, 1: 0.3, 2: 0.7, 3: 1.0}.get(creativity, 0.3),
                        'parsing_success': len(ideas) > 0 and ideas[0].hypothesis != "Generic troubleshooting approach"
                    }
                },
                'recommendations': []
            }
            
            # Add recommendations based on analysis
            if classification and classification.get('confidence', 0) < 0.5:
                response['debug']['recommendations'].append("Low classification confidence - consider manual category override or disambiguation flow")
            if not retrieval_text:
                response['debug']['recommendations'].append("No retrieval context found - responses may be less grounded")
            if not response['debug']['steps']['3_brainstorming']['parsing_success']:
                response['debug']['recommendations'].append("JSON parsing failed - check model output format")
            
        return jsonify(response)
        
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
    
    print(f"\n✓ Server starting:")
    bind = CONFIG['bind_host']
    if bind == '0.0.0.0':
        print(f"  • http://localhost:{CONFIG['port']}")
        print(f"  • http://{local_ip}:{CONFIG['port']}")
        ips = SystemDiagnostics.ipv4_addresses()
        if ips:
            print("  • Local IPv4s:")
            for ip in ips:
                print(f"    - http://{ip}:{CONFIG['port']}")
    else:
        print(f"  • http://{bind}:{CONFIG['port']}")
    print(f"\n✓ Safe mode: {CONFIG['safe_mode']}")
    print(f"✓ LLM backend: {CONFIG['llm_backend']}")
    print("\nPress Ctrl+C to stop\n")
    
    # Start server
    app.run(
        host=CONFIG['bind_host'],  # Bind host
        port=CONFIG['port'],
        debug=False  # Set True for development
    )
