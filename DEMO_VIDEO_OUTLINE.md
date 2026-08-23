# Demo Video Outline

Target length: about 5 minutes.

## 1. Architecture

- FastAPI backend with REST and WebSocket chat.
- Next.js customer assistant and admin dashboard.
- Agent tools for document search, order/ticket lookup, policy calculation, and escalations.
- Pinecone-backed retrieval with OpenAI embeddings in production.
- Source authority model for agreements, current policies, SOPs, deprecated docs, and historical context.

## 2. Working Demo

- Open customer app.
- Ask: `What support SLA applies to Northstar for a P1 incident?`
- Show source-backed response.
- Ask a restricted billing or escalation-style question.
- Confirm escalation.
- Open `/admin` and show dashboard/ticket/escalation workflow.

## 3. Product And Technical Decisions

- Customer agreements override general policy.
- Mutating actions require confirmation.
- OpenAI is reserved for high-risk final answers; cheaper or deterministic paths are available for lower-risk work.
- Production deployment uses Render, Supabase/Postgres, Redis, Pinecone, OpenAI, and Hugging Face envs.

## 4. Close

- Mention what is left out: full SSO, full ticketing integration, background worker scale-out, and production observability dashboards.
- Mention success metric: high-confidence source-backed resolution rate with low incorrect-answer rate.
