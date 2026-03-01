"""
Chunking Registry - Tracks what has been chunked and how
Prevents redundant chunking operations
"""
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ChunkingStatus(Enum):
    PENDING = "pending"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    FAILED = "failed"

@dataclass
class ChunkingRecord:
    """Record of a chunking operation"""
    document_id: str
    source_path: str
    source_type: str  # 'pdf', 'website', 'text'
    chunk_size: int
    chunk_overlap: int
    num_chunks: int
    content_hash: str
    status: ChunkingStatus
    created_at: str
    updated_at: str
    metadata: Dict

class ChunkingRegistry:
    """
    Persistent registry to track chunking operations
    Prevents duplicate chunking of same documents
    """
    
    def __init__(self, registry_path: str = "./chunking_registry.json"):
        self.registry_path = Path(registry_path)
        self.records: Dict[str, ChunkingRecord] = {}
        self.load()
    
    def load(self):
        """Load existing registry from disk"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    for doc_id, record_data in data.items():
                        # Convert status string back to enum
                        record_data['status'] = ChunkingStatus(record_data['status'])
                        self.records[doc_id] = ChunkingRecord(**record_data)
                logger.info(f"Loaded {len(self.records)} chunking records")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.records = {}
        else:
            logger.info("No existing chunking registry found, creating new one")
    
    def save(self):
        """Save registry to disk"""
        try:
            data = {}
            for doc_id, record in self.records.items():
                record_dict = asdict(record)
                record_dict['status'] = record.status.value
                data[doc_id] = record_dict
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.records)} records to registry")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def generate_document_id(self, source_path: str, chunk_config: Dict) -> str:
        """Generate unique ID for a document based on path and chunking config"""
        content = f"{source_path}:{chunk_config.get('chunk_size')}:{chunk_config.get('chunk_overlap')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def compute_content_hash(self, file_path: Path) -> str:
        """Compute hash of file content to detect changes"""
        if not file_path.exists():
            return ""
        
        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.md5(content).hexdigest()
    
    def is_chunked(self, document_path: str, chunk_config: Dict) -> bool:
        """Check if document has already been chunked with given config"""
        doc_id = self.generate_document_id(document_path, chunk_config)
        
        if doc_id not in self.records:
            return False
        
        record = self.records[doc_id]
        
        # Check if content has changed
        if document_path.startswith("http"):
            # For websites, we can't easily check content hash
            # Assume unchanged unless force refresh
            pass
        else:
            current_hash = self.compute_content_hash(Path(document_path))
            if current_hash != record.content_hash:
                logger.info(f"Content changed for {document_path}, needs re-chunking")
                return False
        
        # Check if chunking was successful
        if record.status in [ChunkingStatus.CHUNKED, ChunkingStatus.EMBEDDED, ChunkingStatus.INDEXED]:
            logger.info(f"Document already chunked: {document_path} ({record.num_chunks} chunks)")
            return True
        
        return False
    
    def get_chunks_info(self, document_path: str, chunk_config: Dict) -> Optional[Dict]:
        """Get information about existing chunks"""
        doc_id = self.generate_document_id(document_path, chunk_config)
        
        if doc_id in self.records:
            record = self.records[doc_id]
            return {
                "document_id": record.document_id,
                "num_chunks": record.num_chunks,
                "chunk_size": record.chunk_size,
                "chunk_overlap": record.chunk_overlap,
                "status": record.status.value,
                "created_at": record.created_at
            }
        
        return None
    
    def register_chunking(self, document_path: str, chunk_config: Dict, 
                         num_chunks: int, metadata: Dict = None):
        """Register that a document has been chunked"""
        doc_id = self.generate_document_id(document_path, chunk_config)
        
        # Compute content hash for local files
        content_hash = ""
        if not document_path.startswith("http"):
            content_hash = self.compute_content_hash(Path(document_path))
        
        record = ChunkingRecord(
            document_id=doc_id,
            source_path=document_path,
            source_type="pdf" if document_path.endswith('.pdf') else "website",
            chunk_size=chunk_config.get('chunk_size', 1000),
            chunk_overlap=chunk_config.get('chunk_overlap', 150),
            num_chunks=num_chunks,
            content_hash=content_hash,
            status=ChunkingStatus.CHUNKED,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        self.records[doc_id] = record
        self.save()
        logger.info(f"Registered chunking for {document_path}: {num_chunks} chunks")
    
    def update_status(self, document_path: str, chunk_config: Dict, 
                     status: ChunkingStatus):
        """Update status of chunking operation"""
        doc_id = self.generate_document_id(document_path, chunk_config)
        
        if doc_id in self.records:
            self.records[doc_id].status = status
            self.records[doc_id].updated_at = datetime.now().isoformat()
            self.save()
            logger.debug(f"Updated status for {document_path}: {status.value}")
    
    def get_all_chunked_documents(self) -> List[Dict]:
        """Get list of all chunked documents"""
        return [
            {
                "source_path": record.source_path,
                "num_chunks": record.num_chunks,
                "chunk_size": record.chunk_size,
                "status": record.status.value,
                "created_at": record.created_at
            }
            for record in self.records.values()
        ]
    
    def cleanup_old_records(self, days_old: int = 30):
        """Remove records older than specified days"""
        cutoff = datetime.now().timestamp() - (days_old * 86400)
        to_delete = []
        
        for doc_id, record in self.records.items():
            created_ts = datetime.fromisoformat(record.created_at).timestamp()
            if created_ts < cutoff:
                to_delete.append(doc_id)
        
        for doc_id in to_delete:
            del self.records[doc_id]
        
        if to_delete:
            self.save()
            logger.info(f"Cleaned up {len(to_delete)} old records")
    
    def get_statistics(self) -> Dict:
        """Get registry statistics"""
        total_docs = len(self.records)
        total_chunks = sum(r.num_chunks for r in self.records.values())
        
        by_status = {}
        for record in self.records.values():
            status = record.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "average_chunks_per_doc": total_chunks / total_docs if total_docs > 0 else 0,
            "by_status": by_status,
            "registry_path": str(self.registry_path)
        }
