#!/usr/bin/env python3
"""Fixed reindex with batching to avoid RESOURCE_EXHAUSTED rate limits"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import os
import shutil
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
    print("Fixed Reindexing with Rate-Limit Prevention")
    print("=" * 60)
    
    chunk_size = 500
    chunk_overlap = 50
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=api_key
    )
    
    # Find PDF
    pdf_path = Path("courses_study.pdf")
    if not pdf_path.exists():
        pdf_path = Path("backend/courses_study.pdf")
    if not pdf_path.exists():
        pdf_path = Path("../backend/courses_study.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found")
        return
    
    print(f"📄 Loading: {pdf_path.name}")
    loader = PyPDFLoader(str(pdf_path))
    docs = await asyncio.to_thread(loader.load)
    
    print(f"📝 Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    
    valid_chunks = []
    for i, chunk in enumerate(chunks):
        if chunk.page_content:
            cleaned_content = chunk.page_content.strip().replace("\r", "").replace("\x00", "")
            if len(cleaned_content) > 15:
                chunk.page_content = cleaned_content
                chunk.metadata = chunk.metadata or {}
                chunk.metadata['source'] = pdf_path.name
                chunk.metadata['chunk_index'] = i
                chunk.metadata['chunk_size'] = chunk_size
                valid_chunks.append(chunk)
    
    print(f"✅ Created {len(valid_chunks)} valid chunks")
    
    if not valid_chunks:
        print("❌ No valid chunks created")
        return
    
    db_path = Path("data/chroma_langchain_db")
    if db_path.exists():
        print(f"🗑️ Removing existing DB...")
        try:
            shutil.rmtree(db_path)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"⚠️ Warning during file deletion: {e}")
    
    db_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize an empty Chroma vector store with the first chunk to lock schema
    print(f"💾 Initializing vector store schema...")
    vector_store = await asyncio.to_thread(
        Chroma,
        embedding_function=embeddings,
        persist_directory=str(db_path),
        collection_name="pdf_documents"
    )
    
    # Batch parameters tuned safely for Google AI Studio Free Quotas
    BATCH_SIZE = 15 
    DELAY_SECONDS = 3.0
    
    total_chunks = len(valid_chunks)
    print(f"🚀 Uploading {total_chunks} chunks in batches of {BATCH_SIZE} (with {DELAY_SECONDS}s cooldown)...")
    
    for idx in range(0, total_chunks, BATCH_SIZE):
        batch = valid_chunks[idx : idx + BATCH_SIZE]
        current_batch_num = (idx // BATCH_SIZE) + 1
        total_batches = (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE
        
        try:
            # Send batch sequentially to avoid out-of-order execution issues
            await asyncio.to_thread(vector_store.add_documents, batch)
            print(f"  Processed batch {current_batch_num}/{total_batches} ({len(batch)} chunks)")
        except Exception as batch_error:
            print(f"  ⚠️ Batch {current_batch_num} rate-limit hit. Retrying single-chunk fallback...")
            # If the batch fails, process each item slowly one by one to ensure completion
            for single_doc in batch:
                try:
                    await asyncio.to_thread(vector_store.add_documents, [single_doc])
                    await asyncio.sleep(1.0)
                except Exception as single_error:
                    print(f"    ❌ Skipped broken chunk: {single_error}")
                    
        # Apply cooldown delay between chunks to let the API window reset
        await asyncio.sleep(DELAY_SECONDS)
    
    final_count = vector_store._collection.count()
    print(f"\n✅ Success! Indexed {final_count} chunks")
    
    # Test search validation
    print("\n🔍 Testing searches:")
    try:
        results = vector_store.similarity_search("Computer Science Engineering", k=2)
        for j, doc in enumerate(results):
            print(f"    R{j+1}: {doc.page_content[:80]}...")
    except Exception as e:
        print(f"    Search failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
