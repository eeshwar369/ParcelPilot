# ParcelPilot Enterprise AI Support Platform

Production-minded AI support platform for the CalQuity AI Engineer assessment.

## Submission Links

- Public repository: `https://github.com/eeshwar369/ParcelPilot`
- Hosted customer app: `https://parcelpilot-frontend-3y2l.onrender.com`
- Hosted admin dashboard: `https://parcelpilot-frontend-3y2l.onrender.com/admin`
- Hosted backend health: `https://parcelpilot-backend-9yb7.onrender.com/api/health`

This repo currently includes:

- Customer and internal support chat contexts.
- Tool-using agent with document search, structured lookup, calculations, ticket search, and confirmed actions.
- Backend-enforced account/role access control.
- Cost-aware model router with OpenAI, Hugging Face, and deterministic fallback paths.
- Source authority and conflict handling.
- Internal proactive issue dashboard.
- Next.js customer assistant and internal admin dashboard.
- WebSocket customer chat through FastAPI `/ws/chat`.
- Data ingestion hooks for the supplied PDF/XLSX pack, plus demo fallback data so the app runs immediately.

## Run Locally

```powershell
uvicorn backend.app.api_server:app --host 127.0.0.1 --port 8000
```

Backend API:

```text
http://127.0.0.1:8000
```

Next.js frontend:

```powershell
cd frontend
npm install
npm run dev
```

Then open:

```text
http://127.0.0.1:3000
```

Routes:

- `http://127.0.0.1:3000` - customer ParcelPilot Assistant over WebSocket
- `http://127.0.0.1:3000/admin` - internal operations/admin console

## Run With Docker

```powershell
docker compose -f docker-compose.prod.example.yml --env-file .env.production up --build
```

Docker maps the frontend to:

```text
http://127.0.0.1:3001
```

The backend remains available at:

```text
http://127.0.0.1:8000
```

## Data Pack

Place the assessment files in:

```text
data/raw/
```

Expected files:

- `01_Support_Policy_v3_CURRENT.pdf`
- `02_Support_Policy_v2_DEPRECATED.pdf`
- `03_Cancellation_and_Service_Credit_SOP_v4.pdf`
- `04_Product_Operations_Guide_and_Known_Issues.pdf`
- `05_Northstar_Logistics_Enterprise_Agreement.pdf`
- `06_LumenWorks_Service_Agreement.pdf`
- `ParcelPilot_Assessment_Data.xlsx`

The current implementation can run with built-in demo data. PDF/XLSX extraction is designed to use optional packages when installed. The production version should install the dependencies listed in `requirements.txt`.

## Optional AI Providers

Copy `.env.example` to `.env` or set environment variables directly.

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1024
HF_TOKEN=
HF_TEXT_MODEL=mistralai/Mistral-7B-Instruct-v0.3
MODEL_ROUTING_MODE=cost_aware
OPENAI_DAILY_BUDGET_USD=5
```

Without provider keys, the platform uses deterministic fallback synthesis so the app remains demoable.

## Retrieval / Vector Store

The backend currently uses:

- PDF and XLSX ingestion from `data/raw`
- structured account/order/ticket lookup from the workbook
- `backend/app/vector_store.py` as the retrieval provider interface
- source authority ranking inside the tool layer

Development can use the local vector retriever. Production mode requires:

```text
APP_ENV=production
RETRIEVAL_PROVIDER=pinecone
PINECONE_API_KEY=...
PINECONE_INDEX=...
DATABASE_URL=...
REDIS_URL=...
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

Frontend production variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
NEXT_PUBLIC_WS_BASE_URL=wss://your-api-domain.com
```

See [PRODUCTION_REPLACEMENT_GUIDE.md](PRODUCTION_REPLACEMENT_GUIDE.md).

## Smoke Test

```powershell
python -m backend.tests.smoke_test
```

## Sample Prompts

See [SAMPLE_PROMPTS.md](SAMPLE_PROMPTS.md). The customer assistant and admin console include built-in test prompts.

## Architecture

See [ARCHITECTURE_NOTE.md](ARCHITECTURE_NOTE.md) for the short submission note and [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md) for the expanded architecture plan.

## Product Note And AI Usage

- [PRODUCT_NOTE.md](PRODUCT_NOTE.md)
- [AI_TOOL_USAGE.md](AI_TOOL_USAGE.md)
- [DEMO_VIDEO_OUTLINE.md](DEMO_VIDEO_OUTLINE.md)
