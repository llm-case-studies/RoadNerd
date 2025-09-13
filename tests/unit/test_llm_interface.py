"""
Critical LLMInterface tests for refactoring safety
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add poc/core to path to import modules  
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'poc' / 'core'))

from modules.llm_interface import LLMInterface
import roadnerd_server
from roadnerd_server import CONFIG


class TestLLMInterfaceSimple:
    """Basic LLMInterface tests focused on post-refactoring functionality"""

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
        llm = LLMInterface(llm_backend='ollama', model='llama3.2:3b')
        with patch.object(llm, 'query_ollama', return_value='ollama response') as mock_ollama:
            result = llm.get_response("test", temperature=0.5, num_predict=256)
            assert result == 'ollama response'
            mock_ollama.assert_called_once_with("test", options_overrides={
                'temperature': 0.5, 
                'num_predict': 256, 
                'top_p': None
            })

        # Test llamafile backend
        llm = LLMInterface(llm_backend='llamafile', model='test-model')
        with patch.object(llm, 'query_llamafile', return_value='llamafile response') as mock_llamafile:
            result = llm.get_response("test", temperature=0.3, num_predict=128)
            assert result == 'llamafile response'
            mock_llamafile.assert_called_once_with("test", options_overrides={
                'temperature': 0.3,
                'num_predict': 128, 
                'top_p': None
            })

    def test_connection_error_handling(self):
        """Test graceful handling of connection errors"""
        # Test that connection errors return appropriate messages
        llm = LLMInterface(llm_backend='ollama', model='test')
        with patch('requests.post') as mock_post:
            from requests.exceptions import ConnectionError
            mock_post.side_effect = ConnectionError("Connection refused")
            
            result = llm.query_ollama("test prompt")
            
            # Should return error message, not raise exception
            assert "Ollama not available" in result or "Connection error" in result or "Error connecting" in result

    def test_gpt_oss_vs_standard_model_detection(self):
        """Test that GPT-OSS models are detected correctly"""
        import os
        
        # Test GPT-OSS model detection
        llm = LLMInterface(llm_backend='ollama', model='gpt-oss:20b')
        with patch.dict(os.environ, {'RN_USE_CHAT_MODE': 'auto'}, clear=False):
            # Mock successful chat API call
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.json.return_value = {'message': {'content': 'test response'}}
                mock_post.return_value = mock_response
                
                result = llm.query_ollama("test")
                
                # Should use chat endpoint for GPT-OSS models
                assert mock_post.called
                call_args = mock_post.call_args
                assert '/api/chat' in call_args[0][0]

    def test_options_override_functionality(self):
        """Test that options overrides work correctly"""
        llm = LLMInterface(llm_backend='ollama', model='test')
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {'response': 'test'}
            mock_post.return_value = mock_response
            
            # Test options override
            overrides = {'temperature': 0.8, 'num_predict': 1024}
            llm.query_ollama("test", options_overrides=overrides)
            
            # Verify options were passed in request
            call_args = mock_post.call_args
            request_data = call_args[1]['json']
            assert 'options' in request_data
            assert request_data['options']['temperature'] == 0.8
            assert request_data['options']['num_predict'] == 1024

    def test_llamafile_backend(self):
        """Test llamafile backend functionality"""
        llm = LLMInterface(llm_backend='llamafile', model='test')
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {'content': 'llamafile response'}
            mock_post.return_value = mock_response
            
            result = llm.query_llamafile("test prompt")
            
            # Should return content from llamafile response
            assert result == 'llamafile response'
            
            # Verify correct endpoint was called
            call_args = mock_post.call_args
            assert '/completion' in call_args[0][0]