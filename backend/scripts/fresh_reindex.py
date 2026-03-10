#!/usr/bin/env python3
"""Fresh reindex with Gemini embeddings only"""
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
    
    print("✅ Using Gemini embeddings (3072 dimensions)")
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
    
    print(f"📄 Loading: {pdf_path}")
    loader = PyPDFLoader(str(pdf_path))
    docs = await asyncio.to_thread(loader.load)
    
    print(f"📝 Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
    chunks = splitter.split_documents(docs)
    print(f"✅ Created {len(chunks)} chunks")
    
    # Add metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata['source'] = str(pdf_path.name)
        chunk.metadata['chunk_index'] = i
    
    print(f"💾 Creating vector store...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="data/chroma_langchain_db",
        collection_name="pdf_documents"
    )
    
    # Verify
    print(f"✅ Success! Indexed {len(chunks)} chunks")
    
    # Test search
    test_query = "What BTech programs are offered?"
    print(f"\n🔍 Testing search: '{test_query}'")
    results = vector_store.similarity_search(test_query, k=2)
    for i, doc in enumerate(results):
        print(f"  Result {i+1}: {doc.page_content[:100]}...")
    
    print("\n🎉 Reindexing complete!")

if __name__ == "__main__":
    asyncio.run(main())
