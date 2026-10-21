# Implementation tracker

Converts `procedure.md` phases into a traceable checklist. Status is
reflected from actual repository state: an item is **done** only when the
implementation exists and the automated suite covering it passes; otherwise
it is listed under **open** with its dependency.

Verification command (backend suite, 80 passing checks):

```bash
APP_SESSION_SECRET='test-secret-0123456789abcdef' \
APP_ENVIRONMENT=test \
APP_INGEST_WORKER_ENABLED=false \
APP_MODEL_MODE=mock \
python -m pytest tests -q
```

## Phase checklist

| Phase | Scope | Status | Evidence |
| ----- | ----- | ------ | -------- |
| 1 Application skeleton & configuration | `app/main.py` (`create_app`), `app/core/config.py` with typed `APP_*` settings, `.env.example` matching settings exactly | done | `.env.example` mirrors every `Settings` field; config tests in `tests/unit` |
| 2 Persistence & tenancy | SQLAlchemy models (`app/db/models.py`), session factory, workspace/user/membership rows, tenant-scoped query helpers (`app/core/tenancy.py`) | done | `tests/api/test_auth_and_workspaces.py`, `tests/security/test_tenant_isolation.py` |
| 3 Auth & roles | signup/login/logout/me, role ranks + capability matrix (`app/core/security.py`), session tokens hashed at rest | done | `tests/api/test_auth_and_workspaces.py`, `tests/security/test_tenant_isolation.py` |
| 4 Upload & inspection pipeline | upload endpoint (size/type/empty checks), content sniffing incl. xlsx↔docx PK-container fallback, parser registry (csv/tsv/xlsx/docx/pdf/md/txt/html/json) | done | `tests/integration/test_ingestion_pipeline.py` (`test_empty_and_oversized_rejections`, `test_mislabeled_file_rejected_cleanly`, `test_docx_pdf_txt_ingestion`) |
| 5 Classification, mapping review, normalization | deterministic category classifier, mapping proposals with auto-accept only for unambiguous columns (incl. ambiguous `conv_*` conversion columns paused for review), persisted versioned mapping rules, pipeline stages recorded per job | done | `tests/unit/test_mapping_and_validation.py`, `tests/integration/test_ingestion_pipeline.py` (mapping-review pause/resume tests) |
| 6 Analytics contract | metric totals in the date window, derived metrics (CTR etc.) with citations-ready definitions and explicit limitations, campaign compare, campaign list | done | `tests/integration/test_analytics_and_retrieval.py` (golden values: 1000+1100 impressions, 105/2100 CTR) |
| 7 Retrieval & evidence graph | chunking + 256-dim hash embeddings + vector index, BM25 lexicon candidates, hybrid fusion, tenant-scoped filtering, graph nodes/edges per source, source-versionized vectors, delete/reprocess replaces instead of duplicating | done | `tests/integration/test_analytics_and_retrieval.py` (`test_hybrid_retrieval_tenant_scoped`, `test_vectors_deleted_for_source_update`), `tests/unit/test_retrieval_units.py` |
| 8 Agentic investigation workflow | LangGraph state workflow: retrieve → observe → analyze (verify) → plan → answer; abstention instead of unsupported claims; citations + measurement plan persisted; AI-generated flag honored on responses | done | `tests/integration/test_graph_and_chat.py`, `tests/e2e/test_critical_journey.py` |
| 9 Local model connector | pairing codes hashed at rest, outbound-only channel claims, workspace-scoped queue, fail-closed router with explicit hosted-fallback opt-in (`app/models/*`) | done | `tests/security/test_connector_security.py`, `tests/security/test_tenant_isolation.py::test_connector_tokens_are_tenant_bound` |
| 10 Provider connectors (GA4, Mailchimp) | complete OAuth/PKCE contract with encrypted at-rest credentials (MAC-verified, tamper detection), truthful "not configured" states, deterministic dry-run sync fixtures | done, live sync credential-gated | `tests/security/test_connector_security.py`; live-provider calls are NOT available in CI (no credentials) |
| 11 MCP tool server | shared analytics/graph/chat tools exposed through the MCP server (`app/mcp/server.py`) | done | unit coverage in `tests/unit`, integration via chat workflow tests |
| 12 Semantic answer cache | validity fingerprint over permission rank, source versions, metric-definition versions, model/prompt versions (slots-safe field enumeration) | done | `tests/security/test_tenant_isolation.py::test_cache_never_crosses_tenants` |
| 14 Evaluations harness | `evals/` JSONL cases (investigation, mapping, retrieval, security, tool) with metric definitions | present; runner invoked ad hoc | `evals/README.md` |
| 15 Frontend connection | Pages exist for the full journey, but `frontend/src/services` still serves mock fixtures for most pages | **open** (next: swap mock services for the real `/api/v1` client) | `frontend/src/services/mock/fixtures.ts` still imported |
| 16 Docker Compose | Postgres + API with health checks, volumes, documented local-only credentials; SQLite zero-infra alternative | done | `docker-compose.yml` |
| 17 Documentation | README operating guide, this tracker, `.env.example` | done | `README.md`, `PLAN.md`, `.env.example` |

## Known limitations

- **Frontend ↔ backend:** the React app ships with a complete mock data
  layer. Wiring `frontend/src/services/api.ts`-style fetches to `/api/v1` is
  the remaining integration work; no page claims live data until then.
- **Provider integrations:** Google Analytics / Mailchimp connectors
  implement the full OAuth contract and are tested against local fixtures;
  live sync requires real developer credentials, and the UI shows a
  "not configured" state until then. No live connection is faked.
- **Hosted model fallback:** always off unless `APP_ALLOW_HOSTED_FALLBACK`
  is true and the provider triple (id/key/model) is fully configured. The
  router fails closed with `LocalModelUnavailable` otherwise.
- **Vector/BM25 storage:** store-backed (Postgres + pgvector optional);
  tests run on SQLite with the same code paths.
- **Migrations:** schema is managed via `Base.metadata.create_all` at boot
  for local/dev and the test session; Alembic is available as the declared
  migration tool for production rollout (no revision set has been cut yet —
  cut `alembic init` revisions before the first shared deployment).
- **Real-provider smoke tests:** intentionally opt-in and credential-gated;
  they never run in CI and never use production secrets.

## Decisions

- Model routing is `mock` by default for determinism in tests/CI; Ollama
  mode is for the customer's paired local connector.
- Member re-invite is idempotent: adding an existing member updates the
  requested role and is audited, instead of returning a conflicting 409.
- Login selects the most recently joined membership as the active workspace.
- Conversion-like columns (`conv_*` and other weak prefix matches) pause the
  pipeline for human review; exact aliases (e.g. `conv`) auto-accept.
