"""
LLM and embedding factories with provider normalization.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory for creating LLM instances"""
    
    @staticmethod
    def create_llm(config: dict):
        provider = LLMFactory._normalize_provider(config.get('provider', 'gemini'))
        
        try:
            if provider == 'gemini':
                return LLMFactory._create_gemini(config)
            elif provider == 'openai':
                return LLMFactory._create_openai(config)
            elif provider == 'ollama':
                return LLMFactory._create_ollama(config)
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to create LLM: {e}")
            raise

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        aliases = {
            "local": "ollama",
            "ollama": "ollama",
            "gemini": "gemini",
            "google": "gemini",
            "openai": "openai",
        }
        return aliases.get((provider or "").strip().lower(), (provider or "gemini").strip().lower())
    
    @staticmethod 
    def _create_gemini(config: dict):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise ImportError(
                "langchain-google-genai is required for the Gemini provider. "
                "Install backend requirements before switching to Gemini."
            ) from exc
        
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found")
        
        model = config.get('model', 'gemini-2.5-flash')

        kwargs: Dict[str, Any] = {
            "model": model,
            "google_api_key": api_key,
            "temperature": config.get('temperature', 0.1),
            "convert_system_message_to_human": True,
        }
        max_tokens = config.get('max_tokens', 1000)
        try:
            llm = ChatGoogleGenerativeAI(max_output_tokens=max_tokens, **kwargs)
        except TypeError:
            # Older package versions may still expect max_tokens.
            llm = ChatGoogleGenerativeAI(max_tokens=max_tokens, **kwargs)
        
        logger.info(f"Initialized Gemini LLM with model: {model}")
        return llm

    @staticmethod
    def _create_openai(config: dict):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required for the OpenAI provider."
            ) from exc
        
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        llm = ChatOpenAI(
            model=config.get('model', 'gpt-3.5-turbo'),
            api_key=api_key,
            temperature=config.get('temperature', 0.1),
            max_tokens=config.get('max_tokens', 1000)
        )
        
        logger.info(f"Initialized OpenAI LLM with model: {config.get('model')}")
        return llm
    
    @staticmethod
    def _create_ollama(config: dict):
        try:
            from langchain_ollama import OllamaLLM
        except ImportError as exc:
            raise ImportError(
                "langchain-ollama is required for the local Ollama provider."
            ) from exc
        
        llm = OllamaLLM(
            model=config.get('model', 'llama3.2:3b'),
            base_url=config.get('base_url', 'http://localhost:11434'),
            temperature=config.get('temperature', 0.1)
        )
        
        logger.info(f"Initialized Ollama LLM with model: {config.get('model')}")
        return llm


class EmbeddingFactory:
    """Factory for creating embedding models"""
    
    @staticmethod
    def create_embeddings(config: dict):
        provider = LLMFactory._normalize_provider(config.get('provider', 'gemini'))
        
        try:
            if provider == 'gemini':
                return EmbeddingFactory._create_gemini_embeddings(config)
            elif provider == 'openai':
                return EmbeddingFactory._create_openai_embeddings(config)
            elif provider == 'ollama':
                return EmbeddingFactory._create_ollama_embeddings(config)
            else:
                raise ValueError(f"Unknown embedding provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            raise
    
    @staticmethod
    def _create_gemini_embeddings(config: dict):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "langchain-google-genai is required for Gemini embeddings."
            ) from exc
        
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found")
        
        # Use gemini-embedding-2 (works with new DB)
        model = config.get('model', 'gemini-embedding-2')
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model=model,
            google_api_key=api_key
        )
        
        logger.info(f"Initialized Gemini embeddings with model: {model}")
        return embeddings

    @staticmethod
    def _create_openai_embeddings(config: dict):
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required for OpenAI embeddings."
            ) from exc
        
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        embeddings = OpenAIEmbeddings(
            model=config.get('model', 'text-embedding-3-small'),
            api_key=api_key
        )
        
        logger.info(f"Initialized OpenAI embeddings with model: {config.get('model')}")
        return embeddings
    
    @staticmethod
    def _create_ollama_embeddings(config: dict):
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as exc:
            raise ImportError(
                "langchain-ollama is required for Ollama embeddings."
            ) from exc
        
        embeddings = OllamaEmbeddings(
            model=config.get('model', 'mxbai-embed-large'),
            base_url=config.get('base_url', 'http://localhost:11434')
        )
        
        logger.info(f"Initialized Ollama embeddings with model: {config.get('model')}")
        return embeddings
