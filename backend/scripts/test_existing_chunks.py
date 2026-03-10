#!/usr/bin/env python3
"""
Test using existing chunks from Chroma DB
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
logging.basicConfig(level=logging.INFO)

async def main():
    from src.core.llm_factory import EmbeddingFactory
    from src.core.config_loader import config
    from src.ingestion.vector_store_wrapper import VectorStoreWrapper
    from src.core.orchestrator import AgentOrchestrator
    
    print("=" * 60)
    print("Testing Existing Chunks")
    print("=" * 60)
    
    # Check vector store
    embedding_config = config.get_embedding_config()
    embeddings = EmbeddingFactory.create_embeddings(embedding_config)
    vector_store = VectorStoreWrapper(embeddings)
    
    print(f"\n📊 Vector Store Status:")
    print(f"   Has chunks: {vector_store.has_chunks()}")
    print(f"   Chunk count: {vector_store.get_chunk_count()}")
    
    stats = vector_store.get_collection_stats()
    print(f"   Collection stats: {stats}")
    
    if vector_store.has_chunks():
        print("\n✅ Using existing chunks!")
        
        # Test a search
        print("\n🔍 Testing search with existing chunks...")
        results = vector_store.similarity_search("What courses are offered?", k=3)
        
        if results:
            print(f"   Found {len(results)} results")
            print(f"\n📄 First result preview:")
            print(f"   {results[0].page_content[:300]}...")
            print(f"\n   Metadata: {results[0].metadata}")
        else:
            print("   No results found - embedding dimension mismatch?")
    else:
        print("\n❌ No existing chunks found!")
    
    # Test the full orchestrator
    print("\n" + "=" * 60)
    print("Testing Full Orchestrator with Existing Chunks")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    result = await orchestrator.query("What courses are offered at IIT Bhilai?")
    
    print(f"\n📝 Answer: {result['answer']}")
    print(f"\n📊 Metadata:")
    print(f"   From cache: {result['from_cache']}")
    print(f"   Processing time: {result['processing_time']:.2f}s")
    print(f"   Tools used: {result['tools_used']}")

if __name__ == "__main__":
    asyncio.run(main())
