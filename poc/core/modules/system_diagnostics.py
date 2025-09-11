"""
System diagnostics module for RoadNerd

Provides safe system information gathering and connectivity checks.
Extracted from roadnerd_server.py for modular architecture.
"""

import platform
import socket
import subprocess
from typing import Dict, List


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