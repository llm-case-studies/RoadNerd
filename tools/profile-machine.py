#!/usr/bin/env python3
"""
Unified Machine Profiling & LLM Testing Tool

Creates machine profiles for RoadNerd knowledge base and tests LLM capabilities
across different model sizes to establish performance baselines and limits.

Usage:
  python3 profile-machine.py --create                    # Create new profile
  python3 profile-machine.py --update --test-llm         # Add LLM test results  
  python3 profile-machine.py --benchmark --models all    # Test all available models
  python3 profile-machine.py --export patient.json       # Export for patient deployment
"""

import json
import os
import sys
import subprocess
import platform
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import hashlib

class SystemProfiler:
    def __init__(self, profile_dir: str = None):
        self.profile_dir = Path(profile_dir) if profile_dir else Path(__file__).parent.parent / "poc" / "core" / "profiles"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
    def gather_hardware_info(self) -> Dict[str, Any]:
        """Comprehensive hardware profiling"""
        info = {}
        
        # CPU Information
        try:
            result = subprocess.run(['lscpu'], capture_output=True, text=True)
            cpu_lines = result.stdout.splitlines()
            cpu_info = {}
            
            for line in cpu_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key == 'model_name':
                        cpu_info['model'] = value
                    elif key == 'cpu(s)':
                        cpu_info['logical_cores'] = int(value)
                    elif key == 'core(s)_per_socket':
                        cpu_info['cores_per_socket'] = int(value) 
                    elif key == 'thread(s)_per_core':
                        cpu_info['threads_per_core'] = int(value)
                    elif key == 'cpu_max_mhz':
                        cpu_info['max_freq_mhz'] = float(value)
                    elif key == 'architecture':
                        cpu_info['architecture'] = value
                        
            info['cpu'] = cpu_info
            
        except Exception as e:
            info['cpu'] = {'error': str(e)}
        
        # Memory Information
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True)
            mem_line = result.stdout.splitlines()[1]  # Mem: line
            parts = mem_line.split()
            info['memory'] = {
                'total_mb': int(parts[1]),
                'total_gb': round(int(parts[1]) / 1024, 1),
                'available_mb': int(parts[6]) if len(parts) > 6 else int(parts[3]),
                'available_gb': round((int(parts[6]) if len(parts) > 6 else int(parts[3])) / 1024, 1)
            }
        except Exception as e:
            info['memory'] = {'error': str(e)}
            
        # Storage Information
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            storage_line = result.stdout.splitlines()[1]
            parts = storage_line.split()
            info['storage'] = {
                'filesystem': parts[0],
                'total': parts[1],
                'used': parts[2], 
                'available': parts[3],
                'use_percent': parts[4]
            }
        except Exception as e:
            info['storage'] = {'error': str(e)}
            
        # Graphics Information
        try:
            result = subprocess.run(['lspci', '|', 'grep', '-i', 'vga'], shell=True, capture_output=True, text=True)
            gpu_lines = result.stdout.strip().splitlines()
            gpus = []
            for line in gpu_lines:
                if 'VGA' in line:
                    # Extract GPU info from lspci output
                    parts = line.split(': ', 1)
                    if len(parts) > 1:
                        gpu_desc = parts[1]
                        gpu_type = "integrated" if "Intel" in gpu_desc else "discrete"
                        gpus.append({
                            'type': gpu_type,
                            'model': gpu_desc,
                            'compute_capable': "NVIDIA" in gpu_desc or "AMD" in gpu_desc
                        })
            info['graphics'] = gpus
        except Exception as e:
            info['graphics'] = [{'error': str(e)}]
            
        return info
        
    def gather_software_info(self) -> Dict[str, Any]:
        """Software environment profiling"""
        info = {}
        
        # OS Information
        try:
            with open('/etc/os-release', 'r') as f:
                os_lines = f.readlines()
            
            os_info = {}
            for line in os_lines:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    value = value.strip('"')
                    if key == 'NAME':
                        os_info['distribution'] = value
                    elif key == 'VERSION':
                        os_info['version'] = value
                    elif key == 'VERSION_CODENAME':
                        os_info['codename'] = value
                        
            os_info['kernel'] = platform.release()
            info['os'] = os_info
            
        except Exception as e:
            info['os'] = {'error': str(e)}
            
        # Python Information
        info['python'] = {
            'version': platform.python_version(),
            'implementation': platform.python_implementation()
        }
        
        # Check AI/ML stack
        ai_stack = {}
        
        # Ollama
        ollama_path = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
        if ollama_path.returncode == 0:
            ai_stack['ollama'] = {
                'installed': True,
                'path': ollama_path.stdout.strip()
            }
            # Get ollama models
            try:
                models_result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
                if models_result.returncode == 0:
                    models = []
                    for line in models_result.stdout.splitlines()[1:]:  # Skip header
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 3:
                                models.append({
                                    'name': parts[0],
                                    'id': parts[1],
                                    'size': parts[2]
                                })
                    ai_stack['ollama']['models'] = models
            except:
                pass
        else:
            ai_stack['ollama'] = {'installed': False}
            
        # CUDA availability
        nvidia_smi = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        ai_stack['cuda_available'] = nvidia_smi.returncode == 0
        
        info['ai_stack'] = ai_stack
        return info
        
    def gather_network_info(self) -> Dict[str, Any]:
        """Network interface profiling"""
        info = {'interfaces': []}
        
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
            current_interface = None
            
            for line in result.stdout.splitlines():
                line = line.strip()
                
                # Interface line: "2: enp58s0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500"
                if line and line[0].isdigit() and ':' in line:
                    parts = line.split(': ', 2)
                    if len(parts) >= 2:
                        interface_name = parts[1].split('@')[0]  # Remove @vlan info
                        status_flags = parts[2] if len(parts) > 2 else ''
                        
                        current_interface = {
                            'name': interface_name,
                            'status': 'active' if 'UP' in status_flags else 'inactive',
                            'type': 'unknown',
                            'ips': []
                        }
                        
                        # Determine interface type
                        if interface_name.startswith(('eth', 'enp')):
                            current_interface['type'] = 'ethernet'
                        elif interface_name.startswith(('wlan', 'wlp')):
                            current_interface['type'] = 'wifi'
                        elif interface_name.startswith('lo'):
                            current_interface['type'] = 'loopback'
                        elif interface_name.startswith('docker'):
                            current_interface['type'] = 'virtual'
                            
                        info['interfaces'].append(current_interface)
                        
                # IP address line: "inet 10.55.0.2/24 scope global enp58s0"
                elif line.startswith('inet ') and current_interface:
                    parts = line.split()
                    if len(parts) >= 2:
                        ip_with_cidr = parts[1]
                        ip = ip_with_cidr.split('/')[0]
                        cidr = ip_with_cidr.split('/')[1] if '/' in ip_with_cidr else '32'
                        
                        current_interface['ips'].append({
                            'ip': ip,
                            'cidr': cidr,
                            'scope': 'global' if 'global' in line else 'local'
                        })
                        
        except Exception as e:
            info['error'] = str(e)
            
        return info
        
    def create_profile(self, profile_name: str = None) -> Dict[str, Any]:
        """Create complete machine profile"""
        if not profile_name:
            hostname = platform.node().lower()
            profile_name = hostname.replace('.', '-').replace('_', '-')
            
        profile = {
            'profile_name': profile_name,
            'generated': datetime.now().isoformat(),
            'hardware': self.gather_hardware_info(),
            'software': self.gather_software_info(),
            'network': self.gather_network_info(),
            'llm_benchmarks': {},
            'performance_recommendations': {},
            'common_issues': []
        }
        
        return profile
        
    def save_profile(self, profile: Dict[str, Any], filename: str = None):
        """Save profile to JSON file"""
        if not filename:
            filename = f"{profile['profile_name']}.json"
            
        profile_path = self.profile_dir / filename
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)
            
        print(f"Profile saved: {profile_path}")
        return profile_path
        
    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        """Load existing profile"""
        profile_path = self.profile_dir / f"{profile_name}.json"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_path}")
            
        with open(profile_path, 'r') as f:
            return json.load(f)

class LLMBenchmark:
    def __init__(self, ollama_base: str = "http://localhost:11434"):
        self.ollama_base = ollama_base
        
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{self.ollama_base}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
        except Exception as e:
            print(f"Error getting models: {e}")
        return []
        
    def test_model_performance(self, model_name: str, test_prompts: List[str]) -> Dict[str, Any]:
        """Benchmark a specific model with test prompts"""
        results = {
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }
        
        total_time = 0
        total_tokens = 0
        successful_tests = 0
        
        for i, prompt in enumerate(test_prompts):
            print(f"Testing {model_name} - prompt {i+1}/{len(test_prompts)}")
            
            test_result = self._run_single_test(model_name, prompt, f"test_{i+1}")
            results['tests'].append(test_result)
            
            if test_result['success']:
                successful_tests += 1
                total_time += test_result['response_time']
                total_tokens += test_result.get('tokens', 0)
                
        # Calculate summary metrics
        if successful_tests > 0:
            results['summary'] = {
                'success_rate': successful_tests / len(test_prompts),
                'avg_response_time': total_time / successful_tests,
                'avg_tokens_per_second': total_tokens / total_time if total_time > 0 else 0,
                'total_tests': len(test_prompts),
                'successful_tests': successful_tests
            }
            
        return results
        
    def _run_single_test(self, model_name: str, prompt: str, test_id: str) -> Dict[str, Any]:
        """Run a single model test"""
        start_time = time.time()
        
        try:
            payload = {
                'model': model_name,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0,
                    'num_predict': 128
                }
            }
            
            response = requests.post(f"{self.ollama_base}/api/generate", json=payload, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'test_id': test_id,
                    'success': True,
                    'response_time': end_time - start_time,
                    'response_text': data.get('response', ''),
                    'tokens': len(data.get('response', '').split()),
                    'eval_count': data.get('eval_count', 0),
                    'eval_duration': data.get('eval_duration', 0)
                }
            else:
                return {
                    'test_id': test_id,
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'response_time': end_time - start_time
                }
                
        except Exception as e:
            end_time = time.time()
            return {
                'test_id': test_id,
                'success': False,
                'error': str(e),
                'response_time': end_time - start_time
            }
            
    def get_standard_test_prompts(self) -> List[str]:
        """Standard diagnostic test prompts for RoadNerd"""
        return [
            "My WiFi is not working. What should I check first?",
            "DNS resolution is failing. How do I diagnose this on Ubuntu?", 
            "Network interface shows as up but no internet. What commands should I run?",
            "System is running slow. What are the most important diagnostic commands?",
            "I can't access SSH on this machine. How do I troubleshoot SSH connectivity?"
        ]

class ModelManager:
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".roadnerd" / "models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def cache_ollama_models(self) -> Dict[str, Any]:
        """Create cached copy of Ollama models for patient bootstrapping"""
        ollama_dir = Path.home() / ".ollama" / "models"
        
        if not ollama_dir.exists():
            return {'error': 'Ollama models directory not found'}
            
        cache_info = {
            'cached_at': datetime.now().isoformat(),
            'models': [],
            'total_size_mb': 0
        }
        
        # Create tarball of models
        import tarfile
        cache_file = self.cache_dir / "ollama-models.tar.gz"
        
        print(f"Caching Ollama models to {cache_file}")
        
        with tarfile.open(cache_file, "w:gz") as tar:
            for item in ollama_dir.rglob("*"):
                if item.is_file():
                    arcname = item.relative_to(ollama_dir.parent)
                    tar.add(item, arcname=arcname)
                    
        # Get cache file size
        cache_size = cache_file.stat().st_size
        cache_info['cache_file'] = str(cache_file)
        cache_info['cache_size_mb'] = round(cache_size / (1024 * 1024), 1)
        
        # Get model list
        try:
            models_result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if models_result.returncode == 0:
                for line in models_result.stdout.splitlines()[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            cache_info['models'].append({
                                'name': parts[0],
                                'id': parts[1],
                                'size': parts[2]
                            })
        except:
            pass
            
        return cache_info
        
    def create_bootstrap_script(self, target_profile: Dict[str, Any]) -> str:
        """Create bootstrap script for patient deployment"""
        script_content = f'''#!/usr/bin/env bash
# RoadNerd Patient Bootstrap Script
# Generated: {datetime.now().isoformat()}
# Target Profile: {target_profile.get('profile_name', 'unknown')}

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

# Check if this machine can handle larger models
TOTAL_RAM=$(free -m | awk 'NR==2{{print $2}}')
echo "📊 Detected ${{TOTAL_RAM}}MB RAM"

if [ "$TOTAL_RAM" -gt 16000 ]; then
    echo "🚀 High-capacity machine detected"
    echo "📦 Downloading model cache..."
    curl -fsSL "$NERD_URL/download/ollama-models.tar.gz" -o ollama-models.tar.gz
    
    echo "🔧 Setting up Ollama..."
    # Install Ollama if not present
    if ! command -v ollama &> /dev/null; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    # Extract models
    mkdir -p ~/.ollama
    tar xzf ollama-models.tar.gz -C ~/.ollama
    
    echo "🎯 Starting Ollama service..."
    ollama serve &
    sleep 5
    
    echo "🔄 Role swap: This machine will now act as the Nerd"
    python3 -c "
import sys
sys.path.append('.')
from profile_manager import ProfileManager
pm = ProfileManager()
print('Available profiles:', pm.list_profiles())
"
    
else
    echo "💻 Standard machine - will connect to Nerd for processing"
fi

echo "✅ Bootstrap complete!"
echo "🚀 Starting RoadNerd client..."
python3 roadnerd_client.py "$NERD_URL"
'''
        
        script_path = self.cache_dir / "bootstrap.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
            
        script_path.chmod(0o755)
        return str(script_path)

def main():
    parser = argparse.ArgumentParser(description='RoadNerd Machine Profiling & LLM Testing')
    parser.add_argument('--create', action='store_true', help='Create new machine profile')
    parser.add_argument('--update', action='store_true', help='Update existing profile')
    parser.add_argument('--test-llm', action='store_true', help='Run LLM benchmarks')
    parser.add_argument('--benchmark', action='store_true', help='Run comprehensive benchmarks')
    parser.add_argument('--models', default='available', help='Models to test (available/all/model-name)')
    parser.add_argument('--export', help='Export profile for patient deployment')
    parser.add_argument('--cache-models', action='store_true', help='Cache Ollama models for bootstrapping')
    parser.add_argument('--profile-name', help='Specific profile name to use')
    
    args = parser.parse_args()
    
    profiler = SystemProfiler()
    
    if args.create or (not args.update and not args.export):
        print("🔍 Creating machine profile...")
        profile = profiler.create_profile(args.profile_name)
        profile_path = profiler.save_profile(profile)
        print("✅ Profile created successfully")
        
    if args.update or args.test_llm or args.benchmark:
        profile_name = args.profile_name or platform.node().lower().replace('.', '-').replace('_', '-')
        
        try:
            profile = profiler.load_profile(profile_name)
            print(f"📝 Loaded profile: {profile_name}")
        except FileNotFoundError:
            print(f"Profile {profile_name} not found, creating new one...")
            profile = profiler.create_profile(profile_name)
            
        if args.test_llm or args.benchmark:
            print("🧠 Starting LLM benchmarks...")
            benchmark = LLMBenchmark()
            
            if args.models == 'available':
                models = benchmark.get_available_models()
                model_names = [m['name'] for m in models]
            elif args.models == 'all':
                # Test escalation ladder
                model_names = ['llama3.2:1b', 'llama3.2:3b', 'llama3.2:7b', 'llama3.1:8b-instruct']
            else:
                model_names = [args.models]
                
            test_prompts = benchmark.get_standard_test_prompts()
            
            for model_name in model_names:
                print(f"🎯 Testing {model_name}...")
                results = benchmark.test_model_performance(model_name, test_prompts)
                
                profile['llm_benchmarks'][model_name] = results
                print(f"✅ {model_name}: {results['summary'].get('success_rate', 0):.1%} success rate")
                
        # Save updated profile
        profiler.save_profile(profile)
        print("💾 Profile updated with benchmark results")
        
    if args.cache_models:
        print("📦 Caching models for patient bootstrap...")
        model_manager = ModelManager()
        cache_info = model_manager.cache_ollama_models()
        
        if 'error' not in cache_info:
            print(f"✅ Cached {len(cache_info['models'])} models ({cache_info['cache_size_mb']}MB)")
            
            # Update profile with cache info
            try:
                profile_name = args.profile_name or platform.node().lower().replace('.', '-').replace('_', '-')
                profile = profiler.load_profile(profile_name)
                profile['model_cache'] = cache_info
                profiler.save_profile(profile)
            except:
                pass
        else:
            print(f"❌ Error caching models: {cache_info['error']}")
        
    if args.export:
        profile_name = args.profile_name or platform.node().lower().replace('.', '-').replace('_', '-')
        profile = profiler.load_profile(profile_name)
        
        export_path = Path(args.export)
        with open(export_path, 'w') as f:
            json.dump(profile, f, indent=2)
            
        print(f"📤 Profile exported to: {export_path}")
        
        # Create bootstrap script
        model_manager = ModelManager()
        script_path = model_manager.create_bootstrap_script(profile)
        print(f"🚀 Bootstrap script created: {script_path}")

if __name__ == "__main__":
    main()