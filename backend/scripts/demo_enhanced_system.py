#!/usr/bin/env python3
"""
Demo of Phase 1 + Phase 2: Document ingestion + Two-layer caching
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo():
    from src.ingestion.document_watcher import DocumentIngestionPipeline
    from src.caching.enhanced_cache import ExactMatchCache, SemanticCache, EnhancedCacheManager
    from src.core.llm_factory import EmbeddingFactory
    from src.core.config_loader import config
    from src.ingestion.vector_store_wrapper import VectorStoreWrapper
    
    print("=" * 60)
    print("Phase 1 + Phase 2 Demo: Document Ingestion & Two-Layer Caching")
    print("=" * 60)
    
    # Initialize embeddings and vector store
    embedding_config = config.get_embedding_config()
    embeddings = EmbeddingFactory.create_embeddings(embedding_config)
    vector_store = VectorStoreWrapper(embeddings)
    
    # Initialize ingestion pipeline
    ingestion_config = {
        "chunk_size": 1000,
        "chunk_overlap": 150
    }
    ingestion = DocumentIngestionPipeline(
        vector_store.vector_store,
        embeddings,
        ingestion_config
    )
    
    # Initialize caches
    exact_cache = ExactMatchCache(redis_client=None, ttl=86400)
    semantic_cache = SemanticCache(
        vector_store.vector_store,
        embeddings,
        similarity_threshold=0.90
    )
    cache_manager = EnhancedCacheManager(
        config={"enabled": True},
        exact_cache=exact_cache,
        semantic_cache=semantic_cache
    )
    
    print("\n📄 Phase 1: Document Ingestion")
    print("-" * 40)
    
    # Ingest a PDF
    pdf_files = list(Path("./backend").glob("*.pdf"))
    if pdf_files:
        result = await ingestion.ingest_pdf(pdf_files[0], namespace="demo_courses")
        print(f"✅ Ingested: {result}")
    
    print("\n💾 Phase 2: Cache Testing")
    print("-" * 40)
    
    # Test queries
    test_queries = [
        "What courses are offered?",
        "What courses are offered?",  # Exact duplicate
        "Tell me about available courses",  # Semantic variation
        "List all BTech programs"  # Different question
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        
        # Check cache
        cached = await cache_manager.get(query)
        
        if cached:
            print(f"  ✅ CACHE HIT ({cached['cache_layer']})")
            print(f"  Answer: {cached['answer'][:100]}...")
        else:
            print(f"  ❌ CACHE MISS")
            
            # Simulate generating answer (in real system, would call LLM)
            mock_answer = f"Mock answer for: {query}"
            mock_response = {"answer": mock_answer, "source": "demo"}
            
            # Store in cache
            await cache_manager.set(query, mock_response)
            print(f"  💾 Stored in cache")
    
    # Show cache statistics
    print("\n📊 Cache Statistics:")
    stats = cache_manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Demo complete!")

if __name__ == "__main__":
    asyncio.run(demo())
