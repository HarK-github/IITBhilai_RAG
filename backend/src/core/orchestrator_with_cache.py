"""
Orchestrator with provider switching and two-layer caching.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma

from src.core.config_loader import config
from src.core.llm_factory import EmbeddingFactory, LLMFactory
from src.ingestion import VectorStoreWrapper
from src.tools import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


class ExactMatchCache:
    """Provider-scoped in-memory exact match cache with TTL."""

    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        self.ttl = ttl
        self.max_size = max_size
        self.cache: "OrderedDict[str, Tuple[Dict[str, Any], datetime]]" = OrderedDict()

    @staticmethod
    def _key(query: str, provider: str, model: str) -> str:
        normalized_query = query.lower().strip()
        return f"{provider}:{model}:{normalized_query}"

    async def get(self, query: str, provider: str, model: str) -> Optional[Dict[str, Any]]:
        key = self._key(query, provider, model)
        cached = self.cache.get(key)
        if not cached:
            return None

        response, timestamp = cached
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[key]
            return None

        return dict(response)

    async def set(self, query: str, response: Dict[str, Any], provider: str, model: str):
        key = self._key(query, provider, model)
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        payload = dict(response)
        payload["llm_provider"] = provider
        payload["llm_model"] = model
        payload["cache_layer"] = "exact"
        self.cache[key] = (payload, datetime.now())

    def clear(self, provider: Optional[str] = None, model: Optional[str] = None):
        if provider is None and model is None:
            self.cache.clear()
            return

        keys_to_delete = []
        for key in self.cache.keys():
            parts = key.split(":", 2)
            if len(parts) != 3:
                continue
            current_provider, current_model, _ = parts
            if provider and current_provider != provider:
                continue
            if model and current_model != model:
                continue
            keys_to_delete.append(key)

        for key in keys_to_delete:
            self.cache.pop(key, None)

    def clear_query(self, query: str):
        normalized_query = query.lower().strip()
        keys_to_delete = [key for key in self.cache if key.endswith(f":{normalized_query}")]
        for key in keys_to_delete:
            self.cache.pop(key, None)

    def stats(self) -> Dict[str, Any]:
        return {
            "type": "exact",
            "entries": len(self.cache),
            "ttl_seconds": self.ttl,
            "max_size": self.max_size,
        }


class SemanticCache:
    """Provider-scoped semantic cache backed by the vector store."""

    def __init__(self, vector_store_wrapper: VectorStoreWrapper, similarity_threshold: float = 0.90):
        self.vector_store_wrapper = vector_store_wrapper
        self.similarity_threshold = similarity_threshold
        self.cache_store = Chroma(
            persist_directory=vector_store_wrapper.persist_directory,
            embedding_function=vector_store_wrapper.embeddings,
            collection_name=vector_store_wrapper.semantic_cache_collection_name,
        )

    @staticmethod
    def _filter(provider: str, model: str) -> Dict[str, str]:
        return {
            "cache_type": "semantic",
            "llm_provider": provider,
            "llm_model": model,
        }

    @staticmethod
    def _serialize_response(response: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "answer": response.get("answer", ""),
                "tools_used": response.get("tools_used", []),
                "num_sources": response.get("num_sources", 0),
                "llm_provider": response.get("llm_provider"),
                "llm_model": response.get("llm_model"),
            }
        )

    @staticmethod
    def _deserialize_response(response_str: str) -> Dict[str, Any]:
        try:
            data = json.loads(response_str)
            if isinstance(data, dict):
                data["from_cache"] = True
                data["cache_layer"] = "semantic"
                return data
        except Exception:
            pass
        return {"answer": response_str, "from_cache": True, "cache_layer": "semantic"}

    async def get(self, query: str, provider: str, model: str) -> Optional[Dict[str, Any]]:
        if not self.cache_store:
            return None

        try:
            results = self.cache_store.similarity_search_with_relevance_scores(
                query,
                k=1,
                filter=self._filter(provider, model),
            )
            if not results:
                return None

            doc, score = results[0]
            if score < self.similarity_threshold:
                return None

            response_str = doc.metadata.get("response")
            if not response_str:
                return None

            payload = self._deserialize_response(response_str)
            payload["cache_score"] = score
            payload["llm_provider"] = provider
            payload["llm_model"] = model
            return payload
        except Exception as exc:
            logger.debug(f"Semantic cache error: {exc}")
            return None

    async def set(self, query: str, response: Dict[str, Any], provider: str, model: str):
        if not self.cache_store:
            return

        doc = Document(
            page_content=query.lower().strip(),
            metadata={
                "cache_type": "semantic",
                "response": self._serialize_response(response),
                "timestamp": datetime.now().isoformat(),
                "llm_provider": provider,
                "llm_model": model,
            },
        )

        try:
            await asyncio.to_thread(self.cache_store.add_documents, [doc])
        except Exception as exc:
            logger.warning(f"Failed to store semantic cache: {exc}")

    def clear(self, provider: Optional[str] = None, model: Optional[str] = None):
        where: Dict[str, Any] = {"cache_type": "semantic"}
        if provider:
            where["llm_provider"] = provider
        if model:
            where["llm_model"] = model

        try:
            self.cache_store.delete(where=where)
        except Exception as exc:
            logger.warning(f"Failed to clear semantic cache: {exc}")

    def clear_query(self, query: str, provider: Optional[str] = None, model: Optional[str] = None):
        where: Dict[str, Any] = {"cache_type": "semantic"}
        if provider:
            where["llm_provider"] = provider
        if model:
            where["llm_model"] = model

        try:
            self.cache_store.delete(
                where=where,
                where_document={"$contains": query.lower().strip()},
            )
        except Exception as exc:
            logger.warning(f"Failed to clear semantic cache for query: {exc}")

    def stats(self) -> Dict[str, Any]:
        return {
            "type": "semantic",
            "similarity_threshold": self.similarity_threshold,
        }


class EnhancedCacheManager:
    """Coordinates exact and semantic cache layers."""

    def __init__(self, exact_cache: ExactMatchCache, semantic_cache: Optional[SemanticCache] = None):
        self.exact_cache = exact_cache
        self.semantic_cache = semantic_cache
        self.stats_data = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "total_queries": 0,
        }

    async def get(self, query: str, provider: str, model: str) -> Optional[Dict[str, Any]]:
        self.stats_data["total_queries"] += 1

        result = await self.exact_cache.get(query, provider, model)
        if result:
            self.stats_data["exact_hits"] += 1
            result["cache_layer"] = "exact"
            result["from_cache"] = True
            return result

        if self.semantic_cache:
            result = await self.semantic_cache.get(query, provider, model)
            if result:
                self.stats_data["semantic_hits"] += 1
                return result

        self.stats_data["misses"] += 1
        return None

    async def set(self, query: str, response: Dict[str, Any], provider: str, model: str):
        if not response:
            return

        await self.exact_cache.set(query, response, provider, model)
        if self.semantic_cache:
            await self.semantic_cache.set(query, response, provider, model)

    def clear(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.exact_cache.clear(provider=provider, model=model)
        if self.semantic_cache:
            self.semantic_cache.clear(provider=provider, model=model)

    def clear_query(self, query: str, provider: Optional[str] = None, model: Optional[str] = None):
        self.exact_cache.clear_query(query)
        if self.semantic_cache:
            self.semantic_cache.clear_query(query, provider=provider, model=model)

    def get_stats(self) -> Dict[str, Any]:
        total = self.stats_data["total_queries"]
        hits = self.stats_data["exact_hits"] + self.stats_data["semantic_hits"]
        return {
            **self.stats_data,
            "hit_rate": hits / total if total else 0,
            "exact_hit_rate": self.stats_data["exact_hits"] / total if total else 0,
            "semantic_hit_rate": self.stats_data["semantic_hits"] / total if total else 0,
        }


class CachedAgentOrchestrator:
    """Main orchestrator for the RAG agent."""

    def __init__(self):
        self.cache_manager: Optional[EnhancedCacheManager] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.vector_store_wrapper: Optional[VectorStoreWrapper] = None
        self.embeddings = None
        self.llm = None
        self.default_llm_config: Dict[str, Any] = {}
        self.llm_instances: Dict[Tuple[str, str], Any] = {}

        self.setup_logging()
        self.setup_components()
        self.setup_cache()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def setup_components(self):
        """Initialize LLM, embeddings, vector store, and tools."""
        try:
            self.default_llm_config = config.get_llm_config()
            self.llm = self._get_or_create_llm(self.default_llm_config)
            logger.info(
                "LLM initialized: %s (%s)",
                self.default_llm_config["provider"],
                self.default_llm_config["model"],
            )
        except Exception as exc:
            logger.error(f"Failed to initialize LLM: {exc}")
            self.llm = None

        try:
            self.embedding_config = config.get_embedding_config()
            self.embeddings = EmbeddingFactory.create_embeddings(self.embedding_config)
            logger.info(
                "Embeddings initialized: %s (%s)",
                self.embedding_config["provider"],
                self.embedding_config["model"],
            )
        except Exception as exc:
            logger.error(f"Failed to initialize embeddings: {exc}")
            self.embeddings = None
            self.embedding_config = {}
        
        try:
            self.vector_store_wrapper = VectorStoreWrapper(self.embeddings, embedding_config=self.embedding_config)
            logger.info("Vector store connected: %s", self.vector_store_wrapper.get_collection_stats())
        except Exception as exc:
            logger.error(f"Failed to initialize vector store: {exc}")
            self.vector_store_wrapper = None

        websites_config = Path(__file__).resolve().parents[1] / "config" / "websites.yaml"
        self.tool_registry = ToolRegistry(str(websites_config))
        if self.vector_store_wrapper:
            self.tool_registry.set_vector_store(self.vector_store_wrapper)
            self.tool_registry.register_all_websites()
            logger.info("Registered %s tools", len(self.tool_registry.tools))
        else:
            logger.warning("No vector store available - tools not registered")

    def setup_cache(self):
        """Initialize provider-scoped two-layer caching."""
        cache_config = config.get("caching", {}) or {}
        exact_cfg = cache_config.get("layers", {}).get("exact_match", {})
        semantic_cfg = cache_config.get("layers", {}).get("semantic", {})

        exact_cache = ExactMatchCache(
            ttl=exact_cfg.get("ttl", 3600),
            max_size=exact_cfg.get("max_size", 1000),
        )
        semantic_cache = None
        if self.vector_store_wrapper and self.vector_store_wrapper.vector_store:
            semantic_cache = SemanticCache(
                vector_store_wrapper=self.vector_store_wrapper,
                similarity_threshold=semantic_cfg.get("similarity_threshold", 0.90),
            )

        self.cache_manager = EnhancedCacheManager(exact_cache=exact_cache, semantic_cache=semantic_cache)
        logger.info("Cache system initialized")

    def _get_or_create_llm(self, llm_config: Dict[str, Any]):
        key = (llm_config["provider"], llm_config["model"])
        if key not in self.llm_instances:
            self.llm_instances[key] = LLMFactory.create_llm(llm_config)
        return self.llm_instances[key]

    async def query(
        self,
        question: str,
        use_cache: bool = True,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        llm_config = config.get_llm_config(provider_override=provider, model_override=model)
        llm = self._get_or_create_llm(llm_config)
        provider_name = llm_config["provider"]
        model_name = llm_config["model"]

        if use_cache and self.cache_manager:
            cached_result = await self.cache_manager.get(question, provider_name, model_name)
            if cached_result:
                elapsed = (datetime.now() - start_time).total_seconds()
                cached_result["processing_time"] = elapsed
                cached_result["llm_provider"] = provider_name
                cached_result["llm_model"] = model_name
                return cached_result

        relevant_tools = self.tool_registry.get_relevant_tools(question, top_k=3) if self.tool_registry else []
        logger.info("Selected %s tools for provider %s", len(relevant_tools), provider_name)

        tool_results: List[ToolResult] = []
        for tool in relevant_tools:
            try:
                result = await tool.query(question)
                if result.content:
                    tool_results.append(result)
            except Exception as exc:
                logger.error("Tool %s failed: %s", tool.name, exc)

        if not tool_results and self.vector_store_wrapper:
            fallback = await self._direct_search(question)
            if fallback:
                tool_results.append(fallback)

        context = self._combine_results(tool_results)
        answer = await self._generate_answer(question, context, llm)

        response = {
            "answer": answer,
            "from_cache": False,
            "cache_layer": "miss",
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "tools_used": [tool.source for tool in tool_results],
            "num_sources": len(tool_results),
            "llm_provider": provider_name,
            "llm_model": model_name,
        }

        if use_cache and self.cache_manager and answer and "cannot find" not in answer.lower():
            await self.cache_manager.set(question, response, provider_name, model_name)

        return response

    async def _direct_search(self, question: str) -> Optional[ToolResult]:
        """Direct vector search fallback."""
        if not self.vector_store_wrapper:
            return None

        try:
            results = self.vector_store_wrapper.similarity_search(question, k=3)
            if results:
                content = "\n\n".join(
                    [doc.page_content for doc in results if hasattr(doc, "page_content")]
                )
                return ToolResult(
                    content=content,
                    source="vector_store",
                    confidence=0.7,
                    metadata={"num_results": len(results)},
                )
        except Exception as exc:
            logger.error("Direct search failed: %s", exc)

        return None

    def _combine_results(self, results: List[ToolResult]) -> str:
        if not results:
            return "No relevant information found in the knowledge base."

        combined = []
        for result in results:
            if result.content and result.content.strip():
                combined.append(f"[Source: {result.source}]\n{result.content}\n")

        return "\n---\n".join(combined) if combined else "No relevant information found."

    async def _generate_answer(self, question: str, context: str, llm) -> str:
        if not llm:
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
- Cite specific sources when possible

ANSWER:"""

            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | llm

            max_context = 3000
            if len(context) > max_context:
                context = context[:max_context] + "..."

            result = chain.invoke({"context": context, "question": question})
            if hasattr(result, "content"):
                return result.content
            if hasattr(result, "text"):
                return result.text
            return str(result)
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            return f"Based on available documents: {context[:500]}..."

    def get_cache_stats(self) -> Dict[str, Any]:
        if self.cache_manager:
            stats = self.cache_manager.get_stats()
            stats["exact_cache"] = self.cache_manager.exact_cache.stats()
            if self.cache_manager.semantic_cache:
                stats["semantic_cache"] = self.cache_manager.semantic_cache.stats()
            return stats
        return {"error": "Cache not initialized"}

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "tools_available": len(self.tool_registry.tools) if self.tool_registry else 0,
            "tools": list(self.tool_registry.tools.keys()) if self.tool_registry else [],
            "vector_store_available": self.vector_store_wrapper is not None,
            "llm_available": self.llm is not None,
            "llm_provider": self.default_llm_config.get("provider"),
            "llm_model": self.default_llm_config.get("model"),
            "embedding_provider": self.embedding_config.get("provider"),
            "embedding_model": self.embedding_config.get("model"),
            "embedding_namespace": self.vector_store_wrapper.embedding_namespace if self.vector_store_wrapper else None,
        }

        if self.vector_store_wrapper:
            stats["vector_stats"] = self.vector_store_wrapper.get_collection_stats()

        if self.cache_manager:
            stats["cache"] = self.get_cache_stats()

        return stats
