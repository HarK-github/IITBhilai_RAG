#!/usr/bin/env python3
"""
Re-index documents with Gemini embeddings
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import shutil
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def backup_existing_db():
    """Backup existing Chroma DB"""
    db_path = Path("./chroma_langchain_db")
    backup_path = Path("./chroma_langchain_db_backup_ollama")
    
    if db_path.exists():
        logger.info(f"Backing up {db_path} to {backup_path}")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(db_path, backup_path)
        logger.info("Backup complete")
        return True
    return False

def recreate_vector_store():
    """Recreate vector store with Gemini embeddings"""
    from src.ingestion.vector_store_wrapper import VectorStoreWrapper
    from src.core.llm_factory import EmbeddingFactory
    from src.core.config_loader import config
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    # Get embedding config
    embedding_config = config.get_embedding_config()
    logger.info(f"Using embeddings: {embedding_config}")
    
    # Initialize embeddings
    embeddings = EmbeddingFactory.create_embeddings(embedding_config)
    
    # Remove existing DB to avoid dimension mismatch
    db_path = Path("./chroma_langchain_db")
    if db_path.exists():
        logger.info("Removing existing DB to recreate with correct dimensions")
        shutil.rmtree(db_path)
    
    # Initialize new vector store
    vector_store_wrapper = VectorStoreWrapper(embeddings)
    
    # Load and index PDF documents
    pdf_folder = Path("./backend")
    pdf_files = list(pdf_folder.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning("No PDF files found in ./backend")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    all_docs = []
    for pdf_path in pdf_files:
        logger.info(f"Loading {pdf_path.name}")
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        all_docs.extend(docs)
    
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len
    )
    
    chunks = text_splitter.split_documents(all_docs)
    logger.info(f"Created {len(chunks)} chunks")
    
    # Add to vector store
    if chunks:
        vector_store_wrapper.add_documents(chunks)
        logger.info(f"Successfully indexed {len(chunks)} chunks")
        
        # Verify
        stats = vector_store_wrapper.get_collection_stats()
        logger.info(f"Vector store stats: {stats}")
    else:
        logger.error("No chunks created")

def main():
    """Main reindexing function"""
    logger.info("Starting document reindexing...")
    
    # Backup existing DB
    backup_existing_db()
    
    # Recreate with new embeddings
    try:
        recreate_vector_store()
        logger.info("✅ Reindexing complete!")
    except Exception as e:
        logger.error(f"❌ Reindexing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
