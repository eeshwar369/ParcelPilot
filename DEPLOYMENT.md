# Deployment

## What You Deploy

- Backend: FastAPI service from `backend/app/api_server.py`
- Frontend: Next.js app from `frontend/`
- WebSocket chat: backend route `/ws/chat`
- Production storage/retrieval: Postgres, Redis, Pinecone

## 1. Create `.env.production`

Copy `.env.production.example` to `.env.production` and paste your real values:

```env
APP_ENV=production
ALLOWED_ORIGINS=https://your-frontend-domain.com

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/parcelpilot
REDIS_URL=rediss://USER:PASSWORD@HOST:6379/0

RETRIEVAL_PROVIDER=pinecone
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX=parcelpilot-support
PINECONE_NAMESPACE=production

OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1024

HF_TOKEN=your_huggingface_token
HF_TEXT_MODEL=mistralai/Mistral-7B-Instruct-v0.3

NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
NEXT_PUBLIC_WS_BASE_URL=wss://your-api-domain.com
```

## 2. Local Container Smoke Test

For a local Docker smoke test, use local public URLs so the browser talks to your Docker backend:

```env
ALLOWED_ORIGINS=http://127.0.0.1:3001
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WS_BASE_URL=ws://127.0.0.1:8000
```

```powershell
docker compose -f docker-compose.prod.example.yml --env-file .env.production up --build
```

Open:

```text
http://127.0.0.1:3001
```

## 3. Cloud Deployment Shape

Deploy two services:

- `parcelpilot-backend`
  - Dockerfile: `backend/Dockerfile`
  - Port: `8000`
  - Health check: `/api/health`
  - Env file: `.env.production`

- `parcelpilot-frontend`
  - Dockerfile: `frontend/Dockerfile`
  - Port: `3000`
  - Env vars:
    - `NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com`
    - `NEXT_PUBLIC_WS_BASE_URL=wss://your-backend-domain.com`

## 4. Render Deployment

This repo includes `render.yaml` for a two-service Docker deployment:

- `parcelpilot-backend`
- `parcelpilot-frontend`

Steps:

1. Push this repository to GitHub.
2. In Render, create a new Blueprint from the repository.
3. When Render asks for secret values, paste:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `PINECONE_API_KEY`
   - `OPENAI_API_KEY`
   - `HF_TOKEN`
4. Deploy the backend first and copy its public URL.
5. In the frontend service env vars, set:
   - `NEXT_PUBLIC_API_BASE_URL=https://your-backend-service.onrender.com`
   - `NEXT_PUBLIC_WS_BASE_URL=wss://your-backend-service.onrender.com`
6. In the backend service env vars, set:
   - `ALLOWED_ORIGINS=https://your-frontend-service.onrender.com`
7. Redeploy both services.

If Render gives you different generated service URLs than the defaults in `render.yaml`, update the three URL values above and redeploy.

## 5. After Deploy

1. Check backend health: `https://your-backend-domain.com/api/health`
2. Open frontend: `https://your-frontend-domain.com`
3. Ask: `What support SLA applies to Northstar for a P1 incident?`
4. Confirm the answer is immediate and source-backed.
5. Ask for escalation, confirm it, then verify/respond in `/admin/insights`.

## 6. Important

For production, do not use the local JSON state file as the source of truth. Replace it with Postgres/Supabase tables and run ingestion into Pinecone.
