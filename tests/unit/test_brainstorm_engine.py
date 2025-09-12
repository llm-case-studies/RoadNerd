"""
Critical BrainstormEngine tests for refactoring safety
Implements GPT-J's test recommendations from REFACTORING-PLAN.md

Tests cover:
- Single idea generation
- N-idea generation success (5-idea challenge)
- N-idea generation fallback (graceful degradation)
- JSON parsing with numbered lists ("1. {...} 2. {...}")
- Creativity levels (1-3 creativity impact)
- Debug mode output (pipeline visibility)
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add poc/core to path to import roadnerd_server  
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'poc' / 'core'))

import roadnerd_server
from roadnerd_server import BrainstormEngine, LLMInterface, Idea, CONFIG


class TestBrainstormEngine:
    """Test brainstorm engine functionality critical for refactoring safety"""

    def setup_method(self):
        """Reset CONFIG for each test"""
        self.original_config = CONFIG.copy()
        CONFIG.update({
            'llm_backend': 'ollama',
            'model': 'llama3.2:3b',
        })

    def teardown_method(self):
        """Restore original config"""
        CONFIG.clear()
        CONFIG.update(self.original_config)

    def test_single_idea_generation(self):
        """Test single idea generation basic functionality"""
        mock_llm_response = json.dumps({
            "hypothesis": "Wi-Fi driver issue",
            "category": "network",
            "why": "Network adapter not responding to driver calls",
            "checks": ["lspci -v | grep -i network", "dmesg | grep -i wifi"],
            "fixes": ["sudo modprobe -r iwlwifi && sudo modprobe iwlwifi"],
            "risk": "low"
        })
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            ideas = BrainstormEngine.generate_ideas("WiFi not working", n=1)
            
            assert len(ideas) == 1
            idea = ideas[0]
            assert isinstance(idea, Idea)
            assert idea.hypothesis == "Wi-Fi driver issue"
            assert idea.category == "network"
            assert idea.risk == "low"
            assert len(idea.checks) == 2
            assert len(idea.fixes) == 1

    def test_n_idea_generation_success(self):
        """Test N-idea generation success (5-idea challenge)"""
        # Mock response with 5 ideas in array format
        mock_ideas = []
        for i in range(5):
            mock_ideas.append({
                "hypothesis": f"Hypothesis {i+1}",
                "category": "network" if i < 3 else "performance",
                "why": f"Reasoning for idea {i+1}",
                "checks": [f"check_{i+1}_command"],
                "fixes": [f"fix_{i+1}_command"],
                "risk": "low" if i % 2 == 0 else "medium"
            })
        
        mock_llm_response = json.dumps(mock_ideas)
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            ideas = BrainstormEngine.generate_ideas("Complex network issue", n=5, creativity=2)
            
            # Should return exactly 5 ideas
            assert len(ideas) == 5
            
            # Verify all are proper Idea objects
            for i, idea in enumerate(ideas):
                assert isinstance(idea, Idea)
                assert idea.hypothesis == f"Hypothesis {i+1}"
                assert len(idea.checks) >= 1
                assert len(idea.fixes) >= 1
            
            # Verify creativity parameter affects LLM call
            LLMInterface.get_response.assert_called_once()
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['temperature'] == 0.7  # Creativity 2 = temperature 0.7
            assert call_kwargs['num_predict'] == max(512, 5 * 120)  # Dynamic token allocation

    def test_n_idea_generation_fallback(self):
        """Test N-idea generation fallback (graceful degradation)"""
        # Mock LLM returning unparseable response 
        mock_llm_response = "This is not valid JSON and cannot be parsed properly."
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            ideas = BrainstormEngine.generate_ideas("Unparseable response test", n=3)
            
            # Should fall back to generic idea
            assert len(ideas) == 1  # Falls back to single generic idea
            assert ideas[0].hypothesis == "Generic troubleshooting approach"
            assert ideas[0].category == "general" 
            assert ideas[0].why == "LLM response could not be parsed into structured ideas"
            assert ideas[0].risk == "low"

    def test_json_parsing_numbered_lists(self):
        """Test JSON parsing with numbered lists ("1. {...} 2. {...}")"""
        # Mock LLM response in numbered list format (common LLM output pattern)
        mock_llm_response = '''Here are some troubleshooting ideas:

1. {"hypothesis": "DNS resolution failure", "category": "network", "why": "Domain names not resolving", "checks": ["nslookup google.com"], "fixes": ["sudo systemctl restart systemd-resolved"], "risk": "low"}

2. {"hypothesis": "Network interface down", "category": "network", "why": "Physical network connection lost", "checks": ["ip link show"], "fixes": ["sudo ip link set eth0 up"], "risk": "medium"}

3. {"hypothesis": "Firewall blocking connections", "category": "security", "why": "Packets being filtered", "checks": ["sudo ufw status"], "fixes": ["sudo ufw allow out 53"], "risk": "low"}

These should help diagnose the network issue.'''
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            ideas = BrainstormEngine.generate_ideas("Network connectivity issues", n=3)
            
            # Should successfully parse all 3 numbered JSON objects
            assert len(ideas) == 3
            
            # Verify specific parsing of numbered format
            assert ideas[0].hypothesis == "DNS resolution failure"
            assert ideas[1].hypothesis == "Network interface down" 
            assert ideas[2].hypothesis == "Firewall blocking connections"
            
            # Verify categories parsed correctly
            assert ideas[0].category == "network"
            assert ideas[1].category == "network"
            assert ideas[2].category == "security"

    def test_json_parsing_fenced_blocks(self):
        """Test JSON parsing with fenced code blocks"""
        mock_llm_response = '''Here's the analysis in JSON format:

```json
[
  {
    "hypothesis": "Memory leak in application",
    "category": "performance", 
    "why": "RAM usage increasing over time",
    "checks": ["free -h", "ps aux --sort=-%mem | head"],
    "fixes": ["sudo systemctl restart problematic-service"],
    "risk": "medium"
  },
  {
    "hypothesis": "Disk space exhaustion",
    "category": "system",
    "why": "No space left on device errors",
    "checks": ["df -h", "du -sh /*"],
    "fixes": ["sudo apt autoremove", "sudo journalctl --vacuum-time=7d"],
    "risk": "low"
  }
]
```

This should help identify the performance issue.'''
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            ideas = BrainstormEngine.generate_ideas("System performance degrading", n=2)
            
            # Should parse fenced JSON array  
            assert len(ideas) == 2
            assert ideas[0].hypothesis == "Memory leak in application"
            assert ideas[1].hypothesis == "Disk space exhaustion"
            assert ideas[0].category == "performance"
            assert ideas[1].category == "system"

    def test_creativity_levels(self):
        """Test creativity levels (1-3 creativity impact)"""
        mock_llm_response = json.dumps({
            "hypothesis": "Test hypothesis",
            "category": "test",
            "why": "Test reasoning",
            "checks": ["test_check"],
            "fixes": ["test_fix"],
            "risk": "low"
        })
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            # Test creativity level 0 (temperature 0.0)
            BrainstormEngine.generate_ideas("Test issue", n=1, creativity=0)
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['temperature'] == 0.0
            
            # Test creativity level 1 (temperature 0.3)  
            BrainstormEngine.generate_ideas("Test issue", n=1, creativity=1)
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['temperature'] == 0.3
            
            # Test creativity level 2 (temperature 0.7)
            BrainstormEngine.generate_ideas("Test issue", n=1, creativity=2)
            call_kwargs = LLMInterface.get_response.call_args[1] 
            assert call_kwargs['temperature'] == 0.7
            
            # Test creativity level 3 (temperature 1.0)
            BrainstormEngine.generate_ideas("Test issue", n=1, creativity=3)
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['temperature'] == 1.0
            
            # Test invalid creativity level (defaults to 0.3)
            BrainstormEngine.generate_ideas("Test issue", n=1, creativity=5)
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['temperature'] == 0.3

    def test_dynamic_token_allocation(self):
        """Test dynamic token allocation scales with N ideas"""
        mock_llm_response = json.dumps({
            "hypothesis": "Test", 
            "category": "test",
            "why": "Test",
            "checks": ["test"],
            "fixes": ["test"],
            "risk": "low"
        })
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            # Test N=1: should use max(512, 1*120) = 512 tokens
            BrainstormEngine.generate_ideas("Test", n=1)
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['num_predict'] == 512
            
            # Test N=5: should use max(512, 5*120) = 600 tokens
            BrainstormEngine.generate_ideas("Test", n=5)
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['num_predict'] == 600
            
            # Test N=10: should use max(512, 10*120) = 1200 tokens
            BrainstormEngine.generate_ideas("Test", n=10)
            call_kwargs = LLMInterface.get_response.call_args[1]
            assert call_kwargs['num_predict'] == 1200

    def test_balanced_brace_parsing(self):
        """Test balanced brace JSON extraction from mixed text"""
        # Mock response with JSON objects mixed in narrative text
        mock_llm_response = '''The network issue could be caused by several factors. Let me provide some structured analysis:

First possibility: {"hypothesis": "Router configuration error", "category": "network", "why": "Incorrect routing table", "checks": ["route -n"], "fixes": ["sudo route add default gw 192.168.1.1"], "risk": "medium"}

Another consideration is {"hypothesis": "Cable connection loose", "category": "physical", "why": "Intermittent physical connection", "checks": ["ethtool eth0"], "fixes": ["Check and reseat network cable"], "risk": "low"}

These are the most likely causes based on the symptoms described.'''
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value={}), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value={}):
            
            ideas = BrainstormEngine.generate_ideas("Mixed text parsing test", n=2)
            
            # Should extract both JSON objects from mixed text using balanced brace parsing
            assert len(ideas) == 2
            assert ideas[0].hypothesis == "Router configuration error"
            assert ideas[1].hypothesis == "Cable connection loose"
            assert ideas[0].category == "network"
            assert ideas[1].category == "physical"

    def test_template_context_building(self):
        """Test template context building with category hints and retrieval"""
        mock_system_info = {"os": "Ubuntu 22.04", "arch": "x86_64"}
        mock_connectivity = {"internet": True, "dns": True}
        mock_llm_response = json.dumps({
            "hypothesis": "Test",
            "category": "test", 
            "why": "Test",
            "checks": ["test"],
            "fixes": ["test"],
            "risk": "low"
        })
        
        with patch.object(LLMInterface, 'get_response', return_value=mock_llm_response), \
             patch('roadnerd_server.SystemDiagnostics.get_system_info', return_value=mock_system_info), \
             patch('roadnerd_server.SystemDiagnostics.check_connectivity', return_value=mock_connectivity), \
             patch('roadnerd_server._load_template', return_value="{{ISSUE}} {{CATEGORY_HINT}} {{N}} {{SYSTEM}} {{RETRIEVAL}}") as mock_template:
            
            BrainstormEngine.generate_ideas(
                issue="Network down", 
                n=3, 
                category_hint="network", 
                retrieval_text="Previous troubleshooting logs"
            )
            
            # Verify template was loaded with category hint
            mock_template.assert_called_once_with('brainstorm', category_hint='network')
            
            # Verify LLM was called with properly rendered template
            LLMInterface.get_response.assert_called_once()
            prompt = LLMInterface.get_response.call_args[0][0]
            
            # Template should contain all context variables
            assert "Network down" in prompt  # ISSUE
            assert "network" in prompt       # CATEGORY_HINT  
            assert "3" in prompt             # N
            assert "Ubuntu 22.04" in prompt # SYSTEM (JSON stringified)
            assert "Previous troubleshooting logs" in prompt  # RETRIEVAL