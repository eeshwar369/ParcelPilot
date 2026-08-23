# Production Replacement Guide

This file lists the demo/local components and the production-grade replacements.

## Current Production Target

- Frontend: Next.js app in `frontend/`
- Backend: FastAPI app in `backend/app/api_server.py`
- Retrieval: Pinecone adapter through `RETRIEVAL_PROVIDER=pinecone`
- Database: managed Postgres
- Cache/queues: managed Redis
- Deployment: containers behind HTTPS ingress

## Replace These Local Pieces

| Local/Demo Piece | Production Replacement | Status |
| --- | --- | --- |
| removed stdlib/static fallback UI | `uvicorn backend.app.api_server:app` + Next.js frontend | Done |
| local JSON state file | Postgres tables + migrations | Planned next |
| local lexical vector search | Pinecone managed vector index | Adapter added |
| mocked auth selector | OIDC/SAML auth provider | Planned next |
| local state-changing actions | Postgres-backed action workflow | Planned next |
| manual server start | Docker/Kubernetes/Render/Fly/Railway deployment | Docker files added |

## Required Production Environment

Create `.env.production` from `.env.production.example`:

```text
APP_ENV=production
DATABASE_URL=...
REDIS_URL=...
RETRIEVAL_PROVIDER=pinecone
PINECONE_API_KEY=...
PINECONE_INDEX=parcelpilot-support
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1024
HF_TOKEN=...
HF_TEXT_MODEL=mistralai/Mistral-7B-Instruct-v0.3
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

Frontend variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
NEXT_PUBLIC_WS_BASE_URL=wss://your-api-domain.com
```

In production, the backend intentionally fails fast if Pinecone, Postgres, or Redis configuration is missing.

## Run Production Backend Locally

```powershell
uvicorn backend.app.api_server:app --host 0.0.0.0 --port 8000
```

## Run Production Frontend Locally

```powershell
cd frontend
npm run build
npm run start
```

## Pinecone Notes

The code now has a Pinecone adapter, but a full production ingestion worker should:

1. Extract PDF/XLSX content.
2. Chunk documents.
3. Generate embeddings.
4. Upsert vectors and metadata to Pinecone.
5. Store structured account/order/ticket data in Postgres.
6. Query Pinecone by embedding at runtime.

The current adapter preserves the same interface while the ingestion worker is completed.
