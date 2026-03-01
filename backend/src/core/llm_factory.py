"""
LLM Factory - Supports multiple providers
"""
import logging
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory for creating LLM instances"""
    
    @staticmethod
    def create_llm(config: dict):
        provider = config.get('provider', 'gemini')
        
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
    def _create_gemini(config: dict):
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found")
        
        model = config.get('model', 'gemini-2.5-flash')
        
        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=config.get('temperature', 0.1),
            max_tokens=config.get('max_tokens', 1000),
            convert_system_message_to_human=True
        )
        
        logger.info(f"Initialized Gemini LLM with model: {model}")
        return llm

    @staticmethod
    def _create_openai(config: dict):
        from langchain_openai import ChatOpenAI
        
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
        from langchain_ollama import OllamaLLM
        
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
        provider = config.get('provider', 'gemini')
        
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
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        
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
        from langchain_openai import OpenAIEmbeddings
        
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
        from langchain_ollama import OllamaEmbeddings
        
        embeddings = OllamaEmbeddings(
            model=config.get('model', 'mxbai-embed-large'),
            base_url=config.get('base_url', 'http://localhost:11434')
        )
        
        logger.info(f"Initialized Ollama embeddings with model: {config.get('model')}")
        return embeddings
