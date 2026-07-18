# IIT Bhilai RAG Documentation

This document describes the current code structure, runtime flow, and the new provider-switch path between the local LLM and the Gemini API.

## Overview

The application is a Retrieval-Augmented Generation system for IIT Bhilai content.

It has three main layers:

1. Backend retrieval and orchestration in Python.
2. Chroma-based document and cache storage.
3. Next.js chat UI with a provider switch.

The current implementation supports:

- Local LLM via Ollama.
- Gemini API via `langchain-google-genai`.
- Exact and semantic caching.
- Tool-based retrieval plus vector fallback.
- Automatic embedding namespaces so different embedding models use different Chroma collections.

## Runtime Flow

1. The frontend sends a question to `/api/chat`.
2. The Next.js route forwards the request to the FastAPI backend.
3. The backend resolves the requested provider and model.
4. The orchestrator checks cache layers scoped to that provider/model.
5. If no cache hit is found, it queries the registered tools.
6. If tools return nothing, it falls back to direct vector search.
7. The selected LLM generates the final answer from the retrieved context.
8. The response is cached again for the same provider/model scope.

## Backend Structure

### `backend/src/core/config_loader.py`

This module centralizes configuration.

Key responsibilities:

- Loads YAML and environment variables.
- Normalizes provider aliases:
  - `local` -> `ollama`
  - `google` -> `gemini`
- Resolves LLM configuration per request.
- Resolves embedding configuration.

Important environment variables:

- `LLM_PROVIDER`
- `GEMINI_MODEL`
- `OLLAMA_MODEL`
- `OPENAI_MODEL`
- `EMBEDDING_PROVIDER`
- `GEMINI_EMBEDDING_MODEL`
- `OLLAMA_EMBEDDING_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `CHROMA_PERSIST_DIRECTORY`

### `backend/src/core/llm_factory.py`

This module creates model instances.

Supported LLM providers:

- `gemini`
- `openai`
- `ollama`

Supported embedding providers:

- `gemini`
- `openai`
- `ollama`

The factory now imports provider packages lazily so the app can start even if a provider is not installed, as long as that provider is not selected.

### `backend/src/core/orchestrator_with_cache.py`

This is the active orchestrator used by the FastAPI app.

It now handles:

- Provider-aware LLM selection.
- Tool registry retrieval.
- Direct vector fallback.
- Exact cache scoped by provider and model.
- Semantic cache stored in a separate Chroma collection.

Cache behavior:

- Exact cache uses an in-memory `OrderedDict` with TTL and max size.
- Semantic cache stores cached question-answer pairs in a dedicated provider/model-specific Chroma collection.
- Cache entries include `llm_provider` and `llm_model` metadata so local and Gemini answers do not mix.

### `backend/src/ingestion/vector_store_wrapper.py`

This wrapper manages the document Chroma collection.

It now supports filtered similarity search with scores, which is required for provider-scoped semantic cache lookups.

It also derives a stable embedding namespace from the embedding provider and model, so a new embedding model gets its own Chroma collection automatically.

If the new collection is empty, the wrapper bootstraps it from the PDFs shipped with the repo, which currently means `backend/courses_study.pdf`.

### `backend/src/api/app.py`

FastAPI endpoints:

- `GET /chat`
- `GET /stats`
- `GET /health`
- `GET /providers`
- `GET /cache/stats`
- `DELETE /cache/{question}`
- `DELETE /cache/all`

The `/chat` endpoint accepts:

- `question`
- `provider`
- `model`
- `use_cache`

## Frontend Structure

### `frontend/src/app/page.tsx`

This is the main chat UI.

It now includes:

- A provider toggle for `local` and `gemini`.
- Live backend stats loading.
- Requests that pass the selected provider/model through to the backend.
- Message metadata showing the provider and cache layer.

### `frontend/src/app/api/chat/route.ts`

This route proxies chat requests to the backend.

It forwards:

- `question`
- `provider`
- `model`
- `use_cache`

### `frontend/src/app/api/stats/route.ts`

This route proxies backend stats so the UI can load backend state without hardcoding backend-specific logic in the page.

### `frontend/src/app/globals.css`

The global styles were updated to:

- Support the provider switch UI.
- Improve responsive layout behavior.
- Use a stronger visual hierarchy.
- Provide a more intentional background and surface system.

## Switching Providers

The switch is runtime-based, not restart-based.

Use the frontend toggle to switch between:

- `Local LLM` for Ollama.
- `Gemini API` for Google-hosted generation.

The selected provider is sent with each request, so the backend can choose the correct LLM instance without restarting the process.

The embedding store is separate from the generation model. The backend automatically builds a provider/model-specific embedding namespace, so switching from Gemini embeddings to Ollama embeddings creates a different Chroma collection instead of reusing incompatible vectors.

## Caching Notes

The cache is now scoped to provider and model.

That means:

- A local Ollama answer will not be returned for a Gemini request.
- A Gemini response will not pollute the local cache path.
- Semantic cache entries are stored separately from document embeddings.
- New embedding models automatically get their own collection and bootstrap from the source PDFs when available.

This is important because mixing answer caches across providers can return stale or incompatible completions.

## Files Changed Most Directly

- `backend/src/core/config_loader.py`
- `backend/src/core/llm_factory.py`
- `backend/src/core/orchestrator_with_cache.py`
- `backend/src/ingestion/vector_store_wrapper.py`
- `backend/src/api/app.py`
- `backend/requirements.txt`
- `frontend/src/app/page.tsx`
- `frontend/src/app/api/chat/route.ts`
- `frontend/src/app/api/stats/route.ts`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/globals.css`

## Notes

- The project currently uses the cached orchestrator path in the API app.
- The local provider assumes Ollama is available at `http://localhost:11434` unless overridden.
- Gemini still requires a valid Google API key.
- If the backend stats fail to load, the frontend still works, but the system panel will show fallback values until the backend is reachable.
