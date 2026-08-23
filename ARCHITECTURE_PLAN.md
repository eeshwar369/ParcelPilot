# ParcelPilot AI Support System Architecture Plan

## 1. Executive Summary

ParcelPilot needs an AI support system that can answer customer and internal operations questions using only the supplied data pack: policies, SOPs, agreements, product docs, known issues, accounts, orders, and historical tickets. The system must be careful with source reliability, customer-specific contract overrides, access control, and state-changing actions.

The proposed solution is a production-minded full-stack application with:

- A customer-facing support chatbot scoped to one customer account.
- An internal operations chatbot scoped by mocked staff roles.
- Retrieval over supplied documents with source authority ranking.
- Structured-data tools over account, order, and ticket data.
- Confirm-before-execute state-changing tools for escalations, ticket updates, and follow-up tasks.
- An internal proactive issue dashboard for urgent, repeated, and unusual support patterns.
- Hosted deployment with clear setup instructions and a short architecture/product note.

The assessment implementation can be delivered as a compact hosted demo, but the target architecture should be designed as a production-grade, multi-tenant AI support platform. In a real ParcelPilot deployment, the same product should handle millions of requests per day through stateless API services, queue-backed agent execution, tenant-aware data isolation, horizontal autoscaling, distributed caches, rate limits, model fallbacks, observability, and disaster recovery.

To make this a fully scalable enterprise AI support platform, the architecture also needs platform capabilities beyond chat: tenant onboarding, administration, governance, compliance, model risk controls, billing/quotas, integration management, human review, and operational runbooks. These are not demo-first features, but they are required for a serious enterprise product.

## 2. Product Scope

### 2.1 Primary User Contexts

#### Customer-Facing Chatbot

Purpose:

- Answer direct customer questions about cancellations, credits, SLA coverage, product issues, and account-specific contract terms.
- Restrict all structured-data access to the authenticated customer's account.
- Escalate uncertain, unsupported, or action-oriented requests.

Example:

> Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.

Expected behavior:

1. Resolve the current customer/account context.
2. Look up order `ORD-1001`.
3. Verify the order belongs to the customer account.
4. Search the Northstar agreement.
5. Search the current cancellation SOP and active support policy.
6. Compare agreement terms against general policy.
7. Answer with citations and confidence.
8. Escalate if terms conflict or the requested action requires human approval.

#### Internal Operations Chatbot

Purpose:

- Help authorized ParcelPilot staff investigate support issues across accounts.
- Query tickets, orders, known issues, policies, and agreements.
- Create draft escalations, follow-up tasks, or ticket updates after confirmation.

Example:

> Which high-severity tickets are close to SLA breach, and should any be escalated?

Expected behavior:

1. Confirm user role allows cross-account support access.
2. Query ticket data.
3. Calculate SLA risk using dataset snapshot time from workbook README.
4. Search relevant SLA policy.
5. Rank tickets by urgency.
6. Propose escalations.
7. Require explicit confirmation before creating escalation records.

### 2.2 Additional Client Problem Chosen

I would implement both trust/reliability and a lightweight proactive issue detection view, but if prioritizing one as the explicit product note focus, I would choose:

**Problem 2: Trust and Reliability**

Reason:

- The assessment emphasizes imperfect, conflicting, and outdated sources.
- In logistics support, a wrong fee/credit/SLA answer can directly damage customer trust.
- Trust controls make the chatbot safer and make the internal dashboard more credible.

The proactive issue dashboard is still included as a strong extension because it demonstrates product judgment beyond reactive chat.

## 3. Recommended Tech Stack

### 3.1 Frontend

- **Next.js + React + TypeScript**
  - Fast to build a polished hosted UI.
  - Works well for chat, dashboards, and server-side deployment on Vercel.
- **Tailwind CSS**
  - Rapid, consistent UI development.
- **shadcn/ui or lightweight custom components**
  - Chat layout, tabs, dialogs, buttons, confirmation modals, tables.
- **Lucide icons**
  - Tool status, confirmation, escalation, search, database, warning states.

### 3.2 Backend

- **FastAPI + Python**
  - Strong fit for AI agents, document ingestion, pandas/openpyxl processing, and structured tool APIs.
  - Easy to expose typed endpoints for chat, tool execution, escalations, and dashboard data.
- **Stateless service design**
  - Chat/API workers should be horizontally scalable behind a load balancer.
  - Conversation state, pending actions, audit logs, and usage records live in external stores, not process memory.
- **Async worker tier**
  - Long-running ingestion, embedding, issue detection, batch evaluations, and model retries run outside the request path.
- **Redis**
  - Low-latency session cache, semantic response cache, rate limiting, idempotency keys, and short-lived pending-action tokens.
- **Queue system**
  - Use SQS, Kafka, RabbitMQ, or Redis Streams for background jobs and high-volume event processing.
- **Pydantic**
  - Tool schemas, request validation, response contracts, role/account scoping.
- **LangGraph or a lightweight custom orchestrator**
  - LangGraph is preferred for explicit multi-step flows, tool calls, confirmation checkpoints, and recoverable state.
  - If time is tight, implement a small deterministic orchestration layer using OpenAI tool calling.

### 3.3 AI and Retrieval

- **Hybrid model layer: OpenAI + Hugging Face/open-weight models**
  - OpenAI is reserved for high-risk reasoning, final answer synthesis for complex policy/contract questions, and cases where tool selection must be highly reliable.
  - Hugging Face/open-weight models handle lower-cost tasks such as intent classification, query rewriting, ticket clustering, lightweight summarization, reranking, and optional local embeddings.
  - A model router chooses the cheapest reliable model for each step based on task type, risk level, confidence, and latency budget.
- **OpenAI API**
  - Used as the premium reliability path, not the default for every subtask.
  - Best fit for complex multi-step reasoning, customer-facing final answers, conflict-heavy policy questions, and safety-sensitive escalation decisions.
- **Hugging Face Inference Providers or locally hosted open-weight models**
  - Used for cost-saving auxiliary inference.
  - Hosted option: Hugging Face router with `HF_TOKEN`.
  - Local option: small open-weight models served through `llama.cpp`, `vLLM`, `Ollama`, or `text-generation-inference` when deployment resources allow.
- **Open-source embedding model**
  - Prefer a Sentence Transformers model such as `sentence-transformers/all-MiniLM-L6-v2` or `BAAI/bge-small-en-v1.5` for local/low-cost embeddings.
  - Keep OpenAI embeddings as a configurable fallback if retrieval quality is weak.
- **Postgres + pgvector**
  - Single production database for relational data, vector search, and mocked state-changing actions.
- **LlamaIndex or custom ingestion**
  - Custom ingestion is acceptable here because the corpus is small and source metadata matters more than framework complexity.

### 3.3.1 Cost-Aware Model Routing

The system should not send every step to OpenAI. Most agent work is mechanical: classify intent, search documents, query structured data, calculate fields, detect uncertainty, and format tool traces. Only selected reasoning and final-answer steps need a stronger paid model.

Recommended model router policy:

| Task | Default Model Path | Upgrade Condition |
| --- | --- | --- |
| Intent classification | Hugging Face/open-weight small classifier or small instruct model | Ambiguous intent or action request |
| Query rewriting for retrieval | Hugging Face/open-weight small instruct model | Retrieval returns weak/contradictory results |
| Embeddings | Local Sentence Transformers model | Use OpenAI embeddings only if recall is poor |
| Ticket clustering/similarity | Local embeddings + SQL/rules | Use LLM only for cluster labels/summaries |
| Structured lookup/calculation | No LLM | Never upgrade; deterministic code |
| Source conflict detection | Rules first, small model for summary | Upgrade if contract/policy conflict affects customer-facing answer |
| Internal draft summary | Hugging Face/open-weight model | Upgrade for high-severity/SLA-sensitive recommendation |
| Customer-facing final answer | OpenAI for medium/high-risk cases | Use cheaper model only for simple, well-cited FAQ-style answers |
| State-changing action decision | OpenAI or deterministic policy + OpenAI review | Never execute without user confirmation |

Routing dimensions:

- **Risk:** customer-facing, financial impact, SLA impact, privacy risk, or state-changing action.
- **Complexity:** number of tools/sources needed, amount of conflict, missing inputs.
- **Confidence:** retrieval score, source authority, calculation completeness.
- **Cost budget:** daily/monthly OpenAI spend limit and per-request max cost.
- **Latency:** small local/HF model for quick pre-processing; OpenAI only when needed.

Example routing flow:

```text
user message
  |
  v
cheap intent classifier
  |
  +--> simple read-only query
  |       -> deterministic tools
  |       -> cheap summarizer or template answer
  |
  +--> complex policy/contract query
  |       -> retrieval + structured tools
  |       -> trust/conflict rules
  |       -> OpenAI final reasoning if medium/high risk
  |
  +--> action request
          -> tools gather evidence
          -> OpenAI or rule-based action proposal
          -> confirmation required
```

Implementation module:

```text
backend/app/ai/
  model_router.py
  providers/
    openai_provider.py
    huggingface_provider.py
    local_provider.py
  budgets.py
  task_policy.py
```

The router should log model selection, estimated cost, latency, token usage, and upgrade reason for each step.

### 3.4 Data Processing

- **PyMuPDF or pypdf**
  - Extract text from PDF policies, agreements, SOPs, and product docs.
- **pandas + openpyxl**
  - Load workbook sheets for accounts, orders, tickets, and README snapshot time.
- **SQLAlchemy**
  - Database persistence and structured query layer.

### 3.5 Deployment

Recommended hosted architecture:

- **Frontend:** Vercel
- **Backend API:** Render, Railway, or Fly.io
- **Database:** Supabase Postgres with pgvector
- **Object/data seed:** Repository `data/raw` for assessment files, with ingestion run during setup or release

For a simpler single-platform deployment:

- Deploy FastAPI and built frontend together on Render.
- Use Supabase Postgres externally.

Production architecture:

- **Frontend edge:** CDN + WAF + static asset caching.
- **API edge:** API Gateway or ingress controller with authentication, rate limits, request validation, and tenant routing.
- **Compute:** Kubernetes/EKS/GKE/AKS, ECS/Fargate, or Fly.io Machines for horizontally scaled backend services.
- **Data:** managed Postgres with read replicas, point-in-time recovery, partitioning, and pgvector indexes.
- **Cache:** managed Redis cluster.
- **Queue:** SQS/Kafka/RabbitMQ for async workloads.
- **Secrets:** managed secret store such as AWS Secrets Manager, GCP Secret Manager, Doppler, or Vault.
- **Observability:** OpenTelemetry traces, centralized logs, metrics, alerting, and LLM cost dashboards.

## 4. High-Level Architecture

```text
User Browser
    |
    v
Next.js Web App
    |
    | HTTPS /api/chat, /api/confirm-action, /api/dashboard
    v
FastAPI Backend
    |
    +--> Auth & Context Resolver
    |       - mocked customer account
    |       - mocked internal role
    |       - request-scoped permissions
    |
    +--> Model Router
    |       - OpenAI premium path
    |       - Hugging Face hosted path
    |       - local open-weight path
    |       - budget and risk policies
    |
    +--> Agent Orchestrator
    |       - intent classification
    |       - tool planning
    |       - retrieval + structured lookup
    |       - confidence/conflict evaluation
    |       - answer generation
    |       - action confirmation checkpoint
    |
    +--> Tool Layer
    |       - document_search
    |       - account/order/ticket lookup
    |       - calculations
    |       - escalation/task/ticket update actions
    |
    +--> Trust Layer
    |       - source authority ranking
    |       - conflict detection
    |       - stale/deprecated source handling
    |       - customer-agreement override rules
    |
    +--> Data Access Layer
            - row-level authorization checks
            - SQL queries
            - vector retrieval filters
            - audit logs

Postgres + pgvector
    |
    +--> documents
    +--> document_chunks
    +--> accounts
    +--> orders
    +--> tickets
    +--> escalations
    +--> follow_up_tasks
    +--> audit_events
    +--> model_usage_events
```

### 4.1 CTO-Grade Production Reference Architecture

The production architecture should separate latency-sensitive online paths from heavy offline/async paths.

```text
Internet
  |
  v
CDN + WAF + DDoS Protection
  |
  v
API Gateway / Ingress
  |   - JWT/session validation
  |   - tenant resolution
  |   - request size limits
  |   - per-tenant rate limits
  |   - idempotency keys
  |
  +--> Next.js Web Frontend
  |
  +--> FastAPI Chat API Pods
  |       - stateless
  |       - autoscaled by CPU/RPS/latency
  |       - streams responses
  |       - calls agent coordinator
  |
  +--> FastAPI Tool API Pods
  |       - structured lookup
  |       - document retrieval
  |       - action confirmation
  |       - strict authorization
  |
  +--> Internal Admin/API Pods
          - ingestion controls
          - evals
          - audit review

Redis Cluster
  - rate limits
  - session cache
  - semantic cache
  - pending action tokens
  - idempotency records

Queue / Event Bus
  - document ingestion jobs
  - embedding jobs
  - proactive issue detection
  - escalation notifications
  - audit/model usage events

Worker Pools
  - ingestion workers
  - embedding workers
  - proactive detection workers
  - evaluation workers
  - notification workers

Postgres Primary
  - transactional source of truth
  - accounts/orders/tickets/actions/audits
  - row-level tenant policies

Postgres Read Replicas
  - dashboard queries
  - analytics reads
  - internal reporting

Vector Store
  - pgvector for assessment and early production
  - can split to Pinecone/Weaviate/Qdrant/OpenSearch later if vector traffic dominates

Model Layer
  - OpenAI premium path
  - Hugging Face provider path
  - local/open-weight inference pool
  - model router + budget controller
```

### 4.2 Online Request Path

The online path should be optimized for low latency and safe degradation.

1. Browser sends chat message with user/session context.
2. API Gateway validates auth, request size, tenant, and rate limit.
3. Chat API creates or resumes conversation state from Postgres/Redis.
4. Model router uses a cheap model or deterministic classifier for intent.
5. Agent calls read tools through the Tool API.
6. Tool API enforces tenant and role authorization before every data access.
7. Retrieval uses Redis/semantic cache first, then vector search.
8. Structured data comes from Postgres primary or replica depending on freshness needs.
9. Agent synthesizes response using the cheapest model that satisfies risk policy.
10. Response is streamed to UI with tool trace, citations, confidence, and model/provider trace.
11. Audit and usage events are written asynchronously through the queue.

### 4.3 Async Processing Path

Heavy work should never block chat requests.

- Document ingestion runs as background jobs.
- Embeddings are generated in batches with retry and checkpointing.
- Proactive issue detection runs on a schedule and writes materialized findings.
- Model usage events are aggregated into cost dashboards.
- Evaluation suites run offline against saved test questions.
- Notification delivery runs through workers so a slow third-party integration cannot slow chat.

### 4.4 Scale Targets

Initial production target:

- 1-5 million chat/API requests per day.
- 500-2,000 concurrent active users.
- 99.9% monthly API availability.
- p95 API acknowledgement latency under 500 ms.
- p95 first-token latency under 3 seconds for normal chat.
- p95 complete answer latency under 15 seconds for multi-tool questions.
- p95 dashboard load under 2 seconds from precomputed findings.

Future enterprise target:

- 10-50 million requests per day.
- 10,000+ concurrent users.
- 99.95% availability for customer-facing chat.
- Multi-region active-passive or active-active deployment.
- Tenant-level usage isolation and quota enforcement.

### 4.5 Horizontal Scaling Strategy

Scale independently:

- Frontend edge cache scales through CDN.
- Chat API pods scale by RPS, CPU, memory, and response latency.
- Tool API pods scale by database query volume.
- Worker pools scale by queue depth.
- Embedding workers scale separately from chat workers.
- Local model inference pools scale by GPU/CPU utilization.
- Database read replicas scale dashboard and analytics reads.

Important rule:

- No application server should own durable state. Any pod can die without losing conversations, pending actions, or audit history.

### 4.6 Caching Strategy

Use multiple cache layers:

- CDN cache for static frontend assets.
- Redis request cache for repeated metadata and account context.
- Retrieval cache for repeated document searches.
- Semantic cache for low-risk repeated Q&A where tenant scope and source versions match.
- Model response cache only when:
  - answer is read-only
  - source document versions are unchanged
  - tenant/account scope is identical
  - no private cross-account data is included
- Dashboard cache/materialized views for issue detection.

Cache invalidation:

- Invalidate retrieval and semantic caches on document re-ingestion.
- Invalidate account/order/ticket caches when structured data changes.
- Include `source_version`, `tenant_id`, `account_id`, and `permission_hash` in cache keys.

### 4.7 Database Scaling Strategy

Postgres is the source of truth in the early production architecture.

Techniques:

- Connection pooling with PgBouncer.
- Proper indexes on `account_id`, `tenant_id`, `order_id`, `ticket_id`, `created_at`, `status`, and `severity`.
- Table partitioning for high-volume audit/model usage events by time and tenant.
- Read replicas for dashboards and analytics.
- Materialized views for proactive issue detection.
- Point-in-time recovery.
- Automated backups with restore tests.
- Archival storage for old audit events.

Vector scaling:

- Start with pgvector HNSW/IVFFlat indexes.
- Store embeddings with `tenant_id`, `account_id`, `document_id`, `source_version`, and `authority_score`.
- Filter by tenant/account before ranking wherever possible.
- Split to dedicated vector infrastructure when vector QPS or index size becomes the bottleneck.

### 4.8 Reliability Patterns

Required patterns:

- Request timeouts for every external call.
- Retries with exponential backoff for transient failures.
- Circuit breakers for model providers and third-party APIs.
- Bulkheads so slow model calls do not exhaust all API workers.
- Graceful degradation:
  - If OpenAI is unavailable, use HF/local model for low-risk responses and escalate high-risk requests.
  - If vector search is degraded, fall back to keyword search and lower confidence.
  - If action service is degraded, answer read-only and ask user to retry action later.
- Idempotency keys for confirmed actions.
- Dead-letter queues for failed async jobs.
- Runbooks for incident response.

### 4.9 Multi-Tenant Isolation

Production should treat each customer organization as a tenant.

Controls:

- `tenant_id` on every business, document, audit, and usage table.
- Row-level security policies in Postgres where possible.
- Tenant-aware vector filters.
- Tenant-specific encryption keys for sensitive data if required.
- Per-tenant rate limits and spend limits.
- Per-tenant data retention policies.
- Per-tenant audit exports.

The model prompt should mention tenant boundaries, but actual isolation must happen in auth, tools, SQL filters, vector filters, and cache keys.

## 5. Data Architecture

### 5.1 Source Types

| Source | Use | Reliability Treatment |
| --- | --- | --- |
| Current support policy | General support/SLA rules | High authority |
| Deprecated policy | Historical context only | Low authority; never preferred |
| Cancellation and service credit SOP | Operational rules | High authority |
| Product operations guide and known issues | Issue diagnosis | Medium-high authority |
| Customer agreements | Customer-specific contract terms | Highest authority for that customer |
| Workbook account/order/ticket data | Operational truth snapshot | High authority, scoped by access |
| Historical ticket resolutions | Context/examples | Low authority; cannot override policy/SOP/agreement |

### 5.2 Document Ingestion Pipeline

Steps:

1. Copy source files into `data/raw`.
2. Extract text from PDFs.
3. Normalize encoding, page numbers, document names, and section headings.
4. Chunk documents by section with overlap.
5. Attach metadata:
   - `document_id`
   - `document_name`
   - `source_type`
   - `customer_account_id`, if customer-specific agreement
   - `version`
   - `status`: `current`, `deprecated`, `historical_context`
   - `authority_score`
   - `page_number`
   - `effective_date`, if available
6. Generate embeddings.
7. Store chunks in `document_chunks`.

Chunking strategy:

- Use semantic/heading-aware chunks where possible.
- Target 500-900 tokens per chunk.
- Keep page and section citations.
- Store enough neighboring context to answer policy questions without over-retrieving.

### 5.3 Workbook Ingestion Pipeline

Steps:

1. Read workbook README sheet.
2. Store dataset snapshot time as global reference time.
3. Load account sheet into `accounts`.
4. Load order sheet into `orders`.
5. Load ticket sheet into `tickets`.
6. Validate foreign keys:
   - orders must reference known accounts
   - tickets must reference known accounts, and orders when present
7. Normalize timestamps to UTC internally while displaying dataset-local time when useful.
8. Preserve raw source rows for audit/debugging.

### 5.4 Proposed Database Tables

Core tables:

- `accounts`
  - `id`
  - `name`
  - `tier`
  - `contract_type`
  - `created_at`
  - `raw_data`

- `orders`
  - `id`
  - `account_id`
  - `carrier`
  - `service_level`
  - `status`
  - `pickup_time`
  - `delivery_time`
  - `cancellation_requested_at`
  - `raw_data`

- `tickets`
  - `id`
  - `account_id`
  - `order_id`
  - `category`
  - `severity`
  - `status`
  - `created_at`
  - `last_updated_at`
  - `resolution_summary`
  - `raw_data`

- `documents`
  - `id`
  - `name`
  - `source_type`
  - `status`
  - `authority_score`
  - `customer_account_id`

- `document_chunks`
  - `id`
  - `document_id`
  - `chunk_text`
  - `embedding`
  - `page_number`
  - `section_title`
  - `metadata`

Action tables:

- `escalations`
  - `id`
  - `ticket_id`
  - `account_id`
  - `reason`
  - `priority`
  - `created_by`
  - `created_at`
  - `status`

- `follow_up_tasks`
  - `id`
  - `account_id`
  - `ticket_id`
  - `title`
  - `description`
  - `owner_role`
  - `due_at`
  - `created_by`
  - `status`

- `audit_events`
  - `id`
  - `actor_id`
  - `actor_role`
  - `account_scope`
  - `event_type`
  - `tool_name`
  - `request_payload`
  - `result_summary`
  - `created_at`

- `model_usage_events`
  - `id`
  - `conversation_id`
  - `actor_id`
  - `task_type`
  - `provider`: `openai`, `huggingface`, `local`
  - `model_name`
  - `input_tokens`
  - `output_tokens`
  - `estimated_cost_usd`
  - `latency_ms`
  - `routing_reason`
  - `created_at`

## 6. Access Control Architecture

### 6.1 Mocked Authentication

For assessment speed, authentication can be mocked through a UI identity selector:

Customer users:

- `northstar_user`
  - role: `customer`
  - account_id: Northstar Logistics
- `lumenworks_user`
  - role: `customer`
  - account_id: LumenWorks

Internal users:

- `support_agent`
  - role: `support_agent`
  - allowed account access: all accounts
  - allowed actions: create escalation, create follow-up task, update ticket notes/status
- `ops_manager`
  - role: `ops_manager`
  - allowed account access: all accounts
  - allowed actions: support actions plus dashboard review
- `read_only_analyst`
  - role: `read_only_analyst`
  - allowed account access: all accounts
  - allowed actions: none

### 6.2 Enforcement Principle

Access control must be enforced in backend tools and data access functions, not only in the prompt.

Every tool receives a `UserContext` object:

```text
UserContext
    user_id
    role
    account_id
    allowed_account_ids
    allowed_actions
```

Every data access method checks:

- Is the user allowed to query this account?
- Is the requested order/ticket owned by an allowed account?
- Is the requested document globally visible, internal-only, or customer-specific?
- Is the requested action allowed for this role?

Customer-facing restrictions:

- Customers can only access their own orders, tickets, account terms, and general policies.
- Customers cannot access other customer agreements.
- Customers cannot see internal notes, cross-account ticket clusters, or internal dashboard findings.

Internal restrictions:

- Internal users require a support/ops role.
- Read-only internal users can query but cannot create/update records.
- All state-changing attempts are logged.

### 6.3 Enterprise Identity and Tenant Lifecycle

Production should replace mocked auth with enterprise identity controls.

Identity:

- SSO through OIDC/SAML.
- SCIM user provisioning for enterprise customers.
- Tenant-specific identity provider configuration.
- MFA enforcement for internal/admin users.
- Service accounts for integrations with scoped API keys.

Tenant lifecycle:

- Tenant creation and provisioning workflow.
- Tenant admin role.
- User invite/deactivate workflow.
- Role templates by tenant.
- Per-tenant feature flags.
- Per-tenant model/provider policy.
- Per-tenant data retention policy.
- Tenant suspension and deletion workflow.

Tenant administration:

- Manage users and roles.
- Manage integrations.
- View usage and costs.
- Configure escalation rules.
- Upload/retire documents.
- Review audit logs.
- Configure support SLAs and business hours.

### 6.4 Enterprise Authorization Model

Use a combination of RBAC and ABAC.

RBAC examples:

- `customer_user`
- `customer_admin`
- `support_agent`
- `support_manager`
- `ops_manager`
- `compliance_auditor`
- `platform_admin`
- `integration_service_account`

ABAC attributes:

- tenant
- account
- region
- data classification
- support queue
- ticket severity
- action type
- business unit

Authorization decisions should be centralized in a policy layer, with local enforcement inside every data/tool function.

## 7. Agent Architecture

### 7.1 Agent Style

Use a tool-using agent with explicit workflow states:

1. Parse user request.
2. Identify required context:
   - customer or internal
   - account/order/ticket references
   - action request or answer-only request
3. Plan tools.
4. Execute read-only tools.
5. Evaluate source reliability and conflicts.
6. Generate answer or prepare action.
7. If action is needed, ask for confirmation.
8. Execute confirmed action.
9. Return final response with citations, tool trace, and uncertainty notes.

### 7.2 Agent Graph

```text
START
  |
  v
load_user_context
  |
  v
classify_request
  |
  | uses cheap/local/HF model by default
  |
  +--> clarification_needed --> ask_clarifying_question --> END
  |
  v
plan_tool_calls
  |
  | uses deterministic rules first; upgrades model only if ambiguous
  |
  v
execute_read_tools
  |
  v
trust_and_conflict_check
  |
  | rules first; OpenAI only for complex customer-facing conflicts
  |
  +--> insufficient_confidence --> prepare_escalation_option
  |
  v
draft_response
  |
  | cheap model for low-risk internal summaries
  | OpenAI for customer-facing or high-risk final answers
  |
  +--> action_requested_or_recommended --> prepare_pending_action
  |                                         |
  |                                         v
  |                                  ask_confirmation --> END
  |
  v
final_answer
  |
  END

CONFIRMED_ACTION_ENDPOINT
  |
  v
validate_pending_action
  |
  v
execute_state_change_tool
  |
  v
return_action_result
```

### 7.3 Answer Contract

Each agent answer should include:

- Direct answer.
- Brief reasoning.
- Citations/source list.
- Confidence level: `high`, `medium`, `low`.
- Any source conflicts or assumptions.
- Next step if escalation is needed.

Example:

```json
{
  "answer": "Northstar can cancel ORD-1001 without a cancellation fee if ...",
  "confidence": "high",
  "sources": [
    {
      "name": "Northstar Logistics Enterprise Agreement",
      "page": 3,
      "authority": "customer_contract"
    },
    {
      "name": "Cancellation and Service Credit SOP v4",
      "page": 5,
      "authority": "current_sop"
    }
  ],
  "tool_trace": [
    "lookup_order",
    "document_search",
    "calculate_cancellation_fee"
  ],
  "requires_confirmation": false
}
```

## 8. Tool Design

The assessment requires at least three distinct tools. This architecture includes more, while keeping the tool surface clear.

### 8.1 Document Search Tool

Name:

- `document_search`

Purpose:

- Search policies, SOPs, agreements, product docs, and historical ticket context.

Inputs:

- `query`
- `source_types`
- `account_id`
- `include_deprecated`
- `max_results`

Access behavior:

- Customer users can search general current docs and their own agreement.
- Internal users can search all docs based on role.
- Deprecated docs are excluded by default unless the trust layer asks for conflict analysis.

Ranking:

1. Vector similarity.
2. Source authority score.
3. Current status over deprecated.
4. Customer-specific agreement over general policy when account-specific terms apply.

Output:

- Relevant chunks with citations and source metadata.

### 8.2 Structured Lookup Tool

Name:

- `lookup_record`

Purpose:

- Find accounts, orders, and tickets.

Inputs:

- `record_type`: `account`, `order`, `ticket`
- `identifier`
- `account_id`, optional

Access behavior:

- Verifies account ownership before returning records.
- Returns an authorization error if the record belongs to another account.

Output:

- Normalized record fields.
- Relevant raw fields for audit.

### 8.3 Calculation Tool

Name:

- `calculate_policy_outcome`

Purpose:

- Calculate cancellation-fee eligibility, service-credit eligibility, SLA breach risk, or delay duration.

Inputs:

- `calculation_type`
- `order_id`
- `ticket_id`
- `policy_context`
- `snapshot_time`

Examples:

- pickup delay duration
- SLA age
- cancellation window
- service credit amount or eligibility

Output:

- Calculated values.
- Formula/logic used.
- Required source references.

### 8.4 Ticket Search and Pattern Tool

Name:

- `search_tickets`

Purpose:

- Query support activity by category, severity, account, product issue, time range, or SLA risk.

Inputs:

- `filters`
- `group_by`
- `sort`
- `limit`

Output:

- Matching tickets.
- Aggregations if requested.

### 8.5 State-Changing Action Tools

State-changing tools must never execute immediately from the first model response.

#### `prepare_escalation`

Creates a pending action, not a real escalation.

Inputs:

- `ticket_id`
- `account_id`
- `reason`
- `priority`
- `recommended_owner`

Output:

- `pending_action_id`
- confirmation summary

#### `create_escalation`

Executes only after explicit user confirmation.

Inputs:

- `pending_action_id`
- `confirmation_token`

Output:

- created escalation record

#### `prepare_follow_up_task`

Creates a pending follow-up task.

#### `create_follow_up_task`

Executes confirmed follow-up task.

#### `prepare_ticket_update`

Creates a pending ticket update.

#### `update_ticket`

Executes confirmed ticket update.

### 8.6 Confirmation Pattern

For any state-changing request:

1. Agent gathers evidence.
2. Agent proposes the action.
3. Backend stores a pending action with a short expiry.
4. UI shows a confirmation dialog.
5. User clicks Confirm.
6. Backend validates pending action, permissions, and expiry.
7. Backend executes action and logs it.

The model cannot bypass this because write tools are only exposed through the confirmation endpoint.

## 9. Source Reliability and Conflict Handling

### 9.1 Authority Ranking

Highest to lowest:

1. Customer-specific signed agreement for the account.
2. Current SOP.
3. Current support policy.
4. Product operations guide and known issues.
5. Structured operational data from workbook.
6. Historical ticket resolutions.
7. Deprecated policy.

Notes:

- Structured data is operationally authoritative for order/ticket facts.
- Contracts/SOPs/policies are authoritative for rule interpretation.
- Historical tickets are never normative; they are only examples or context.
- Deprecated policy is only used to explain possible conflict or stale guidance.

### 9.2 Conflict Rules

When sources disagree:

- Customer agreement overrides general policy for that customer.
- Current docs override deprecated docs.
- SOP controls operational workflow if policy is broad and SOP is specific.
- Structured order/ticket data controls factual status.
- Historical ticket resolution cannot override current policy or agreement.

### 9.3 Confidence Model

High confidence:

- Relevant current source found.
- No conflict with higher authority source.
- Structured record is present and access-authorized.
- Calculation inputs are complete.

Medium confidence:

- Answer is supported, but one input is ambiguous or indirect.
- Multiple sources align but no customer-specific agreement applies.

Low confidence:

- Missing key record.
- Conflicting sources with no clear override.
- Request needs human judgment or unsupported exception.
- User asks for an action outside available tools.

Low-confidence responses should recommend escalation.

### 9.4 Model Governance and Risk Controls

Enterprise AI systems need governance around prompts, models, evals, and releases.

Controls:

- Version every prompt, tool schema, retrieval policy, and model routing policy.
- Store the exact prompt/template version used for each answer.
- Track model provider, model name, token usage, cost, latency, and fallback reason.
- Maintain golden evaluation sets for customer-facing, internal, access-control, and action workflows.
- Block production rollout if evals regress beyond threshold.
- Use red-team tests for prompt injection, data exfiltration, unsafe actions, and cross-tenant leakage.
- Require approval for changing high-risk prompts or model routing policies.
- Keep a human-review queue for low-confidence, high-impact, or disputed answers.
- Allow support managers to mark answers as correct/incorrect and feed that back into evals.
- Maintain a model/provider risk register covering data handling, reliability, latency, cost, and vendor dependency.

Risk tiers:

| Tier | Example | Required Handling |
| --- | --- | --- |
| Low | General product FAQ with current citation | Cheap model or cached answer allowed |
| Medium | SLA interpretation, service-credit eligibility | Strong retrieval, citations, confidence check |
| High | Contract override, fee decision, state-changing recommendation | OpenAI or approved premium model, strict citations, escalation if uncertain |
| Critical | Legal dispute, refund execution, customer data export/deletion | Human review required |

### 9.5 Human-in-the-Loop Review

Human review is required for:

- Low-confidence answers.
- Conflicting high-authority sources.
- Customer-visible answers involving material financial impact.
- Requests that require unsupported exceptions.
- Critical compliance or deletion/export actions.
- Repeated user disputes.

Review queue fields:

- conversation ID
- tenant/account
- user role
- proposed answer/action
- source citations
- confidence
- risk tier
- reviewer decision
- corrected answer/action
- reason code

Reviewer outcomes should become evaluation cases so the platform improves without blindly trusting historical resolutions.

## 10. Multi-Step Example Flow

Question:

> Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.

Flow:

1. User context:
   - Customer user scoped to Northstar, or internal user asking about Northstar.
2. `lookup_record(order, ORD-1001)`
   - Confirms account ownership.
   - Retrieves order dates/status/carrier/service level.
3. `document_search`
   - Search Northstar agreement for cancellation terms.
   - Search current cancellation SOP.
   - Search current support policy if needed.
4. `calculate_policy_outcome`
   - Apply cancellation window and fee rules.
5. Trust layer:
   - Agreement overrides general policy.
   - Deprecated policy ignored unless conflict explanation needed.
6. Response:
   - Yes/no answer.
   - Explain calculation.
   - Cite agreement and SOP.
   - Say whether human escalation is needed.

## 11. Proactive Issue Detection

### 11.1 Dashboard Features

Internal dashboard sections:

- SLA risk queue
  - High-severity tickets approaching or exceeding SLA.
- Recurring issue clusters
  - Similar tickets grouped by category, known issue, carrier, route, or error text.
- Customer impact view
  - Accounts with multiple active tickets or repeated operational failures.
- Unusual activity
  - Spikes in complaints by category or carrier compared with dataset baseline.
- Recommended actions
  - Escalate, create follow-up, investigate known issue, contact carrier.

### 11.2 Detection Methods

Initial implementation:

- Rule-based thresholds.
- SQL aggregations.
- Simple text similarity over ticket descriptions/resolutions.
- SLA age calculations using workbook snapshot time.

Examples:

- `severity = high AND sla_due_at < snapshot_time + 2 hours`
- `same category appears >= 3 times in 24 hours`
- `same order/carrier issue affects multiple accounts`
- `ticket open time exceeds SLA threshold`

Later implementation:

- Time-series anomaly detection.
- Embedding-based clustering.
- Root-cause summarization.
- Alert routing to Slack/email/Jira.

## 12. API Architecture

### 12.1 Backend Endpoints

```text
POST /api/chat
    Send message to agent.

POST /api/actions/confirm
    Confirm and execute pending state-changing action.

GET /api/conversations/{conversation_id}
    Fetch conversation history.

GET /api/dashboard/issues
    Fetch proactive issue findings.

GET /api/dashboard/sla-risk
    Fetch tickets approaching/exceeding SLA.

POST /api/ingest
    Development/admin ingestion endpoint, disabled or protected in hosted demo.

GET /api/health
    Health check for deployment.
```

### 12.2 Frontend Routes

```text
/
    Main app shell with identity selector.

/chat/customer
    Customer-facing chat.

/chat/internal
    Internal operations chat.

/dashboard
    Proactive issue detection dashboard for internal users.

/audit
    Optional internal audit/tool trace view.
```

### 12.3 Enterprise Integration Architecture

The platform should support integrations without coupling the agent directly to third-party systems.

Integration patterns:

- REST APIs for synchronous lookups and actions.
- Webhooks for ticket updates, escalation events, and document ingestion completion.
- Event bus topics for asynchronous customer activity.
- Batch import/export through object storage.
- Connector framework for CRM, ticketing, warehouse, and carrier systems.

Likely integrations:

- Zendesk, Intercom, Freshdesk, Salesforce Service Cloud.
- Slack, Microsoft Teams, email.
- Jira/Linear for engineering issues.
- Snowflake/BigQuery/Databricks for analytics exports.
- S3/GCS/Azure Blob for documents and logs.
- Carrier APIs for live shipment state in future production.

Connector design:

- Each connector runs as an isolated worker or service.
- Connector credentials are tenant-scoped and stored in a secret manager.
- Connector actions are idempotent.
- Webhook events are verified with signatures.
- Failed events go to a dead-letter queue.
- All external writes are audited.

### 12.4 Public Platform APIs

Enterprise customers may need APIs beyond the web UI.

```text
POST /v1/chat/sessions
POST /v1/chat/sessions/{id}/messages
POST /v1/actions/{pending_action_id}/confirm
GET  /v1/audit/events
GET  /v1/usage
POST /v1/documents
GET  /v1/documents/{id}/status
POST /v1/integrations/webhooks/{provider}
GET  /v1/admin/tenants/{tenant_id}/users
```

API requirements:

- Versioned APIs.
- Idempotency keys for writes.
- Pagination and filtering.
- Request signing for webhooks.
- Per-tenant API keys/service accounts.
- OpenAPI specification.
- Backward-compatible deprecation policy.

## 13. UI Plan

### 13.1 App Shell

Top bar:

- ParcelPilot Support AI
- User context selector
- Account/role badge
- Link tabs: Customer Chat, Internal Chat, Issue Dashboard

### 13.2 Chat Interface

Main elements:

- Message thread.
- Prompt input.
- Tool activity rail showing:
  - document search
  - order lookup
  - ticket lookup
  - calculations
  - pending action
- Source/citation panel.
- Confirmation modal for actions.

The interface should visibly show tool use because the assessment asks for it and because it improves trust.

### 13.3 Dashboard

Internal dashboard layout:

- SLA Risk table.
- Recurring Issues list.
- Account Impact table.
- Suggested Actions column with confirm-required buttons.

Avoid a marketing-style landing page. The first screen should be the actual usable app.

## 14. Deployment Plan

### 14.1 Environments

Local:

- Next.js dev server.
- FastAPI dev server.
- Local Postgres or Docker Compose Postgres with pgvector.

Hosted demo:

- Vercel for frontend.
- Render/Railway/Fly.io for FastAPI.
- Supabase Postgres with pgvector.

### 14.2 Environment Variables

Frontend:

```text
NEXT_PUBLIC_API_BASE_URL=
```

Backend:

```text
OPENAI_API_KEY=
HF_TOKEN=
DATABASE_URL=
APP_ENV=production
ALLOWED_ORIGINS=
MODEL_ROUTING_MODE=cost_aware
OPENAI_DAILY_BUDGET_USD=
OPENAI_REQUEST_BUDGET_USD=
DEFAULT_EMBEDDING_PROVIDER=local
LOCAL_LLM_BASE_URL=
```

Optional:

```text
LOG_LEVEL=
DEMO_AUTH_SECRET=
HF_BILL_TO_ORG=
ENABLE_LOCAL_LLM=false
```

### 14.3 Release Steps

1. Create repository with frontend and backend folders.
2. Add data pack to `data/raw` or document how to place it locally.
3. Build ingestion command:
   - `python -m app.ingest`
4. Provision Supabase Postgres and enable pgvector.
5. Run database migrations.
6. Run ingestion against production database.
7. Deploy FastAPI backend.
8. Configure backend environment variables.
9. Deploy frontend.
10. Configure frontend API base URL.
11. Test required sample questions in hosted environment.
12. Record demo video.

### 14.4 Deployment Topology

```text
Vercel
  Next.js frontend
        |
        | HTTPS
        v
Render/Railway/Fly.io
  FastAPI backend
        |
        | TLS database connection
        v
Supabase
  Postgres + pgvector
```

### 14.4.1 Production Deployment Topology

For millions of requests, the preferred topology is:

```text
Cloudflare/Akamai/Fastly
  CDN + WAF + DDoS protection
        |
        v
API Gateway / Kubernetes Ingress
        |
        +--> frontend service or Vercel-hosted Next.js
        |
        +--> chat-api service
        |       replicas: min 3, autoscaled
        |
        +--> tool-api service
        |       replicas: min 3, autoscaled
        |
        +--> admin-api service
                private/internal access only

Kubernetes / ECS / GKE / EKS
        |
        +--> ingestion-worker deployment
        +--> embedding-worker deployment
        +--> issue-detection-worker deployment
        +--> eval-worker deployment
        +--> local-model-inference deployment, optional GPU/CPU node pool

Managed Services
        |
        +--> Postgres primary + read replicas
        +--> Redis cluster
        +--> Queue/event bus
        +--> Object storage for raw documents and exports
        +--> Secret manager
        +--> Observability stack
```

Minimum replica guidance:

- `chat-api`: 3 replicas across availability zones.
- `tool-api`: 3 replicas across availability zones.
- `workers`: scale from 1 to N by queue depth.
- `local-model-inference`: isolated node pool so model load cannot starve API pods.

### 14.4.2 Multi-Region Strategy

Phase 1:

- Single region, multi-AZ.
- Automated backups.
- Read replicas.
- Infrastructure as code.

Phase 2:

- Active-passive multi-region.
- Warm standby backend and database replica.
- DNS failover.
- Object storage replication.

Phase 3:

- Active-active for read-heavy traffic.
- Tenant-level routing to home region.
- Global CDN and regional model/provider routing.

Recommended DR targets:

- Early production: RPO under 15 minutes, RTO under 2 hours.
- Enterprise production: RPO under 5 minutes, RTO under 30 minutes.

### 14.5 CI/CD

GitHub Actions:

- Lint frontend.
- Type-check frontend.
- Run backend tests.
- Run ingestion validation tests.
- Optionally deploy on push to main.

Minimal workflow:

```text
pull_request:
  - frontend npm test/typecheck
  - backend pytest
  - backend ingestion smoke test

main:
  - deploy frontend through Vercel integration
  - deploy backend through Render/Railway integration
```

Production CI/CD:

- Build immutable container images.
- Run unit, integration, security, and eval tests.
- Generate software bill of materials.
- Scan dependencies and containers for vulnerabilities.
- Deploy to staging automatically.
- Run smoke tests and golden AI evals in staging.
- Promote to production with blue/green or canary rollout.
- Auto-rollback on elevated error rate, latency regression, or eval failure.
- Keep database migrations backward compatible.

### 14.6 Infrastructure as Code

Use Terraform, Pulumi, or AWS CDK for:

- Network/VPC.
- Kubernetes/ECS cluster.
- Databases and replicas.
- Redis.
- Queues.
- Object storage.
- Secrets.
- IAM/service accounts.
- Monitoring alerts.
- DNS and certificates.

All production infrastructure should be reproducible from code.

### 14.7 Rate Limiting and Quotas

Rate limits:

- Per IP.
- Per user.
- Per tenant.
- Per API route.
- Per model provider.

Quotas:

- Daily/monthly OpenAI budget per tenant.
- Daily/monthly total model budget per tenant.
- Max concurrent conversations per tenant.
- Max ingestion jobs per tenant.
- Max document size and upload count.

Abuse controls:

- Prompt injection monitoring.
- Excessive tool-call loop detection.
- Request body limits.
- CAPTCHA or support intervention for suspicious anonymous traffic, if public.

## 15. Security and Privacy

Key controls:

- Backend-only OpenAI API key.
- Backend-only Hugging Face token.
- No secret keys in frontend.
- Tool-layer account authorization.
- Customer agreement filtering by account.
- Audit logs for tool calls and actions.
- Audit logs for model choices and estimated cost.
- Confirmation before all writes.
- Redacted errors to users.
- CORS restricted to frontend domain.
- Prompt includes security guidance, but security does not rely on prompt alone.
- OpenAI budget guardrails so unexpected loops cannot burn through credits.

Production-grade security controls:

- SSO/OIDC integration for internal users.
- Customer authentication through tenant-aware identity provider.
- RBAC and ABAC for internal roles.
- Postgres row-level security for tenant isolation.
- Encryption in transit and at rest.
- Secrets stored only in managed secret stores.
- PII/sensitive-field redaction in logs.
- Prompt-injection and data-exfiltration tests.
- Security headers and strict CORS.
- Dependency and container vulnerability scanning.
- Audit logs immutable or exported to append-only storage.
- Principle of least privilege for service accounts.
- Private networking between backend, database, Redis, and queues.
- Admin APIs on private network or behind zero-trust access.

Compliance-ready controls to add if ParcelPilot sells to larger enterprises:

- SOC 2 evidence collection.
- Data retention and deletion workflows.
- Tenant-specific data export.
- Access review process.
- Incident response policy.
- Vendor risk tracking for model providers.
- DPA and subprocessor documentation.

### 15.1 Data Governance and Lifecycle

Enterprise platform requirements:

- Classify data as public, internal, confidential, restricted, or regulated.
- Tag documents and fields with sensitivity labels.
- Apply field-level redaction for logs, traces, and model prompts.
- Define retention policies by tenant and data type.
- Support tenant data export.
- Support tenant deletion with verifiable purge workflow.
- Support legal hold for selected tenants/accounts/tickets.
- Store immutable audit trails for sensitive actions.
- Keep raw document versions for traceability.
- Track document effective dates and retirement dates.
- Require approval before a new policy version becomes active.

Data lifecycle:

```text
ingest -> classify -> validate -> embed -> publish -> monitor -> retire/archive/delete
```

Deletion behavior:

- Delete or anonymize conversation content according to tenant retention policy.
- Remove embeddings when source chunks are deleted.
- Invalidate caches after deletion.
- Preserve legally required audit metadata when allowed.
- Produce deletion reports for tenant admins.

### 15.2 Data Residency

For enterprise customers, support region-aware deployment.

Controls:

- Tenant home region.
- Region-specific object storage.
- Region-specific database cluster.
- Region-specific model provider policy.
- No cross-region replication for restricted tenants unless explicitly enabled.
- Audit record of where model processing occurred.

### 15.3 Vendor and Model Provider Controls

For every external model/provider:

- Track subprocessor status.
- Track data retention policy.
- Track whether prompts are used for training.
- Track region availability.
- Track uptime/SLA.
- Track fallback provider.
- Track cost limits.

Provider use should be configurable per tenant. Some enterprise tenants may require OpenAI only, local-only inference, or no external model calls for restricted data.

Assessment-specific privacy risks:

- Customer asks about another customer's order.
  - Tool returns authorization error.
- Customer asks for another customer's agreement terms.
  - Retrieval filter excludes other agreements.
- Model tries to answer from memory.
  - System prompt requires supplied sources; answer generator must cite retrieved context.
- Historical ticket says something wrong.
  - Trust layer marks historical ticket as low authority and prevents it from overriding current docs.

## 16. Testing Strategy

### 16.1 Unit Tests

- Document metadata classification.
- Authority ranking.
- Access control filters.
- Model router task classification.
- Model router budget fallback behavior.
- Structured lookup ownership checks.
- Cancellation/service-credit calculations.
- SLA calculations from snapshot time.
- Pending action confirmation flow.

### 16.2 Integration Tests

- Customer cannot access another account's order.
- Internal support can query cross-account data.
- Deprecated policy is not used as primary answer source.
- Customer agreement overrides general policy.
- Escalation requires confirmation before creation.
- Chat request uses multiple tools for cancellation question.
- Simple internal summaries stay on Hugging Face/local model path.
- High-risk customer-facing contract conflicts upgrade to OpenAI.

### 16.3 Evaluation Set

Create a small `evals/questions.yml` file with:

- Known answer questions.
- Access-control attack questions.
- Conflict-source questions.
- Action-confirmation questions.
- Low-confidence/escalation questions.

Evaluate:

- Correctness.
- Citation quality.
- Access-control safety.
- Escalation appropriateness.
- Tool path correctness.

### 16.4 Load and Scale Tests

Use k6, Locust, or Artillery to test:

- Sustained chat traffic.
- Burst traffic.
- Streaming response behavior.
- Rate-limit correctness.
- Redis cache hit rate.
- Database connection pool saturation.
- Queue backpressure.
- Worker autoscaling.
- Model provider timeout/fallback behavior.

Example production readiness gates:

- p95 chat API acknowledgement under 500 ms at target RPS.
- p95 first token under 3 seconds for cached/retrieval-light questions.
- p95 full answer under 15 seconds for multi-tool questions.
- Error rate under 0.5% during steady-state load.
- No unauthorized data leakage in access-control attack tests.
- Confirmed actions are idempotent under retries.

### 16.5 Chaos and Resilience Tests

Test failure modes:

- OpenAI outage.
- Hugging Face outage.
- Redis unavailable.
- Read replica lag.
- Queue backlog spike.
- Slow vector search.
- Worker crash during embedding job.
- Database failover.
- Partial region outage.

Expected behavior:

- High-risk responses escalate instead of guessing.
- Low-risk flows fall back to alternate providers or cached responses.
- Actions remain idempotent.
- Users receive clear degraded-mode messaging.
- Alerts fire before SLOs are materially breached.

## 17. Observability

For the assessment, implement simple observability:

- Log every tool call.
- Log source documents used.
- Log every model call and selected provider.
- Track estimated OpenAI cost per conversation.
- Log confidence level.
- Log escalations and confirmations.
- Store conversation summaries.

Production expansion:

- OpenTelemetry traces.
- LLM cost/latency metrics.
- Per-provider success/error rates.
- Cost saved by using local/Hugging Face models instead of OpenAI.
- Retrieval hit-rate metrics.
- Human escalation outcome tracking.
- Prompt/version audit history.

### 17.1 Production SLOs

Recommended SLOs:

- API availability: 99.9% early production, 99.95% enterprise target.
- Chat request accepted: p95 under 500 ms.
- First token latency: p95 under 3 seconds.
- Full multi-tool answer latency: p95 under 15 seconds.
- Dashboard load: p95 under 2 seconds.
- Unauthorized data exposure: zero tolerated incidents.
- Confirmed action duplicate rate: zero tolerated duplicates.

### 17.2 Dashboards

Operational dashboards:

- API request rate, latency, and errors.
- Tool call latency and errors by tool.
- Retrieval hit rate and empty-result rate.
- Database CPU, locks, slow queries, connections, replica lag.
- Redis memory, evictions, hit rate.
- Queue depth and worker lag.
- Model calls by provider/model/task.
- OpenAI spend, HF spend, local inference utilization.
- Cost per conversation and per tenant.
- Escalation rate and low-confidence rate.

### 17.3 Alerts

Critical alerts:

- API error rate above threshold.
- p95 latency above SLO.
- Database unavailable or replica lag high.
- Redis unavailable.
- Queue depth growing beyond worker capacity.
- Model provider outage or timeout spike.
- OpenAI spend budget exceeded or unusual spend spike.
- Access-control denial spike.
- State-changing action failure spike.

### 17.4 Usage, Billing, and Cost Attribution

Even if ParcelPilot does not directly bill customers by usage initially, enterprise platforms need usage attribution.

Track per tenant:

- chat messages
- conversations
- tool calls
- document searches
- structured lookups
- state-changing actions
- model calls by provider/model
- token usage
- estimated model cost
- storage used
- documents ingested
- dashboard/API calls

Controls:

- tenant monthly budget
- tenant daily budget
- per-model provider caps
- hard and soft quota limits
- alerts at 50%, 80%, 100% budget
- graceful downgrade when budget is exceeded

Cost dashboard:

- cost per tenant
- cost per conversation
- cost by workflow
- OpenAI vs Hugging Face vs local-model savings
- cache savings
- highest-cost users or workflows

### 17.5 Product Analytics

Track whether the platform is useful, not just whether it is online.

Metrics:

- containment rate: resolved without human intervention
- correct containment rate: resolved without later human rework
- escalation precision
- average time to resolution
- support-agent time saved
- customer satisfaction after AI interaction
- percentage of answers with accepted citations
- low-confidence rate
- dispute/reopen rate
- proactive issue detection precision
- incidents prevented or SLA breaches avoided

These metrics should be available by tenant, account, workflow, source type, and model routing policy.

## 18. Implementation Phases

### Phase 1: Foundation

Deliverables:

- Repo structure.
- FastAPI backend.
- Next.js frontend.
- Mock auth/user context.
- Database schema.
- Health checks.

### Phase 2: Data Ingestion

Deliverables:

- PDF extraction.
- Excel workbook loading.
- Snapshot time parsing.
- Source metadata and authority scoring.
- Embeddings into pgvector.

### Phase 3: Tool Layer

Deliverables:

- `document_search`
- `lookup_record`
- `calculate_policy_outcome`
- `search_tickets`
- pending action tools
- confirmed action tools
- audit logging

### Phase 4: Hybrid Model Router

Deliverables:

- OpenAI provider adapter.
- Hugging Face provider adapter.
- Optional local model provider adapter.
- Task-to-model routing policy.
- OpenAI budget guardrails.
- Model usage logging.
- Fallback behavior when HF/local model is unavailable.

### Phase 5: Agent

Deliverables:

- Tool-calling agent.
- Multi-step reasoning.
- Trust/conflict checker.
- Answer formatter with citations.
- Escalation decision logic.
- Per-node model selection through the router.

### Phase 6: UI

Deliverables:

- Customer chat.
- Internal chat.
- Tool trace display.
- Model/provider trace display for internal users.
- Source panel.
- Confirmation modal.
- Internal dashboard.

### Phase 7: Deployment

Deliverables:

- Production database.
- Hosted backend.
- Hosted frontend.
- Seed/ingestion instructions.
- Public repository instructions.

### Phase 8: Final Submission

Deliverables:

- README.
- Architecture note.
- Product note.
- Demo video script.
- AI tool usage note.
- Hosted URL.

### Phase 9: Production Hardening

Deliverables:

- Kubernetes/ECS deployment manifests.
- Horizontal autoscaling policies.
- Redis cache and rate limiting.
- Queue-backed worker architecture.
- Idempotency for state-changing actions.
- Production SLO dashboards.
- Load-test suite.
- Chaos/failure-mode tests.
- Backup and restore procedure.
- Runbooks for common incidents.

### Phase 10: Enterprise Readiness

Deliverables:

- Real SSO/OIDC.
- SAML and SCIM support.
- Tenant admin console.
- Tenant-level quotas and spend controls.
- Tenant-specific retention and export controls.
- Multi-region DR.
- SOC 2 readiness evidence.
- Advanced audit search.
- Human review and QA workflow.
- Connector framework and webhooks.
- Public versioned APIs.
- Data residency controls.
- Model governance and prompt approval workflow.
- Usage attribution and billing dashboards.

### Phase 11: Enterprise Platform Operations

Deliverables:

- Tenant onboarding playbook.
- Tenant offboarding/deletion playbook.
- Incident response runbooks.
- DR restore drills.
- Access review workflow.
- Vendor/model provider review workflow.
- Customer-facing status page.
- Enterprise support SLAs.
- Operational readiness review checklist.
- Quarterly security and AI safety review.

## 19. Proposed Repository Structure

```text
parcelpilot-ai-support/
  README.md
  ARCHITECTURE.md
  PRODUCT_NOTE.md
  AI_TOOL_USAGE.md
  docker-compose.yml
  .env.example

  data/
    raw/
      .gitkeep
    processed/
      .gitkeep

  backend/
    pyproject.toml
    app/
      main.py
      config.py
      auth/
        context.py
        permissions.py
      ai/
        model_router.py
        budgets.py
        task_policy.py
        providers/
          openai_provider.py
          huggingface_provider.py
          local_provider.py
      agent/
        graph.py
        prompts.py
        response_schema.py
        trust.py
      tools/
        document_search.py
        structured_lookup.py
        calculations.py
        actions.py
        ticket_patterns.py
      data/
        ingest_documents.py
        ingest_workbook.py
        chunking.py
      db/
        models.py
        session.py
        migrations/
      api/
        chat.py
        actions.py
        dashboard.py
        health.py
      tests/

  frontend/
    package.json
    app/
      page.tsx
      chat/
        customer/page.tsx
        internal/page.tsx
      dashboard/page.tsx
    components/
      chat/
      dashboard/
      layout/
      common/
    lib/
      api.ts
      types.ts
```

## 20. Key Technical Trade-Offs

### Full RAG framework vs custom retrieval

Decision:

- Use custom retrieval or very thin LlamaIndex integration.

Reason:

- The corpus is small.
- Source metadata, authority ranking, and account filtering are more important than generic RAG abstraction.

### LangGraph vs simple tool-calling loop

Decision:

- Prefer LangGraph if time allows; otherwise implement a deterministic loop.

Reason:

- LangGraph makes confirmation checkpoints and multi-step flows easier to reason about.
- A simpler loop may be faster for the assessment.

### Real auth vs mocked auth

Decision:

- Mock auth for assessment, but enforce permissions in backend tools.

Reason:

- The assessment allows mocked auth.
- The important engineering signal is that data privacy is enforced below the model layer.

### Hosted database vs local files

Decision:

- Use Postgres + pgvector.

Reason:

- Cleaner deployment story.
- One system for relational and vector data.
- Better demonstrates production judgment than in-memory/local-only storage.

### Customer and internal chatbot vs one chatbot

Decision:

- Build both contexts using the same backend agent and different permission scopes.

Reason:

- Demonstrates access control and product breadth.
- Avoids duplicating logic.

### OpenAI-only vs hybrid model routing

Decision:

- Use OpenAI as the premium model path and Hugging Face/local open-weight models for cheaper supporting tasks.

Reason:

- The app can reduce OpenAI spend by keeping classification, retrieval query rewriting, embeddings, clustering, and low-risk internal summaries on cheaper models.
- High-risk customer-facing answers still need the stronger reliability path.
- The model router gives the product a controllable cost/reliability trade-off instead of hard-coding one provider everywhere.

Risk:

- Cheaper models may produce weaker summaries or miss subtle policy conflicts.

Mitigation:

- Deterministic tools and trust rules handle facts and calculations.
- Medium/high-risk cases upgrade to OpenAI.
- The UI and logs expose the model/provider used for each step.
- Evaluation tests verify that privacy, contract override, and action-confirmation behavior do not depend on a weaker model.

### Simple hosted demo vs production-scale architecture

Decision:

- Build the assessment as a compact deployable demo, but design the architecture so it can evolve into a horizontally scalable, multi-tenant production system.

Reason:

- A hiring assessment should be shippable quickly.
- A CTO-grade architecture must show the path from demo to enterprise production without rewriting the core system.

Trade-off:

- Kubernetes, Kafka, multi-region DR, and SOC 2 controls are too heavy for the first submission.
- The code should still isolate concerns cleanly: API, tools, model router, workers, database, auth, and audit.

Production evolution path:

1. Start with one backend service, managed Postgres, Redis, and hosted frontend.
2. Split long-running ingestion and issue detection into workers.
3. Add API gateway, WAF, rate limits, and queues.
4. Split chat API, tool API, and admin API.
5. Add read replicas, partitioning, materialized views, and stronger vector infrastructure.
6. Add multi-region DR and enterprise compliance controls.

### Postgres/pgvector vs dedicated vector database

Decision:

- Start with Postgres + pgvector, then split vector search only when scale requires it.

Reason:

- For early production, one database simplifies permissions, backups, and deployment.
- Tenant-aware filtering is easier to keep correct in one data layer.

Upgrade trigger:

- Vector search becomes a dominant latency or cost bottleneck.
- Corpus grows beyond comfortable Postgres index management.
- Need independent vector scaling, hybrid search, or advanced reranking at high QPS.

### Synchronous agent execution vs queue-backed execution

Decision:

- Keep normal chat streaming synchronous, but move expensive and non-interactive work to queues.

Reason:

- Users expect live chat responses.
- Ingestion, embeddings, proactive detection, evals, and notifications should not compete with chat latency.

Production rule:

- Any operation that can take more than a few seconds and does not need to block the user should run asynchronously.

## 21. Demo Video Plan

Target duration: approximately 5 minutes.

### 0:00-0:45 Architecture

- Explain frontend, backend, agent, tool layer, database, and source reliability.

### 0:45-2:00 Customer Chat Demo

- Select Northstar customer.
- Ask cancellation question for an order.
- Show tool trace and citations.
- Show answer explaining agreement/SOP precedence.

### 2:00-3:10 Access Control Demo

- Ask Northstar user about LumenWorks order/agreement.
- Show refusal caused by backend authorization.

### 3:10-4:10 Internal Operations Demo

- Select support agent.
- Ask for high-severity tickets near SLA breach.
- Show structured lookup/calculation and recommended escalation.
- Confirm action and show created escalation.

### 4:10-5:00 Product/Technical Decisions

- Source authority model.
- Confirmation before actions.
- Trust/conflict handling.
- Proactive issue dashboard.
- What would be built next.

## 22. Product Note Outline

### Chosen Additional Problem

Trust and Reliability.

### How It Is Addressed

- Source authority ranking.
- Deprecated source handling.
- Customer contract override logic.
- Historical tickets treated as context only.
- Confidence levels.
- Escalation on uncertainty.
- Citations and visible tool trace.

### What Else I Would Build

Priority 1:

- Human-in-the-loop review queue for low-confidence answers and escalations.

Priority 2:

- Feedback loop from resolved escalations into evaluation datasets.

Priority 3:

- Slack/email/Jira integrations for operational alerts.

Priority 4:

- Admin console for uploading new policies and managing effective dates.

Priority 5:

- More advanced issue clustering and trend detection.

### Intentionally Left Out

- Real SSO/auth provider.
- Real carrier API integrations.
- Automatic refunds/credits.
- Production-grade admin controls.
- Advanced anomaly detection models.

### Success Metric

Primary metric:

- Percentage of support requests correctly resolved or routed without human rework.

Supporting metrics:

- Average response time.
- Escalation precision.
- Citation acceptance rate by support agents.
- Unauthorized-data exposure rate, target zero.

## 23. Build Priority Recommendation

If time is limited, build in this order:

1. Internal chatbot with strong tool layer.
2. Customer chatbot using the same tools with stricter account scope.
3. Source reliability and conflict handling.
4. Confirmation-based escalation action.
5. Dashboard for proactive issue detection.
6. Hosted deployment and demo polish.

This order maximizes the assessment signal: agent design, data reasoning, security, multi-step workflows, and deployment readiness.
