#!/usr/bin/env python3
"""Optimized reindex with smaller chunks for better performance"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_chroma import Chroma
    
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not set")
        return
    
    print("=" * 60)
    print("Optimized Reindexing with Smaller Chunks")
    print("=" * 60)
    
    # Optimized chunk sizes to avoid rate limits
    # Gemini can handle ~100 chunks per minute, so smaller chunks = faster
    chunk_size = 500  # Reduced from 1000 to 500
    chunk_overlap = 50  # Reduced from 150 to 50
    
    print(f"📏 Chunk size: {chunk_size} chars")
    print(f"🔗 Overlap: {chunk_overlap} chars")
    print(f"🎨 Using Gemini embeddings (3072 dimensions)")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        google_api_key=api_key
    )
    
    # Find PDF
    pdf_path = Path("../backend/courses_study.pdf")
    if not pdf_path.exists():
        pdf_path = Path("backend/courses_study.pdf")
    if not pdf_path.exists():
        pdf_path = Path("courses_study.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found")
        return
    
    print(f"📄 Loading: {pdf_path.name}")
    loader = PyPDFLoader(str(pdf_path))
    docs = await asyncio.to_thread(loader.load)
    
    print(f"📝 Splitting into smaller chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    print(f"✅ Created {len(chunks)} chunks (was 470 before)")
    
    # Add metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata['source'] = pdf_path.name
        chunk.metadata['chunk_index'] = i
        chunk.metadata['chunk_size'] = chunk_size
    
    # Process in batches to avoid rate limits
    batch_size = 50
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    
    print(f"💾 Creating vector store in {total_batches} batches...")
    
    # Create empty vector store first
    db_path = Path("data/chroma_langchain_db")
    db_path.mkdir(parents=True, exist_ok=True)
    
    vector_store = Chroma(
        persist_directory=str(db_path),
        embedding_function=embeddings,
        collection_name="pdf_documents"
    )
    
    # Add in batches
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"  Batch {batch_num}/{total_batches}: Adding {len(batch)} chunks...")
        vector_store.add_documents(batch)
        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)
    
    print(f"✅ Success! Indexed {len(chunks)} chunks")
    
    # Test search
    test_queries = [
        "What BTech programs are offered?",
        "Tell me about Computer Science Engineering",
        "What are the prerequisites for courses?"
    ]
    
    print("\n🔍 Testing searches:")
    for query in test_queries:
        print(f"\n  Q: {query}")
        results = vector_store.similarity_search(query, k=2)
        for j, doc in enumerate(results):
            preview = doc.page_content[:80].replace('\n', ' ')
            print(f"    R{j+1}: {preview}...")
    
    print("\n" + "=" * 60)
    print("🎉 Reindexing complete!")
    print(f"📊 Statistics:")
    print(f"   Total chunks: {len(chunks)}")
    print(f"   Chunk size: {chunk_size}")
    print(f"   Batches: {total_batches}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
