"""
Orchestrator with full caching integration (Exact + Semantic)
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate

from src.tools import ToolRegistry, ToolResult
from src.ingestion import VectorStoreWrapper
from src.core.config_loader import config
from src.core.llm_factory import LLMFactory, EmbeddingFactory

logger = logging.getLogger(__name__)


class ExactMatchCache:
    """Simple in-memory exact match cache"""
    def __init__(self, ttl: int = 86400):
        self.cache = {}
        self.ttl = ttl
    
    async def get(self, query: str):
        key = query.lower().strip()
        if key in self.cache:
            return self.cache[key]
        return None
    
    async def set(self, query: str, response: Dict):
        key = query.lower().strip()
        self.cache[key] = response


class SemanticCache:
    """Semantic cache using vector store - simplified"""
    def __init__(self, vector_store, embedding_model, similarity_threshold: float = 0.90):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
    
    async def get(self, query: str) -> Optional[Dict]:
        try:
            results = self.vector_store.similarity_search_with_score(query, k=1)
            if results and results[0][1] >= self.similarity_threshold:
                doc = results[0][0]
                if doc.metadata.get('cache_type') == 'semantic':
                    import json
                    return json.loads(doc.metadata.get('response', '{}'))
        except Exception as e:
            logger.debug(f"Semantic cache error: {e}")
        return None
    
    async def set(self, query: str, response: Dict):
        from langchain_core.documents import Document
        import json
        
        doc = Document(
            page_content=query.lower().strip(),
            metadata={
                "cache_type": "semantic",
                "response": json.dumps(response),
                "timestamp": datetime.now().isoformat()
            }
        )
        try:
            self.vector_store.add_documents([doc])
        except Exception as e:
            logger.warning(f"Failed to store semantic cache: {e}")


class CachedAgentOrchestrator:
    """Orchestrator with two-layer caching"""
    
    def __init__(self):
        self.cache_manager = None
        self.tool_registry = None
        self.vector_store_wrapper = None
        self.llm = None
        self.embeddings = None
        
        self.setup_logging()
        self.setup_components()
        self.setup_cache()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def setup_components(self):
        """Initialize LLM and vector store"""
        try:
            llm_config = config.get_llm_config()
            self.llm = LLMFactory.create_llm(llm_config)
            logger.info(f"LLM initialized: {llm_config['provider']}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
        
        try:
            embedding_config = config.get_embedding_config()
            self.embeddings = EmbeddingFactory.create_embeddings(embedding_config)
            logger.info(f"Embeddings initialized: {embedding_config['provider']}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            self.embeddings = None
        
        try:
            self.vector_store_wrapper = VectorStoreWrapper(self.embeddings)
            stats = self.vector_store_wrapper.get_collection_stats()
            logger.info(f"Vector store connected: {stats}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            self.vector_store_wrapper = None
        
        self.tool_registry = ToolRegistry("src/config/websites.yaml")
        if self.vector_store_wrapper:
            self.tool_registry.set_vector_store(self.vector_store_wrapper)
            self.tool_registry.register_all_websites()
            logger.info(f"Registered {len(self.tool_registry.tools)} tools")
    
    def setup_cache(self):
        """Setup simple cache"""
        self.exact_cache = ExactMatchCache()
        self.semantic_cache = None
        if self.vector_store_wrapper and self.embeddings:
            self.semantic_cache = SemanticCache(
                vector_store=self.vector_store_wrapper.vector_store,
                embedding_model=self.embeddings,
                similarity_threshold=0.90
            )
        logger.info("✅ Cache system initialized")
    
    async def query(self, question: str, use_cache: bool = True) -> Dict[str, Any]:
        start_time = datetime.now()
        
        # Check exact cache
        if use_cache:
            cached = await self.exact_cache.get(question)
            if cached:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Exact cache HIT in {elapsed:.3f}s")
                cached["from_cache"] = True
                cached["cache_layer"] = "exact"
                cached["processing_time"] = elapsed
                return cached
            
            # Check semantic cache
            if self.semantic_cache:
                cached = await self.semantic_cache.get(question)
                if cached:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"✅ Semantic cache HIT in {elapsed:.3f}s")
                    cached["from_cache"] = True
                    cached["cache_layer"] = "semantic"
                    cached["processing_time"] = elapsed
                    return cached
        
        # Cache miss - generate fresh response
        logger.info(f"❌ CACHE MISS - Generating fresh response")
        
        # Direct vector search
        context = await self._direct_search(question)
        answer = await self._generate_answer(question, context if context else "")
        
        response = {
            "answer": answer,
            "from_cache": False,
            "cache_layer": "miss",
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "tools_used": ["vector_store"],
            "num_sources": 1
        }
        
        # Store in cache
        if use_cache and answer and "cannot find" not in answer.lower():
            await self.exact_cache.set(question, response)
            if self.semantic_cache:
                await self.semantic_cache.set(question, response)
            logger.info(f"💾 Response cached")
        
        return response
    
    async def _direct_search(self, question: str) -> Optional[str]:
        """Direct vector search"""
        if not self.vector_store_wrapper:
            return None
        
        try:
            results = self.vector_store_wrapper.similarity_search(question, k=3)
            if results:
                content_parts = []
                for doc in results:
                    # Skip cache entries
                    if hasattr(doc, 'metadata') and doc.metadata.get('cache_type') == 'semantic':
                        continue
                    if hasattr(doc, 'page_content'):
                        content_parts.append(doc.page_content)
                content = "\n\n".join(content_parts[:3])
                logger.info(f"Direct search found {len(content_parts)} real documents")
                return content
        except Exception as e:
            logger.error(f"Direct search failed: {e}")
        return None
    
    async def _generate_answer(self, question: str, context: str) -> str:
        if not self.llm:
            return context[:500] if context else "LLM not available"
        
        try:
            template = """You are an AI assistant for IIT Bhilai. Answer based ONLY on the context.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""
            
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | self.llm
            
            if len(context) > 3000:
                context = context[:3000] + "..."
            
            result = chain.invoke({"context": context, "question": question})
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Based on available documents: {context[:500]}..."
    
    def get_cache_stats(self) -> Dict:
        return {"exact_hits": 0, "semantic_hits": 0, "hit_rate": 0}
    
    def get_stats(self) -> Dict:
        return {
            "tools_available": len(self.tool_registry.tools) if self.tool_registry else 0,
            "vector_store_available": self.vector_store_wrapper is not None,
            "llm_available": self.llm is not None
        }
