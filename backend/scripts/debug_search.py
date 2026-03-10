#!/usr/bin/env python3
"""
Debug search to see what's being retrieved
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from src.core.llm_factory import EmbeddingFactory
from src.core.config_loader import config
from src.ingestion.vector_store_wrapper import VectorStoreWrapper

async def debug():
    print("=" * 60)
    print("Debugging Vector Search")
    print("=" * 60)
    
    # Initialize
    embedding_config = config.get_embedding_config()
    embeddings = EmbeddingFactory.create_embeddings(embedding_config)
    vector_store = VectorStoreWrapper(embeddings)
    
    print(f"\n📊 Database Stats: {vector_store.get_collection_stats()}")
    
    # Test different queries
    test_queries = [
        "courses",
        "BTech", 
        "programs",
        "Bachelor of Technology",
        "What courses are offered"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        results = vector_store.similarity_search(query, k=3)
        
        if results:
            print(f"   Found {len(results)} results")
            for i, doc in enumerate(results, 1):
                print(f"\n   Result {i}:")
                print(f"   Content: {doc.page_content[:150]}...")
                print(f"   Metadata: source={doc.metadata.get('source', 'unknown')}, page={doc.metadata.get('page', 'unknown')}")
        else:
            print("   ❌ No results found!")

if __name__ == "__main__":
    asyncio.run(debug())
