"""
Configuration loader with environment variables and YAML files.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class ConfigLoader:
    """Load and manage configuration"""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = Path(__file__).resolve().parents[1] / "config"
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
            'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            'ollama_model': os.getenv('OLLAMA_MODEL', self.get('agent.model', 'llama3.2:3b')),
            'embedding_provider': os.getenv('EMBEDDING_PROVIDER', 'gemini'),
            'gemini_embedding_model': os.getenv('GEMINI_EMBEDDING_MODEL', 'text-embedding-004'),
            'openai_embedding_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
            'ollama_embedding_model': os.getenv('OLLAMA_EMBEDDING_MODEL', self.get('agent.embedding_model', 'mxbai-embed-large')),
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
    
    @staticmethod
    def _normalize_provider(provider: Optional[str], default: str = "gemini") -> str:
        """Normalize provider aliases to a canonical name."""
        normalized = (provider or default).strip().lower()
        aliases = {
            "local": "ollama",
            "ollama": "ollama",
            "gemini": "gemini",
            "google": "gemini",
            "openai": "openai",
        }
        return aliases.get(normalized, normalized)

    def get_llm_config(
        self,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get LLM configuration, optionally overriding the active provider."""
        provider = self._normalize_provider(
            provider_override or self.config['env']['llm_provider']
        )
        
        if provider == 'gemini':
            return {
                'provider': 'gemini',
                'api_key': self.config['env']['google_api_key'],
                'model': model_override or self.config['env']['gemini_model'],
                'temperature': self.get('agent.temperature', 0.1),
                'max_tokens': self.get('agent.max_tokens', 1000),
                'display_name': 'Gemini'
            }
        elif provider == 'openai':
            return {
                'provider': 'openai',
                'api_key': self.config['env']['openai_api_key'],
                'model': model_override or self.config['env']['openai_model'],
                'temperature': self.get('agent.temperature', 0.1),
                'max_tokens': self.get('agent.max_tokens', 1000),
                'display_name': 'OpenAI'
            }
        elif provider == 'ollama':
            return {
                'provider': 'ollama',
                'model': model_override or self.config['env']['ollama_model'],
                'base_url': self.get('agent.ollama_base_url', 'http://localhost:11434'),
                'temperature': self.get('agent.temperature', 0.1),
                'display_name': 'Local Ollama'
            }
        raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def get_embedding_config(
        self,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get embedding configuration."""
        provider = self._normalize_provider(
            provider_override or self.config['env']['embedding_provider']
        )
        
        if provider == 'gemini':
            return {
                'provider': 'gemini',
                'api_key': self.config['env']['google_api_key'],
                'model': model_override or self.config['env']['gemini_embedding_model'],
                'task_type': 'retrieval_document',
                'display_name': 'Gemini Embeddings'
            }
        elif provider == 'openai':
            return {
                'provider': 'openai',
                'api_key': self.config['env']['openai_api_key'],
                'model': model_override or self.config['env']['openai_embedding_model'],
                'display_name': 'OpenAI Embeddings'
            }
        elif provider == 'ollama':
            return {
                'provider': 'ollama',
                'model': model_override or self.config['env']['ollama_embedding_model'],
                'base_url': self.get('agent.ollama_base_url', 'http://localhost:11434')
            }
        raise ValueError(f"Unsupported embedding provider: {provider}")

    def get_runtime_summary(self) -> Dict[str, Any]:
        """Return a compact view of the active model configuration."""
        llm = self.get_llm_config()
        embeddings = self.get_embedding_config()
        return {
            "llm_provider": llm["provider"],
            "llm_model": llm["model"],
            "embedding_provider": embeddings["provider"],
            "embedding_model": embeddings["model"],
            "embedding_namespace": self.get_embedding_namespace(embeddings),
            "chroma_dir": self.config["env"]["chroma_dir"],
        }

    @staticmethod
    def _slugify(value: str, max_length: int = 48) -> str:
        """Create a stable Chroma-safe identifier."""
        cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        if len(cleaned) <= max_length:
            return cleaned or "default"
        return cleaned[:max_length].strip("_") or "default"

    def get_embedding_namespace(self, embedding_config: Optional[Dict[str, Any]] = None) -> str:
        """Create a namespace that isolates vector stores by embedding provider/model."""
        embedding_config = embedding_config or self.get_embedding_config()
        provider = self._slugify(str(embedding_config.get("provider", "default")))
        model = self._slugify(str(embedding_config.get("model", "default")))
        return f"{provider}__{model}"

    def get_collection_name(self, base_name: str, embedding_config: Optional[Dict[str, Any]] = None) -> str:
        """Build a provider/model-specific collection name."""
        namespace = self.get_embedding_namespace(embedding_config)
        return f"{self._slugify(base_name)}__{namespace}"

# Global config instance
config = ConfigLoader()
