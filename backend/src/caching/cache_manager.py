"""
Multi-layer cache manager for RAG agent
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

class ExactMatchCache:
    """In-memory exact match cache with TTL"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = OrderedDict()
        self.ttl = ttl
        self.max_size = max_size
    
    def _get_key(self, query: str) -> str:
        """Generate cache key"""
        return hashlib.md5(query.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[str]:
        """Get cached response"""
        key = self._get_key(query)
        
        if key in self.cache:
            response, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                logger.debug(f"Exact cache hit for query: {query[:50]}...")
                return response
            else:
                # Expired
                del self.cache[key]
        
        return None
    
    def set(self, query: str, response: str):
        """Cache response"""
        key = self._get_key(query)
        
        # Manage size
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        self.cache[key] = (response, datetime.now())
        logger.debug(f"Cached response for query: {query[:50]}...")


class SemanticCache:
    """Semantic cache using vector similarity"""
    
    def __init__(self, vector_store, embedding_model, threshold: float = 0.95):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.threshold = threshold
        self.collection_name = "semantic_cache"
    
    def get(self, query: str) -> Optional[str]:
        """Find similar query in cache"""
        try:
            results = self.vector_store.similarity_search_with_score(
                query, 
                k=1,
                filter={"cache_type": "semantic"}
            )
            
            if results and results[0][1] > self.threshold:
                logger.debug(f"Semantic cache hit with score: {results[0][1]}")
                return results[0][0].metadata.get("answer")
        except Exception as e:
            logger.warning(f"Semantic cache error: {e}")
        
        return None
    
    def set(self, query: str, answer: str, metadata: Dict = None):
        """Store query-answer pair in semantic cache"""
        from langchain_core.documents import Document
        
        doc = Document(
            page_content=query,
            metadata={
                "answer": answer,
                "cache_type": "semantic",
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
        )
        
        try:
            self.vector_store.add_documents([doc])
        except Exception as e:
            logger.warning(f"Failed to store semantic cache: {e}")


class CacheManager:
    """Orchestrates multiple cache layers"""
    
    def __init__(self, config: Dict, vector_store=None, embedding_model=None):
        self.config = config
        self.enabled = config.get('enabled', True)
        
        # Initialize cache layers
        self.exact_cache = None
        self.semantic_cache = None
        
        if config.get('layers', {}).get('exact_match', {}).get('enabled'):
            exact_config = config['layers']['exact_match']
            self.exact_cache = ExactMatchCache(
                max_size=exact_config.get('max_size', 1000),
                ttl=exact_config.get('ttl', 3600)
            )
        
        if config.get('layers', {}).get('semantic', {}).get('enabled'):
            if vector_store and embedding_model:
                sem_config = config['layers']['semantic']
                self.semantic_cache = SemanticCache(
                    vector_store=vector_store,
                    embedding_model=embedding_model,
                    threshold=sem_config.get('similarity_threshold', 0.95)
                )
        
        self.stats = {
            'exact_hits': 0,
            'semantic_hits': 0,
            'misses': 0,
            'total_queries': 0
        }
    
    async def get(self, query: str) -> Optional[str]:
        """Get from cache (checks layers in order)"""
        if not self.enabled:
            return None
        
        self.stats['total_queries'] += 1
        
        # Layer 1: Exact match
        if self.exact_cache:
            result = self.exact_cache.get(query)
            if result:
                self.stats['exact_hits'] += 1
                return result
        
        # Layer 2: Semantic
        if self.semantic_cache:
            result = self.semantic_cache.get(query)
            if result:
                self.stats['semantic_hits'] += 1
                # Promote to exact cache
                if self.exact_cache:
                    self.exact_cache.set(query, result)
                return result
        
        self.stats['misses'] += 1
        return None
    
    async def set(self, query: str, answer: str, metadata: Dict = None):
        """Store in all cache layers"""
        if not self.enabled:
            return
        
        if self.exact_cache:
            self.exact_cache.set(query, answer)
        
        if self.semantic_cache:
            self.semantic_cache.set(query, answer, metadata)
    
    def get_stats(self) -> Dict:
        """Get cache performance statistics"""
        total = self.stats['total_queries']
        hits = self.stats['exact_hits'] + self.stats['semantic_hits']
        
        return {
            **self.stats,
            'hit_rate': hits / total if total > 0 else 0,
            'exact_hit_rate': self.stats['exact_hits'] / total if total > 0 else 0,
            'semantic_hit_rate': self.stats['semantic_hits'] / total if total > 0 else 0
        }
