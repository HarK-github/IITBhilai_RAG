# IIT Bhilai Knowledge Retrieval System

A high-performance, pluggable Retrieval-Augmented Generation (RAG) pipeline designed for domain-specific information retrieval. Built with a hub-and-spoke architecture, the system efficiently ingests documents, processes queries through a two-layer caching mechanism, and delivers low-latency responses via a production-ready FastAPI backend.

![alt text](image-2.png)

## Architecture & System Design

The system is decoupled into independent, scalable components:

- **Document Ingestion Pipeline**: Automates the processing of unstructured documents using semantic chunking strategies (500-character chunks with 50-character overlap) and generates dense embeddings (3072 dimensions).
- **Two-Layer Caching Mechanism**: 
  - **L1 (Exact Match)**: Sub-millisecond in-memory cache for repeated identical queries.
  - **L2 (Semantic Match)**: Vector-based similarity search using Chroma DB with a configurable threshold (e.g., 90%) to catch conceptually identical queries and reduce LLM round-trips.
- **Vector Storage**: Leverages Chroma DB for persistent, high-dimensional vector storage and fast nearest-neighbor retrieval.
- **RESTful API**: FastAPI-driven backend with CORS support, structured routing, and comprehensive health/metric endpoints.
- **Client Interface**: React/Next.js frontend offering a responsive, real-time query interface.

## Technical Stack

- **Backend Core**: Python 3.13, FastAPI, LangChain
- **Vector Database**: Chroma DB
- **Embeddings & Inference**: Gemini Embedding 2 (3072d), Gemini 2.5 Flash
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS

## Performance Characteristics

| Operation | Typical Latency | Description |
|-----------|----------------|-------------|
| Exact Cache Hit (L1) | < 1 ms | Handled completely in-memory |
| Semantic Cache Hit (L2) | 1-2 s | Requires vector similarity calculation |
| Cache Miss (Full RAG) | 3-5 s | Full pipeline execution (retrieval + generation) |

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/chat?question={query}` | Execute a retrieval-augmented query |
| `GET` | `/health` | System health and connectivity status |
| `GET` | `/stats` | Global system statistics |
| `GET` | `/cache/stats` | Cache hit/miss rates and latency metrics |
| `DELETE` | `/cache/{question}` | Invalidate specific cache entry |
| `DELETE` | `/cache/all` | Flush entire cache |

### Response Schema

```json
{
  "question": "What BTech programs are offered?",
  "answer": "IIT Bhilai offers BTech programs in Computer Science and Engineering, Data Science and Artificial Intelligence, Electrical Engineering, Mechanical Engineering, and Mechatronics Engineering.",
  "processing_time": 3.58,
  "from_cache": false,
  "cache_layer": "miss",
  "sources": ["vector_store"]
}
```

## Local Development Setup

### Requirements
- Python 3.13+
- Node.js 18+
- Valid LLM/Embedding API Keys

### Backend Initialization

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Configure environment variables in .env
python run.py
```
*Server runs at `http://localhost:8000`*

### Frontend Initialization

```bash
cd frontend
npm install
npm run dev
```
*Client runs at `http://localhost:3000`*

## Configuration (`.env`)

The system behavior and LLM integration are configurable via environment variables:

```env
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
CHROMA_PERSIST_DIRECTORY=./data/chroma_langchain_db
```
