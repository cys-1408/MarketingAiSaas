# Marketing Intelligence and Campaign Copilot SaaS (MarketingAiSaas)

A multi-tenant SaaS that turns raw marketing exports (CSV/XLSX/PDF/DOCX/CSV
feedback) into cited, evidence-linked investigations about campaign
performance: deterministic analytics, retrieval-augmented chat with
abstention instead of guesswork, an evidence graph, and exportable reports.

This README describes the implementation that exists today. Every claim
below is backed by the automated suite:

```bash
APP_SESSION_SECRET='test-secret-0123456789abcdef' \
APP_ENVIRONMENT=test \
APP_INGEST_WORKER_ENABLED=false \
APP_MODEL_MODE=mock \
python -m pytest tests -q            # 80 checks pass
```

## 1. Product purpose and feature scope

- **Workspaces & roles:** sign up → own workspace; invite members with
  roles (`viewer`, `analyst`, `marketer`, `admin`, `owner`) mapped to
  capability ranks; login resolves the most recently joined membership.
- **Source ingestion:** upload spreadsheet/document/CSV sources; the
  pipeline inspects, classifies, proposes field mappings (with a human
  review queue when a column is ambiguous), normalizes rows, persists
  metrics/feedback with provenance, chunks + indexes text, and updates the
  campaign evidence graph — all as recorded workflow stages per job.
- **Analytics:** every metric is a deterministic sum/derivation over stored
  rows in the requested window, each carrying unit, definition and
  zero-spend-safe limitations. Derived metrics (e.g. CTR = clicks /
  impressions) never claim a division that has no denominator.
- **Investigation chat:** asks grounded questions; answers cite stored
  evidence, mark themselves `ai_generated: true`, include a measurement
  plan, and **abstain** when evidence is insufficient rather than
  fabricating claims.
- **Evidence graph:** campaigns ↔ metrics ↔ feedback ↔ objections linked
  per source version, explorable via `/graphs/paths`.
- **Reports:** evidence-linked generated reports over a campaign window.
- **Local model connector:** pair a local Ollama machine via one-time
  codes; inference requests queue per workspace and are claimed outbound
  by the connector. Tenants cannot receive each other's requests.
- **Semantic cache:** answer caching invalidated by permission rank,
  source versions, metric-definition versions, model/prompt versions;
  proven tenant-isolated.

## 2. Architecture and request/data flow

```
frontend (React/Vite; currently served with mock fixtures)
  └─► FastAPI app (app/main.py, routes under /api/v1)
        ├─ app/api/*        auth, workspaces, uploads, ingestion jobs,
        │                   campaigns, chat, evidence, reports, models,
        │                   integrations, evaluations
        ├─ app/ingestion/*  inspection → classification → mapping →
        │                   normalization → validation → persistence →
        │                   chunk/index → graph (stage-tracked jobs)
        ├─ app/tools/*      analytics, feedback, products, report,
        │                   verification (shared by API + agents + MCP)
        ├─ app/retrieval/*  chunk fingerprints, embeddings, BM25, hybrid fusion
        ├─ app/graph/*      node/edge construction, evidence paths
        ├─ app/agents/*     LangGraph-style investigation workflow
        ├─ app/models/*     router (mock | local connector), Ollama channel
        ├─ app/connectors/* GA4/Mailchimp OAuth + sync framework
        ├─ app/cache/*      semantic answer cache with validity fingerprint
        └─ SQLAlchemy → SQLite (dev/tests) or PostgreSQL (compose/prod)
```

Uploads are stored on disk under `APP_OBJECT_STORAGE_DIR`; jobs run in a
worker thread in the API process (tests disable the worker and drive
stages synchronously for determinism).

## 3. Supported file types and source pipeline

Supported declared types: `csv`, `tsv`, `xlsx`, `pdf`, `docx`, `md`,
`txt`, `html`, `json`. Inspection sniffs magic signatures; Office zip
containers (xlsx/docx share the `PK` header) retry the declared type once
before rejecting a bad file. Rejected cleanly: empty files, oversized
payloads/rows/cells/pages, mislabeled content (e.g. fake `.xlsx`).

Pipeline stages per job: `queued → inspecting → mapping
[→ awaiting_review] → normalizing → validating → persisting → chunking →
indexing → graph → ready | partially_ready | failed`. Duplicate identical
uploads reuse the existing **active** source (idempotent); deleted sources
can be re-uploaded as new ones. Reprocessing creates a new source version
and replaces prior-version vectors instead of duplicating them.

## 4. Canonical entities and metric-contract principles

Canonical schemas live in `app/models/domain.py` (single source of truth:
field names, aliases, kinds). The frontend never invents metric semantics;
it consumes what the backend computes from these definitions.

- Stored metrics: `campaign + day + metric_name → value/unit/definition`
  with `source_id`, `source_version`, raw-row provenance.
- Base metrics persist their definition (e.g. "count of clicks recorded");
  derived metrics carry their formula ("clicks / impressions").
- Every answer, metric and recommendation must be supported by evidence or
  clearly labeled as a hypothesis/limitation.

## 5. Workspace setup, roles, and tenant security

Signup creates user + workspace + owner membership. `/workspaces/{id}/members`
adds members (re-invite updates an existing member's role and is audited).
Role → capability matrix in `app/core/security.py`: ingest/mapping/report
actions need analyst+, deletion needs admin+, member/integration management
needs owner. All record reads are tenant-scoped; probing another tenant's
ids yields the same "not found" behavior as unknown ids. The cache
fingerprint includes the caller's permission rank so a viewer cannot be
served an owner's cached answer.

## 6. Environment variables and secret handling

All configuration comes from environment variables (or `.env`), namespaced
`APP_*`, matching `app/core/config.py` field-for-field; see
`.env.example` with explanations of required vs optional values.

Secrets (session secret, hosted API key, OAuth client secrets) are never
hardcoded, never logged (values are excluded/redacted from log records),
and stored provider credentials are encrypted at rest with an HMAC-verified
payload (tamper detection; redacted previews expose field names only).
In production set `APP_SESSION_SECRET` (≥16 chars; the default is rejected
outside development).

## 7. Local services and Docker Compose startup

Zero-infra default: SQLite + on-disk object storage; no services needed.

With Compose (production-like local run):

```bash
docker compose up -d postgres          # DB with health check + volume
docker compose up -d api --build       # API on :8000, env from compose file
docker compose run --rm api alembic upgrade head   # migrations (when added)
docker compose down -v                 # stop and reset volumes
```

Credentials in the compose file are local-only defaults, documented and
overridable. Health is proven by `/ready` (actually probes the database),
not by container status. The customer's Ollama connector is intentionally
**not** a Compose service: it pairs outbound from the user's own machine.

## 8. Database migration and demo-data loading

Development/test sessions create schema via `Base.metadata.create_all`;
Alembic is the declared production migration tool (run `alembic init
alembic` and cut the first revision before any shared deployment).

Synthetic demo sources live in `data/synthetic_demo/` and evaluation cases
in `evals/` — all clearly labeled synthetic; they are never presented as
customer data.

## 9. Backend startup

```bash
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
# Health: /health (liveness), /ready (DB + model + integrations truth)
```

## 10. Tests, lint, type-check, evaluation

```bash
python -m pytest tests -q                       # full suite (80 checks)
python -m pytest tests/unit -q                  # unit slice
python -m ruff check app tests                  # lint
evals/README.md                                 # evaluation case format
```

Negative-path coverage includes malformed/oversized files, ambiguous
conversion columns (paused for review), duplicate uploads, source-version
vector replacement on reprocess, cross-tenant access, prompt injection,
empty retrieval, OAuth state replay/expiry, expired credentials,
token/MAC tampering, and hosted fallback without consent.

Provider smoke tests are opt-in and credential-gated — never run against
live providers in CI, and never using production secrets.

## 11. Configuring a real provider integration

Set both client id and secret (see `.env.example`); until then the UI
shows a truthful "not configured" state. GA4: `APP_GOOGLE_ANALYTICS_*`.
Mailchimp: `APP_MAILCHIMP_*`. The OAuth contract (state hashing + one-time
use + expiry + PKCE + encrypted token persistence + safe disconnect) is
implemented and tested; live sync behavior depends on each provider's
current API and is documented in the connector capability matrix inside
`app/connectors/providers`.

## 12. Installing/pairing/using/revoking the local Ollama connector

1. Set `APP_MODEL_MODE=ollama`.
2. In the app, begin pairing → a one-time 8-character code is shown once
   (hashed at rest; expires in minutes).
3. Run the connector on the machine running Ollama and submit the code
   (outbound connection only; no inbound ports). The connector receives a
   revocable access token and selects its model.
4. The router now sends inference requests for that workspace through the
   queue; only that workspace's requests are claimable by that connector.
5. Revoke from Settings at any time.

Privacy statement: **local inference is distinct from cloud storage.**
When the paired local connector is used, retrieved context is sent to the
customer's own machine for inference. Hosted fallback is off by default,
requires explicit opt-in (`APP_ALLOW_HOSTED_FALLBACK=true`) plus a fully
configured provider, and is never switched to silently. Failure surfaces
as an explicit "local model unavailable" condition.

## 13. Source deletion / reprocessing

`DELETE /api/v1/ingestion/sources/{id}` removes the source's metrics,
feedback, graph contributions and vectors, cancels all of its job records,
and deletes the campaigns it created (audit-recorded). `POST
.../reprocess` creates a new version job; on completion prior-version
vectors are replaced, not accumulated. Deletion is logical for the source
row (`deleted_at`) while dependent data is physically removed.

## 14. Demo flow

Sign up → upload `data/synthetic_demo/*.csv` → confirm/auto-accept
mappings → open Analytics (deterministic golden values) → ask a
grounded investigation question → explore the evidence graph → generate a
report → reprocess and delete the source to observe version/cleanup
propagation. An equivalent scripted journey exists as
`tests/e2e/test_critical_journey.py`.

## 15. Security considerations and production checklist

- Change `APP_SESSION_SECRET` to a long random value in production.
- Use PostgreSQL (`APP_DATABASE_URL`), run Alembic migrations, and back up
  both the database and `APP_OBJECT_STORAGE_DIR` together.
- Keep `APP_INGEST_WORKER_ENABLED=true` in any shared deployment (tests
  disable it for determinism only).
- All logs are single-line JSON with correlation ids and secret redaction;
  error tracebacks are preserved for diagnosis.
- Rate limits: 120 req/min general, 20/min on chat (configurable).
- Before go-live: real provider credentials in a secret manager, HTTPS
  termination, CORS restricted to known origins, and `APP_ENVIRONMENT !=
  development` (which refuses the default session secret).

## 16. Known limitations

- The React frontend is feature-complete against mock fixtures; wiring it
  to the real `/api/v1` backend is the main remaining integration task
  (tracked in `PLAN.md`).
- Alembic revisions have not been cut yet (schema is created
  programmatically for dev/test).
- Google Analytics / Mailchimp live sync requires real developer
  credentials; the connector contract and tests cover the full flow with
  local fixtures only.
