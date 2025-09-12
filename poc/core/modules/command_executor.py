"""
Command execution module for RoadNerd

Provides safe command execution with risk analysis and safety checks.
Extracted from roadnerd_server.py for modular architecture.
"""

import subprocess
from typing import Dict


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
    def execute_safely(cmd: str, safe_mode: bool = True) -> Dict:
        """Execute command with safety checks"""
        analysis = CommandExecutor.analyze_command(cmd)
        
        if analysis['risk_level'] == 'high' and safe_mode:
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