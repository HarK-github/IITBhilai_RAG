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

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi import APIRouter
import os

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter()

@api_router.get("/health")
async def health():
    if orchestrator:
        return {
            "status": "healthy",
            "vector_store": orchestrator.vector_store_wrapper.has_chunks() if orchestrator.vector_store_wrapper else False
        }
    return {"status": "initializing"}

@api_router.get("/chat")
async def chat(
    question: str = Query(..., description="Your question about IIT Bhilai"),
    provider: str | None = Query(None, description="LLM provider override (gemini, local, ollama, openai)"),
    model: str | None = Query(None, description="Optional model override"),
    use_cache: bool = Query(True, description="Use exact + semantic cache"),
):
    if not orchestrator:
        return JSONResponse(status_code=503, content={"error": "Agent not ready"})
    
    result = await orchestrator.query(question, use_cache=use_cache, provider=provider, model=model)
    return {
        "question": question,
        "answer": result["answer"],
        "processing_time": result["processing_time"],
        "from_cache": result["from_cache"],
        "cache_layer": result.get("cache_layer", "unknown"),
        "llm_provider": result.get("llm_provider"),
        "llm_model": result.get("llm_model"),
        "sources": result.get("tools_used", [])
    }

@api_router.get("/stats")
async def stats():
    if not orchestrator:
        return {"error": "Agent not ready"}
    return orchestrator.get_stats()

@api_router.get("/providers")
async def providers():
    if not orchestrator:
        return {"error": "Agent not ready"}
    return {
        "active": {
            "llm_provider": orchestrator.default_llm_config.get("provider"),
            "llm_model": orchestrator.default_llm_config.get("model"),
        },
        "supported": ["gemini", "local", "ollama", "openai"],
    }

@api_router.get("/cache/stats")
async def cache_stats():
    if orchestrator:
        return orchestrator.get_cache_stats()
    return {"error": "Cache not available"}

@api_router.delete("/cache/{question}")
async def clear_cache(question: str):
    if orchestrator and orchestrator.cache_manager:
        orchestrator.cache_manager.clear_query(question)
        return {"status": "cleared", "question": question}
    return {"status": "not_found", "question": question}

@api_router.delete("/cache/all")
async def clear_all_cache():
    if orchestrator and orchestrator.cache_manager:
        count = len(orchestrator.cache_manager.exact_cache.cache)
        orchestrator.cache_manager.clear()
        return {"status": "cleared", "count": count}
    return {"status": "error"}

app.include_router(api_router, prefix="/api")

# Mount frontend
frontend_out = Path(__file__).parent.parent.parent.parent / "frontend" / "out"

@app.get("/")
async def root():
    if (frontend_out / "index.html").exists():
        return FileResponse(frontend_out / "index.html")
    return {"status": "Frontend not built. Run npm run build in frontend directory."}

if frontend_out.exists():
    app.mount("/", StaticFiles(directory=str(frontend_out), html=True), name="static")
