#!/usr/bin/env python3
"""Clean up cache pollution from vector store"""
import chromadb
from pathlib import Path

def cleanup():
    print("=" * 60)
    print("Cleaning up cache pollution from vector store")
    print("=" * 60)
    
    client = chromadb.PersistentClient(path='./chroma_langchain_db')
    collection = client.get_collection('pdf_documents')
    
    # Get all documents
    all_docs = collection.get()
    
    if not all_docs['ids']:
        print("No documents found in collection")
        return
    
    # Identify cache entries
    cache_ids = []
    pdf_ids = []
    
    for i, (doc_id, metadata) in enumerate(zip(all_docs['ids'], all_docs['metadatas'])):
        if metadata and metadata.get('cache_type') == 'semantic':
            cache_ids.append(doc_id)
        else:
            pdf_ids.append(doc_id)
    
    print(f"\n📊 Found:")
    print(f"   Total documents: {len(all_docs['ids'])}")
    print(f"   Cache entries: {len(cache_ids)}")
    print(f"   PDF documents: {len(pdf_ids)}")
    
    if cache_ids:
        # Delete cache entries
        collection.delete(ids=cache_ids)
        print(f"\n✅ Deleted {len(cache_ids)} cache entries")
        
        # Verify cleanup
        remaining = collection.count()
        print(f"📊 Remaining documents: {remaining}")
    else:
        print("\n✅ No cache entries found - already clean!")
    
    # Show sample of remaining documents
    if pdf_ids:
        sample = collection.get(ids=pdf_ids[:2])
        print("\n📄 Sample remaining document:")
        if sample['documents']:
            print(f"   Content preview: {sample['documents'][0][:150]}...")
        if sample['metadatas']:
            print(f"   Metadata: {sample['metadatas'][0]}")

if __name__ == "__main__":
    cleanup()
