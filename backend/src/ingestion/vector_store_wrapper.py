"""
Wrapper for Chroma vector store - Checks existing chunks
"""
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)

class VectorStoreWrapper:
    """Wrapper for Chroma vector store with existing chunk detection"""
    
    def __init__(
        self,
        embeddings,
        persist_directory: str = "./chroma_langchain_db",
        embedding_config: Optional[Dict[str, Any]] = None,
        source_documents_dir: Optional[str] = None,
    ):
        self.embeddings = embeddings
        self.embedding_config = embedding_config or {}
        self.persist_directory = str(
            Path(persist_directory).expanduser()
            if Path(persist_directory).is_absolute()
            else (Path(__file__).resolve().parents[2] / persist_directory).resolve()
        )
        self.source_documents_dir = Path(source_documents_dir).expanduser() if source_documents_dir else Path(__file__).resolve().parents[2]
        self.embedding_namespace = self._build_embedding_namespace()
        self.collection_name = f"pdf_documents__{self.embedding_namespace}"
        self.semantic_cache_collection_name = f"semantic_cache__{self.embedding_namespace}"
        self.vector_store = None
        self.existing_chunk_count = 0
        self._initialize()
        self._check_existing_chunks()
        self._bootstrap_if_empty()

    @staticmethod
    def _slugify(value: str, max_length: int = 48) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        if len(cleaned) <= max_length:
            return cleaned or "default"
        return cleaned[:max_length].strip("_") or "default"

    def _build_embedding_namespace(self) -> str:
        provider = self.embedding_config.get("provider")
        model = self.embedding_config.get("model")
        if not provider:
            provider = self._slugify(type(self.embeddings).__name__)
        if not model:
            model = getattr(self.embeddings, "model", None) or getattr(self.embeddings, "_default_model", None) or "default"
        return f"{self._slugify(str(provider))}__{self._slugify(str(model))}"
    
    def _initialize(self):
        """Initialize Chroma connection"""
        try:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            logger.info(
                "Connected to Chroma at %s using collection %s",
                self.persist_directory,
                self.collection_name,
            )
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

    def _bootstrap_if_empty(self):
        """Auto-index local PDFs into the provider/model-specific collection."""
        if self.existing_chunk_count > 0 or not self.vector_store:
            return

        pdf_files = sorted(self.source_documents_dir.rglob("*.pdf"))
        if not pdf_files:
            logger.info("No source PDFs found for bootstrap in %s", self.source_documents_dir)
            return

        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                length_function=len,
                separators=["\n\n", "\n", " ", ""],
            )

            chunks = []
            for pdf_path in pdf_files:
                loader = PyPDFLoader(str(pdf_path))
                documents = loader.load()
                file_chunks = splitter.split_documents(documents)
                for index, chunk in enumerate(file_chunks):
                    chunk.metadata.update({
                        "source": str(pdf_path),
                        "filename": pdf_path.name,
                        "chunk_index": index,
                        "total_chunks": len(file_chunks),
                        "embedding_namespace": self.embedding_namespace,
                    })
                chunks.extend(file_chunks)

            if not chunks:
                logger.info("Bootstrap skipped: no chunks were produced from source PDFs")
                return

            logger.info(
                "Bootstrapping %s with %s chunks from %s PDFs",
                self.collection_name,
                len(chunks),
                len(pdf_files),
            )
            self.vector_store.add_documents(chunks)
            self.existing_chunk_count = len(chunks)
        except Exception as exc:
            logger.warning("Automatic bootstrap for %s failed: %s", self.collection_name, exc)
    
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
    
    def similarity_search_with_score(self, query: str, k: int = 4, filter: Dict = None) -> List:
        """Search with relevance scores"""
        if not self.vector_store:
            return []
        
        try:
            if filter:
                results = self.vector_store.similarity_search_with_relevance_scores(
                    query,
                    k=k,
                    filter=filter,
                )
            else:
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
                    "has_data": count > 0,
                    "collection_name": self.collection_name,
                    "embedding_namespace": self.embedding_namespace,
                }
        except Exception as e:
            logger.error(f"Stats error: {e}")
        
        return {
            "available": False,
            "has_data": False,
            "collection_name": self.collection_name,
            "embedding_namespace": self.embedding_namespace,
        }
