#!/usr/bin/env python3
"""
Profile Manager for RoadNerd - Machine-specific knowledge and configurations
"""

import json
import os
import glob
from pathlib import Path
from typing import Dict, List, Optional, Any

class ProfileManager:
    def __init__(self, profiles_dir: str = None):
        if profiles_dir is None:
            self.profiles_dir = Path(__file__).parent / "profiles"
        else:
            self.profiles_dir = Path(profiles_dir)
        
        self.profiles_dir.mkdir(exist_ok=True)
        self._profiles_cache = {}
    
    def get_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Load a specific machine profile"""
        if profile_name in self._profiles_cache:
            return self._profiles_cache[profile_name]
        
        profile_file = self.profiles_dir / f"{profile_name}.json"
        if not profile_file.exists():
            return None
        
        try:
            with open(profile_file, 'r') as f:
                profile = json.load(f)
                self._profiles_cache[profile_name] = profile
                return profile
        except Exception as e:
            print(f"Error loading profile {profile_name}: {e}")
            return None
    
    def list_profiles(self) -> List[str]:
        """List available profiles"""
        profile_files = glob.glob(str(self.profiles_dir / "*.json"))
        return [Path(f).stem for f in profile_files]
    
    def detect_current_machine(self) -> Optional[str]:
        """Try to detect which profile matches current machine"""
        try:
            import subprocess
            import platform
            
            # Get hostname
            hostname = platform.node()
            
            # Get CPU model
            try:
                result = subprocess.run(['lscpu'], capture_output=True, text=True)
                cpu_info = result.stdout
            except:
                cpu_info = ""
            
            # Check all profiles for matches
            for profile_name in self.list_profiles():
                profile = self.get_profile(profile_name)
                if not profile:
                    continue
                
                # Match by hostname pattern
                if hostname and profile_name in hostname.lower():
                    return profile_name
                
                # Match by CPU model
                if (profile.get('hardware', {}).get('cpu', {}).get('model', '') in cpu_info):
                    return profile_name
            
            return None
        except Exception:
            return None
    
    def get_machine_issues(self, profile_name: str = None) -> List[Dict[str, Any]]:
        """Get machine-specific common issues"""
        if profile_name is None:
            profile_name = self.detect_current_machine()
        
        if profile_name is None:
            return []
        
        profile = self.get_profile(profile_name)
        if not profile:
            return []
        
        return profile.get('common_issues', [])
    
    def get_performance_info(self, profile_name: str = None) -> Dict[str, Any]:
        """Get performance recommendations"""
        if profile_name is None:
            profile_name = self.detect_current_machine()
        
        if profile_name is None:
            return {}
        
        profile = self.get_profile(profile_name)
        if not profile:
            return {}
        
        return profile.get('performance_profile', {})
    
    def find_matching_solutions(self, issue_text: str, profile_name: str = None) -> List[Dict[str, Any]]:
        """Find solutions that match the issue from machine profile"""
        machine_issues = self.get_machine_issues(profile_name)
        issue_lower = issue_text.lower()
        
        matching_solutions = []
        
        for issue_category in machine_issues:
            # Check if any symptoms match
            for symptom in issue_category.get('symptoms', []):
                if symptom.lower() in issue_lower:
                    # Add all solutions from this category
                    for solution in issue_category.get('solutions', []):
                        matching_solutions.append({
                            'category': issue_category.get('category', 'unknown'),
                            'solution': solution
                        })
                    break
        
        return matching_solutions
    
    def export_profile(self, profile_name: str, output_path: str) -> bool:
        """Export profile to another location"""
        profile = self.get_profile(profile_name)
        if not profile:
            return False
        
        try:
            with open(output_path, 'w') as f:
                json.dump(profile, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting profile: {e}")
            return False

# Global instance
profile_manager = ProfileManager()

def get_current_profile_info() -> Dict[str, Any]:
    """Helper function to get current machine profile info"""
    current_profile = profile_manager.detect_current_machine()
    if current_profile:
        return {
            'profile_name': current_profile,
            'profile_data': profile_manager.get_profile(current_profile),
            'performance': profile_manager.get_performance_info(current_profile)
        }
    return {'profile_name': None, 'profile_data': None, 'performance': {}}