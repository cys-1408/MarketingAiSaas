# MarketingAiSaas --- Final Implementation Contract

## File-by-file requirements for the complete Marketing Intelligence and Campaign Copilot SaaS

**Reference project:** Marketing Intelligence and Campaign Copilot SaaS\
**Repository root:** `MarketingAiSaas/`\
**Specification source:**
`marketing_intelligence_campaign_copilot_saas_full_spec.md`\
**Status required:** Final, fully implemented, integrated, tested
deliverable for the defined scope --- not a sample, mock-up, UI-only
prototype, or proof of concept.

------------------------------------------------------------------------

# 1. Non-negotiable implementation instructions

Use this document together with the project specification and the
supplied file tree. Preserve the existing structure unless a technically
necessary change is explained and documented. Implement every listed
file according to its responsibility, and make the entire application
work end to end.

## 1.1 What "fully implemented" means

-   Implement the behavior described in the specification, not merely
    the names of technologies.
-   Connect the frontend to the real FastAPI backend and connect backend
    workflows to configured persistence, background jobs, retrieval,
    graph, model, and integration services.
-   All user-facing actions must perform their advertised operation,
    return useful status, handle errors, and persist the appropriate
    state.
-   Every API route must have request/response schemas, authentication
    and authorization where required, validation, stable error behavior,
    and tests.
-   Every ingestion stage must be callable in the real pipeline and
    record its status, outcome, and safe diagnostics.
-   All important records must have stable IDs, tenant/workspace
    ownership, provenance, timestamps, and source/version lineage as
    applicable.
-   Every factual answer, metric, recommendation, and generated product
    claim must be supported by evidence or clearly labelled as a
    hypothesis/uncertain result.
-   Use migrations or a documented schema-management approach for
    persistent relational data. Do not rely on in-memory dictionaries as
    the application database.
-   Implement meaningful automated tests and an end-to-end smoke test. A
    service being installed or a screen rendering is not proof that the
    feature works.
-   Document environment variables, setup, migrations, service startup,
    local model setup, supported integration setup, tests,
    troubleshooting, and operational limitations.
-   Handle empty data, malformed inputs, expired credentials, provider
    errors, timeouts, cancellation, partial failures, retry, stale
    indexes, and source deletion.
-   Do not claim an integration, metric, model capability, or provider
    field works until its implementation and tests demonstrate that it
    does.
-   Use dependency injection or clear service boundaries so files can be
    tested without requiring every external service for every unit test.
-   Use typed interfaces, schemas, error types, and explicit
    configuration. Avoid unstructured dictionaries where a domain model
    or schema is appropriate.

## 1.2 No hardcoded behavior or unfinished work

Do not leave TODOs, FIXMEs, placeholder implementations, fake success
responses, `pass` bodies, empty event handlers, demo-only branches
presented as real features, unimplemented buttons, or comments promising
a future implementation.

Do not hardcode tenant IDs, user IDs, credentials, OAuth tokens, API
keys, model responses, campaign metrics, file paths, provider responses,
source IDs, chart values, or "successful" job statuses. Use
configuration, persisted records, provider APIs, deterministic
calculations, and properly scoped test fixtures.

Allowed exceptions: - Synthetic data can exist in
`data/synthetic_demo/`, test fixtures, and evaluation datasets. Label it
as synthetic everywhere it is shown to users. - Static product copy,
navigation labels, icons, design tokens, enum values, and protocol
constants may be defined in code. - A documented provider capability
matrix may identify unsupported provider features. The UI must not
falsely imply unsupported functionality is active. - Test doubles and
mocks are allowed in tests, but must never be used as the production
implementation. - The frontend may use loading, empty, error, and
disabled states; these must reflect real backend state and actual
capability.

If a third-party provider requires credentials or a developer account
that is not available in the build environment, implement the complete
connector contract and OAuth/sync logic, add a documented configuration
path and automated tests, and show a clear "not configured" state until
credentials are supplied. Never fake a live connection.
Provider-specific functionality must respect the provider's current API
and terms.

## 1.3 Required product boundaries

-   This is a multi-tenant SaaS. Every query and operation must enforce
    server-side tenant/workspace authorization.
-   Uploaded files and live integrations must enter the same canonical
    data and downstream indexing/graph pipeline.
-   Automatically accept mappings only when confidence, deterministic
    validation, and semantic checks justify it. Put consequential
    ambiguity into a review queue.
-   Never silently reinterpret an unknown conversion field as a purchase
    or merge metrics whose definitions differ.
-   Never present correlation as proof of causation. Mark
    interpretations and proposed explanations as hypotheses unless
    supported by an appropriate experiment.
-   Never invent missing values, performance improvements, source
    citations, customer statements, product facts, or evaluation scores.
-   The initial Ollama mode means local inference on the customer's
    computer while SaaS data services remain cloud-hosted. Do not
    describe it as fully offline or fully on-device.
-   The local connector must make authenticated outbound TLS
    connections; do not expose the customer's Ollama API publicly or
    require inbound router ports.
-   Hosted-model fallback must be disabled unless the user explicitly
    opts in. Never silently switch from local inference to a hosted
    model.
-   Do not publish content, send campaigns, alter audiences, or change
    live provider settings without explicit authorization and approval.
-   Retrieved files and source text are untrusted input. They must not
    override system instructions or authorize tools.
-   The first release can use a modular monolith and background workers;
    do not create needless microservices merely to demonstrate a
    technology.

## 1.4 Required implementation evidence

For each feature, provide: 1. Unit tests for the underlying logic. 2.
Integration tests for database/provider/service interactions where
applicable. 3. API tests for authorization, validation, error handling,
and expected responses. 4. Frontend tests for meaningful interactions
and error/loading states where practical. 5. End-to-end tests for
critical user journeys. 6. Logs/metrics that help diagnose failures
without exposing secrets or sensitive source text. 7. Documentation of
configuration, known provider limits, and how to verify the feature.

Do not mark a feature complete just because the code compiles.
Completion requires working behavior and passing tests.

------------------------------------------------------------------------

# 2. Repository-level architecture and ownership

The repository is split into these cooperating areas:

-   `app/`: Python backend, APIs, domain logic, ingestion, connectors,
    retrieval, graph, agent workflow, tools, MCP, and model
    orchestration.
-   `frontend/`: React/TypeScript application, route pages, shared
    components, feature modules, API client, types, and user
    interaction.
-   `data/synthetic_demo/`: clearly labelled synthetic data used for
    repeatable demonstrations and tests.
-   `evals/`: curated, version-controlled
    retrieval/answer/tool/ingestion evaluation datasets and evaluation
    configuration.
-   `tests/`: automated Python tests, integration tests, security tests,
    and end-to-end test support.
-   `.env.example`: documented environment-variable template with safe
    non-secret examples.
-   `docker-compose.yml`: local development services and health checks.
-   `pyproject.toml`: Python project metadata, runtime dependencies,
    development dependencies, tooling, and test configuration.
-   `PLAN.md`: implementation and verification checklist; it must be
    updated to reflect actual state rather than claim unverified
    completion.
-   `README.md`: complete project setup, architecture, configuration,
    tests, integrations, model privacy boundaries, and troubleshooting.
-   `marketing_intelligence_campaign_copilot_saas_full_spec.md`: the
    product specification; retain it as the reference contract.

The backend must have one authoritative implementation for domain rules.
The frontend must not independently invent metric calculations, mapping
decisions, tenant authorization, or evidence validity.

------------------------------------------------------------------------

# 3. Backend: exact file-by-file requirements

## 3.1 Application entry point

### `MarketingAiSaas -> app -> __init__.py`

Must: - Declare the Python package cleanly. - Expose only stable
package-level symbols if there is a real need. - Avoid initializing
network clients, database connections, workers, or model runtimes as an
import side effect. - Keep imports predictable so tests and CLI commands
can import modules safely.

Acceptance: - Importing `app` does not start services or perform network
calls.

### `MarketingAiSaas -> app -> main.py`

Must be the FastAPI application composition root: - Create the FastAPI
app with title, version, description, lifespan handling, and documented
API metadata. - Register all route routers from `app/api/`. - Register
authentication/authorization dependencies, request-ID middleware, safe
exception handlers, CORS from configuration, and structured logging. -
Initialize and close shared resources through lifespan management:
database engine/session factory, object-storage client,
vector/BM25/graph adapters, model router, job backend, and telemetry
exporters where configured. - Expose `/health` for process liveness and
`/ready` for dependency readiness. Liveness must not claim every
dependency is healthy; readiness must report unavailable required
dependencies safely. - Ensure startup fails clearly when a required
configuration is invalid. Optional integrations should be reported as
unconfigured, not treated as connected. - Avoid embedding business logic
in route registration. - Ensure secrets, access tokens, source text, and
prompts are not written to logs by default.

Acceptance: - App starts using documented configuration; OpenAPI
includes all intended routes; readiness responds accurately; shutdown
closes resources; tests can construct the app with test dependencies.

------------------------------------------------------------------------

## 3.2 Core configuration, security, tenancy, and logging

### `MarketingAiSaas -> app -> core -> __init__.py`

Must: - Keep the core package import-safe. - Avoid importing modules in
ways that create circular dependencies. - Export stable shared types
only when useful.

### `MarketingAiSaas -> app -> core -> config.py`

Must: - Define typed settings for environment, API prefix, database URL,
object storage, job queue, vector store, graph store,
embedding/reranking models, model providers, Ollama connector channel,
CORS, upload limits, timeouts, quotas, logging, and telemetry. - Load
configuration from environment variables or a documented settings
source. - Validate required settings at startup and distinguish required
services from optional integrations. - Support separate development,
test, and production configurations without hardcoding credentials. -
Provide safe defaults for local development while never shipping default
production secrets. - Define limits for upload size, file types, row
counts, job duration, agent iterations, graph depth, tool calls, and
request rate. - Avoid printing secret values in validation errors or
logs.

Acceptance: - Invalid settings fail with actionable messages that do not
expose secret contents; `.env.example` maps to actual setting names.

### `MarketingAiSaas -> app -> core -> logging.py`

Must: - Configure structured JSON or similarly parseable logs. - Attach
request ID, tenant/workspace ID when safe, user ID when appropriate, job
ID, integration connection ID, stage name, and correlation/trace IDs. -
Redact credentials, authorization headers, OAuth tokens, API keys, and
sensitive customer text. - Provide consistent error logging and timing
fields. - Ensure prompt content, retrieved excerpts, and generated copy
are excluded from telemetry by default. - Allow diagnostics to identify
which stage failed without exposing the underlying customer content.

Acceptance: - Tests verify redaction and required correlation fields.

### `MarketingAiSaas -> app -> core -> security.py`

Must: - Implement password/session or token verification using a
standard, maintained security library and configured algorithm. -
Implement password hashing if password-based auth is used; never store
plaintext passwords. - Define reusable authentication dependencies and
permission checks. - Validate tokens, expiry, issuer/audience when
applicable, and revocation/session status. - Protect sensitive endpoints
against unauthorized access and apply safe request validation. -
Implement CSRF protections where cookie-based authentication requires
them. - Enforce rate limits and safe error responses for login, password
reset, upload, chat, and expensive operations. - Use short-lived pairing
credentials for local connector pairing and ensure they are
one-time/expiring/revocable. - Never rely on a frontend-only route guard
as authorization.

Acceptance: - Tests cover missing, invalid, expired, revoked, and
insufficient-permission credentials.

### `MarketingAiSaas -> app -> core -> tenancy.py`

Must: - Define the authoritative workspace/tenant resolution and
membership authorization layer. - Verify that the authenticated user
belongs to the requested workspace and has the required
role/permission. - Provide reusable tenant-aware query scopes and
service-level authorization helpers. - Ensure background jobs carry an
explicit tenant/workspace context and re-check authorization/ownership
before acting. - Enforce isolation for relational queries, object
storage paths, vector retrieval, graph retrieval, caches, conversations,
reports, evaluation records, and connector sessions. - Reject
user-supplied tenant IDs that do not match authorized membership. -
Provide role/permission definitions for owner, administrator, analyst,
marketer, reviewer, and read-only viewer (or document a deliberate
equivalent). - Avoid using a tenant ID in metadata as the only security
control.

Acceptance: - Cross-tenant tests prove that another tenant's records
cannot be read, modified, searched, cited, cached, or deleted.

------------------------------------------------------------------------

## 3.3 API route modules

Every route module must use Pydantic request/response models, shared
authentication and tenancy dependencies, service-layer calls, stable
error codes, request IDs, pagination where relevant, and OpenAPI
descriptions. Route files must not contain complex business logic or raw
unrestricted SQL.

### `MarketingAiSaas -> app -> api -> __init__.py`

Must: - Expose router imports only if needed. - Avoid import-time side
effects and circular dependencies.

### `MarketingAiSaas -> app -> api -> routes_auth.py`

Must implement: - Signup and login flows, token/session creation,
logout/revocation, current-user retrieval, and password-reset
request/confirmation if password reset is supported in the UI. - Input
validation, normalized email handling, password policy, generic
authentication errors that avoid account enumeration, rate limiting, and
audit events. - Secure token storage/transport and expiry. - Correct
membership/workspace creation behavior: either create the initial
workspace transactionally during signup or provide a clear onboarding
step. - Responses containing only safe user fields; never return
password hashes or secrets.

Acceptance: - Tests cover duplicate signup, invalid credentials, expired
sessions, logout, password reset expiry, and unauthorized access.

### `MarketingAiSaas -> app -> api -> routes_workspaces.py`

Must implement: - `POST /api/v1/workspaces`,
`GET /api/v1/workspaces/{workspace_id}`, member management, and usage
information. - Workspace creation, membership invitation/addition, role
changes, member removal, and workspace access checks as supported by the
product. - Usage metrics for actual stored/processed records, uploads,
storage, jobs, model requests, and configured quotas. - Audit events for
membership and permission changes. - Transactional consistency when
creating workspaces and their first owner.

Acceptance: - A user cannot inspect or administer a workspace without
authorization; usage numbers come from real records.

### `MarketingAiSaas -> app -> api -> routes_uploads.py`

Must implement: - Secure upload initiation and/or direct upload handling
for CSV, TSV, XLSX, PDF, DOCX, Markdown, TXT, HTML, and JSON where the
relevant parser is implemented. - File extension, MIME type, actual
content signature where practical, size, encoding, and safe filename
validation. - Tenant-owned object storage, source registration,
checksum, source version, uploader, timestamps, and ingestion job
creation. - Upload progress/status if supported by the transport; clear
errors and partial extraction warnings. - Safe handling of archive
bombs, oversized content, malformed files, and potentially malicious
documents. - Idempotency or duplicate-upload detection where
appropriate. - Never trust a client-provided path or store user files at
arbitrary filesystem paths.

Acceptance: - Uploaded files become persisted source records and real
ingestion jobs; invalid files fail clearly and safely.

### `MarketingAiSaas -> app -> api -> routes_ingestion.py`

Must implement: - Start and inspect ingestion jobs; retrieve job
stage/status, safe errors, counts, mapping review items, and
readiness. - Confirm/edit/skip/leave-unmapped mapping decisions. -
Trigger source reprocessing and retry failed jobs where permitted. -
Cancel eligible jobs and resume from safe retry boundaries. - Enforce
the defined state machine: `queued`, `inspecting`, `mapping`,
`awaiting_review`, `normalizing`, `indexing`, `graph_updating`,
`validating`, `ready`, `partially_ready`, `retryable_failure`, `failed`,
and `cancelled`. - Ensure stage transitions are validated and persisted;
duplicate requests must not create uncontrolled duplicate work. -
Publish progress that reflects the actual worker state.

Acceptance: - A job can move through the real pipeline; failures and
retries are visible; mapping decisions persist and affect reprocessing.

### `MarketingAiSaas -> app -> api -> routes_integrations.py`

Must implement: - List supported/configured providers and their
capabilities. - Initiate provider authorization, handle OAuth callback
with state/PKCE validation where applicable, store encrypted
credentials, test connection, trigger sync, inspect status/freshness,
and disconnect/revoke. - Support incremental sync when provider cursors
are available, initial import windows, pagination, provider rate limits,
retry, idempotency, and sync audit events. - Never report a provider as
connected unless authorization and connection validation succeeded. -
Clearly distinguish supported, configured, connected, stale, error, and
disconnected states. - Do not claim provider fields or scopes that the
selected provider does not expose.

Acceptance: - Provider-specific tests cover authorization state, expired
credentials, pagination, rate limits, partial sync, incremental cursors,
disconnect, and no-duplicate retries.

### `MarketingAiSaas -> app -> api -> routes_campaigns.py`

Must implement: - Campaign list/detail endpoints, real summaries,
date-range filtering, campaign comparisons, funnel metrics, and any
supported segment/channel/product filters. - Use shared analytics/domain
services rather than recomputing metrics in route code. - Return metric
value, unit, definition, numerator/denominator when relevant,
attribution/window, date range, source/freshness, and known
limitations. - Handle missing metrics and incompatible definitions
explicitly. - Validate date ranges and prevent unauthorized campaign IDs
from being queried.

Acceptance: - Results match deterministic analytics tests and only
include authorized campaign data.

### `MarketingAiSaas -> app -> api -> routes_chat.py`

Must implement: - Authenticated investigation requests with workspace
scope, conversation/session context, user question, and supported
optional filters. - Invoke the bounded LangGraph workflow; stream
progress or results if streaming is implemented; persist conversations
and final results where required. - Return answer sections separating
observed facts, evidence, interpretation, hypothesis, recommendation,
measurement plan, and limitations when relevant. - Return
citations/evidence IDs, tool/metric provenance, source freshness, and
abstention reason when evidence is insufficient. - Enforce quotas,
timeouts, cancellation, permission-aware retrieval, and model-provider
policy. - Do not let the model choose arbitrary SQL, shell commands, or
unapproved tools.

Acceptance: - Questions that can be answered return verifiable evidence;
unanswerable questions abstain or ask a focused clarification instead of
fabricating.

### `MarketingAiSaas -> app -> api -> routes_evidence.py`

Must implement: - Fetch evidence records and citation targets, graph
entities, graph neighbors, and evidence paths. - Return source locator
information such as file/page/sheet/row/record ID, source version, exact
excerpt or metric result, metric definition, timestamps, and evidence
type. - Distinguish direct observations from inferred graph links and
hypotheses. - Enforce tenant/permission checks on every evidence item
and path. - Return contradictory evidence when available instead of
silently suppressing it.

Acceptance: - Every displayed citation resolves to an actual permitted
source record or computed analytics result.

### `MarketingAiSaas -> app -> api -> routes_reports.py`

Must implement: - Generate evidence-linked campaign reports for a
selected campaign/date range and allowed evidence IDs. - Include
methodology, metric definitions, source list, freshness, limitations,
facts, hypotheses, recommendations, and experiment options as
applicable. - Persist report versions and generation status; allow
authorized retrieval and export in documented formats. - Validate that
supplied evidence IDs belong to the workspace and support the claims. -
Do not publish, email, or share reports externally without an explicit
authorized action.

Acceptance: - Reports are reproducible from stored evidence and do not
contain unsupported metrics or citations.

------------------------------------------------------------------------

## 3.4 Ingestion pipeline

All uploads and provider data must use shared downstream normalization,
persistence, indexing, and graph logic. Source-specific parsing may
differ.

### `MarketingAiSaas -> app -> ingestion -> __init__.py`

Must: - Expose stable ingestion interfaces where useful. - Avoid
starting jobs or loading large models on import.

### `MarketingAiSaas -> app -> ingestion -> inspection.py`

Must: - Detect and inspect actual file type, encoding, sheets, tables,
column headings, sample values, page count, metadata, row count, and
extraction warnings. - Use content inspection as well as extension/MIME
hints. - Produce a typed inspection result with safe diagnostics and
source locators. - Reject unsupported, corrupt, oversized, or unsafe
files with clear errors. - Preserve original source metadata and avoid
logging sensitive contents.

Acceptance: - Tests cover supported formats, mislabeled extensions,
empty files, corrupt files, unusual encodings, multi-sheet workbooks,
and large inputs.

### `MarketingAiSaas -> app -> ingestion -> classification.py`

Must: - Classify inputs into supported categories such as campaign
metrics, customer feedback, product facts, brand rules, CRM records,
campaign plans, experiment results, or unknown. - Combine deterministic
clues (headers, data types, structure, known schemas) with
model-assisted proposals where configured. - Return category,
confidence, reasons, and uncertainty. - Never treat an LLM
classification as authoritative without validation. - Route unknown or
mixed-content sources to review rather than force a false
classification.

Acceptance: - Evaluation fixtures measure classification quality and
verify uncertain cases are not silently auto-accepted.

### `MarketingAiSaas -> app -> ingestion -> parsers.py`

Must: - Implement actual parsers for every file format claimed as
supported: CSV, TSV, XLSX, PDF, DOCX, Markdown, plain text, HTML, and
JSON where appropriate. - Preserve tables, headings, pages, sheet names,
row numbers, source IDs, and extraction warnings where possible. -
Normalize parser outputs into common typed structures used by later
stages. - Defend against malformed files, excessive resource use, unsafe
HTML, and parser exceptions. - Avoid silently dropping tables or rows;
report partial extraction.

Acceptance: - Format-specific fixtures verify content and source
locators; each advertised format has a real parser and tests.

### `MarketingAiSaas -> app -> ingestion -> mapping.py`

Must: - Map source fields to canonical schemas using names, aliases,
data types, representative values, provider schemas, historical
versioned rules, and semantic clues. - Return proposed target field,
alternatives, confidence/reasoning, validation preview, and impact if
unresolved. - Automatically accept only high-confidence mappings that
pass deterministic and semantic checks. - Put ambiguous or consequential
mappings into a review queue. - Store customer mapping decisions as
versioned rules and detect schema drift before reusing them. - Preserve
unmapped columns instead of silently discarding them. - Treat conversion
events and metric names carefully; do not assume that "conversion" means
purchase. - Provide a stable interface for model-assisted suggestions
without making an LLM the sole validator.

Acceptance: - Tests cover clear mapping, ambiguous conversion columns,
conflicting metric definitions, changed headers, reused rules, and
user-edited mappings.

### `MarketingAiSaas -> app -> ingestion -> validation.py`

Must: - Validate required fields, types, allowed values, units, date
formats/time zones, nullability, numeric ranges, semantic consistency,
and cross-field constraints. - Validate metric contracts including
numerator, denominator, aggregation, attribution method/window,
dimensions, source precedence, effective date, and version. - Return
structured errors/warnings and row-level or field-level source
locators. - Distinguish invalid data from suspicious-but-usable data. -
Quarantine incompatible records when they could distort important
results. - Never silently coerce values in ways that change meaning.

Acceptance: - Invalid critical fields cannot enter published analytics
without an explicit resolution path; warning/error counts are testable.

### `MarketingAiSaas -> app -> ingestion -> normalization.py`

Must: - Convert validated inputs into canonical domain entities and
metric records. - Normalize dates, units, currency representation,
channel names, campaign/product/segment identifiers, and other supported
fields using explicit rules. - Preserve original values, normalized
values, transformation details, source IDs, source version, row/page
locator, and timestamps. - Use shared canonical schemas for both
uploaded and integration-derived records. - Keep metric definitions and
attribution semantics attached to values. - Use stable IDs and
transaction-safe persistence interfaces.

Acceptance: - Equivalent file and integration records produce compatible
canonical representations; lineage is retained.

### `MarketingAiSaas -> app -> ingestion -> deduplication.py`

Must: - Detect exact and near duplicates using stable provider IDs,
source IDs, checksums, business keys, and configured similarity rules. -
Distinguish repeated ingestion of the same source record from legitimate
repeated events. - Preserve source lineage and version history. - Make
repeated uploads/sync retries idempotent. - Avoid merging records solely
because their text or values look similar when they may represent
distinct events. - Support deletion/recomputation of one source
contribution without deleting evidence still supported by other sources.

Acceptance: - Re-importing the same data does not create uncontrolled
duplicates; legitimate distinct events remain distinct.

### `MarketingAiSaas -> app -> ingestion -> jobs.py`

Must: - Coordinate the full ingestion state machine and stage
execution. - Persist job state, stage runs, timestamps, progress, row
counts, errors, retryability, and source version. - Run work in a real
background-job mechanism rather than blocking API requests for large
tasks. - Implement idempotent stage boundaries, safe retries,
cancellation, resumability, and dead-letter/terminal failure handling as
appropriate. - After normalization, invoke persistence, document
chunking/indexing, BM25 indexing, embedding/vector indexing, graph
construction, quality checks, and readiness publication. - On source
update/deletion, update or remove dependent records, chunks, embeddings,
graph edges, and affected caches. - Never mark a job `ready` merely
because the task was enqueued. - Avoid logging full source content or
secrets.

Acceptance: - End-to-end ingestion tests demonstrate real status
transitions, partial readiness, retry, cancellation, source update, and
source deletion cleanup.

------------------------------------------------------------------------

## 3.5 Live integration connector framework

### `MarketingAiSaas -> app -> connectors -> __init__.py`

Must: - Expose the connector framework without creating provider
connections at import time.

### `MarketingAiSaas -> app -> connectors -> base.py`

Must: - Define typed provider-neutral interfaces for `connect()`,
`test_connection()`, `discover_resources()`, `fetch_initial_data()`,
`fetch_incremental_data()`, `normalize()`, `get_sync_status()`, and
`disconnect()`. - Define provider capability metadata, supported
objects/metrics, cursor behavior, rate limits, required scopes, and
known limitations. - Define normalized provider errors and sync result
schemas. - Require idempotent behavior and explicit tenant/connection
context. - Support provider-specific adapters without leaking provider
response shapes into analytics.

Acceptance: - A fake test connector can exercise the framework contract;
real provider adapters implement every required method or explicitly
report unsupported capabilities.

### `MarketingAiSaas -> app -> connectors -> oauth.py`

Must: - Implement secure OAuth state creation/validation, callback
handling, PKCE where supported, redirect URI validation, token
exchange/refresh, encrypted token persistence, scope recording, expiry
handling, revocation/disconnect, and audit events. - Prevent CSRF,
callback replay, open redirects, token leakage, and cross-tenant
connection binding. - Avoid logging tokens or authorization codes. -
Keep provider credentials out of frontend storage and API responses.

Acceptance: - Security tests cover state mismatch, expired state,
invalid callback, token refresh failure, revocation, and workspace
ownership.

### `MarketingAiSaas -> app -> connectors -> sync.py`

Must: - Orchestrate initial and incremental provider sync. - Handle
pagination, cursors, rate limits, retries with backoff,
transient/permanent errors, partial sync, idempotency, freshness, and
sync history. - Pass provider records into the shared canonical
normalization and downstream ingestion pipeline. - Record provider field
coverage and sync warnings. - Detect provider schema changes and avoid
falsely declaring a complete sync when pages or objects failed. -
Respect provider deletion/update semantics where available.

Acceptance: - Tests demonstrate pagination, retry without duplicates,
cursor continuation, partial failure visibility, and shared canonical
output.

### `MarketingAiSaas -> app -> connectors -> providers -> __init__.py`

Must: - Register and expose actual provider adapters supported by this
release. - Provide capability discovery and configuration validation. -
Avoid listing a provider as functional merely because its name appears
in the registry. - Keep adapters isolated by provider and use the common
connector interface.

Acceptance: - The UI's provider list is derived from real adapter
capability/configuration metadata.

**Provider implementation rule:** Implement at least one high-value
analytics connector and one campaign/CRM or email connector as real
integrations for the intended release. Do not invent endpoints, scopes,
or data fields. Verify provider API behavior against current official
documentation when implementing. If credentials are unavailable in the
development environment, test with recorded sanitized fixtures and
clearly show the integration as unconfigured until a real authorization
succeeds.

------------------------------------------------------------------------

## 3.6 Retrieval and RAG

### `MarketingAiSaas -> app -> retrieval -> __init__.py`

Must: - Expose stable retrieval contracts and avoid initializing
indexes/models on import.

### `MarketingAiSaas -> app -> retrieval -> chunking.py`

Must: - Split narrative documents into semantically coherent chunks and
preserve headings, page/sheet/row locators, source IDs, source versions,
timestamps, tenant, permissions, and chunk lineage. - Use table-aware
chunking for metrics and tabular material; do not flatten numeric tables
in a way that destroys row/column meaning. - Avoid splitting critical
values from their labels/units/definitions. - Provide configurable chunk
sizing and overlap, with safe limits. - Deduplicate repeated content
while retaining provenance.

Acceptance: - Tests confirm chunk contents remain traceable to original
source locations and table relationships are preserved.

### `MarketingAiSaas -> app -> retrieval -> embeddings.py`

Must: - Define an embedding adapter and implement the configured
embedding provider/model. - Batch requests, normalize output dimensions,
handle model failures, enforce timeouts, and record model/version
metadata. - Support local or configured embedding execution without
silently sending data to an unapproved external provider. - Re-embed
affected chunks when model/version changes require it. - Never use a
hardcoded vector or pretend a failed embedding succeeded.

Acceptance: - Tests verify vector dimensions, batch behavior, failure
handling, version tracking, and deterministic mock behavior in tests.

### `MarketingAiSaas -> app -> retrieval -> vector_search.py`

Must: - Implement vector index upsert, search, deletion, metadata
filtering, and source-version updates using the configured vector
database. - Enforce tenant/workspace and permission filters before or
within retrieval, not only after generation. - Return stable
chunk/evidence IDs, scores, source locators, and metadata. - Handle
index not ready, empty results, stale chunks, and database errors. -
Keep vector records synchronized with canonical source lifecycle.

Acceptance: - Integration tests prove tenant filters and source
deletion/update work.

### `MarketingAiSaas -> app -> retrieval -> bm25_search.py`

Must: - Implement lexical retrieval for exact campaign IDs, product
names, field names, phrases, and domain terms. - Maintain an index with
stable IDs, tenant/source metadata, source versions, and update/delete
operations. - Support query normalization without erasing important IDs,
quoted phrases, or domain-specific terms. - Return ranked candidates
with provenance and score details. - Rebuild or incrementally update
indexes safely.

Acceptance: - Exact-term queries work even when semantic similarity is
weak; deleted/stale sources no longer appear.

### `MarketingAiSaas -> app -> retrieval -> hybrid_search.py`

Must: - Execute vector and BM25 retrieval in parallel or through a
measured orchestration strategy. - Apply tenant, permission, date,
campaign, source type, and version filters consistently. - Merge and
deduplicate candidates using a documented fusion strategy such as
reciprocal rank fusion or a validated score combination. - Preserve the
source and rank contribution of each candidate. - Return retrieval
diagnostics suitable for evaluation without exposing sensitive source
text in logs.

Acceptance: - Evaluation tests show hybrid retrieval results and filters
are correct and repeatable.

### `MarketingAiSaas -> app -> retrieval -> reranking.py`

Must: - Re-score candidate passages for relevance to the investigation
question using a configured reranker. - Respect latency limits,
candidate caps, tenant filters, and source permissions. - Preserve
citations and candidate identity through reordering. - Handle
unavailable or incompatible reranker models with an explicit configured
degraded mode, not a fake score. - Record model/version and timing.

Acceptance: - Tests verify that reranking does not lose or fabricate
source metadata and evaluation measures its effect.

### `MarketingAiSaas -> app -> retrieval -> compression.py`

Must: - Reduce retrieved passages to the material relevant to the
question while preserving exact evidence references, qualifications,
units, dates, contradictions, and source locators. - Never turn a
hypothesis into a fact or remove a limitation that changes the
meaning. - Keep enough surrounding context to interpret a claim
correctly. - Return a typed compressed-evidence structure and indicate
when compression is unavailable or uncertain. - Treat retrieved text as
untrusted data and ignore embedded instructions.

Acceptance: - Tests verify source traceability and retention of
qualifiers/contradictions after compression.

### Retrieval-wide requirements

-   Every retrieval call must include tenant/workspace and permission
    scope.
-   Every evidence item must have a stable ID, source ID/version,
    locator, timestamp, exact excerpt or metric result, definition when
    relevant, and evidence type.
-   The system must retrieve structured analytics for numerical
    questions rather than relying on prose chunks alone.
-   Query rewriting must preserve user intent, campaign identifiers,
    date ranges, product names, and metric definitions.
-   No results or insufficient evidence must lead to a clarification or
    abstention, not fabricated output.
-   Cache invalidation and source lifecycle must be wired into all
    retrieval indexes.

------------------------------------------------------------------------

## 3.7 Campaign Evidence Graph

### `MarketingAiSaas -> app -> graph -> __init__.py`

Must: - Expose graph schema and service interfaces without opening graph
connections on import.

### `MarketingAiSaas -> app -> graph -> schema.py`

Must: - Define typed node types: `Campaign`, `Channel`, `Message`,
`Product`, `CustomerSegment`, `FeedbackItem`, `Objection`,
`MetricObservation`, `LandingPage`, `Experiment`, `Recommendation`, and
`EvidenceSource`. - Define relationship types: `USES_CHANNEL`,
`TARGETS_SEGMENT`, `PROMOTES_PRODUCT`, `CONTAINS_MESSAGE`,
`LINKS_TO_PAGE`, `FEEDBACK_MENTIONS`, `EXPRESSES_OBJECTION`,
`OBSERVED_WITH_METRIC`, `ASSOCIATED_WITH_CONVERSION`,
`TESTED_IN_EXPERIMENT`, `SUPPORTED_BY`, `CONTRADICTED_BY`, and
`DERIVED_FROM`. - Require stable IDs, tenant/workspace ownership, source
provenance, source version, timestamps, and time range where
applicable. - Label each relationship as observed, derived, or inferred,
with a description of the derivation rule where relevant. - Explicitly
prevent graph relationships from being treated as causal proof.

Acceptance: - Schema validation rejects missing provenance or invalid
node/edge types.

### `MarketingAiSaas -> app -> graph -> construction.py`

Must: - Build and update graph nodes and edges from canonical persisted
records and evidence. - Be idempotent, tenant-aware,
source-version-aware, and capable of removing/recomputing one source's
contribution. - Preserve edge provenance and distinguish direct
observations from inferred links. - Handle entity resolution
conservatively and avoid merging distinct entities without sufficient
evidence. - Update graph data after ingestion, mapping changes, source
deletion, and reprocessing. - Record graph build status and errors as
part of the ingestion pipeline.

Acceptance: - Reprocessing creates no uncontrolled duplicate
nodes/edges; source deletion removes only unsupported contributions.

### `MarketingAiSaas -> app -> graph -> retrieval.py`

Must: - Resolve relevant graph entities from a question and authorized
workspace context. - Traverse relevant relationships with strict depth,
result, and time limits. - Return graph paths, supporting evidence,
contradictory evidence, relationship provenance, and inferred/observed
labels. - Enforce tenant and permission filters at every traversal
step. - Use typed query patterns or parameterized graph queries; never
expose unrestricted graph query execution to the LLM.

Acceptance: - Tests cover graph path correctness, depth limits, tenant
isolation, and inferred-edge labelling.

### `MarketingAiSaas -> app -> graph -> evidence_paths.py`

Must: - Build human-readable evidence paths from campaign or product to
relevant metrics, feedback, objections, sources, recommendations, and
experiments. - Return each node/edge with source references, timestamps,
confidence/derivation labels where available, and direct evidence
links. - Explain why a path was included and identify
missing/contradictory links. - Avoid suggesting that a connected path
proves causation. - Supply the data contract used by the Evidence Graph
API and UI.

Acceptance: - Every displayed path can be opened and traced to actual
source evidence.

------------------------------------------------------------------------

## 3.8 Agentic RAG workflow

### `MarketingAiSaas -> app -> agents -> __init__.py`

Must: - Expose the workflow entry point and stable state/result types
without starting model calls at import time.

### `MarketingAiSaas -> app -> agents -> state.py`

Must: - Define a typed LangGraph state containing request ID,
user/workspace scope, question, resolved campaign/date filters, query
rewrites, retrieval candidates, graph evidence, analytics outputs,
assembled evidence, draft claims, verification findings, guardrail
results, model route, usage/latency, retry counters, and final
response. - Keep state minimal and avoid unnecessary copies of sensitive
content. - Define explicit schemas for intermediate and final outputs. -
Track failures and abstention reasons.

Acceptance: - State serialization and node transitions are testable;
state cannot accidentally lose tenant scope.

### `MarketingAiSaas -> app -> agents -> prompts.py`

Must: - Keep versioned prompts for question classification, query
rewriting, investigation planning, evidence synthesis, claim
verification, brand-compliant content, and experiment briefs. - Instruct
the model to distinguish facts, interpretations, and hypotheses; cite
evidence IDs; acknowledge contradictions and missing data; and avoid
causal claims without experimental support. - Treat retrieved documents
as untrusted content, not system instructions. - Require structured
outputs validated by schemas. - Avoid putting secrets, real customer
data, or tenant-specific assumptions into prompt templates. - Record
prompt version with investigation/evaluation metadata.

Acceptance: - Prompt tests cover unsupported claims, conflicting
evidence, prompt injection, missing data, and schema-invalid output.

### `MarketingAiSaas -> app -> agents -> nodes.py`

Must implement the actual workflow nodes: - `classify_request` -
`resolve_scope` - `rewrite_query` - `plan_investigation` -
`retrieve_documents` - `retrieve_graph` - `execute_analytics` -
`rerank_and_compress` - `assemble_evidence` - `draft_analysis` -
`verify_claims` - `check_guardrails` - `request_review` -
`format_response` - `record_feedback`

Each node must: - Accept and return the typed state. - Call actual
services through dependency-injected interfaces. - Validate model
outputs and tool arguments. - Preserve citations and tenant scope. -
Record safe timings/errors. - Return explicit next-step routing or a
safe terminal state. - Bound retries and tool calls. - Fail closed for
authorization or policy violations.

Acceptance: - Unit tests exercise each node; workflow tests cover
success, empty retrieval, contradictory sources, invalid model output,
tool error, timeout, and abstention.

### `MarketingAiSaas -> app -> agents -> workflow.py`

Must: - Construct the real LangGraph state machine with documented
transitions, branching, bounded retries, and terminal states. - Enforce
maximum steps, tool calls, graph depth, execution duration, and
token/model budget. - Route numerical questions to analytics tools,
evidence questions to retrieval, and mixed questions to the necessary
combination. - Apply claim verification and guardrails before formatting
a user-visible answer. - Handle optional human review where a mapping,
brand claim, or sensitive action requires it. - Support cancellation and
clear progress events where the API exposes them. - Record workflow
version and diagnostics for evaluation. - Never mark a workflow
successful if a required model/analytics/verification step failed.

Acceptance: - Integration tests run a complete investigation from
request to verified answer using real configured services or controlled
test adapters.

------------------------------------------------------------------------

## 3.9 Analytics, feedback, product, report, and MCP tools

### `MarketingAiSaas -> app -> tools -> __init__.py`

Must: - Export typed domain tool interfaces without performing work on
import.

### `MarketingAiSaas -> app -> tools -> analytics.py`

Must implement validated, tenant-aware operations such as: -
`get_campaign_summary(campaign_id, start_date, end_date)` -
`compare_campaigns(campaign_ids, metric_names, date_range)` -
`get_funnel_metrics(campaign_id, funnel_definition, date_range)` -
`get_segment_performance(segment_id, campaign_ids, metric_names)`

Requirements: - Use parameterized, read-only database queries and
approved metric contracts. - Validate campaign ownership, date ranges,
allowed metric names, aggregation, units, denominators, attribution
windows, and source precedence. - Return structured values with metric
definitions, freshness, source IDs, sample sizes/counts where available,
and limitations. - Avoid division-by-zero and misleading percentages;
report missing/undefined metrics explicitly. - Never allow arbitrary SQL
generated by a model. - Use deterministic calculations that can be
tested independently.

Acceptance: - Golden test fixtures prove exact numeric results and
definitions.

### `MarketingAiSaas -> app -> tools -> feedback.py`

Must implement: - Search customer feedback from authorized indexed
records using terms, semantic search, product, date range, and
source-type filters. - Identify recurring questions/objections only when
supported by actual feedback records. - Return exact excerpts or
appropriately minimized/redacted excerpts, source IDs, dates, product
references, and retrieval scores. - Distinguish a measured count from a
model-generated theme interpretation. - Avoid sensitive-trait inference
and respect data permissions.

Acceptance: - Every reported objection/theme links to underlying
permitted feedback records and can be checked.

### `MarketingAiSaas -> app -> tools -> products.py`

Must implement: - Retrieve approved product facts, feature descriptions,
limitations, FAQs, brand rules, and permitted claims. - Return source
citations and freshness/version. - Provide approved facts to content
generation and validate factual claims against source material. - Never
invent a product feature, guarantee, price, compatibility, or outcome. -
Enforce workspace scope and any brand-review permissions.

Acceptance: - Content claims that lack approved evidence are flagged or
removed.

### `MarketingAiSaas -> app -> tools -> reports.py`

Must implement: - Build structured report data from authorized campaign
metrics, evidence, graph paths, recommendations, and experiment
briefs. - Validate every evidence ID and metric before report
generation. - Persist report versions, status, source list, metric
definitions, date range, freshness, limitations, and audit
information. - Generate supported downloadable formats if included in
the UI; report export must use actual report data, not placeholder
files. - Keep report generation separate from external publishing or
email sending.

Acceptance: - Report tests compare generated report content with source
evidence and verify unauthorized evidence is rejected.

### `MarketingAiSaas -> app -> mcp -> __init__.py`

Must: - Expose the MCP server factory/configuration without starting a
server on import.

### `MarketingAiSaas -> app -> mcp -> server.py`

Must: - Implement a real MCP server exposing only approved typed tools
for analytics, retrieval, product facts, graph queries, source
freshness, experiment briefs, and reports. - Publish valid tool schemas,
descriptions, permission requirements, side-effect classification,
timeouts, and audit behavior. - Reuse the same domain services and
authorization logic as FastAPI; MCP must not become a bypass around
tenant security. - Validate tool arguments, enforce allowlists and
limits, and never expose unrestricted SQL, shell execution, or arbitrary
filesystem access. - Make read-only behavior the default; any
state-changing action must require explicit authorization and
appropriate confirmation. - Return structured results with provenance
and stable errors. - Document how the MCP server is started and how
clients authenticate.

Acceptance: - MCP tests validate schemas, permission enforcement, tool
allowlists, error behavior, and audit events.

------------------------------------------------------------------------

## 3.10 Evaluation and observability support

### `MarketingAiSaas -> app -> evaluation -> __init__.py`

Must: - Expose evaluation interfaces without running evaluation on
import.

The folder currently has no other listed files. Add concrete
implementation modules here as needed; at minimum, create a real
evaluator module and schemas/configuration rather than leaving the
package empty. The added filenames must be documented in `PLAN.md` and
`README.md`.

Recommended additions: - `app/evaluation/schemas.py`: typed evaluation
case/result/metric models. - `app/evaluation/retrieval.py`: Recall@k,
Precision@k, MRR, nDCG@k, evidence coverage, and tenant-filter checks. -
`app/evaluation/answers.py`: citation correctness/completeness,
faithfulness, numeric accuracy, fact-versus-hypothesis labelling,
abstention, and brand compliance. - `app/evaluation/agents.py`: tool
selection, argument validity, unnecessary calls, completion/failure,
latency, token usage, and cost. - `app/evaluation/ingestion.py`: mapping
accuracy, parsing success, duplicate detection, entity-resolution
quality, sync correctness, retry recovery, reprocessing, and
source-deletion cleanup. - `app/evaluation/runner.py`: versioned
execution, result persistence, summaries, and reproducibility.

These are implementation recommendations for the currently empty
package, not a claim that these files already exist.

### `MarketingAiSaas -> app -> evaluation -> schemas.py` (add)

Must: - Define typed test cases, expected evidence, expected abstention,
expected numeric results, metric definitions, run metadata, and
evaluation results. - Version datasets and metric implementations.

### `MarketingAiSaas -> app -> evaluation -> retrieval.py` (add)

Must: - Compute retrieval ranking metrics and evidence coverage against
labelled evaluation cases. - Test tenant and permission filtering
explicitly.

### `MarketingAiSaas -> app -> evaluation -> answers.py` (add)

Must: - Evaluate claim support, citation resolution, numeric accuracy,
contradiction handling, uncertainty labelling, and appropriate
abstention. - Prefer deterministic checks for numbers and citation IDs;
use model-based judges only as supplemental signals and document their
limits.

### `MarketingAiSaas -> app -> evaluation -> agents.py` (add)

Must: - Evaluate tool choice, tool argument validity, tool call count,
workflow completion, error/timeout handling, latency, and usage.

### `MarketingAiSaas -> app -> evaluation -> ingestion.py` (add)

Must: - Evaluate classification/mapping accuracy, review rate, parsing
success, duplicates, entity resolution, sync, retries, reprocessing, and
deletion cleanup.

### `MarketingAiSaas -> app -> evaluation -> runner.py` (add)

Must: - Execute a selected versioned dataset, persist run
status/results, produce reproducible summaries, and expose results
through an authorized API or CLI. - Never show fabricated quality
scores. If no run exists, show "not evaluated."

### Observability requirement across the backend

Implement or configure metrics/traces for ingestion stage timing, row
counts, mapping outcomes, schema drift, connector freshness, API errors,
retrieval candidate counts, reranking/graph latency, tool calls, model
version, usage, citation verification, evaluation results, cache
invalidation, storage use, and tenant quotas. Redact sensitive content
by default.

------------------------------------------------------------------------

# 9. Demo data, evaluation data, and tests

## 9.1 `MarketingAiSaas -> data -> synthetic_demo ->`

This directory must contain a coherent, reproducible, clearly labelled
synthetic workspace dataset. Add real fixture files such as: -
`campaign_metrics.csv`: multiple campaigns, dates, channels, spend,
delivery/click/session/conversion/revenue values, and explicit metric
definitions. - `customer_feedback.csv`: synthetic reviews/support/survey
comments linked to product or campaign where appropriate. -
`products.json`: synthetic product facts, features, limitations, and
approved claims. - `brand_guidelines.md`: tone, terminology, prohibited
claims, disclaimers, and channel rules. - `campaigns.json`: campaign
metadata, audience/segment, offer, message, and landing-page
references. - `experiment_results.csv`: synthetic control/variant
observations with sample counts and explicit experimental metadata. -
`README.md`: states that all records are fictional and explains the demo
scenario and loading process.

Requirements: - Use internally consistent relationships and metric
definitions so the demo can be checked deterministically. - Include a
campaign with strong engagement and weak purchases, supporting feedback,
relevant product facts, and an experiment hypothesis. - Include an
ambiguous conversion column for the mapping-review flow. - Include
conflicting/outdated/unanswerable cases for verification and abstention
tests. - Never present synthetic results as real customer results. - Do
not load these files into a real customer workspace automatically
without explicit demo seeding.

## 9.2 `MarketingAiSaas -> evals ->`

Must contain version-controlled evaluation datasets and instructions,
not remain empty. Recommended files: - `README.md`: dataset purpose,
schema, versioning, and execution instructions. -
`investigation_cases.jsonl`: answerable, ambiguous, contradictory,
stale, and unanswerable questions with expected evidence IDs and
expected answer behavior. - `retrieval_cases.jsonl`: query, allowed
scope, relevant source/chunk IDs, and relevance labels. -
`mapping_cases.jsonl`: input schema, expected mappings,
confidence/review expectation, and invalid cases. - `tool_cases.jsonl`:
questions, expected tools, argument constraints, and prohibited tool
choices. - `security_cases.jsonl`: cross-tenant, prompt-injection,
permission, and cache-isolation scenarios. - `metric_definitions.json`:
versioned definitions used by evaluation cases.

Requirements: - No fabricated benchmark scores. - Dataset changes must
be versioned/reviewable. - Each case must specify what constitutes a
pass and how expected evidence is identified.

## 9.3 `MarketingAiSaas -> tests ->`

Must contain automated tests organized by responsibility. Add at
minimum: - `conftest.py`: isolated test configuration, dependency
overrides, test database lifecycle, and test clients. - `unit/`:
canonical normalization, mapping, validation, deduplication, metric
calculations, retrieval fusion, graph schema, evidence verification, and
permissions. - `integration/`: ingestion pipeline, persistence,
vector/BM25 indexing, graph updates, connector sync, MCP tools, source
deletion, and cache invalidation. - `api/`: auth, workspace membership,
uploads, job lifecycle, mapping review, integrations, chat, campaigns,
evidence, reports, and evaluation endpoints. - `security/`: cross-tenant
access, role enforcement, prompt injection, malicious uploads, OAuth
state, token redaction, and cache isolation. - `e2e/`: a repeatable
critical user journey from workspace creation through file ingestion,
mapping review, analytics/investigation, evidence graph, report, and
source deletion/reprocessing. - Provider/model contract tests using safe
fixtures or test adapters; keep real-provider smoke tests opt-in and
credential-gated.

Required negative tests: - Malformed/oversized files, ambiguous
conversion columns, duplicate uploads, schema drift, conflicting metric
definitions, expired credentials, provider rate limits, pagination
failure, partial import, prompt injection, cross-tenant access, empty
retrieval, stale cache, inferred graph edges, unsupported causal claims,
local connector offline/timeout/incompatible model, and hosted fallback
without consent.

Acceptance: - A documented command runs the suite; failures are
actionable; test reports are generated; no real customer secrets or
source content are committed.

------------------------------------------------------------------------

# 10. Root configuration and documentation

### `MarketingAiSaas -> .env.example`

Must: - List every environment variable required for local setup and all
supported optional services, using placeholder values only. - Include
database, object storage, background jobs, vector database, graph
database, embedding/reranker, model router, connector channel,
auth/session, CORS, upload limits, rate limits, logging, telemetry, and
provider OAuth configuration as applicable. - Explain which settings are
required and which are optional. - Never contain real credentials,
tokens, private keys, or production secrets. - Match the setting names
in `app/core/config.py` exactly.

### `MarketingAiSaas -> docker-compose.yml`

Must: - Define reproducible local development services actually used by
the application, such as PostgreSQL, Redis/job broker, vector store,
graph database, object storage emulator if selected, and observability
services if included. - Configure persistent development volumes, health
checks, service dependencies, ports, resource settings, and environment
variables. - Avoid committing default production credentials; local-only
credentials must be clearly documented and overridable. - Include a safe
startup order and readiness checks. - Ensure application setup
instructions explain which services run in Compose and which run
separately. - Do not claim a service is healthy solely because its
container is running. - Provide a clear path for migrations, demo data
loading, and service shutdown/reset.

### `MarketingAiSaas -> pyproject.toml`

Must: - Declare Python version constraints, project metadata, runtime
dependencies, optional development/test dependencies, and package
configuration. - Include compatible dependencies for FastAPI,
Pydantic/settings, database/ORM and migrations, job processing, parsers,
vector/graph adapters, LangChain/LangGraph, MCP, model providers,
telemetry, and testing according to actual implementation. - Configure
pytest, formatting/lint/type checking, and coverage thresholds where
used. - Pin compatible versions or use reproducible constraints. - Avoid
unused or incompatible dependencies and ensure imports match installed
packages. - Include no secret values.

### `MarketingAiSaas -> PLAN.md`

Must: - Convert the nine project phases into a traceable checklist with
owner/status, dependencies, acceptance criteria, tests, and verification
evidence. - Reflect actual repository state truthfully. - Mark an item
complete only after implementation and tests pass. - Record known
limitations, provider credentials required, model compatibility
constraints, and decisions. - Remove claims that something is "done"
merely because a folder or file exists. - Track additions to currently
empty `evaluation`, `tests`, `evals`, graph, chart, UI, and feature
folders.

### `MarketingAiSaas -> README.md`

Must provide a complete setup and operating guide: 1. Product purpose
and feature scope. 2. Architecture diagram and request/data flow. 3.
Supported file types and source pipeline. 4. Canonical entities and
metric-contract principles. 5. Workspace setup, roles, and tenant
security. 6. Required environment variables and secret handling. 7.
Local services and Docker Compose startup. 8. Database migration and
demo-data loading commands. 9. Backend startup commands. 10. Backend
test, lint, type-check, and evaluation commands. 11. How to configure a
real provider integration and what its current limitations are. 12. How
to install/pair/use/revoke the local Ollama connector. 13. Clear privacy
statement: local inference is distinct from cloud data storage;
retrieved context is sent to the customer's local connector for
inference; hosted fallback requires explicit opt-in. 14. Troubleshooting
for database, vector, graph, queue, parser, provider, model, and
connector errors. 15. Source deletion/reprocessing behavior, backups,
retention, and operational cautions. 16. Demo flow and explicit
synthetic-data labels. 17. Security considerations and production
deployment checklist.

The README must describe the implementation that exists, not a generic
plan or a list of aspirational features.

### `MarketingAiSaas -> marketing_intelligence_campaign_copilot_saas_full_spec.md`

Must: - Remain the detailed product specification used as the source of
truth. - Keep architecture, boundaries, acceptance criteria, and privacy
statements consistent with implementation. - If a requirement is
deliberately changed, record the decision and update affected
documentation/tests rather than silently diverging.

------------------------------------------------------------------------

# 11. Cross-file contracts that must be implemented end to end

## 11.1 Upload to searchable intelligence

The complete flow must work: 1. User uploads a file. 2. Backend
validates it, stores it safely, and registers source/version/provenance.
3. A background job inspects and classifies it. 4. Parser extracts
structured data and document content with source locators. 5. Mapping
proposes canonical fields and flags consequential ambiguity. 6. User
resolves mapping review items where required. 7. Validation checks
schemas and metric definitions. 8. Normalization writes canonical
records with original values and provenance. 9. Deduplication and
versioning run idempotently. 10. Structured analytics data is persisted.
11. Documents are chunked, embedded, and indexed in vector and BM25
search. 12. Graph nodes/edges are built with provenance. 13. Quality
checks determine ready/partially-ready/failure status. 14. UI displays
actual status, warnings, counts, and freshness. 15. A question can
retrieve records, calculate metrics, cite sources, and show graph paths.
16. Source update/deletion correctly updates every derived store and
invalidates affected caches.

## 11.2 Integration to shared intelligence

The complete flow must work: 1. User chooses a supported provider. 2.
OAuth state/authorization and scopes are validated. 3. Credentials are
encrypted and associated with the authorized workspace. 4. The
connection is tested and its real state shown. 5. Initial import and
incremental sync use pagination/cursors/rate limits. 6. Provider records
are normalized into the same canonical entities used by file ingestion.
7. Indexes and graph are updated through shared services. 8. Sync
history, freshness, warnings, and errors are persisted and displayed. 9.
Retry does not create duplicates. 10. Disconnect/revoke prevents future
access and cleans up or disables credentials safely.

## 11.3 Question to verified investigation

The complete flow must work: 1. Authenticate the user and resolve
workspace/permissions. 2. Classify the question and resolve
campaign/date/metric scope. 3. Rewrite the query without losing
important IDs or constraints. 4. Plan a bounded investigation. 5.
Retrieve authorized vector and BM25 candidates. 6. Rerank and compress
while preserving source references. 7. Retrieve relevant graph paths and
contradictory evidence. 8. Execute deterministic analytics tools for
numeric questions. 9. Assemble an evidence bundle with source versions
and metric definitions. 10. Generate structured analysis using the
selected model adapter. 11. Verify claim support, citations, arithmetic,
freshness, and causal language. 12. Apply guardrails and abstain/clarify
if support is insufficient. 13. Return facts, interpretations,
hypotheses, recommendations, measurement plan, citations, and
limitations. 14. Record safe telemetry and user feedback.

## 11.4 Local Ollama inference

The complete flow must work: 1. Customer installs and starts Ollama and
installs/starts the local connector with explicit consent. 2. Customer
pairs the connector using a short-lived, one-time code. 3. Connector
establishes an authenticated outbound TLS channel; no inbound port or
public Ollama API is required. 4. User selects an installed model and
sees capability/health results. 5. Model router sends only the required
prompt/context/tool schema through the paired connector. 6. Connector
calls only the configured local Ollama endpoint and returns a validated
response. 7. SaaS verifies claims, citations, numbers, permissions, and
policy before display. 8. Offline, sleeping, timeout, incompatible
output, context overflow, and out-of-memory cases fail visibly and
safely. 9. Hosted fallback remains disabled unless explicitly enabled
and disclosed. 10. Disconnect/revoke blocks further inference requests;
logs exclude prompt/output content by default. 11. Tests prove one
workspace cannot receive another workspace's connector requests.

------------------------------------------------------------------------

# 12. Definition of done

The project is not complete until all of the following are demonstrated:

-   Clean install of backend and frontend from documented instructions.
-   Required services start and report truthful health/readiness.
-   Database schema/migrations work from a clean environment.
-   User can sign up, log in, create a workspace, and exercise
    role-based access.
-   Uploads work for every advertised file type and show extraction
    warnings/errors.
-   Automatic classification/mapping works; ambiguous mappings require
    review.
-   Mapping decisions persist as versioned rules and schema drift is
    detected.
-   Normalization, validation, deduplication, and provenance work
    correctly.
-   At least one real configured live source integration imports data
    into the shared canonical pipeline; a second real connector is
    implemented according to the target MVP.
-   Incremental sync, retry, rate limits, pagination, and disconnect are
    handled.
-   Analytics metrics are deterministic and include definitions, dates,
    units, sources, and freshness.
-   Vector retrieval, BM25, hybrid fusion, reranking, contextual
    compression, and metadata filtering are implemented and evaluated.
-   LangChain/LangGraph are used in the real investigation path, with
    bounded tools and explicit state transitions.
-   MCP exposes approved typed tools without bypassing authorization.
-   Campaign Evidence Graph nodes, edges, and paths are built from
    actual source records with provenance and observed/inferred labels.
-   Claims and citations are verified; missing evidence causes
    qualification or abstention.
-   Recommendations and content are tied to evidence and approved
    brand/product facts.
-   Experiment briefs contain a hypothesis, control/variant, primary and
    guardrail metrics, sample-size considerations, duration, stopping
    rules, confounders, and success criteria.
-   Local Ollama connector pairing, model checks, inference, disconnect,
    timeout/offline behavior, privacy disclosures, and opt-in fallback
    all work.
-   Source deletion and reprocessing clean up or recompute dependent
    records, indexes, graph relationships, and caches correctly.
-   Semantic cache checks tenant, permissions, source versions,
    definitions, model/prompt versions, and freshness before reuse.
-   Evaluation datasets and automated evaluation runs exist; scores are
    measured, not fabricated.
-   Logs/traces/metrics provide useful operational diagnostics without
    exposing secrets or sensitive source text.
-   UI screens have working actions and real data states; no production
    screen silently uses mock fixtures.
-   Tests cover tenant isolation, prompt injection, malformed inputs,
    stale data, citations, numeric correctness, provider failures, and
    model/connector failures.
-   `npm run build`, frontend typecheck/lint/test commands, Python
    lint/typecheck/test commands, and documented smoke tests run
    successfully.
-   Documentation matches actual behavior and explicitly describes
    limitations.
-   No TODO/FIXME placeholder logic, fake success states, hardcoded
    production data, unimplemented visible buttons, or unverified
    completion claims remain.

**Final instruction:** Implement this as a complete, coherent
application for the stated scope now. Do not return only a plan, a
scaffold, sample screens, mock API responses, or a list of files to
implement later. Do not silently skip requirements. Where external
credentials or services are necessary, implement the complete
integration path, tests, configuration, and honest "not configured"
behavior rather than pretending it works. Run the tests and fix failures
before declaring the deliverable complete. The goal is not to promise
that software will never need maintenance; it is to deliver the defined
scope fully implemented, integrated, tested, documented, and free of
known unfinished placeholders at handoff.
