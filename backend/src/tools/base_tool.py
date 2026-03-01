"""
Base interface for all tools/plugins
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized tool output"""
    content: str
    source: str
    confidence: float
    metadata: Dict[str, Any]


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, name: str, description: str, config: Dict = None):
        self.name = name
        self.description = description
        self.config = config or {}
        self.enabled = True
    
    @abstractmethod
    async def query(self, question: str) -> ToolResult:
        """Execute tool query"""
        pass
    
    @abstractmethod
    def can_handle(self, question: str) -> float:
        """Return confidence score (0-1) if tool can handle question"""
        pass
    
    def get_metadata(self) -> Dict:
        """Return tool metadata"""
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "type": self.__class__.__name__
        }


class WebsiteTool(BaseTool):
    """Tool for querying a specific website"""
    
    def __init__(self, name: str, namespace: str, vector_store, 
                 description: str = None, config: Dict = None):
        super().__init__(name, description or f"Query {name} website", config)
        self.namespace = namespace
        self.vector_store = vector_store
        self.keywords = config.get('keywords', []) if config else []
    
    async def query(self, question: str) -> ToolResult:
        """Search within this website's namespace"""
        try:
            # Use the vector store wrapper
            if hasattr(self.vector_store, 'similarity_search'):
                results = self.vector_store.similarity_search(question, k=3)
            else:
                results = []
            
            # Filter by namespace if metadata filtering is supported
            if results and hasattr(results[0], 'metadata'):
                filtered = []
                for doc in results:
                    source = doc.metadata.get('source', doc.metadata.get('source_url', ''))
                    if self.namespace.lower() in source.lower():
                        filtered.append(doc)
                results = filtered[:3]
            
            if results:
                content = "\n\n".join([doc.page_content for doc in results])
                logger.debug(f"Tool {self.name} found {len(results)} results")
                return ToolResult(
                    content=content,
                    source=self.name,
                    confidence=0.8,
                    metadata={
                        "namespace": self.namespace,
                        "num_results": len(results),
                        "sources": [doc.metadata.get('source', doc.metadata.get('source_url', 'local')) 
                                   for doc in results]
                    }
                )
            
            return ToolResult(
                content="",
                source=self.name,
                confidence=0.0,
                metadata={"error": "No relevant content found"}
            )
            
        except Exception as e:
            logger.error(f"Tool {self.name} query failed: {e}")
            return ToolResult(
                content="",
                source=self.name,
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def can_handle(self, question: str) -> float:
        """Check if question is relevant to this website"""
        question_lower = question.lower()
        
        # Check for keywords
        if self.keywords:
            matching = sum(1 for kw in self.keywords if kw in question_lower)
            score = matching / len(self.keywords) if self.keywords else 0
            return min(score, 1.0)
        
        # Default confidence - check for IIT Bhilai related terms
        iit_keywords = ['iit', 'bhilai', 'course', 'admission', 'campus', 'faculty', 'hostel']
        if any(kw in question_lower for kw in iit_keywords):
            return 0.6
        
        return 0.3
