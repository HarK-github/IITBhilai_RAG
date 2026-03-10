#!/usr/bin/env python3
"""
Test two-layer caching system
"""
import asyncio
import time
from src.core.orchestrator_with_cache import CachedAgentOrchestrator

async def test_caching():
    print("=" * 60)
    print("Testing Two-Layer Cache System")
    print("=" * 60)
    
    orchestrator = CachedAgentOrchestrator()
    
    # Test queries (same and similar)
    test_queries = [
        "What courses are offered?",
        "What courses are offered?",  # Exact duplicate
        "What courses are available?",  # Semantic duplicate
        "List all courses",  # Semantic duplicate
        "Tell me about BTech programs"  # Different question
    ]
    
    print("\n📊 Initial Cache Stats:")
    print(orchestrator.get_cache_stats())
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*40}")
        print(f"Query {i}: '{query}'")
        print(f"{'='*40}")
        
        start = time.time()
        result = await orchestrator.query(query)
        elapsed = time.time() - start
        
        print(f"✅ Answer: {result['answer'][:150]}...")
        print(f"📈 Cache: {'HIT' if result['from_cache'] else 'MISS'} ({result['cache_layer']})")
        print(f"⏱️ Total time: {result['processing_time']:.3f}s")
        
        if result['from_cache']:
            print(f"💾 Retrieved from: {result['cache_layer']} cache")
    
    print("\n" + "=" * 60)
    print("Final Cache Statistics:")
    print("=" * 60)
    stats = orchestrator.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n🎉 Cache hit rate: {stats.get('hit_rate', 0)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(test_caching())
