#!/usr/bin/env python3
"""Test the orchestrator"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    from src.core.orchestrator import AgentOrchestrator
    
    print("Initializing orchestrator...")
    orchestrator = AgentOrchestrator()
    
    stats = orchestrator.get_stats()
    print(f"\nStats: {stats}")
    
    # Test query
    question = "WWhat are the CSE core courses?"
    print(f"\nQuestion: {question}")
    
    result = await orchestrator.query(question)
    print(f"\nAnswer: {result['answer']}")
    print(f"\nMetadata:")
    print(f"  - From cache: {result['from_cache']}")
    print(f"  - Processing time: {result['processing_time']:.2f}s")
    print(f"  - Tools used: {result['tools_used']}")

if __name__ == "__main__":
    asyncio.run(main())
