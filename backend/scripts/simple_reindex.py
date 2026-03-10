#!/usr/bin/env python3
"""Simple reindexing without complex factory"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import shutil
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
import os

# Set API key
os.environ['GOOGLE_API_KEY'] = 'AIzaSyC9IKGxPvxXNJwLvZahqPw5RfUr-m9XpUI'

def main():
    print("Starting simple reindexing...")
    
    # Remove old DB
    db_path = Path("./chroma_langchain_db")
    if db_path.exists():
        print("Removing old database...")
        shutil.rmtree(db_path)
    
    # Initialize embeddings
    print("Initializing Gemini embeddings...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="text-embedding-004",
        google_api_key=os.environ['GOOGLE_API_KEY']
    )
    
    # Load PDFs
    pdf_folder = Path("./backend")
    pdf_files = list(pdf_folder.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    all_docs = []
    for pdf_path in pdf_files:
        print(f"Loading {pdf_path.name}...")
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        all_docs.extend(docs)
    
    # Split
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"Created {len(chunks)} chunks")
    
    # Create vector store
    print("Creating vector store with Gemini embeddings...")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_langchain_db",
        collection_name="pdf_documents"
    )
    
    print(f"✅ Success! Indexed {len(chunks)} documents")
    print(f"Vector store size: {vector_store._collection.count()} documents")

if __name__ == "__main__":
    main()
