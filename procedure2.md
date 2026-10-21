# procedure2.md — Final Completion Procedure for Marketing AI SaaS

**Repository:** `MarketingAiSaas/`  
**Product name:** **Marketing AI SaaS**  
**Purpose:** Finish the remaining work after `procedure.md` and the reported backend verification pass.  
**Starting baseline supplied by the project owner:** `python -m pytest tests -q` completed with **80 passed**. Do not claim that this file's additional work has been completed until it is implemented and verified in the actual repository.

---

## 0. Mandatory execution rules

This is an implementation and verification procedure, not a proposal for a future prototype. Work in the existing repository and preserve the working backend unless a change is necessary to complete the requirements below.

1. Read `procedure.md`, `PLAN.md`, `README.md`, the product specification, the current OpenAPI schema, the current frontend package manifest, and the existing React source before editing.
2. Inspect the actual repository and identify its real framework, routes, components, API response shapes, test tools, and package scripts. Do not invent files or assume a route exists merely because a feature is described here.
3. Keep existing working behavior and tests. Make small, reviewable changes and rerun the relevant tests after each meaningful change.
4. Do not replace real backend behavior with mock fixtures, fabricated metrics, fake success notifications, hardcoded campaign data, or local-only UI state presented as persisted server state.
5. Tests may use mocks and synthetic fixtures. Production runtime paths must use real API calls and real persisted backend state.
6. Do not silently weaken, delete, skip, or loosen a test just to obtain a green result. If a test is incorrect, explain why, correct the test against the intended contract, and preserve coverage.
7. Do not claim linting, type-checking, frontend tests, browser tests, migrations, live integrations, or end-to-end verification passed unless the exact command or check was run successfully.
8. Any provider requiring external credentials must show an honest **Not configured** or equivalent state until a real connection has been completed. Never fake a live connection.
9. Do not expose tokens, credentials, source excerpts, customer data, or private prompts in logs, error messages, URLs, browser storage, or frontend telemetry.
10. All user-visible product branding in the frontend must be **Marketing AI SaaS** exactly. This is mandatory and applies to every screen, route title, navigation element, login/onboarding experience, page heading, browser document title, metadata, loading/empty/error state, toast, modal, tooltip, accessibility label where branding is included, footer, settings/about page, and frontend README or user-facing help text. Do not display `MarketingAiSaas`, `Marketing Intelligence and Campaign Copilot SaaS`, another product name, a placeholder name, or a demo brand as the product identity. Internal Python package names and repository paths may remain unchanged where they are implementation identifiers, not user-facing branding.

## 1. Scope and known starting state

The previous procedure and the completion report indicate that the backend suite has 80 passing tests and that security, ingestion, analytics, auth, OAuth, cache, and root-documentation fixes have been made. Treat this as a **reported baseline**, not as proof of any new frontend or release check.

The known remaining items are:

- Replace frontend mock-fixture wiring with real `/api/v1` backend calls.
- Ensure every visible frontend workflow is genuinely implemented or explicitly disabled with an honest reason; no fake success paths.
- Add/complete frontend tests and browser-level critical-journey tests using the repository's existing stack.
- Run frontend build, type-check, lint, and test commands that actually exist; add missing scripts/tooling where appropriate.
- Run Python linting and a dedicated type-check, if not already configured; fix issues rather than reporting them as passed.
- Introduce Alembic migrations if the application uses SQLAlchemy and currently relies on `create_all` for development/test schema creation. Preserve the current schema and prove clean-database setup and upgrade behavior.
- Reconcile `PLAN.md`, `README.md`, `procedure.md`, and the product specification with actual verified capabilities and known credential-gated limitations.
- Perform final end-to-end and security regression checks.

Do not broaden scope by rebuilding the backend from scratch. Use the existing API and service contracts as the source of truth.

---

## 2. Phase 1 — Repository and API contract audit

### 2.1 Inspect the real codebase

From `MarketingAiSaas/`, inspect:

- `procedure.md` and this file.
- `PLAN.md` and `README.md`.
- `app/main.py`, `app/core/config.py`, `app/core/security.py`, `app/core/tenancy.py`.
- All `app/api/routes_*.py` modules.
- Existing Pydantic request/response schemas and service functions.
- The frontend package manifest, lockfile, entry point, route configuration, page components, API helpers, state/query layer, styles, and tests.
- `docker-compose.yml`, `.env.example`, `pyproject.toml`, and database setup code.
- Existing test fixtures and the reported 80-test suite.

Record the actual frontend stack and commands. Do not replace the package manager or framework merely for preference.

### 2.2 Build a route-to-screen contract matrix

Create or update an implementation checklist (for example, `frontend/INTEGRATION_MATRIX.md`, if the repository has no suitable existing file). For every screen or user-facing action, record:

- Screen/component and route.
- Product area.
- Required backend endpoint and HTTP method.
- Request parameters/body and response schema.
- Authentication and workspace scope.
- Loading, empty, success, partial-success, and error states.
- Mutation behavior and how the UI refreshes server state.
- Tests that verify the behavior.
- Status: implemented, blocked by configuration, or unsupported.

Use the actual OpenAPI schema and route implementations. Do not invent endpoints. If a needed endpoint is genuinely missing, implement it in the backend using existing service and authorization patterns, add request/response schemas and tests, and document the change.

### 2.3 Preserve backend contracts

- Prefer generating or sharing typed frontend API types from the actual OpenAPI schema if compatible with the current project setup.
- Keep a single API client layer. Do not scatter raw `fetch`/Axios calls throughout components.
- Do not duplicate backend analytics calculations, mapping confidence decisions, tenant authorization, evidence validation, or job-state logic in React.
- Use the backend's real error envelope and status codes. If backend error responses are inconsistent, standardize them through shared backend error handling and test the contract.
- Keep API base URL and development proxy configuration environment-driven. Do not hardcode production hostnames or secrets.
- Ensure local development can configure the frontend API origin without editing source files.

**Phase 1 acceptance:** A reviewed matrix maps every visible frontend workflow to a real endpoint or an explicitly documented unavailable capability. The backend remains green.

---

## 3. Phase 2 — Establish mandatory Marketing AI SaaS branding

### 3.1 Exact product name

The exact product name is:

**Marketing AI SaaS**

Use that exact spelling, capitalization, and spacing for the product identity everywhere in the frontend.

The repository folder may still be `MarketingAiSaas`; this is not the user-facing product name. Internal module identifiers do not need to be renamed if doing so would introduce risk.

### 3.2 Centralize the brand identity

Use the existing frontend configuration or add a single brand constants/configuration module appropriate to the current stack. The canonical display name must be `Marketing AI SaaS`.

Use this constant for branding where the framework supports it, including:

- Application shell and primary navigation.
- Login, signup, password-reset, invitation, and onboarding screens.
- Workspace selection and empty-workspace screens.
- Browser document title and route-specific title composition.
- HTML metadata (`title`, description, Open Graph title where used).
- About/help/settings screens and footer.
- Loading screens and first-run experiences.
- Not-found and global error pages.
- Toasts, dialogs, confirmation screens, and tooltips when they identify the product.
- Accessibility labels or announcements that refer to the product.
- Frontend user guide, in-app help, and product-facing copy.
- Any favicon/logo asset's accessible name or adjacent text if it identifies the product.

If the repository includes product-name strings in several locations, replace user-facing aliases with the canonical name. Avoid broad blind replacement of internal package paths, Python imports, API identifiers, test fixtures that are intentionally testing an alias, or historical documentation where preserving context matters.

### 3.3 Branding audit

Add a repeatable branding check or test. It must verify that:

- The document title includes `Marketing AI SaaS`.
- The primary application shell displays `Marketing AI SaaS`.
- Authentication and onboarding pages display `Marketing AI SaaS`.
- No obsolete product identity appears in the user-facing frontend source or rendered pages.
- The production build does not use demo-only or prototype branding.
- Branding remains consistent in light/dark themes and responsive layouts.

If a user-supplied campaign, workspace, customer, or product has a different name, preserve that as customer data; the rule applies to the SaaS product identity, not the names of customer entities.

**Phase 2 acceptance:** Branding is exact, centralized where practical, covered by tests, and visually checked on key routes. The app is called **Marketing AI SaaS** everywhere it identifies itself as the product.

---

## 4. Phase 3 — Implement the real frontend API layer

Adapt names and files to the actual frontend structure; do not create duplicate layers if equivalent infrastructure already exists.

### 4.1 API client

Implement or complete a shared API client that provides:

- Configurable base URL.
- JSON request/response handling and supported upload handling.
- Typed request and response interfaces.
- Request cancellation and timeout behavior where appropriate.
- Request IDs/correlation IDs where supported by the backend.
- Authentication/session handling consistent with the backend's actual auth model.
- Workspace context supplied explicitly for workspace-scoped calls.
- Standardized parsing of backend errors without exposing internal stack traces.
- Safe handling of `401`, `403`, `404`, `409`, `413`, `422`, `429`, and `5xx` responses.
- No credentials or access tokens in query strings or application logs.
- No silent fallback from API failures to mock data.

If cookie-based auth is used, follow the backend's cookie, credentials, and CSRF contract. If bearer tokens are used, follow the actual token lifecycle and storage policy; do not store sensitive tokens in insecure browser storage simply for convenience. Never invent an auth mechanism that differs from the server.

### 4.2 Data fetching and cache behavior

Use the project's existing query/state library if one is present. Otherwise implement a consistent approach suitable for the stack.

- Query keys must include the relevant workspace and filters.
- Changing workspaces must invalidate or isolate previous workspace data.
- Mutations must update or invalidate affected queries.
- Do not reuse cached results across users or workspaces.
- Handle cancellation on route changes and stale requests.
- Show actual backend timestamps/freshness when available.
- Do not display fabricated loading progress or job completion percentages.
- An API failure must remain an error state, not silently fall back to a local fixture.
- A genuinely empty response should display an empty state, not an error or fake data.

### 4.3 Remove production mock wiring

Search the frontend for mock fixtures, seeded arrays, hardcoded metrics, fake delay functions, demo API adapters, static chart data, and simulated success handlers.

For each occurrence:

1. Determine whether it is test-only, synthetic-demo-only, or used by a production route.
2. Keep test fixtures in test directories and clearly labelled synthetic demo data in the demo path.
3. Replace production-route mock reads with real API calls.
4. Remove fake success callbacks and fake loading delays.
5. If the backend capability is not configured or is unsupported, display an honest disabled/unconfigured state with a concise explanation.
6. Do not remove a screen merely because its integration is credential-gated; display the real configuration/connection state and setup guidance where the backend supports it.
7. Do not report success before the server confirms success.
8. Add tests proving that API failures do not cause mock data to appear.

**Phase 3 acceptance:** All production screens use the shared API client and real server state. Mock data is restricted to tests or an explicitly invoked synthetic demo mode.

---

## 5. Phase 4 — Wire every existing frontend workflow

Implement only the workflows supported by the current product contract and backend. The following list is the expected coverage checklist; use actual routes and capabilities.

### 5.1 Authentication and onboarding

- Sign up, log in, log out, and restore the current session according to the backend contract.
- Display validation errors beside relevant fields and accessible form-level summaries.
- Prevent duplicate submissions while a request is pending.
- Handle expired sessions and revoked credentials safely.
- Create/select a workspace through real backend calls.
- Display current user and workspace data from the API.
- Do not permit client-side route guards to substitute for server authorization.
- Handle invitations and membership changes only if supported by the backend.
- Show **Marketing AI SaaS** branding on all authentication and onboarding routes.

### 5.2 Workspace, members, and settings

- Fetch only workspaces the current user can access.
- Switch workspace through an explicit action; clear or invalidate old workspace caches.
- Fetch real membership and role data.
- Submit supported role/member changes to the backend and reflect the returned result.
- Display actual usage and quota values only when the backend supplies them.
- Do not display fabricated usage bars, fake member counts, or placeholder activity as real.
- Show permission errors clearly without leaking whether inaccessible resources exist beyond the backend's intended response.

### 5.3 Uploads and source management

- Support only file types advertised by the backend.
- Submit actual file bytes through the documented upload API.
- Show progress only when real transport/job progress is available.
- Show source name, source version, uploader/time, ingestion status, counts, warnings, and safe errors from server data.
- Poll or subscribe to job status using the actual supported mechanism, with cancellation and bounded polling.
- Prevent duplicate submissions when a request is in progress.
- Allow retry, reprocess, cancel, or delete only when the API permits the operation.
- After deletion, refresh affected source, campaign, evidence, report, and search views.
- Never show “indexed” or “ready” based solely on upload completion; use the persisted job state.
- Never show file contents or extracted excerpts in telemetry or generic error messages.

### 5.4 Mapping review and ingestion jobs

- Display the actual mapping review queue and source locator information.
- Show proposed field, confidence/reason, alternatives, and warnings only when supplied by the backend.
- Let users confirm, edit, skip, or leave unmapped only when the endpoint supports that action.
- Submit decisions to the backend and refresh job state from the response.
- Show clear distinctions between queued, inspecting, mapping, awaiting review, normalizing, indexing, graph updating, validating, ready, partially ready, retryable failure, failed, and cancelled states where those states are returned by the backend.
- Do not infer that a job is ready because a page was refreshed or a request was accepted.
- Show safe, actionable retry information and preserve the job/source association.
- Test review-required ambiguous conversion mappings and the resume/reprocess path.

### 5.5 Integrations

- Render the provider list from actual backend capability/configuration metadata where available.
- Separate **supported**, **configured**, **connected**, **stale**, **error**, **disconnected**, and **not configured** states.
- Use the backend's OAuth start/callback workflow; do not handle provider secrets in frontend code.
- Show required setup/scopes and a link to documented configuration where applicable.
- Show connection test, last sync, freshness, sync status, warnings, and safe errors from actual records.
- Trigger sync, retry, or disconnect only through supported API actions.
- Do not display a green connected badge before successful authorization and connection validation.
- When credentials are absent, state that the provider is not configured; do not simulate a connection or import.
- Ensure disconnect/revoke updates the visible state after server confirmation.

### 5.6 Campaigns and analytics

- Fetch campaigns and campaign details from the API.
- Connect filters (date range, channel, segment, product, metric) to supported query parameters.
- Render charts and tables from returned data only.
- Handle empty and missing metrics without substituting zero unless the backend defines zero as the correct value.
- Display metric definitions, units, attribution/window, date range, source/freshness, and limitations when supplied.
- Do not calculate authoritative metric values independently in the browser.
- For campaign comparisons, preserve incompatible/missing-definition warnings.
- Distinguish no data from zero performance and from a failed request.
- Ensure workspace changes and date filters invalidate stale results.

### 5.7 Chat and investigations

- Submit the actual question, conversation/session context, workspace, and supported filters to the chat API.
- Render the response structure from the backend: observed facts, evidence, interpretation, hypotheses, recommendations, measurement plan, citations, and limitations where available.
- Show a citation only when the backend returns a resolvable evidence reference.
- Clicking a citation must open the correct evidence/source/metric detail, using an authorized API call.
- Show abstention and clarification requests clearly; do not rewrite an abstention as a confident answer.
- Display errors, cancellation, and timeout states honestly.
- If streaming is supported, handle partial events and terminal states according to the actual protocol. If streaming is not supported, do not fake token-by-token streaming.
- Do not let the frontend call arbitrary SQL, shell, filesystem, or unapproved tools.
- Treat all source-derived content as untrusted text; do not execute or interpret it as markup/commands.

### 5.8 Evidence Graph

- Fetch graph entities, paths, edges, and evidence details through the actual API.
- Render graph relationships from returned data; do not invent edges or nodes.
- Clearly distinguish observed, derived, and inferred relationships.
- Display provenance, source references, timestamps, and derivation explanations where provided.
- Explain visually or in accompanying text that connected evidence does not itself prove causation.
- Handle empty graphs, too-large result sets, missing nodes, and API failures.
- Ensure every selectable node or evidence link resolves to a real permitted record.

### 5.9 Reports

- Generate reports through the backend and show real job/generation status.
- Display methodology, metric definitions, sources, freshness, limitations, facts, hypotheses, recommendations, and experiment options when returned.
- Fetch saved report versions from the backend.
- Download only actual generated report content in formats the backend supports.
- Do not generate an empty or fabricated file to simulate a successful export.
- Do not publish, email, or externally share a report unless a real endpoint exists and the user explicitly confirms the action.
- Test unauthorized evidence IDs and report access across workspaces.

### 5.10 Errors, empty states, accessibility, and responsive layout

Across all routes:

- Provide loading, empty, error, partial, and success states appropriate to actual server responses.
- Make retries explicit and bounded; do not automatically repeat unsafe mutations.
- Use accessible labels, keyboard navigation, focus management, semantic headings, and announced validation/status changes.
- Ensure dialogs can be opened and dismissed by keyboard and have clear focus behavior.
- Ensure responsive layouts work on supported desktop/tablet/mobile widths.
- Check light and dark themes if both are present.
- Avoid using color alone to communicate status.
- Never hide permission failures behind an infinite spinner.
- Every visible button, link, menu item, chart control, tab, filter, and form must perform its stated action or be visibly disabled with a reason.

**Phase 4 acceptance:** Every existing production screen and visible action is accounted for in the route-to-screen matrix and uses a real API or honest unavailable state.

---

## 6. Phase 5 — Database migrations and clean-environment setup

The completion report states that Alembic migrations do not currently exist and that schema creation uses `create_all` for development/tests. Confirm the repository state before changing it.

If the backend uses SQLAlchemy and migrations are absent:

1. Add Alembic as a compatible project dependency and configure it to use the application's existing database settings and metadata.
2. Create an initial migration representing the current intended schema. Review the generated migration manually; do not blindly trust autogeneration.
3. Include all existing tables, indexes, uniqueness constraints, foreign keys, tenant ownership constraints, and required database-level protections.
4. Ensure migrations do not contain credentials or environment-specific database URLs.
5. Add documented commands for creating a new migration, reviewing it, upgrading, and checking the current revision.
6. Make startup behavior explicit. Production should not silently run destructive schema creation or unreviewed migrations at import time.
7. Keep `create_all` only where appropriate for isolated tests or explicitly documented lightweight development use. Do not let it mask missing production migrations.
8. Test an empty database upgrade, an existing-schema upgrade path where feasible, and a fresh test database.
9. Verify rollback strategy and document any migration that is not safely reversible.
10. Update `docker-compose.yml`, `.env.example`, and `README.md` only where needed to make the migration path reproducible.

If the project intentionally chooses not to use Alembic, document a technically sound alternative with versioned schema changes and tests. Do not simply leave the gap undocumented.

**Acceptance:** A clean database can be created from the documented migration process, and schema version is observable. No claim of migration completion without a successful clean-database test.

---

## 7. Phase 6 — Lint, type-check, frontend tests, and build

### 7.1 Frontend package scripts

Inspect the existing package manager and scripts. Add or correct scripts using the project's actual tools; do not add a tool solely to create a green-looking command.

Provide appropriate equivalents of:

- `build`
- `typecheck`
- `lint`
- `test`
- `test:e2e` or the documented browser smoke test

If the frontend uses TypeScript, run the compiler in no-emit/type-check mode as configured. If it uses JavaScript, use the project's configured static checks and tests rather than claiming TypeScript checking applies.

### 7.2 Frontend test coverage

At minimum, cover:

- API client success/error/timeout/auth behavior.
- Authentication and workspace selection.
- Branding on primary and authentication routes.
- Upload and ingestion job state transitions.
- Mapping review submission and API failure.
- Integration configured/unconfigured/connected/error states.
- Campaign analytics with real-shaped responses, missing metrics, and empty results.
- Chat response with citations, abstention, and backend error.
- Evidence Graph path rendering and provenance labels.
- Report generation, status, and actual download behavior.
- Workspace cache isolation.
- No mock fallback after production API failure.
- Every critical action's disabled/pending state.

Use component tests for deterministic behavior and browser tests for critical user journeys. Tests may use controlled API mocks, but include at least one test environment that runs the frontend against the actual backend/test database.

### 7.3 Backend lint and type checking

- Inspect `pyproject.toml` and current Python tool configuration.
- Configure a consistent Ruff lint/format check if it fits the project.
- Configure a dedicated type checker (for example, mypy or Pyright) appropriate to the current codebase.
- Start with checks that do not silently exclude core application modules.
- Fix real findings or document a narrow, justified exclusion with a follow-up issue and rationale.
- Do not use broad ignores or disable checks globally to obtain a passing result.
- Re-run the full backend test suite after fixes.

### 7.4 Required final command record

Run and record the exact commands actually supported by the project. The final report must include command, exit status, and summary; include a command only if it was run.

Expected categories:

- Python tests: `python -m pytest tests -q`
- Python lint: the configured Ruff command
- Python type-check: the configured type checker command
- Frontend dependency install using the repository's lockfile and package manager
- Frontend lint
- Frontend type-check
- Frontend unit/component tests
- Frontend production build
- Browser/E2E smoke test
- Migration upgrade against a clean test database
- API health/readiness and OpenAPI smoke check
- End-to-end critical journey

Do not say "all checks pass" if any required check was skipped or failed. Report skipped checks as skipped and explain why.

---

## 8. Phase 7 — End-to-end critical journey

Build a repeatable test journey using synthetic data and isolated test infrastructure. The journey should use the actual frontend and backend, not a collection of disconnected mocked components.

1. Start the documented services and verify readiness.
2. Create or authenticate a test user.
3. Create/select a workspace.
4. Upload a clearly labelled synthetic fixture.
5. Confirm that a real ingestion job is created and reaches its actual status.
6. Exercise mapping review where the fixture contains a consequential ambiguous field.
7. Confirm the mapping decision persists and ingestion resumes.
8. Verify canonical records and metric definitions.
9. Verify search results in vector/BM25/hybrid retrieval where configured.
10. Ask an investigation question through the frontend.
11. Verify the answer's metric values and citations against backend evidence.
12. Open the cited evidence/source detail.
13. Open the Evidence Graph and verify provenance and observed/inferred labels.
14. Generate a report and verify its stored data and actual download.
15. Delete or reprocess the synthetic source.
16. Confirm dependent records, chunks, embeddings, graph contributions, and caches are cleaned or recomputed according to the source lifecycle contract.
17. Verify another tenant cannot read, search, cite, mutate, or delete the first tenant's data.
18. Verify an unconfigured provider is shown as unconfigured, not connected.
19. Verify hosted model fallback remains disabled unless explicit consent is configured.
20. Verify the UI continues to identify itself as **Marketing AI SaaS** throughout the journey.

The journey must clean up its own data and be safe to rerun. It must not require live customer credentials. Live-provider smoke tests remain opt-in and credential-gated.

---

## 9. Phase 8 — Security and privacy regression checks

Preserve and rerun the existing backend security tests. Add frontend/backend integration checks for the following:

- An unauthenticated user cannot access private routes or APIs.
- A user cannot access another workspace by editing a URL, request body, query parameter, or cached client state.
- Switching workspaces does not briefly display the previous workspace's private records.
- API `403`/`404` responses are handled according to the server contract and do not reveal private details.
- Source excerpts, credentials, OAuth tokens, bearer tokens, and private prompts are not printed in browser/server logs.
- Retrieved text containing instructions cannot trigger unauthorized actions or override system policy.
- The frontend does not render untrusted source text as executable HTML.
- Upload errors do not reveal server filesystem paths or stack traces.
- OAuth secrets remain server-side.
- Provider connection status is based on persisted backend status.
- No live campaign publish/send/change action is available without a real approved backend action and explicit confirmation.
- Hosted-model fallback is never silently enabled by frontend behavior.
- Synthetic demo data is labelled and is never silently loaded into a customer workspace.
- A failed request cannot fall back to a stale cached value from a different tenant.
- Logout/session expiry clears private UI state and redirects safely.
- CSRF protection is respected if cookie-based auth is used.

Do not weaken server-side authorization in order to make frontend navigation work. UI permissions improve usability; the backend remains authoritative.

---

## 10. Phase 9 — Integration and capability truthfulness

The existing report states that live Google Analytics/Mailchimp sync is credential-gated and local fixtures are used for tests. Do not claim live integration success without real credentials and a real connection.

For each supported connector:

- Verify the official API implementation and current scopes against official provider documentation when making code changes.
- Test OAuth state/PKCE behavior as applicable, token encryption, refresh/expiry, pagination, rate limits, incremental cursor behavior, retries, partial failures, and disconnect.
- Pass provider records through the shared canonical ingestion pipeline.
- Keep provider-specific unsupported fields and limitations visible in the capability matrix.
- Provide an opt-in live smoke test that can run when credentials are configured.
- Report the result honestly: `not configured`, `configured but not connected`, `connected`, `syncing`, `stale`, `error`, or `disconnected`, as supported.
- Never insert fixture data into a live connector result to make the screen look populated.

If live credentials are unavailable during this completion pass, mark the live smoke test as **not run — credentials unavailable**. This is a limitation, not a passing test.

---

## 11. Phase 10 — Documentation and status reconciliation

Update the following files only after the implementation and checks are complete.

### `MarketingAiSaas -> PLAN.md`

- Mark frontend API wiring complete only after the relevant screens and tests use the real backend.
- Track branding verification as a named acceptance item.
- Record migration implementation and clean-database verification.
- Record frontend build, type-check, lint, tests, browser smoke, Python lint/type-check, and backend tests separately.
- Keep live provider tests credential-gated when credentials are unavailable.
- Record known limitations without hiding them.
- Do not mark work complete because code was added; link or record the verification evidence.

### `MarketingAiSaas -> README.md`

- Keep setup commands aligned with the actual lockfile/package manager.
- Document frontend environment variables and how the frontend reaches `/api/v1`.
- Document the exact frontend and backend verification commands.
- Document migrations and clean database setup.
- Explain how to configure live integrations and distinguish local fixture tests from live-provider verification.
- Preserve the accurate privacy statement: local inference is not the same as local-only data storage; hosted fallback requires explicit opt-in.
- Use **Marketing AI SaaS** as the product's user-facing name.

### `MarketingAiSaas -> procedure.md`

- Preserve the original procedure as the baseline implementation contract.
- If updating its status notes, do not erase the original requirements or claim they were always completed.
- Point to `procedure2.md` as the follow-on completion procedure, if appropriate.

### `MarketingAiSaas -> procedure2.md`

- Keep this file as the actionable follow-on contract.
- Update its completion checklist only when verified.
- Do not replace implementation instructions with a summary claiming all work is done.

### Frontend user-facing text

- All product identity references must say **Marketing AI SaaS**.
- Customer campaign names, product names, workspace names, and imported source content are data, not product branding, and must not be rewritten as part of the branding sweep.
- Do not expose internal folder names or developer-only implementation labels in the interface unless intentionally shown as technical information.

---

## 12. Release acceptance checklist

Do not call the remaining work complete until every applicable item below is verified.

### Branding
- [ ] The user-facing product name is exactly **Marketing AI SaaS** everywhere in the frontend.
- [ ] Browser title and metadata use the correct brand.
- [ ] Authentication, onboarding, main shell, settings, errors, and empty states use the same brand.
- [ ] Automated branding check passes.
- [ ] No old/prototype product identity appears in the production frontend.

### Frontend/backend integration
- [ ] A route-to-screen API contract matrix exists and matches actual backend routes.
- [ ] Production screens use the real `/api/v1` backend.
- [ ] No production screen silently uses mock fixtures.
- [ ] Every visible action works or is honestly disabled with a reason.
- [ ] Loading, empty, error, partial, and success states reflect actual backend responses.
- [ ] Auth and workspace state are correctly handled.
- [ ] Upload, mapping review, integrations, analytics, chat, evidence, and reports are wired wherever supported.
- [ ] Citations resolve to real authorized evidence.
- [ ] Downloads contain actual generated report content.
- [ ] Cross-workspace caches and UI state are isolated.

### Backend and database
- [ ] Existing baseline backend suite reruns successfully.
- [ ] Alembic migrations exist and pass a clean-database upgrade, or a documented and tested alternative is accepted.
- [ ] Health, readiness, and OpenAPI smoke checks pass.
- [ ] Tenant isolation and source deletion/reprocessing tests remain green.
- [ ] No credentials or customer content are exposed in logs.

### Quality gates
- [ ] Frontend production build passes.
- [ ] Frontend lint passes.
- [ ] Frontend type-check/static checks pass.
- [ ] Frontend unit/component tests pass.
- [ ] Browser/E2E smoke test passes.
- [ ] Python lint passes.
- [ ] Python type-check passes.
- [ ] Full backend tests pass after final code changes.
- [ ] End-to-end synthetic critical journey passes.
- [ ] All skipped checks are disclosed; none is represented as passing.

### Integrations and product truthfulness
- [ ] Unconfigured providers are not presented as connected.
- [ ] Live integration behavior is tested only with actual credentials; otherwise the test is marked not run.
- [ ] Hosted-model fallback is fail-closed unless explicitly enabled by the user.
- [ ] No live campaign or provider mutation occurs without explicit authorized approval.
- [ ] Synthetic demo data is labelled and opt-in.
- [ ] Reports, analytics, citations, and graph relationships do not fabricate facts or causation.

### Handoff
- [ ] `PLAN.md` and `README.md` reflect the verified state.
- [ ] Known limitations are listed honestly.
- [ ] No unfinished placeholders or fake success states remain in the agreed scope.
- [ ] Final report lists commands actually run, their outcomes, and any remaining blocked items.

---

## 13. Required final completion report

When implementation is finished, provide a concise but evidence-based handoff containing:

1. **Branding:** where the exact `Marketing AI SaaS` name was verified and which automated checks cover it.
2. **Frontend wiring:** the workflows connected to the real backend and any unsupported/configuration-gated workflow.
3. **Database:** migration approach and clean-database verification result.
4. **Tests and quality gates:** exact commands, pass/fail status, and summary. Do not include unrun commands in the passing list.
5. **End-to-end journey:** what was exercised and the result.
6. **Security/privacy:** relevant regression checks and outcomes.
7. **Live integrations:** which were truly tested against provider services, which were tested only with fixtures, and which could not run due to missing credentials.
8. **Remaining limitations:** anything not completed, with the reason and impact.

**Final rule:** Do not claim that the application is completely finished until the applicable release checklist has evidence. A green backend suite is an important baseline, but it does not prove frontend integration, migrations, frontend quality gates, or live provider connectivity. Deliver the remaining scope in the existing application, use real backend state, preserve tenant isolation, and keep **Marketing AI SaaS** as the exact user-facing product name everywhere in the frontend.
