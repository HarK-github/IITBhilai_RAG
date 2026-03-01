"""
FastAPI server for IIT Bhilai RAG Agent
"""
import sys
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.orchestrator_with_cache import CachedAgentOrchestrator

# Global orchestrator instance
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    print("🚀 Initializing IIT Bhilai RAG Agent...")
    orchestrator = CachedAgentOrchestrator()
    print("✅ Agent ready!")
    yield
    print("👋 Shutting down...")

app = FastAPI(
    title="IIT Bhilai RAG Agent",
    description="Pluggable AI Agent for IIT Bhilai Information",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "IIT Bhilai RAG Agent",
        "status": "running",
        "endpoints": ["/chat", "/stats", "/health", "/cache/stats"]
    }

@app.get("/health")
async def health():
    if orchestrator:
        return {
            "status": "healthy",
            "vector_store": orchestrator.vector_store_wrapper.has_chunks() if orchestrator.vector_store_wrapper else False
        }
    return {"status": "initializing"}

@app.get("/chat")
async def chat(question: str = Query(..., description="Your question about IIT Bhilai")):
    if not orchestrator:
        return JSONResponse(status_code=503, content={"error": "Agent not ready"})
    
    result = await orchestrator.query(question)
    return {
        "question": question,
        "answer": result["answer"],
        "processing_time": result["processing_time"],
        "from_cache": result["from_cache"],
        "cache_layer": result.get("cache_layer", "unknown"),
        "sources": result.get("tools_used", [])
    }

@app.get("/stats")
async def stats():
    if not orchestrator:
        return {"error": "Agent not ready"}
    return orchestrator.get_stats()

@app.get("/cache/stats")
async def cache_stats():
    if orchestrator and hasattr(orchestrator, 'exact_cache'):
        cache_size = len(orchestrator.exact_cache.cache) if hasattr(orchestrator.exact_cache, 'cache') else 0
        return {
            "cache_size": cache_size,
            "has_semantic_cache": orchestrator.semantic_cache is not None,
            "type": "in-memory"
        }
    return {"error": "Cache not available"}

@app.delete("/cache/{question}")
async def clear_cache(question: str):
    if orchestrator and hasattr(orchestrator, 'exact_cache'):
        key = question.lower().strip()
        if hasattr(orchestrator.exact_cache, 'cache') and key in orchestrator.exact_cache.cache:
            del orchestrator.exact_cache.cache[key]
            return {"status": "cleared", "question": question}
    return {"status": "not_found", "question": question}

@app.delete("/cache/all")
async def clear_all_cache():
    if orchestrator and hasattr(orchestrator, 'exact_cache'):
        if hasattr(orchestrator.exact_cache, 'cache'):
            count = len(orchestrator.exact_cache.cache)
            orchestrator.exact_cache.cache.clear()
            return {"status": "cleared", "count": count}
    return {"status": "error"}
