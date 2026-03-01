"""
Automated document detection and ingestion pipeline
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio

from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)

class DocumentIngestionPipeline:
    """Handles automated document ingestion with metadata tagging"""
    
    def __init__(self, vector_store, embeddings, config: Dict):
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.config = config
        self.processed_files = set()
        self.load_state()
        
        # Text splitter for semantic chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.get('chunk_size', 1000),
            chunk_overlap=config.get('chunk_overlap', 150),
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_state(self):
        """Load previously processed files state"""
        state_file = Path("./ingestion_state.json")
        if state_file.exists():
            with open(state_file, 'r') as f:
                data = json.load(f)
                self.processed_files = set(data.get('processed_files', []))
    
    def save_state(self):
        """Save processed files state"""
        state_file = Path("./ingestion_state.json")
        with open(state_file, 'w') as f:
            json.dump({
                'processed_files': list(self.processed_files),
                'last_updated': datetime.now().isoformat()
            }, f)
    
    def generate_document_id(self, source: str, content_hash: str) -> str:
        """Generate unique document ID"""
        return hashlib.md5(f"{source}:{content_hash}".encode()).hexdigest()
    
    def create_metadata(self, source: str, namespace: str, filename: str, 
                       chunk_index: int, total_chunks: int) -> Dict:
        """Create strict metadata tags for each chunk"""
        return {
            "source": source,
            "namespace": namespace,
            "filename": filename,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "ingested_at": datetime.now().isoformat(),
            "source_type": "pdf" if filename.endswith('.pdf') else "web",
            "document_id": self.generate_document_id(source, filename)
        }
    
    async def ingest_pdf(self, file_path: Path, namespace: str = "local_pdfs"):
        """Ingest a single PDF file"""
        logger.info(f"Ingesting PDF: {file_path}")
        
        # Load PDF
        loader = PyPDFLoader(str(file_path))
        documents = loader.load()
        
        # Create content hash for deduplication
        content_hash = hashlib.md5(
            "".join([doc.page_content for doc in documents]).encode()
        ).hexdigest()
        
        doc_id = self.generate_document_id(str(file_path), content_hash)
        
        # Check if already processed
        if doc_id in self.processed_files:
            logger.info(f"Skipping already processed file: {file_path}")
            return None
        
        # Semantic chunking
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Split into {len(chunks)} chunks")
        
        # Add metadata to each chunk
        for idx, chunk in enumerate(chunks):
            chunk.metadata.update(
                self.create_metadata(
                    source=str(file_path),
                    namespace=namespace,
                    filename=file_path.name,
                    chunk_index=idx,
                    total_chunks=len(chunks)
                )
            )
        
        # Add to vector store
        await asyncio.to_thread(
            self.vector_store.add_documents, chunks
        )
        
        # Mark as processed
        self.processed_files.add(doc_id)
        self.save_state()
        
        logger.info(f"✅ Successfully ingested {file_path.name} ({len(chunks)} chunks)")
        
        # Fire ingestion alert for cache invalidation
        await self.fire_ingestion_alert(namespace)
        
        return {"document_id": doc_id, "chunks": len(chunks)}
    
    async def ingest_website(self, url: str, namespace: str, 
                            max_pages: int = 10):
        """Ingest website content"""
        logger.info(f"Ingesting website: {url}")
        
        from langchain_community.document_loaders import WebBaseLoader
        
        loader = WebBaseLoader(url)
        documents = loader.load()
        
        # Limit pages if needed
        if len(documents) > max_pages:
            documents = documents[:max_pages]
        
        # Chunk documents
        chunks = self.text_splitter.split_documents(documents)
        
        # Add metadata
        for idx, chunk in enumerate(chunks):
            chunk.metadata.update(
                self.create_metadata(
                    source=url,
                    namespace=namespace,
                    filename=url.replace('/', '_'),
                    chunk_index=idx,
                    total_chunks=len(chunks)
                )
            )
        
        # Add to vector store
        await asyncio.to_thread(
            self.vector_store.add_documents, chunks
        )
        
        logger.info(f"✅ Successfully ingested website {url} ({len(chunks)} chunks)")
        
        # Fire ingestion alert
        await self.fire_ingestion_alert(namespace)
        
        return {"url": url, "chunks": len(chunks)}
    
    async def fire_ingestion_alert(self, namespace: str):
        """Signal that new data has been ingested (for cache invalidation)"""
        # This will be used by Phase 5 cache invalidation
        alert_file = Path("./ingestion_alerts.json")
        
        alerts = []
        if alert_file.exists():
            with open(alert_file, 'r') as f:
                alerts = json.load(f)
        
        alerts.append({
            "namespace": namespace,
            "timestamp": datetime.now().isoformat(),
            "action": "invalidate_cache"
        })
        
        # Keep last 100 alerts
        alerts = alerts[-100:]
        
        with open(alert_file, 'w') as f:
            json.dump(alerts, f, indent=2)
        
        logger.info(f"📡 Ingestion alert fired for namespace: {namespace}")


class DocumentWatcher(FileSystemEventHandler):
    """Watches folders for new documents and triggers ingestion"""
    
    def __init__(self, ingestion_pipeline: DocumentIngestionPipeline):
        self.ingestion_pipeline = ingestion_pipeline
        self.supported_extensions = {'.pdf', '.txt', '.md'}
    
    def on_created(self, event):
        """Handle new file creation"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in self.supported_extensions:
                logger.info(f"📄 New document detected: {file_path}")
                asyncio.run(
                    self.ingestion_pipeline.ingest_pdf(file_path)
                )
    
    def on_modified(self, event):
        """Handle file modifications"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in self.supported_extensions:
                logger.info(f"📝 Document modified: {file_path}")
                asyncio.run(
                    self.ingestion_pipeline.ingest_pdf(file_path)
                )


async def start_watcher(watch_path: str, ingestion_pipeline: DocumentIngestionPipeline):
    """Start the file system watcher"""
    event_handler = DocumentWatcher(ingestion_pipeline)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=False)
    observer.start()
    logger.info(f"👀 Watching directory: {watch_path}")
    return observer
