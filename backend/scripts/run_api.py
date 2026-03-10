#!/usr/bin/env python3
"""
FastAPI server for IIT Bhilai RAG Agent
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
from src.core.orchestrator_with_cache import CachedAgentOrchestrator

# Global orchestrator instance
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global orchestrator
    print("🚀 Initializing IIT Bhilai RAG Agent...")
    orchestrator = CachedAgentOrchestrator()
    print("✅ Agent ready!")
    yield
    # Shutdown
    print("👋 Shutting down...")

app = FastAPI(
    title="IIT Bhilai RAG Agent",
    description="Pluggable AI Agent for IIT Bhilai Information",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "IIT Bhilai RAG Agent",
        "status": "running",
        "endpoints": ["/chat", "/stats", "/health"]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    if orchestrator:
        return {
            "status": "healthy", 
            "vector_store": orchestrator.vector_store_wrapper.has_chunks() if orchestrator.vector_store_wrapper else False
        }
    return {"status": "initializing"}

@app.get("/chat")
async def chat(question: str = Query(..., description="Your question about IIT Bhilai")):
    """Ask a question to the agent"""
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
    """Get agent statistics"""
    if not orchestrator:
        return {"error": "Agent not ready"}
    
    stats = orchestrator.get_stats()
    cache_stats = orchestrator.get_cache_stats()
    
    return {
        "system": stats,
        "cache": cache_stats
    }

if __name__ == "__main__":
    uvicorn.run(
        "run_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
