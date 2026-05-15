 
# IIT Bhilai RAG Agent

A production-ready, pluggable Retrieval-Augmented Generation system for IIT Bhilai information retrieval. The system ingests documents, provides intelligent answers using Gemini LLM, and features a two-layer caching system for optimal performance.

![System Architecture](image-2.png)

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [API Documentation](#api-documentation)
- [Performance Metrics](#performance-metrics)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Rate Limiting](#rate-limiting)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

The IIT Bhilai RAG Agent is a comprehensive question-answering system designed to provide accurate, context-aware responses about IIT Bhilai's courses, programs, and campus information. The system uses semantic search to retrieve relevant information from indexed documents and generates natural language responses using Google's Gemini language model.

## Architecture

The system implements a hub-and-spoke architecture with the following components:

### Core Components

- **Document Ingestion Pipeline**: Automated processing of PDF documents with semantic chunking and embedding generation
- **Two-Layer Cache System**: Exact match (sub-millisecond) and semantic similarity (90% threshold) caching
- **Vector Store**: Chroma DB with 470 chunks indexed using Gemini embeddings (3072 dimensions)
- **LLM Integration**: Google Gemini 2.5 Flash for answer generation
- **FastAPI Backend**: RESTful API with CORS support for frontend integration
- **Next.js Frontend**: Modern chat interface with ChatGPT-like user experience

### Data Flow

1. Documents are ingested, chunked, and embedded into vector representations
2. User queries are processed through the two-layer cache system
3. Semantic search retrieves relevant document chunks
4. LLM generates contextual answers based on retrieved content
5. Responses are cached for future identical or similar queries

## Features

- Automated document detection and ingestion with chunking registry
- Semantic chunking with configurable parameters (500 chars, 50 overlap)
- Two-layer caching (exact and semantic) for reduced latency
- Pluggable tool registry for multi-website and multi-source support
- Production-ready FastAPI server with comprehensive endpoints
- Next.js frontend with responsive ChatGPT-like interface
- Rate limit handling and batch processing for API optimization
- Persistent vector storage with Chroma DB

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI, Python 3.13 |
| LLM Provider | Google Gemini 2.5 Flash |
| Embeddings | Google Gemini Embedding 2 (3072 dimensions) |
| Vector Database | Chroma DB |
| Orchestration | LangChain |
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Caching | In-memory exact cache, vector-based semantic cache |

## Installation

### Prerequisites

- Python 3.13 or higher
- Node.js 18 or higher
- Google Gemini API key (get from [Google AI Studio](https://aistudio.google.com/))
- 4GB RAM minimum (8GB recommended)
- 500MB free disk space for vector store

### Backend Setup

```bash
# Clone the repository
git clone <repository-url>
cd IITBhilai_RAG/backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY
```

### Frontend Setup

```bash
cd ../frontend
npm install
```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Required
GOOGLE_API_KEY=your_api_key_here

# LLM Configuration
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash

# Embedding Configuration
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=gemini-embedding-2

# Database Configuration
CHROMA_PERSIST_DIRECTORY=./data/chroma_langchain_db

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Chunking Parameters

The system uses optimized chunking parameters to balance context preservation and API rate limits:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Chunk Size | 500 characters | Length of each text segment |
| Chunk Overlap | 50 characters | Overlap between consecutive chunks |
| Batch Size | 20 chunks | Number of chunks per API call |
| Similarity Threshold | 0.90 | Minimum score for semantic cache hits |

## Running the System

### Start Backend Server

```bash
cd backend
python run.py
```

The API will be available at `http://localhost:8000`

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
Agent ready!
```

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Verify System Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "vector_store": true
}
```

## API Documentation

### Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/chat` | Ask a question to the agent | None |
| GET | `/health` | Health check endpoint | None |
| GET | `/stats` | System statistics | None |
| GET | `/cache/stats` | Cache performance metrics | None |
| DELETE | `/cache/{question}` | Clear cached response for specific question | None |
| DELETE | `/cache/all` | Clear entire cache | None |

### Chat Endpoint

**Request**
```bash
curl "http://localhost:8000/chat?question=What%20BTech%20programs%20are%20offered"
```

**Response (Cache Miss)**
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

**Response (Cache Hit)**
```json
{
  "question": "What BTech programs are offered?",
  "answer": "IIT Bhilai offers BTech programs in Computer Science and Engineering, Data Science and Artificial Intelligence, Electrical Engineering, Mechanical Engineering, and Mechatronics Engineering.",
  "processing_time": 0.000017,
  "from_cache": true,
  "cache_layer": "exact",
  "sources": ["vector_store"]
}
```

### Cache Management

Clear cache for specific question:
```bash
curl -X DELETE "http://localhost:8000/cache/What%20BTech%20programs%20are%20offered"
```

Clear entire cache:
```bash
curl -X DELETE "http://localhost:8000/cache/all"
```

View cache statistics:
```bash
curl "http://localhost:8000/cache/stats"
```

## Performance Metrics

### Latency Benchmarks

| Operation | First Request | Cached Request |
|-----------|---------------|----------------|
| Exact Match Query | 3-5 seconds | < 0.001 seconds |
| Semantic Variation | 3-5 seconds | 1-2 seconds |
| Document Indexing (470 chunks) | 37 API calls | N/A |

### Cache Performance

| Metric | Value |
|--------|-------|
| Exact Cache Hit Rate | 20-40% |
| Semantic Cache Hit Rate | 30-50% |
| Memory Usage | < 100MB |
| Storage (Vector DB) | 9.1 MB |

## Project Structure

```
IITBhilai_RAG/
├── backend/
│   ├── src/
│   │   ├── api/                 # FastAPI endpoints
│   │   │   └── app.py
│   │   ├── core/                # Core orchestration logic
│   │   │   ├── orchestrator_with_cache.py
│   │   │   ├── config_loader.py
│   │   │   └── llm_factory.py
│   │   ├── caching/             # Two-layer cache system
│   │   │   └── enhanced_cache.py
│   │   ├── tools/               # Pluggable tool registry
│   │   │   ├── tool_registry.py
│   │   │   └── base_tool.py
│   │   ├── ingestion/           # Document processing pipeline
│   │   │   ├── vector_store_wrapper.py
│   │   │   ├── document_ingestion.py
│   │   │   └── chunking_registry.py
│   │   └── config/              # YAML configuration files
│   │       ├── agent.yaml
│   │       ├── cache.yaml
│   │       └── websites.yaml
│   ├── data/                    # Chroma DB storage
│   ├── scripts/                 # Utility scripts
│   ├── tests/                   # Test files
│   ├── run.py                   # Main entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx         # Main chat interface
│   │       ├── layout.tsx
│   │       ├── globals.css
│   │       └── api/chat/        # API route
│   ├── components/
│   ├── package.json
│   └── tsconfig.json
└── README.md
```
 
### Logging

Enable debug logging for detailed diagnostics:
```python
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use of this software is strictly prohibited.

## Support

For issues, questions, or contributions:
- Documentation: Refer to this README
- Issues: Create a ticket in the project management system
- Email: Contact the development team

--- 
