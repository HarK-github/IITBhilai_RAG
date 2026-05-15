
# IIT Bhilai RAG Agent

A production-ready, pluggable Retrieval-Augmented Generation (RAG) system for IIT Bhilai information retrieval. The system ingests documents, provides intelligent answers using Gemini LLM, and features a two-layer caching system for optimal performance.
![alt text](image-2.png)
## Architecture Overview

The system implements a hub-and-spoke architecture with the following components:

- **Document Ingestion Pipeline**: Automated processing of PDF documents with semantic chunking and embedding generation
- **Two-Layer Cache System**: Exact match (sub-millisecond) and semantic similarity (90% threshold) caching
- **Vector Store**: Chroma DB with 470 chunks indexed using Gemini embeddings (3072 dimensions)
- **LLM Integration**: Google Gemini 2.5 Flash for answer generation
- **FastAPI Backend**: RESTful API with CORS support for frontend integration

## Features

- Automated document detection and ingestion
- Semantic chunking with configurable chunk sizes (500 chars, 50 overlap)
- Two-layer caching (exact and semantic) for reduced latency
- Pluggable tool registry for multi-website support
- Production-ready FastAPI server
- Next.js frontend with ChatGPT-like interface

## Tech Stack

- **Backend**: Python 3.13, FastAPI, LangChain, Chroma DB
- **LLM**: Google Gemini 2.5 Flash
- **Embeddings**: Google Gemini Embedding 2 (3072 dimensions)
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Caching**: In-memory exact cache, vector-based semantic cache

## Installation

### Prerequisites

- Python 3.13 or higher
- Node.js 18 or higher
- Google Gemini API key

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Configuration

### Environment Variables (.env)

```env
GOOGLE_API_KEY=your_api_key_here
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
CHROMA_PERSIST_DIRECTORY=./data/chroma_langchain_db
```

### Chunking Configuration

The system uses optimized chunking parameters to stay within API rate limits:
- Chunk size: 500 characters
- Chunk overlap: 50 characters
- Batch size: 20 chunks per API call

## Running the System

### Start Backend Server

```bash
cd backend
python run.py
```

The API will be available at `http://localhost:8000`

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/chat?question={query}` | Ask a question to the agent |
| GET | `/health` | Health check endpoint |
| GET | `/stats` | System statistics |
| GET | `/cache/stats` | Cache performance metrics |
| DELETE | `/cache/{question}` | Clear cached response for specific question |
| DELETE | `/cache/all` | Clear entire cache |

## API Response Format

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

## Performance Metrics

| Operation | Latency |
|-----------|---------|
| Exact Cache Hit | < 0.001 seconds |
| Semantic Cache Hit | 1-2 seconds |
| Fresh Query (Cache Miss) | 3-5 seconds |
| Document Indexing (470 chunks) | 37 API calls |

## Project Structure

```
IITBhilai_RAG/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI endpoints
│   │   ├── core/          # Orchestrator, LLM factory
│   │   ├── caching/       # Two-layer cache system
│   │   ├── tools/         # Pluggable tool registry
│   │   ├── ingestion/     # Document processing
│   │   └── config/        # YAML configuration files
│   ├── data/              # Chroma DB storage
│   ├── scripts/           # Utility scripts
│   ├── run.py             # Main entry point
│   └── requirements.txt
├── frontend/
│   ├── src/app/           # Next.js pages
│   ├── components/        # React components
│   └── package.json
└── README.md
```

## Rate Limiting Considerations

The free tier of Gemini API has the following limits:
- Gemini 2.5 Flash: 5 requests per minute, 20 requests per day
- Gemini Embedding 2: 100 requests per minute, 1000 requests per day

For development, consider using Ollama locally to avoid rate limits.

## Testing

Run the cache performance test:

```bash
cd backend
python test_cache_working.py
```

Expected output:
- Query 1: Cache miss (3-5 seconds)
- Query 2: Cache hit (exact) - sub-millisecond
- Query 3: Cache hit (semantic) - 1-2 seconds

## Cache Architecture

The system implements a two-layer cache:

1. **Exact Match Cache**: In-memory dictionary storing exact query-response pairs. TTL: 24 hours.

2. **Semantic Cache**: Vector-based similarity search using Chroma DB. Threshold: 90% similarity. Queries above this threshold return cached responses.

## License

This project is proprietary and confidential.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
```