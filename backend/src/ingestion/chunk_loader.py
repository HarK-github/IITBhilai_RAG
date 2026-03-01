"""
Load existing chunks from Chroma DB without re-chunking
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ChunkLoader:
    """
    Load existing chunks from Chroma DB
    Prevents re-chunking by checking what's already stored
    """
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.chunk_stats = {}
        self.load_chunk_info()
    
    def load_chunk_info(self):
        """Load information about existing chunks from vector store"""
        try:
            if hasattr(self.vector_store, '_collection'):
                collection = self.vector_store._collection
                count = collection.count()
                
                # Get some sample metadata to understand structure
                if count > 0:
                    sample = collection.get(limit=5)
                    if sample and sample['metadatas']:
                        # Extract unique sources
                        sources = set()
                        for meta in sample['metadatas']:
                            if 'source' in meta:
                                sources.add(meta['source'])
                            if 'filename' in meta:
                                sources.add(meta['filename'])
                            if 'namespace' in meta:
                                sources.add(meta['namespace'])
                        
                        self.chunk_stats = {
                            'total_chunks': count,
                            'unique_sources': list(sources),
                            'sample_metadata': sample['metadatas'][0] if sample['metadatas'] else {}
                        }
                        
                        logger.info(f"Found {count} existing chunks from {len(sources)} sources")
                    else:
                        logger.warning("No metadata found in existing chunks")
                else:
                    logger.info("No existing chunks found in vector store")
                    
        except Exception as e:
            logger.error(f"Failed to load chunk info: {e}")
            self.chunk_stats = {'total_chunks': 0, 'error': str(e)}
    
    def has_existing_chunks(self) -> bool:
        """Check if there are already chunks in the DB"""
        return self.chunk_stats.get('total_chunks', 0) > 0
    
    def get_chunk_count(self) -> int:
        """Get number of existing chunks"""
        return self.chunk_stats.get('total_chunks', 0)
    
    def get_sources(self) -> List[str]:
        """Get list of unique sources in the DB"""
        return self.chunk_stats.get('unique_sources', [])
    
    def get_stats(self) -> Dict:
        """Get chunk statistics"""
        return self.chunk_stats
    
    def get_chunks_by_source(self, source_name: str, limit: int = 10) -> List:
        """Retrieve chunks from a specific source"""
        try:
            results = self.vector_store.similarity_search(
                "",  # Empty query to get random chunks
                k=limit,
                filter={"source": source_name} if source_name else None
            )
            return results
        except Exception as e:
            logger.error(f"Failed to get chunks from {source_name}: {e}")
            return []
    
    def verify_chunk_integrity(self) -> Dict:
        """Verify that chunks are properly stored and accessible"""
        results = {
            'total_chunks': self.chunk_stats.get('total_chunks', 0),
            'accessible': False,
            'sample_chunk': None
        }
        
        try:
            # Try to retrieve a chunk
            test_query = "courses"
            retrieved = self.vector_store.similarity_search(test_query, k=1)
            
            if retrieved:
                results['accessible'] = True
                results['sample_chunk'] = {
                    'content_preview': retrieved[0].page_content[:200],
                    'metadata': retrieved[0].metadata
                }
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
