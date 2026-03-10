import asyncio
import sys
sys.path.insert(0, '.')

from src.core.orchestrator_with_cache import CachedAgentOrchestrator

async def main():
    orch = CachedAgentOrchestrator()
    
    # Manually simulate what happens in query()
    question = "What courses are offered?"
    
    # Get direct search results
    context = await orch._direct_search(question)
    if context:
        print("=" * 60)
        print("CONTEXT from direct search:")
        print("=" * 60)
        print(context.content[:800])
        print("\n" + "=" * 60)
        
        # Now generate answer
        print("Generating answer from LLM...")
        answer = await orch._generate_answer(question, context.content)
        print(f"\nLLM Answer: {answer}")
    else:
        print("No context found")

asyncio.run(main())
