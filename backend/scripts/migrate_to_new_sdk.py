#!/usr/bin/env python3
"""
Migrate to new Google GenAI SDK
Install: pip install google-genai
"""

import os
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Migrate to new SDK"""
    
    # Install new SDK
    os.system("pip install google-genai")
    
    # Use new SDK for embeddings
    from google import genai
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    api_key = os.getenv('GOOGLE_API_KEY')
    client = genai.Client(api_key=api_key)
    
    # Custom embedding class for new SDK
    class NewGeminiEmbeddings:
        def __init__(self, client):
            self.client = client
        
        def embed_documents(self, texts):
            embeddings = []
            for text in texts:
                result = self.client.models.embed_content(
                    model="gemini-embedding-2",  # or gemini-embedding-001
                    contents=text
                )
                embeddings.append(result.embeddings[0].values)
            return embeddings
        
        def embed_query(self, text):
            result = self.client.models.embed_content(
                model="gemini-embedding-2",
                contents=text
            )
            return result.embeddings[0].values
    
    # Backup existing DB
    db_path = Path("./chroma_langchain_db")
    if db_path.exists():
        backup = Path("./chroma_langchain_db_backup")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(db_path, backup)
        logger.info("Backed up existing DB")
        shutil.rmtree(db_path)
    
    # Load documents
    pdf_files = Path("./backend").glob("*.pdf")
    all_docs = []
    for pdf in pdf_files:
        loader = PyPDFLoader(str(pdf))
        all_docs.extend(loader.load())
    
    # Split
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=80)
    chunks = splitter.split_documents(all_docs)
    logger.info(f"Created {len(chunks)} chunks")
    
    # Create new vector store
    embeddings = NewGeminiEmbeddings(client)
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./chroma_langchain_db",
        collection_name="pdf_documents"
    )
    
    logger.info("✅ Migration complete with new SDK!")
    logger.info("Using gemini-embedding-2 (768 dimensions)")

if __name__ == "__main__":
    migrate()
