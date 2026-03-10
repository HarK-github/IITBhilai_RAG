#!/usr/bin/env python3
"""
Inspect existing Chroma DB to see what chunks are stored
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.utils import embedding_functions

def inspect_db():
    print("=" * 60)
    print("Inspecting Existing Chroma DB")
    print("=" * 60)
    
    # Connect to existing DB
    client = chromadb.PersistentClient(path="./chroma_langchain_db")
    
    # List all collections
    collections = client.list_collections()
    print(f"\n📚 Collections found: {len(collections)}")
    for col in collections:
        print(f"  - {col.name}: {col.count()} documents")
    
    # Get the main collection
    if collections:
        collection = collections[0]
        print(f"\n📄 Collection: {collection.name}")
        print(f"   Document count: {collection.count()}")
        
        # Get a sample document
        if collection.count() > 0:
            sample = collection.get(limit=1)
            if sample['metadatas']:
                print(f"\n📝 Sample document metadata:")
                for key, value in sample['metadatas'][0].items():
                    print(f"   {key}: {value}")
                
                print(f"\n📄 Sample content preview:")
                print(f"   {sample['documents'][0][:200]}...")
    
    print("\n✅ Inspection complete!")

if __name__ == "__main__":
    inspect_db()
