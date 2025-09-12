"""
Simplified LLMInterface tests for refactoring safety
Focus on core functionality without complex mocking
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add poc/core to path to import roadnerd_server  
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'poc' / 'core'))

import roadnerd_server
from roadnerd_server import LLMInterface, CONFIG


class TestLLMInterfaceSimple:
    """Simplified test LLM interface functionality"""

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

    def test_get_response_backend_routing(self):
        """Test LLMInterface.get_response() backend routing"""
        # Test ollama backend
        CONFIG['llm_backend'] = 'ollama'
        with patch.object(LLMInterface, 'query_ollama', return_value='ollama response') as mock_ollama:
            result = LLMInterface.get_response("test", temperature=0.5, num_predict=256)
            assert result == 'ollama response'
            mock_ollama.assert_called_once_with("test", options_overrides={
                'temperature': 0.5, 
                'num_predict': 256, 
                'top_p': None
            })

        # Test llamafile backend
        CONFIG['llm_backend'] = 'llamafile' 
        with patch.object(LLMInterface, 'query_llamafile', return_value='llamafile response') as mock_llamafile:
            result = LLMInterface.get_response("test", num_predict=512)
            assert result == 'llamafile response'
            mock_llamafile.assert_called_once_with("test", options_overrides={
                'temperature': None,
                'num_predict': 512,
                'top_p': None
            })

        # Test unknown backend
        CONFIG['llm_backend'] = 'unknown'
        result = LLMInterface.get_response("test")
        assert result == "No LLM backend configured"

    def test_connection_error_handling(self):
        """Test graceful handling of connection errors"""
        # Test that connection errors return appropriate messages
        with patch('requests.post') as mock_post:
            from requests.exceptions import ConnectionError
            mock_post.side_effect = ConnectionError("Connection refused")
            
            result = LLMInterface.query_ollama("test prompt")
            
            assert "Ollama not available" in result
            assert "Connection refused" in result

    def test_gpt_oss_vs_standard_model_detection(self):
        """Test that GPT-OSS models are detected correctly"""
        import os
        
        # Test GPT-OSS model detection
        CONFIG['model'] = 'gpt-oss:20b'
        with patch.dict(os.environ, {'RN_USE_CHAT_MODE': 'auto'}, clear=False):
            # Mock successful chat API call
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.json.return_value = {'message': {'content': 'test response'}}
                mock_post.return_value = mock_response
                
                result = LLMInterface.query_ollama("test")
                
                # Should have called the chat API endpoint
                mock_post.assert_called_once()
                call_args = mock_post.call_args[0]
                assert 'api/chat' in call_args[0]

        # Test standard model routing  
        CONFIG['model'] = 'llama3.2:3b'
        with patch.dict(os.environ, {'RN_USE_CHAT_MODE': 'auto'}, clear=False):
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.json.return_value = {'response': 'test response'}
                mock_post.return_value = mock_response
                
                result = LLMInterface.query_ollama("test")
                
                # Should have called the generate API endpoint
                mock_post.assert_called_once()
                call_args = mock_post.call_args[0]
                assert 'api/generate' in call_args[0]

    def test_options_override_functionality(self):
        """Test that options overrides work correctly"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {'response': 'test'}
            mock_post.return_value = mock_response
            
            # Test options override
            overrides = {'temperature': 0.8, 'num_predict': 1024}
            LLMInterface.query_ollama("test", options_overrides=overrides)
            
            # Verify the request was made with overrides
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload['options']['temperature'] == 0.8
            assert payload['options']['num_predict'] == 1024

    def test_llamafile_backend(self):
        """Test llamafile backend functionality"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {'content': 'llamafile response'}
            mock_post.return_value = mock_response
            
            result = LLMInterface.query_llamafile("test prompt")
            
            assert result == 'llamafile response'
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert 'completion' in call_args[0][0]  # Should call /completion endpoint
            
            payload = call_args[1]['json']
            assert payload['prompt'] == 'test prompt'
            assert payload['n_predict'] == 200