import os
import json
import sys
from pathlib import Path

import chromadb

def export_chroma_to_json():
    print("Exporting ChromaDB to JSON...")
    
    # Initialize ChromaDB client
    persist_dir = str(Path(__file__).parent.parent / "data" / "chroma_langchain_db")
    client = chromadb.PersistentClient(path=persist_dir)
    
    # Get collection
    collection_name = "pdf_documents"
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        print(f"Error getting collection: {e}")
        return
        
    # Get all data (including embeddings)
    result = collection.get(include=['embeddings', 'documents', 'metadatas'])
    
    if not result or not result['ids']:
        print("No data found in collection.")
        return
        
    print(f"Found {len(result['ids'])} chunks.")
    
    # Format into a clean list
    export_data = []
    for i in range(len(result['ids'])):
        emb = result['embeddings'][i]
        if hasattr(emb, 'tolist'):
            emb = emb.tolist()
        elif not isinstance(emb, list):
            emb = list(emb)
            
        export_data.append({
            'id': result['ids'][i],
            'document': result['documents'][i],
            'metadata': result['metadatas'][i],
            'embedding': emb
        })
        
    # Save to frontend/public/embeddings.json
    frontend_public = Path(__file__).parent.parent.parent / "frontend" / "public"
    frontend_public.mkdir(parents=True, exist_ok=True)
    
    out_file = frontend_public / "embeddings.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f)
        
    print(f"Exported to {out_file} ({out_file.stat().st_size / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    export_chroma_to_json()
