#!/usr/bin/env python3
"""Test caching performance"""

import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_caching():
    from src.core.orchestrator import AgentOrchestrator
    
    print("Initializing orchestrator...")
    orchestrator = AgentOrchestrator()
    
    question = "What courses are offered at IIT Bhilai?"
    
    print(f"\n📝 Testing with question: {question}\n")
    
    # First query (should be cache miss)
    print("🔄 First query (should be CACHE MISS)...")
    start = time.time()
    result1 = await orchestrator.query(question, use_cache=True)
    time1 = time.time() - start
    print(f"   ✅ Completed in {time1:.2f}s")
    print(f"   📊 From cache: {result1['from_cache']}")
    print(f"   💡 Answer preview: {result1['answer'][:100]}...")
    
    # Second query (should be cache hit)
    print("\n🔄 Second query (should be CACHE HIT)...")
    start = time.time()
    result2 = await orchestrator.query(question, use_cache=True)
    time2 = time.time() - start
    print(f"   ✅ Completed in {time2:.2f}s")
    print(f"   📊 From cache: {result2['from_cache']}")
    print(f"   💡 Answer preview: {result2['answer'][:100]}...")
    
    # Compare
    print("\n" + "="*50)
    print("📊 CACHE PERFORMANCE SUMMARY")
    print("="*50)
    print(f"First query (miss):  {time1:.2f}s")
    print(f"Second query (hit):  {time2:.2f}s")
    print(f"Speed improvement:    {((time1 - time2)/time1)*100:.1f}% faster")
    
    if result2['from_cache']:
        print("\n✅ CACHING IS WORKING! Second query served from cache.")
    else:
        print("\n⚠️ Caching may not be working. Checking stats...")
        stats = orchestrator.get_stats()
        if 'cache' in stats:
            print(f"Cache stats: {stats['cache']}")
        else:
            print("Cache not initialized properly")

if __name__ == "__main__":
    asyncio.run(test_caching())
