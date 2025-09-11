#!/usr/bin/env python3
"""
LLM Interface Module - Interface to various LLM backends
Extracted from roadnerd_server.py to improve modularity
"""

import os
from typing import Dict, Optional


class LLMInterface:
    """Interface to various LLM backends (Ollama, Llamafile, etc.)"""
    
    def __init__(self, llm_backend: str = 'ollama', model: str = 'llama3.2'):
        """
        Initialize LLM Interface with configuration.
        
        Args:
            llm_backend: The LLM backend to use ('ollama', 'llamafile')
            model: The model name to use
        """
        self.llm_backend = llm_backend
        self.model = model
    
    def query_ollama(self, prompt: str, options_overrides: Optional[Dict] = None) -> str:
        """Query Ollama API - automatically selects chat vs generate based on model"""
        try:
            import requests
            base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            
            # Check if we should use chat mode (auto-detect GPT-OSS models or force via env)
            use_chat_mode = os.getenv('RN_USE_CHAT_MODE', 'auto').lower()
            force_chat = (use_chat_mode == 'force') or (use_chat_mode == 'auto' and self.model.startswith('gpt-oss'))
            
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
                    'model': self.model,
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
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'options': options,
                }
                response = requests.post(f'{base}/api/generate', json=payload)
                return response.json().get('response', 'No response from Ollama')
        except Exception as e:
            return f"Ollama not available: {e}"
    
    def query_llamafile(self, prompt: str, options_overrides: Optional[Dict] = None) -> str:
        """Query llamafile server"""
        try:
            import requests
            base = os.getenv('LLAMAFILE_BASE_URL', 'http://localhost:8081')
            response = requests.post(f'{base}/completion', json={'prompt': prompt, 'n_predict': 200})
            return response.json().get('content', 'No response from llamafile')
        except Exception as e:
            return f"Llamafile not available: {e}"
    
    def get_response(self, prompt: str, *, temperature: Optional[float] = None, 
                     num_predict: Optional[int] = None, top_p: Optional[float] = None) -> str:
        """Get response from configured LLM with optional per-request options."""
        overrides = {'temperature': temperature, 'num_predict': num_predict, 'top_p': top_p}
        if self.llm_backend == 'ollama':
            return self.query_ollama(prompt, options_overrides=overrides)
        elif self.llm_backend == 'llamafile':
            return self.query_llamafile(prompt, options_overrides=overrides)
        else:
            return f"Unsupported LLM backend: {self.llm_backend}"
    
    # Static methods for backward compatibility with existing code
    @staticmethod
    def query_ollama_static(prompt: str, model: str, options_overrides: Optional[Dict] = None) -> str:
        """Static method for backward compatibility - creates temporary instance"""
        instance = LLMInterface(llm_backend='ollama', model=model)
        return instance.query_ollama(prompt, options_overrides)
    
    @staticmethod 
    def query_llamafile_static(prompt: str, options_overrides: Optional[Dict] = None) -> str:
        """Static method for backward compatibility - creates temporary instance"""
        instance = LLMInterface(llm_backend='llamafile', model='')
        return instance.query_llamafile(prompt, options_overrides)
    
    @staticmethod
    def get_response_static(prompt: str, llm_backend: str, model: str, *, 
                           temperature: Optional[float] = None, num_predict: Optional[int] = None, 
                           top_p: Optional[float] = None) -> str:
        """Static method for backward compatibility - creates temporary instance"""
        instance = LLMInterface(llm_backend=llm_backend, model=model)
        return instance.get_response(prompt, temperature=temperature, num_predict=num_predict, top_p=top_p)