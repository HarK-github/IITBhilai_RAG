#!/usr/bin/env python3
"""
Test chunking registry - prevents duplicate chunking
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)

async def main():
    from src.ingestion.document_ingestion import SmartDocumentIngestion
    from src.core.llm_factory import EmbeddingFactory
    from src.core.config_loader import config
    from src.ingestion.vector_store_wrapper import VectorStoreWrapper
    
    print("=" * 60)
    print("Testing Chunking Registry - Preventing Duplicate Chunking")
    print("=" * 60)
    
    # Initialize
    embedding_config = config.get_embedding_config()
    embeddings = EmbeddingFactory.create_embeddings(embedding_config)
    vector_store = VectorStoreWrapper(embeddings)
    
    # Create ingestion with registry
    ingestion = SmartDocumentIngestion(
        vector_store.vector_store,
        embeddings,
        config={"chunk_size": 1000, "chunk_overlap": 150}
    )
    
    # First ingestion
    print("\n📄 First ingestion attempt...")
    result1 = await ingestion.ingest_pdf(
        Path("./backend/courses_study.pdf"),
        namespace="test",
        force_rechunk=False
    )
    print(f"Result: {result1}")
    
    # Second ingestion (should skip)
    print("\n📄 Second ingestion attempt (should skip)...")
    result2 = await ingestion.ingest_pdf(
        Path("./backend/courses_study.pdf"),
        namespace="test",
        force_rechunk=False
    )
    print(f"Result: {result2}")
    
    # Show registry stats
    print("\n📊 Chunking Registry Statistics:")
    stats = ingestion.get_registry_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Force re-chunking
    print("\n🔄 Force re-chunking...")
    result3 = await ingestion.ingest_pdf(
        Path("./backend/courses_study.pdf"),
        namespace="test",
        force_rechunk=True
    )
    print(f"Result: {result3}")
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
