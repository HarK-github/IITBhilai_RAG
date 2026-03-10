import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.orchestrator_with_cache import CachedAgentOrchestrator

async def main():
    orch = CachedAgentOrchestrator()
    question = "What courses are offered at IIT Bhilai?"
    
    # Step 1: Direct search
    print("=== Direct search results ===")
    direct_result = await orch._direct_search(question)
    if direct_result:
        print(f"Content length: {len(direct_result.content)} chars")
        print(f"Content preview: {direct_result.content[:500]}...")
    else:
        print("No direct search results")
    
    # Step 2: Combine results (simulate tool results)
    tool_results = []
    if direct_result:
        tool_results.append(direct_result)
    context = orch._combine_results(tool_results)
    print(f"\n=== Combined context (length: {len(context)} chars) ===")
    print(context[:800])
    
    # Step 3: Generate answer
    print("\n=== Generating answer ===")
    answer = await orch._generate_answer(question, context)
    print(f"Answer: {answer}")

asyncio.run(main())
