# Architecture Note

The detailed architecture lives in [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md).

## Agent Design

The agent follows a tool-first workflow:

1. Resolve user context.
2. Extract order/ticket/account references.
3. Execute authorized tools.
4. Search documents.
5. Run deterministic calculations.
6. Evaluate source authority and confidence.
7. Use the model router for answer synthesis.
8. Prepare state-changing actions only as pending actions.
9. Execute actions only after confirmation.

## Tool Design

Implemented tools:

- document search
- order lookup
- ticket lookup
- ticket search
- policy outcome calculation
- prepare escalation
- confirm escalation

Access control is enforced inside the tool layer.

## Data Handling

The app loads built-in demo data immediately. The ingestion hook supports files in `data/raw` and can upgrade PDF/XLSX extraction when optional dependencies are installed.

Production data should live in Postgres with pgvector, Redis cache, queue-backed workers, and tenant-aware authorization.

Current retrieval implementation:

- The local build uses `backend/app/vector_store.py`, a dependency-free local vector-style index based on bag-of-words vectors and cosine similarity.
- Document results are combined with source authority scores in `document_search`.
- Production mode is configured to require `RETRIEVAL_PROVIDER=pinecone`.
- The Pinecone adapter is present in `backend/app/vector_store.py`; a production ingestion worker should upsert embedded chunks into Pinecone.

## Reliability

The system ranks sources by authority and treats deprecated policies and historical tickets as low-authority context. Customer agreements override general policies. Low-confidence or conflicting cases are escalated.

## Model Routing

The model router supports:

- deterministic fallback
- OpenAI premium reasoning path
- Hugging Face lower-cost path
- cost and model trace logging

## Trade-Offs

The first build is dependency-light so it runs immediately. The architecture plan describes the production path to FastAPI, Postgres, Redis, queues, managed model providers, Kubernetes/ECS, SSO, compliance, and multi-region operation.
