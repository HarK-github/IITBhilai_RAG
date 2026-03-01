"""
Configuration loader with environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
from typing import Dict, Any

# Load .env file
load_dotenv()

class ConfigLoader:
    """Load and manage configuration"""
    
    def __init__(self, config_dir: str = "src/config"):
        self.config_dir = Path(config_dir)
        self.config = {}
        self.load_all()
    
    def load_all(self):
        """Load all configuration files"""
        # Load YAML configs
        yaml_files = ['agent.yaml', 'cache.yaml', 'websites.yaml']
        for yaml_file in yaml_files:
            path = self.config_dir / yaml_file
            if path.exists():
                with open(path, 'r') as f:
                    self.config[yaml_file.replace('.yaml', '')] = yaml.safe_load(f)
        
        # Load environment variables with correct model names
        self.config['env'] = {
            'google_api_key': os.getenv('GOOGLE_API_KEY'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'llm_provider': os.getenv('LLM_PROVIDER', 'gemini'),
            # Updated to gemini-2.5-flash (latest)
            'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            'embedding_provider': os.getenv('EMBEDDING_PROVIDER', 'gemini'),
            # NO "models/" prefix - just the model name
            'gemini_embedding_model': os.getenv('GEMINI_EMBEDDING_MODEL', 'text-embedding-004'),
            'openai_embedding_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
            'chroma_dir': os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_langchain_db'),
        }
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        parts = key.split('.')
        value = self.config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        provider = self.config['env']['llm_provider']
        
        if provider == 'gemini':
            return {
                'provider': 'gemini',
                'api_key': self.config['env']['google_api_key'],
                'model': self.config['env']['gemini_model'],  # gemini-2.5-flash
                'temperature': self.get('agent.temperature', 0.1),
                'max_tokens': self.get('agent.max_tokens', 1000)
            }
        elif provider == 'openai':
            return {
                'provider': 'openai',
                'api_key': self.config['env']['openai_api_key'],
                'model': self.config['env']['openai_model'],
                'temperature': self.get('agent.temperature', 0.1),
                'max_tokens': self.get('agent.max_tokens', 1000)
            }
        else:
            # Fallback to Ollama
            return {
                'provider': 'ollama',
                'model': self.get('agent.model', 'llama3.2:3b'),
                'base_url': self.get('agent.ollama_base_url', 'http://localhost:11434'),
                'temperature': self.get('agent.temperature', 0.1)
            }
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration - NO prefix in model names"""
        provider = self.config['env']['embedding_provider']
        
        if provider == 'gemini':
            return {
                'provider': 'gemini',
                'api_key': self.config['env']['google_api_key'],
                'model': self.config['env']['gemini_embedding_model'],  # Just "text-embedding-004"
                'task_type': 'retrieval_document'
            }
        elif provider == 'openai':
            return {
                'provider': 'openai',
                'api_key': self.config['env']['openai_api_key'],
                'model': self.config['env']['openai_embedding_model']
            }
        else:
            return {
                'provider': 'ollama',
                'model': self.get('agent.embedding_model', 'mxbai-embed-large'),
                'base_url': self.get('agent.ollama_base_url', 'http://localhost:11434')
            }

# Global config instance
config = ConfigLoader()
