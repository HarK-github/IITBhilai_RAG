"""
Two-layer caching system - Uses separate collection for semantic cache
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import OrderedDict
import asyncio

logger = logging.getLogger(__name__)


class ExactMatchCache:
    """Layer 1: Exact string match cache"""
    
    def __init__(self, redis_client=None, ttl: int = 86400):
        self.redis_client = redis_client
        self.ttl = ttl
        self.in_memory_cache = OrderedDict()
        self.max_memory_size = 1000
    
    def _generate_hash(self, query: str) -> str:
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    async def get(self, query: str) -> Optional[Dict]:
        hash_id = self._generate_hash(query)
        
        if hash_id in self.in_memory_cache:
            response, timestamp = self.in_memory_cache[hash_id]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return response
            else:
                del self.in_memory_cache[hash_id]
        return None
    
    async def set(self, query: str, response: Dict):
        hash_id = self._generate_hash(query)
        
        if len(self.in_memory_cache) >= self.max_memory_size:
            self.in_memory_cache.popitem(last=False)
        
        self.in_memory_cache[hash_id] = (response, datetime.now())
        logger.debug(f"Cached exact response for: {query[:50]}...")


class SemanticCache:
    """Layer 2: Vector similarity cache - Uses separate collection"""
    
    def __init__(self, cache_store, similarity_threshold: float = 0.90):
        self.cache_store = cache_store  # This is the separate cache collection
        self.similarity_threshold = similarity_threshold
    
    def _serialize_response(self, response: Dict) -> str:
        """Serialize response to JSON string"""
        serializable = {
            "answer": response.get("answer", ""),
            "tools_used": response.get("tools_used", []),
            "num_sources": response.get("num_sources", 0)
        }
        return json.dumps(serializable)
    
    def _deserialize_response(self, response_str: str) -> Dict:
        """Deserialize JSON string"""
        try:
            data = json.loads(response_str)
            data["from_cache"] = True
            data["cache_layer"] = "semantic"
            return data
        except:
            return {"answer": response_str, "from_cache": True, "cache_layer": "semantic"}
    
    async def get(self, query: str) -> Optional[Dict]:
        """Find semantically similar query in cache store only"""
        try:
            from langchain_core.documents import Document
            
            # Search only in cache store
            results = self.cache_store.similarity_search_with_score(query, k=1)
            
            if results and len(results) > 0:
                doc, score = results[0]
                if score >= self.similarity_threshold and doc.metadata.get("cache_type") == "semantic":
                    response_str = doc.metadata.get("response")
                    if response_str:
                        logger.info(f"✅ Semantic cache HIT (score: {score:.3f})")
                        return self._deserialize_response(response_str)
            
            return None
            
        except Exception as e:
            logger.warning(f"Semantic cache error: {e}")
            return None
    
    async def set(self, query: str, response: Dict):
        """Store in cache store only"""
        from langchain_core.documents import Document
        
        response_str = self._serialize_response(response)
        
        doc = Document(
            page_content=query.lower().strip(),
            metadata={
                "cache_type": "semantic",
                "response": response_str,
                "timestamp": datetime.now().isoformat(),
                "query_hash": hashlib.md5(query.lower().encode()).hexdigest()
            }
        )
        
        try:
            await asyncio.to_thread(self.cache_store.add_documents, [doc])
            logger.debug(f"Stored in semantic cache: {query[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to store semantic cache: {e}")


class EnhancedCacheManager:
    """Orchestrates two-layer cache system"""
    
    def __init__(self, config: Dict, exact_cache: ExactMatchCache, 
                 semantic_cache: SemanticCache):
        self.config = config
        self.exact_cache = exact_cache
        self.semantic_cache = semantic_cache
        self.stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "total_queries": 0
        }
    
    async def get(self, query: str) -> Optional[Dict]:
        self.stats["total_queries"] += 1
        
        result = await self.exact_cache.get(query)
        if result:
            self.stats["exact_hits"] += 1
            result["cache_layer"] = "exact"
            return result
        
        result = await self.semantic_cache.get(query)
        if result:
            self.stats["semantic_hits"] += 1
            return result
        
        self.stats["misses"] += 1
        return None
    
    async def set(self, query: str, response: Dict):
        await self.exact_cache.set(query, response)
        await self.semantic_cache.set(query, response)
    
    def get_stats(self) -> Dict:
        total = self.stats["total_queries"]
        hits = self.stats["exact_hits"] + self.stats["semantic_hits"]
        return {
            **self.stats,
            "hit_rate": hits / total if total > 0 else 0
        }
