"""
Wrapper for Chroma vector store - Checks existing chunks
"""
from langchain_chroma import Chroma
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class VectorStoreWrapper:
    """Wrapper for Chroma vector store with existing chunk detection"""
    
    def __init__(self, embeddings, persist_directory: str = "./chroma_langchain_db"):
        self.embeddings = embeddings
        self.persist_directory = persist_directory
        self.vector_store = None
        self.existing_chunk_count = 0
        self._initialize()
        self._check_existing_chunks()
    
    def _initialize(self):
        """Initialize Chroma connection"""
        try:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name="pdf_documents"
            )
            logger.info(f"Connected to Chroma at {self.persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise
    
    def _check_existing_chunks(self):
        """Check how many chunks already exist"""
        try:
            if hasattr(self.vector_store, '_collection'):
                self.existing_chunk_count = self.vector_store._collection.count()
                if self.existing_chunk_count > 0:
                    logger.info(f"✓ Found {self.existing_chunk_count} existing chunks in database")
                else:
                    logger.info("No existing chunks found - database is empty")
        except Exception as e:
            logger.warning(f"Could not check existing chunks: {e}")
            self.existing_chunk_count = 0
    
    def has_chunks(self) -> bool:
        """Check if there are any chunks in the DB"""
        return self.existing_chunk_count > 0
    
    def get_chunk_count(self) -> int:
        """Get number of chunks in DB"""
        return self.existing_chunk_count
    
    def similarity_search(self, query: str, k: int = 4, filter: Dict = None) -> List:
        """Search for similar documents"""
        if not self.vector_store:
            return []
        
        try:
            if filter:
                results = self.vector_store.similarity_search(query, k=k, filter=filter)
            else:
                results = self.vector_store.similarity_search(query, k=k)
            
            logger.debug(f"Search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def similarity_search_with_score(self, query: str, k: int = 4) -> List:
        """Search with relevance scores"""
        if not self.vector_store:
            return []
        
        try:
            results = self.vector_store.similarity_search_with_relevance_scores(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Search with scores failed: {e}")
            return []
    
    def add_documents(self, documents: List, **kwargs):
        """Add documents - only if needed"""
        if not documents:
            logger.warning("No documents to add")
            return
        
        if self.existing_chunk_count > 0:
            logger.warning(f"Database already has {self.existing_chunk_count} chunks!")
            logger.warning("Use force_reindex=True to override")
            return
        
        self.vector_store.add_documents(documents, **kwargs)
        self.existing_chunk_count += len(documents)
        logger.info(f"Added {len(documents)} documents (total: {self.existing_chunk_count})")
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        try:
            if self.vector_store and hasattr(self.vector_store, '_collection'):
                count = self.vector_store._collection.count()
                return {
                    "document_count": count, 
                    "available": True,
                    "has_data": count > 0
                }
        except Exception as e:
            logger.error(f"Stats error: {e}")
        
        return {"available": False, "has_data": False}
