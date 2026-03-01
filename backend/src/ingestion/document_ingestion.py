"""
Document ingestion with chunking registry check
"""
import logging
from pathlib import Path
from typing import Dict, Optional
import asyncio

from .chunking_registry import ChunkingRegistry, ChunkingStatus
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class SmartDocumentIngestion:
    """Document ingestion that checks registry before chunking"""
    
    def __init__(self, vector_store, embeddings, config: Dict = None):
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.config = config or {}
        
        # Initialize chunking registry
        self.registry = ChunkingRegistry()
        
        # Chunking configuration
        self.chunk_size = config.get('chunk_size', 1000)
        self.chunk_overlap = config.get('chunk_overlap', 150)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def get_chunk_config(self) -> Dict:
        """Get current chunking configuration"""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
    
    async def ingest_pdf(self, file_path: Path, namespace: str = "local_pdfs", 
                        force_rechunk: bool = False) -> Optional[Dict]:
        """
        Ingest PDF with registry check to avoid duplicate chunking
        
        Args:
            file_path: Path to PDF file
            namespace: Namespace for metadata
            force_rechunk: Force re-chunking even if already chunked
        
        Returns:
            Dict with ingestion results or None if skipped
        """
        logger.info(f"Checking PDF: {file_path}")
        
        # Check if already chunked
        chunk_config = self.get_chunk_config()
        
        if not force_rechunk and self.registry.is_chunked(str(file_path), chunk_config):
            info = self.registry.get_chunks_info(str(file_path), chunk_config)
            logger.info(f"✓ PDF already chunked: {file_path.name} ({info['num_chunks']} chunks)")
            return {
                "status": "skipped",
                "reason": "already_chunked",
                "info": info
            }
        
        # Perform chunking
        logger.info(f"🔄 Chunking PDF: {file_path.name}")
        
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(str(file_path))
        documents = loader.load()
        
        # Semantic chunking
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"✓ Created {len(chunks)} chunks (size={self.chunk_size}, overlap={self.chunk_overlap})")
        
        # Register chunking
        self.registry.register_chunking(
            document_path=str(file_path),
            chunk_config=chunk_config,
            num_chunks=len(chunks),
            metadata={"namespace": namespace, "filename": file_path.name}
        )
        
        self.registry.update_status(str(file_path), chunk_config, ChunkingStatus.CHUNKED)
        
        # Add metadata to chunks
        for idx, chunk in enumerate(chunks):
            chunk.metadata.update({
                "source": str(file_path),
                "namespace": namespace,
                "filename": file_path.name,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap
            })
        
        # Add to vector store
        await asyncio.to_thread(self.vector_store.add_documents, chunks)
        self.registry.update_status(str(file_path), chunk_config, ChunkingStatus.INDEXED)
        
        logger.info(f"✅ Successfully ingested {file_path.name} ({len(chunks)} chunks)")
        
        return {
            "status": "success",
            "filename": file_path.name,
            "chunks": len(chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
    
    async def ingest_directory(self, directory: Path, namespace: str = "local_pdfs",
                              force_rechunk: bool = False) -> Dict:
        """Ingest all PDFs in a directory"""
        results = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }
        
        pdf_files = list(directory.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        
        for pdf_path in pdf_files:
            try:
                result = await self.ingest_pdf(pdf_path, namespace, force_rechunk)
                results["total"] += 1
                
                if result["status"] == "success":
                    results["success"] += 1
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                
                results["details"].append(result)
                
            except Exception as e:
                logger.error(f"Failed to ingest {pdf_path}: {e}")
                results["failed"] += 1
                results["details"].append({"status": "failed", "filename": pdf_path.name, "error": str(e)})
        
        return results
    
    def get_registry_stats(self) -> Dict:
        """Get statistics from chunking registry"""
        return self.registry.get_statistics()
    
    def list_chunked_documents(self) -> list:
        """List all chunked documents"""
        return self.registry.get_all_chunked_documents()