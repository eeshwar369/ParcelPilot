# Architecture Note

## Agent Design

ParcelPilot uses a support agent that receives a user identity and message, enforces account scope, gathers context through tools, and returns a source-backed answer. The agent routes higher-risk answers through OpenAI and can use lower-cost Hugging Face or deterministic fallback paths for simpler work. WebSocket chat streams status and final answer events to the customer UI.

## Tool Design

The backend exposes tools for document search, order lookup, ticket lookup, ticket search, policy outcome calculation, and confirmed escalation creation. Mutating actions are staged as pending actions and require confirmation before execution. Admin users can verify and respond to escalations in the dashboard.

## Document And Structured Data Handling

PDF and workbook files are ingested from `data/raw`. PDFs become document chunks with metadata such as source type, account, authority, status, and page. Workbook sheets hydrate structured accounts, orders, and tickets. In development, retrieval can run locally; in production, document chunks are embedded with OpenAI and queried through Pinecone.

## Source Reliability And Conflict Handling

Sources are ranked by authority: signed customer agreements override current policy, current policy overrides SOP/product docs, and deprecated or historical sources are treated as lower-trust context. The answer payload includes source snippets, confidence, and tool traces so users can audit why an answer was produced.

## Major Trade-Offs

The assessment version keeps persistence lightweight and file-backed for portability, while production deployment validates Supabase/Postgres, Redis, and Pinecone envs. Authentication is demo-oriented rather than full SSO. The implementation prioritizes explainable retrieval, action safety, and deployability over deep workflow automation.
