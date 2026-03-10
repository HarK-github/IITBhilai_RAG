#!/usr/bin/env python3
"""
Test caching with working orchestrator
"""
import asyncio
import time
from src.core.orchestrator_with_cache import CachedAgentOrchestrator

async def main():
    print("=" * 60)
    print("Testing Two-Layer Cache System")
    print("=" * 60)
    
    orch = CachedAgentOrchestrator()
    
    test_queries = [
        "What courses are offered?",
        "What courses are offered?",           # exact duplicate
        "What courses are available?",         # semantic variation
        "List all courses",                    # semantic variation
        "Tell me about BTech programs"         # new topic
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*40}")
        print(f"Query {i}: '{query}'")
        print(f"{'='*40}")
        
        start = time.time()
        result = await orch.query(query)
        elapsed = time.time() - start
        
        print(f"✅ Answer: {result['answer'][:150]}...")
        print(f"📈 Cache: {'HIT' if result['from_cache'] else 'MISS'} ({result['cache_layer']})")
        print(f"⏱️ Time: {elapsed:.3f}s (orchestrator reported: {result['processing_time']:.3f}s)")
    
    print("\n" + "=" * 60)
    print("Final Cache Statistics:")
    print("=" * 60)
    stats = orch.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n🎉 Cache hit rate: {stats.get('hit_rate', 0)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
