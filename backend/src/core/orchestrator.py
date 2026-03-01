"""
Main agent orchestrator - supports multiple LLM providers
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate  # Add this import

from src.caching import CacheManager
from src.tools import ToolRegistry, ToolResult
from src.ingestion import VectorStoreWrapper
from src.core.config_loader import config
from src.core.llm_factory import LLMFactory, EmbeddingFactory

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Main orchestrator for the RAG agent"""
    
    def __init__(self):
        self.cache_manager = None
        self.tool_registry = None
        self.vector_store_wrapper = None
        self.llm = None
        self.embeddings = None
        
        self.setup_logging()
        self.setup_components()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = config.get('agent.logging.level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def setup_components(self):
        """Initialize all components"""
        # Initialize LLM
        try:
            llm_config = config.get_llm_config()
            self.llm = LLMFactory.create_llm(llm_config)
            logger.info(f"LLM initialized: {llm_config['provider']}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
        
        # Initialize embeddings
        try:
            embedding_config = config.get_embedding_config()
            self.embeddings = EmbeddingFactory.create_embeddings(embedding_config)
            logger.info(f"Embeddings initialized: {embedding_config['provider']} with model {embedding_config.get('model', 'default')}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            self.embeddings = None
        
        # Initialize vector store
        try:
            self.vector_store_wrapper = VectorStoreWrapper(self.embeddings)
            stats = self.vector_store_wrapper.get_collection_stats()
            logger.info(f"Vector store connected: {stats}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            self.vector_store_wrapper = None
        
        # Setup cache
        cache_enabled = config.get('caching.enabled', False)
        if cache_enabled and self.vector_store_wrapper:
            self.cache_manager = CacheManager(
                config=config.get('caching', {}),
                vector_store=self.vector_store_wrapper,
                embedding_model=self.embeddings
            )
        
        # Setup tool registry
        self.tool_registry = ToolRegistry("config/websites.yaml")
        
        # Set vector store in registry
        if self.vector_store_wrapper:
            self.tool_registry.set_vector_store(self.vector_store_wrapper)
            self.tool_registry.register_all_websites()
            logger.info(f"Registered {len(self.tool_registry.tools)} tools")
        else:
            logger.warning("No vector store available - tools not registered")
    
    async def query(self, question: str, use_cache: bool = True) -> Dict[str, Any]:
        """Process a user query"""
        start_time = datetime.now()
        
        # Check cache
        if use_cache and self.cache_manager:
            cached_answer = await self.cache_manager.get(question)
            if cached_answer:
                return {
                    "answer": cached_answer,
                    "from_cache": True,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "tools_used": []
                }
        
        # Get relevant tools
        relevant_tools = self.tool_registry.get_relevant_tools(question, top_k=3)
        logger.info(f"Selected {len(relevant_tools)} tools")
        
        # Query tools
        tool_results = []
        for tool in relevant_tools:
            try:
                result = await tool.query(question)
                if result.content:
                    tool_results.append(result)
                    logger.debug(f"Tool {tool.name} returned {len(result.content)} chars")
            except Exception as e:
                logger.error(f"Tool {tool.name} failed: {e}")
        
        # Fallback to direct search
        if not tool_results and self.vector_store_wrapper:
            fallback = await self._direct_search(question)
            if fallback:
                tool_results.append(fallback)
                logger.info("Fallback direct search provided results")
        
        # Generate answer
        context = self._combine_results(tool_results)
        answer = await self._generate_answer(question, context)
        
        # Prepare result
        result = {
            "answer": answer,
            "from_cache": False,
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "tools_used": [t.source for t in tool_results],
            "num_sources": len(tool_results)
        }
        
        # Cache successful responses (not error messages)
        if use_cache and self.cache_manager and answer and "cannot find" not in answer.lower():
            await self.cache_manager.set(question, answer, {
                "tools_used": [t.source for t in tool_results],
                "timestamp": datetime.now().isoformat()
            })
        
        return result
    async def _direct_search(self, question: str) -> Optional[ToolResult]:
        """Direct vector search fallback"""
        if not self.vector_store_wrapper:
            return None
        
        try:
            results = self.vector_store_wrapper.similarity_search(question, k=3)
            if results:
                content = "\n\n".join([doc.page_content for doc in results])
                logger.info(f"Direct search found {len(results)} results")
                return ToolResult(
                    content=content,
                    source="vector_store",
                    confidence=0.7,
                    metadata={"num_results": len(results)}
                )
        except Exception as e:
            logger.error(f"Direct search failed: {e}")
        
        return None
    
    def _combine_results(self, results: List[ToolResult]) -> str:
        """Combine tool results"""
        if not results:
            return "No relevant information found in the knowledge base."
        
        combined = []
        for r in results:
            if r.content and len(r.content.strip()) > 0:
                combined.append(f"[Source: {r.source}]\n{r.content}\n")
        
        if not combined:
            return "No relevant information found."
        
        return "\n---\n".join(combined)
    
    async def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using LLM"""
        if not self.llm:
            return context[:500] if context else "LLM not available. Please check configuration."
        
        try:
            template = """You are an AI assistant for IIT Bhilai. Answer based ONLY on the context provided.

CONTEXT:
{context}

QUESTION:
{question}

INSTRUCTIONS:
- Be concise and accurate
- Only use information from the context above
- If the context doesn't contain the answer, say "I cannot find this information in the available documents."
- Do not make up information
- Cite specific sources when possible (like which document or website)

ANSWER:"""
            
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | self.llm
            
            # Truncate context if too long
            max_context = 3000
            if len(context) > max_context:
                context = context[:max_context] + "..."
            
            result = chain.invoke({"context": context, "question": question})
            
            # Extract text based on result type
            if hasattr(result, 'content'):
                return result.content
            elif hasattr(result, 'text'):
                return result.text
            else:
                return str(result)
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Based on available documents: {context[:500]}..."
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        stats = {
            "tools_available": len(self.tool_registry.tools),
            "tools": list(self.tool_registry.tools.keys()),
            "vector_store_available": self.vector_store_wrapper is not None,
            "llm_available": self.llm is not None
        }
        
        if self.vector_store_wrapper:
            stats["vector_stats"] = self.vector_store_wrapper.get_collection_stats()
        
        if self.cache_manager:
            stats["cache"] = self.cache_manager.get_stats()
        
        return stats
