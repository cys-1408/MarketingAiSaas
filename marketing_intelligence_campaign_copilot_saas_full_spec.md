# Marketing Intelligence and Campaign Copilot SaaS

## Full Project Specification and Implementation Blueprint

**Project type:** Multi-tenant SaaS for marketing intelligence, campaign
investigation, and evidence-backed decision support.\
**Core interaction:** Customers upload files and connect marketing
platforms. The system automatically prepares their workspace, requesting
review only for ambiguous mappings.\
**LLM deployment:** SaaS-hosted application services with an optional customer-side
Ollama companion connector. Model inference runs on the customer’s own computer;
the SaaS does not expose the customer’s Ollama API to the public internet.\
**Differentiator:** The Campaign Evidence Graph connects recommendations
to campaign metrics, customer evidence, product facts, source records,
and experiments.

## 1. Executive Summary

Marketing teams store campaign performance, customer feedback, CRM
records, product documentation, brand guidelines, competitor research,
and historical reports across separate files and platforms.
Investigating why a campaign generated clicks but few purchases often
requires manual data cleaning and cross-source analysis.

Marketing Intelligence and Campaign Copilot automates this work. A
customer creates a workspace, uploads files, and connects supported
platforms. The system inspects and classifies inputs, proposes field
mappings, validates records, resolves entities, calculates supported
metrics, indexes documents, and builds a knowledge graph. Ambiguous
mappings or conflicting definitions enter a focused review queue instead
of being silently guessed.

Once onboarding is complete, users can investigate campaigns through
natural-language chat, compare performance, explore customer objections,
generate brand-compliant content, plan A/B tests, and create
evidence-linked reports. Both uploaded files and live integrations feed
the same canonical data model and shared processing pipeline.

**Product principle:** Customers provide data and resolve meaningful
ambiguities. The SaaS automates the remaining preparation and
investigation workflow.

The system must not invent missing metrics, present correlation as proof
of causation, or cite evidence that does not exist. The default supported
Ollama mode means local model inference, not automatically local data storage:
files, databases, retrieval indexes, and graph data may still be hosted by the
SaaS unless a separate private-deployment option is built.

## 2. Problem Statement

Marketing teams face fragmented data, manual spreadsheet cleanup,
inconsistent metric definitions, disconnected customer feedback, and
generic AI recommendations without traceable evidence. Data also changes
over time, creating stale indexes and answers. Different integrations
may expose different fields, attribution rules, and synchronization
behavior.

The SaaS addresses these problems through automated onboarding,
canonical schemas, data validation, hybrid retrieval, analytics tools, a
knowledge graph, and an evidence-grounded investigation workflow.

## 3. Goals

-   Support file uploads and live marketing-platform integrations from
    the first architecture.
-   Automatically classify inputs, propose mappings, validate data, and
    link entities.
-   Ask customers to review only ambiguous mappings, conflicting
    definitions, and uncertain matches.
-   Normalize inputs into a shared canonical model with provenance and
    version history.
-   Answer natural-language questions using documents, structured
    metrics, and graph relationships.
-   Compare campaigns by channel, audience, offer, creative, product,
    and time period.
-   Discover recurring customer questions and objections from permitted
    data.
-   Generate content using approved product facts and brand rules.
-   Turn recommendations into measurable experiment briefs.
-   Link factual claims to evidence and make the Campaign Evidence Graph
    explorable.
-   Evaluate retrieval, numeric accuracy, citations, tool selection, and
    appropriate abstention.
-   Provide tenant isolation, access control, deletion, source updates,
    monitoring, and usage controls.

## 4. Non-Goals and Boundaries

The initial product is a decision-support platform, not an autonomous
campaign operator. It must not publish content, send campaigns, alter
audiences, or modify live provider settings without explicit
authorization. It must not claim causal explanations from observational
data alone, infer sensitive traits for targeting, or silently treat an
unknown conversion event as a purchase. Not every component must be a
separate microservice in the first release.

## 5. Target Users

-   **Marketing managers:** investigate performance and choose what to
    test.
-   **Growth marketers:** find funnel drop-offs and opportunities.
-   **CRM and lifecycle teams:** improve email, retention, and lifecycle
    messaging.
-   **Product marketing teams:** connect objections and product facts to
    messaging.
-   **Marketing analysts:** validate metrics and prepare reports.
-   **Brand reviewers:** check tone, claims, terminology, and
    disclaimers.
-   **Workspace administrators:** manage members, permissions,
    integrations, retention, and quotas.

## 6. Customer Journey

1.  Create an account and company workspace.
2.  Upload supported files and/or authorize a marketing-platform
    integration.
3.  Inspect formats, schemas, tables, sheets, and source metadata.
4.  Propose mappings to canonical fields using names, aliases, data
    types, sample values, provider schemas, and existing relationships.
5.  Automatically accept validated, unambiguous mappings; queue
    ambiguous or conflicting mappings for review.
6.  Save customer decisions as versioned mapping rules.
7.  Validate, normalize, deduplicate, and store records with provenance.
8.  Build document chunks, embeddings, vector indexes, BM25 indexes, and
    graph relationships in background jobs.
9.  Run quality checks and publish a workspace readiness status.
10. Display summaries, data-quality warnings, source freshness, and the
    investigation chatbot.
11. Answer questions with citations, analytics results, and graph paths.
12. Synchronize connected sources and refresh affected records, indexes,
    graph relationships, and caches.

Users should not configure RAG pipelines, create graph nodes manually,
or operate the databases.

## 7. Inputs and Data Sources

### File uploads

Support CSV, TSV, XLSX, PDF, DOCX, Markdown, plain text, HTML, and JSON
where suitable parsers are available. Files may contain campaign
reports, CRM exports, customer reviews, surveys, support-ticket text,
product catalogs, FAQs, brand guidelines, competitor research collected
from permitted sources, campaign plans, landing-page copy, and
experiment results.

The upload UI must show supported formats, size limits, progress,
errors, and partial extraction warnings.

### Live integrations

Design a provider-neutral connector framework. Initial candidates
include: - Web analytics platforms for sessions, traffic sources,
landing-page behavior, and supported conversion events. - Email
marketing platforms for campaign metadata, delivery and engagement
metrics, and permitted audience information. - CRM platforms for leads,
lifecycle stages, and available downstream outcomes. - Advertising
platforms for campaign, creative, spend, and conversion metrics where
exposed.

Provider scopes, API limits, metric semantics, and accessible fields
must be verified during implementation. Do not promise data a provider
does not expose.

### Shared pipeline rule

Uploads and integrations must feed the same normalization pipeline.
Source-specific adapters may parse different formats, but analytics,
retrieval, and graph construction should use shared canonical entities
and metric contracts.

## 8. Automated Ingestion and Mapping

### Pipeline stages

1.  Register the source, tenant, owner, source version, and job.
2.  Inspect file type, encoding, sheets, headings, tables, and provider
    metadata.
3.  Classify content as campaign metrics, feedback, product facts, brand
    rules, CRM records, or another supported type.
4.  Extract structured rows, document text, tables, dates, and source
    locators.
5.  Propose mappings to canonical fields.
6.  Validate types, allowed values, date formats, units, required
    fields, and semantic consistency.
7.  Resolve campaign, product, channel, and segment entities across
    sources.
8.  Queue uncertain mappings and risky transformations for review.
9.  Normalize validated records while preserving original values and
    provenance.
10. Deduplicate and version records.
11. Persist structured records.
12. Build document chunks, embeddings, vector indexes, and BM25 indexes.
13. Create or update graph nodes and edges with provenance.
14. Check record counts, key relationships, metric definitions, and
    index readiness.
15. Publish ready, partially ready, awaiting review, or failed status.
16. Record timings, errors, retries, and safe diagnostics.

### Mapping outcomes

-   **Auto-accepted:** high-confidence mapping passes deterministic
    validation and has no material semantic ambiguity.
-   **Needs review:** multiple interpretations exist, metric definitions
    conflict, or a match could change the analysis.
-   **Rejected or quarantined:** malformed, unsafe, incompatible, or
    invalid data.

An LLM may propose mappings and explain unfamiliar fields, but it must
not be the sole authority for validation. Use typed schemas, explicit
rules, and test fixtures.

### Mapping review UI

Show the source, sheet/table, original column, representative values,
proposed canonical field, alternatives, explanation, validation results,
and impact if unresolved. Provide confirm, edit, skip, and
leave-unmapped actions. Reuse versioned decisions only when future
source schemas remain compatible; detect schema drift.

### Job states

`queued` → `inspecting` → `mapping` → `awaiting_review` when needed →
`normalizing` → `indexing` → `graph_updating` → `validating` → `ready`.

Also support `partially_ready`, `retryable_failure`, `failed`, and
`cancelled`. Retries should resume from failed stages where possible.

## 9. Example Investigation

A marketer asks: "Our email campaign had good engagement but very few
purchases. What went wrong, and what should we change?"

The system should resolve the campaign and date range, query
delivery/click/session/purchase/revenue metrics, compare suitable
historical campaigns, retrieve customer feedback and product facts,
inspect graph relationships, identify supporting and contradictory
evidence, and distinguish facts from hypotheses. It can then propose a
testable change, generate brand-compliant variants, and prepare an
experiment brief.

Example response:

-   **Observed:** Engagement was strong, but purchase conversion was
    lower than the selected comparison.
-   **Evidence:** Show exact values, definitions, date range, and source
    references.
-   **Possible explanation:** Feedback contains recurring delivery-cost
    questions. If the landing page does not clearly answer them, this
    may be a hypothesis worth testing.
-   **Recommendation:** Test clearer delivery information for an
    eligible audience.
-   **Measurement:** Purchase conversion as the primary metric, with
    unsubscribe rate and revenue per recipient as guardrails.
-   **Limitations:** Explain missing session tracking, attribution
    uncertainty, and sample-size issues.

Demo numbers must be labelled synthetic. Never invent performance
values.

## 10. Required Technology Domain and Real Use

  -----------------------------------------------------------------------
  Technology                          Concrete implementation role
  ----------------------------------- -----------------------------------
  **LLM**                             Interpret questions, propose
                                      mappings, synthesize evidence,
                                      draft content, and plan
                                      experiments.

  **RAG**                             Ground answers in uploaded reports,
                                      feedback, product docs, brand
                                      rules, and historical results.

  **Agentic RAG**                     Coordinate multi-step retrieval,
                                      analytics, graph queries, and
                                      verification.

  **LangChain**                       Model interfaces, prompts,
                                      retrievers, structured outputs, and
                                      tool wrappers.

  **LangGraph**                       Stateful investigation workflow
                                      with routing, validation, bounded
                                      retries, and review gates.

  **Vector Database**                 Store embeddings and metadata for
                                      semantic retrieval.

  **Embeddings**                      Represent document chunks and
                                      evidence for semantic similarity
                                      search.

  **Hybrid Search**                   Combine semantic retrieval with
                                      lexical search.

  **BM25**                            Retrieve exact campaign IDs,
                                      product names, phrases, and domain
                                      terms.

  **Reranking**                       Re-score candidates for query
                                      relevance before synthesis.

  **Knowledge Graph**                 Represent campaigns, products,
                                      segments, messages, feedback,
                                      metrics, and experiments as
                                      entities and relationships.

  **Graph Retrieval**                 Traverse connected relationships to
                                      find evidence missed by flat
                                      retrieval.

  **MCP**                             Expose approved analytics, CRM,
                                      product, graph, and reporting tools
                                      through Model Context Protocol.

  **Tool Calling**                    Request typed operations such as
                                      campaign comparison, metric
                                      calculation, feedback search, and
                                      report generation.

  **Query Rewriting**                 Turn vague questions into focused
                                      retrieval queries and normalize
                                      terminology.

  **Contextual Compression**          Keep relevant passages while
                                      preserving source references and
                                      qualifications.

  **Semantic Chunking**               Split narrative documents by
                                      meaningful sections rather than
                                      fixed token counts alone.

  **Metadata Filtering**              Filter by tenant, permission,
                                      campaign, product, channel, date,
                                      source type, and version.

  **Citation Grounding**              Link factual claims to real source
                                      rows, pages, records, or analytics
                                      outputs.

  **Hallucination Detection**         Check claim support and numerical
                                      correctness; qualify or remove
                                      unsupported claims.

  **RAG Evaluation**                  Measure retrieval relevance,
                                      evidence coverage, faithfulness,
                                      citations, and abstention.

  **Guardrails**                      Enforce permissions, schema
                                      validation, privacy,
                                      prompt-injection defenses, brand
                                      rules, and approval.

  **Semantic Caching**                Reuse eligible results only when
                                      permissions, source versions, and
                                      freshness remain valid.

  **FastAPI**                         Serve authenticated APIs for
                                      uploads, jobs, chat, analytics,
                                      integrations, and reports.

  **Observability**                   Track ingestion, retrieval, graph
                                      queries, tools, latency, cost,
                                      errors, cache behavior, and
                                      evaluation.
  -----------------------------------------------------------------------

## 11. High-Level Architecture

``` mermaid
flowchart TD
    USER[Customer and Workspace Members] --> UI[React and TypeScript UI]
    UI --> API[FastAPI Gateway]
    API --> AUTH[Authentication, Tenant Isolation and Permissions]
    AUTH --> UPLOAD[File Upload Service]
    AUTH --> CONN[Connector Framework]
    UPLOAD --> JOBS[Background Ingestion Jobs]
    CONN --> JOBS
    JOBS --> INSPECT[Inspection and Classification]
    INSPECT --> MAP[Automatic Mapping and Validation]
    MAP --> REVIEW[Ambiguity Review Queue]
    REVIEW --> NORM[Canonical Normalization]
    MAP --> NORM
    NORM --> PG[(PostgreSQL)]
    NORM --> OBJ[(Object Storage)]
    NORM --> INDEX[Chunking, Embeddings and Indexing]
    INDEX --> VDB[(Vector Database)]
    INDEX --> BM25[BM25 Index]
    NORM --> GRAPHBUILD[Graph Construction]
    GRAPHBUILD --> KG[(Knowledge Graph)]
    API --> AGENT[LangGraph Investigation Workflow]
    AGENT --> QUERY[Query Rewriting and Planning]
    QUERY --> RET[Hybrid Retrieval]
    RET --> VDB
    RET --> BM25
    RET --> RERANK[Reranking and Contextual Compression]
    AGENT --> GR[Graph Retrieval]
    GR --> KG
    AGENT --> TOOLS[Typed Analytics and Domain Tools]
    TOOLS --> PG
    TOOLS --> MCP[MCP Tool Interface]
    RERANK --> EVIDENCE[Evidence Assembly]
    GR --> EVIDENCE
    TOOLS --> EVIDENCE
    EVIDENCE --> ROUTER[Model Provider Router]
    ROUTER --> LOCAL[Customer-Side Connector]
    LOCAL --> OLLAMA[Ollama on Customer Computer]
    ROUTER --> HOSTED[Optional Hosted Model Provider]
    OLLAMA --> VERIFY[Citation Grounding and Hallucination Checks]
    HOSTED --> VERIFY
    VERIFY --> RESULT[Answer, Recommendation and Experiment Plan]
    RESULT --> UI
    JOBS --> OBS[Observability and Evaluation]
    AGENT --> OBS
    VERIFY --> OBS
```

This is a logical architecture. The first deployment can use a modular
backend and a small number of worker processes.

### 11.1 Customer-side Ollama inference architecture

**Required product behavior:** A customer can choose an Ollama model running
on their own computer. The SaaS continues to host the web application,
authentication, file processing, canonical data, retrieval services, analytics,
knowledge graph, and agent orchestration unless an explicitly separate private
installation is provided. The selected Ollama model performs inference on the
customer's hardware.

Recommended request path:

1. The user installs Ollama and downloads a supported model locally.
2. The user installs a small signed **Marketing Copilot Local Connector** on
their computer and pairs it with their SaaS account using a short-lived code.
3. The connector makes an outbound authenticated TLS connection to the SaaS
control plane. Do not require inbound ports, router changes, or a public Ollama
endpoint.
4. When an investigation reaches a model step, the SaaS model router sends the
minimum required prompt, retrieved context, tool schema, and request ID through
the connector channel.
5. The connector calls the customer's local Ollama API, validates the response
format, and returns the result through the authenticated channel.
6. SaaS-side verification checks citations, numbers, permissions, and policy
before the result is displayed.
7. The connector reports model name/version, health, latency, and errors, but
must not send prompts or model outputs to telemetry by default.

**Important boundary:** Local inference does not mean zero data leaves the SaaS.
If uploaded files and retrieval indexes are stored in the SaaS, the SaaS will
send relevant retrieved snippets to the customer's local connector for model
inference. Conversely, using local Ollama does not stop source files, analytics,
embeddings, graph data, or chat history from being stored in the cloud. Explain
this clearly in onboarding and settings.

#### Connector safety requirements

- Bind the local Ollama API to loopback by default; never ask users to expose it
  directly to the public internet.
- The connector should make outbound TLS connections only, authenticate each
  session, use short-lived pairing tokens, rotate/revoke credentials, and
  support immediate disconnect.
- Do not run arbitrary shell commands or arbitrary MCP tools on the customer
  machine. The connector should only invoke the configured Ollama endpoint and
  narrowly defined local health/model-management operations.
- Validate message sizes, request IDs, model names, timeouts, and response
  schemas. Apply rate limits and cancellation.
- Require explicit user consent before installing, starting on login, or
  allowing remote inference requests. Show a visible connected/disconnected
  status and the selected model.
- Never silently download a model, change system configuration, or execute
  generated code. Model downloads and updates must be user initiated.
- Provide connector logs that exclude prompt content by default and let users
  export diagnostic logs after review.
- Keep tenant authorization in the SaaS backend. A connector is not an
  authorization boundary and must not receive another tenant's requests.

#### Model capability compatibility

Create a provider-neutral `ModelAdapter` interface for chat, structured output,
tool-call proposals, cancellation, health checks, and capability reporting.
Ollama model capabilities vary. At connection time, run a short compatibility
check for the configured model's context length, JSON/structured output, tool
calling behavior (if supported), and response latency. LangGraph must not assume
that every local model can call tools reliably. The application—not the model—
executes tools after validating the proposed tool name and arguments.

If a selected model cannot reliably produce structured output or tool-call
proposals, use deterministic routing and schema-constrained fallback steps,
reduce agent autonomy, or mark that model as unsupported for those workflows.
A user may select a different model or an explicitly enabled hosted fallback.
Hosted fallback must be opt-in and clearly indicate that prompts/context will be
sent to the selected hosted provider. Never silently switch from local inference
to a cloud model.

#### Local hardware and availability behavior

The customer's machine must be on, reachable by the connector, and running
Ollama for local inference. Handle sleeping devices, offline connectors, model
not installed, out-of-memory errors, model load time, slow generation, and
context-window overflow. Queue or pause the model-dependent step, explain the
reason, and offer retry or an explicitly consented fallback. Do not report a
failed local inference as a completed analysis.

For an 8 GB RAM computer with integrated graphics, recommend starting with a
small quantized model and a conservative context window. Large models can be
slow or fail due to memory pressure. The product should show model requirements
and test actual latency rather than promising all models will work.

#### Data residency modes

| Mode | Model inference | Files and retrieval data | Product implications |
|---|---|---|---|
| SaaS + customer Ollama (initial target) | Customer computer | SaaS cloud | Local inference; relevant context crosses to the connector over TLS |
| SaaS + hosted model (optional) | Hosted provider | SaaS cloud | Only with explicit selection and disclosure |
| Private customer deployment (future, separate architecture) | Customer infrastructure | Customer infrastructure | Requires private deployment of API, storage, databases, indexes, graph, jobs, and observability |

Do not describe the initial SaaS + customer Ollama mode as fully on-device,
offline, or end-to-end local. The SaaS needs connectivity for cloud data,
retrieval, integrations, and orchestration. A genuinely private/on-premises mode
is a distinct deployment target and should be scoped separately.

## 12. SaaS Security and Tenant Isolation

Every company-owned record must be associated with a tenant/workspace.
Enforce authorization across APIs, jobs, relational queries, object
storage, vector search, graph queries, caches, integrations, reports,
and conversation history. A tenant ID in metadata is not enough without
server-side checks.

Use role-based permissions, such as owner, administrator, analyst,
marketer, reviewer, and read-only viewer. Encrypt provider credentials,
use least-privilege OAuth scopes, and support disconnection and
revocation.

Source deletion should trigger cleanup or recomputation of extracted
records, chunks, embeddings, and graph edges. If derived data has
multiple sources, remove only the deleted source's contribution.

Treat uploaded documents and retrieved content as untrusted. Do not
follow embedded instructions that attempt to override policy, reveal
secrets, or invoke unauthorized actions. Minimize personal data, redact
logs, and avoid inferring sensitive traits.

## 13. Canonical Data Model

Suggested relational entities:

-   `tenants`, `workspaces`, `users`, `memberships`, `roles`,
    `permissions`
-   `sources`, `source_versions`, `ingestion_jobs`,
    `ingestion_stage_runs`, `ingestion_errors`
-   `mapping_rules`, `mapping_candidates`, `mapping_reviews`
-   `campaigns`, `campaign_metrics`, `products`, `segments`, `messages`,
    `landing_pages`
-   `feedback_items`, `experiments`, `experiment_results`
-   `integration_connections`, `sync_runs`, `sync_cursors`
-   `evidence_records`, `recommendations`, `conversation_sessions`
-   `evaluation_runs`, `audit_events`, `cache_metadata`

The vector database stores chunks, embeddings, and retrieval metadata.
The graph database stores entities and relationships. All stores must
use stable IDs and tenant-aware authorization.

Each metric should define its numerator, denominator, unit, aggregation
rule, attribution method/window, valid dimensions, source precedence,
known limitations, version, and effective date. Similar-looking metrics
must not be treated as equivalent until definitions are reconciled.

Example evidence record:

``` json
{
  "evidence_id": "ev_1042",
  "tenant_id": "tenant_example",
  "source_id": "source_27",
  "source_version": 3,
  "source_type": "campaign_metric",
  "campaign_id": "campaign_27",
  "metric_name": "click_to_purchase_conversion",
  "metric_value": 0.018,
  "metric_unit": "ratio",
  "date_range": {"start": "2026-09-01", "end": "2026-09-14"},
  "metric_definition": "Attributed purchases divided by attributed clicks",
  "evidence_type": "measured_fact",
  "retrieved_at": "2026-10-20T00:00:00Z"
}
```

Illustrative schema only; example values are not claims about a real
campaign.

## 14. Connector Framework

Each provider connector should implement:

-   `connect()` --- establish authorized access.
-   `test_connection()` --- verify access and scopes.
-   `discover_resources()` --- list accessible accounts, campaigns, and
    report types.
-   `fetch_initial_data()` --- import the initial data window.
-   `fetch_incremental_data()` --- retrieve changes from a cursor where
    supported.
-   `normalize()` --- convert provider records into canonical entities.
-   `get_sync_status()` --- report progress, freshness, and errors.
-   `disconnect()` --- revoke or remove access as supported.

Shared connector services should handle OAuth callback validation,
encrypted tokens, refresh behavior, pagination, rate limits, retries,
idempotency, cursors, audit events, and error normalization.

Start with scheduled polling and add webhooks when supported. Track
modifications and deletions according to provider capabilities. Make
imports idempotent and retry transient failures without duplicating
records.

Build one high-value analytics connector and one campaign/CRM connector
first. Verify current API scopes and fields during implementation rather
than assuming all providers expose the same metrics.

## 15. RAG and Retrieval Design

### Document preparation

Parse sources with suitable parsers. Preserve headings, tables, row
references, pages, timestamps, URLs, source IDs, and versions. Use
table-aware processing for metrics and semantic chunking for narrative
documents. Deduplicate near-identical content while preserving lineage.

### Retrieval pipeline

1.  Classify the question and resolve authorized scope.
2.  Rewrite vague questions into focused subqueries.
3.  Apply tenant and permission filters before retrieval.
4.  Retrieve vector candidates and BM25 candidates.
5.  Merge and deduplicate candidates.
6.  Rerank candidates against the question.
7.  Contextually compress passages while preserving citations.
8.  Retrieve connected evidence through graph traversal.
9.  Run analytics tools when numerical answers are needed.
10. Assemble an evidence bundle.
11. Verify citations and numbers before responding.

Combine vector and lexical retrieval using a defined fusion method such
as reciprocal rank fusion or a validated score-combination method.
Evaluate retrieval against a fixed test set.

Every evidence item should preserve a stable ID, source ID, tenant and
permission scope, source locator, version, timestamp, exact excerpt or
metric result, metric definition, and evidence type. Citations must
resolve to actual source material.

## 16. Agentic RAG Workflow

Use LangGraph as a bounded state machine with nodes:

1.  `classify_request`
2.  `resolve_scope`
3.  `rewrite_query`
4.  `plan_investigation`
5.  `retrieve_documents`
6.  `retrieve_graph`
7.  `execute_analytics`
8.  `rerank_and_compress`
9.  `assemble_evidence`
10. `draft_analysis`
11. `verify_claims`
12. `check_guardrails`
13. `request_review`
14. `format_response`
15. `record_feedback`

Set strict limits on tool calls, graph depth, retries, and execution
time. If evidence is insufficient, ask a focused question or abstain
instead of looping indefinitely.

## 17. Analytics Tools and MCP

Suggested typed tools:

-   `get_campaign_summary(campaign_id, start_date, end_date)`
-   `compare_campaigns(campaign_ids, metric_names, date_range)`
-   `get_funnel_metrics(campaign_id, funnel_definition, date_range)`
-   `get_segment_performance(segment_id, campaign_ids, metric_names)`
-   `search_customer_feedback(query, product_id, date_range, source_types)`
-   `get_product_facts(product_id, topic)`
-   `get_brand_rules(channel, content_type)`
-   `query_campaign_graph(entity_type, entity_id, relationship_types, depth_limit)`
-   `get_source_freshness(source_ids)`
-   `create_experiment_brief(hypothesis, control, variant, audience, metrics)`
-   `generate_campaign_report(campaign_id, date_range, evidence_ids)`

Use parameterized, read-only analytics queries by default. Validate
arguments, enforce authorization inside each tool, limit rows and graph
depth, and return structured results with freshness and metric
definitions. Do not expose unrestricted SQL or arbitrary shell
execution.

An MCP server should expose approved analytics, retrieval, product,
graph, and reporting tools. Document each tool's schema, permissions,
side effects, timeout, and audit behavior. MCP does not replace
authorization or validation.

## 18. Knowledge Graph and Campaign Evidence Graph

Node types: `Campaign`, `Channel`, `Message`, `Product`,
`CustomerSegment`, `FeedbackItem`, `Objection`, `MetricObservation`,
`LandingPage`, `Experiment`, `Recommendation`, and `EvidenceSource`.

Relationship types: `USES_CHANNEL`, `TARGETS_SEGMENT`,
`PROMOTES_PRODUCT`, `CONTAINS_MESSAGE`, `LINKS_TO_PAGE`,
`FEEDBACK_MENTIONS`, `EXPRESSES_OBJECTION`, `OBSERVED_WITH_METRIC`,
`ASSOCIATED_WITH_CONVERSION`, `TESTED_IN_EXPERIMENT`, `SUPPORTED_BY`,
`CONTRADICTED_BY`, and `DERIVED_FROM`.

Every edge should preserve provenance, source version, time range when
applicable, and whether it is observed or inferred. A graph edge does
not prove causation.

The graph UI should let users open nodes, inspect sources, follow
evidence paths, see contradictory evidence, and distinguish direct
evidence from inferred links and hypotheses.

## 19. Recommendations, Content, and Experiments

Each recommendation should contain the proposed action, scope,
supporting evidence IDs, observed facts, interpretation, hypothesis,
primary metric, guardrail metrics, risks, missing data, and experiment
plan.

Generate subject lines, email variants, landing-page copy, and ad
concepts using approved product facts and brand rules. Validate claims
against source material and show citations for factual product claims.

Experiment briefs should specify the hypothesis, control, variant,
eligible audience, primary metric, guardrails, sample-size
considerations, duration, stopping rules, confounders, and success
criteria. Do not fabricate predicted improvement percentages.

Require explicit approval before publishing content, sending campaigns,
or changing live settings.

## 20. Hallucination Detection and Guardrails

The verifier should split the answer into factual claims, map each claim
to evidence, check whether the evidence supports its wording, validate
numbers and denominators, flag causal language unsupported by
experimental evidence, detect contradictory or stale sources, and remove
or qualify unsupported claims.

Use transparent labels such as `strongly supported`,
`partially supported`, `hypothesis`, and `insufficient evidence` until
numeric confidence is calibrated.

Guardrails cover tenant permissions, PII minimization, prompt injection,
tool allowlists, schema validation, output constraints, brand rules,
quotas, and human approval.

## 21. Semantic Caching

Cache repeated low-risk questions only when tenant, permissions, source
versions, date range, metric definitions, model/prompt versions, and
freshness remain compatible. Invalidate affected entries after source
imports, mapping changes, metric-definition changes, permission changes,
or synchronization. Re-check authorization on cache hits and avoid
caching sensitive customer-level outputs.

## 22. RAG Evaluation and Testing

Build a version-controlled set of answerable, ambiguous, conflicting,
outdated, and unanswerable questions.

**Retrieval metrics:** Recall@k, Precision@k, MRR, nDCG@k, evidence
coverage, and tenant/permission filter correctness.

**Answer metrics:** faithfulness, citation correctness/completeness,
numeric accuracy, relevant finding coverage, correct
fact-versus-hypothesis labeling, appropriate abstention, and brand
compliance.

**Agent/tool metrics:** correct tool selection, argument validity,
analytics correctness, unnecessary tool calls, completion/failure rate,
latency, token usage, and cost.

**Ingestion/connector metrics:** mapping accuracy, review rate, parsing
success, duplicate detection, entity-resolution precision,
incremental-sync correctness, retry recovery, reprocessing correctness,
and source-deletion cleanup.

Test malformed files, ambiguous conversion columns, duplicate uploads,
schema drift, conflicting metric definitions, expired credentials,
provider rate limits, pagination failures, partial imports, prompt
injection, cross-tenant access, empty retrieval, stale caches, inferred
graph edges, and unsupported causal claims.

## 23. Observability

Track ingestion stage timings, row counts, mapping decisions, schema
drift, connector freshness, API errors, retrieval candidate counts,
reranking and graph latency, tool calls, model versions, token usage,
citation verification, evaluation scores, cache invalidation, storage
use, and tenant quotas.

Use structured logs and traces. Redact personal data, credentials, and
sensitive customer text. Provide dashboards for ingestion health, stale
connections, answer quality, latency, cost, and errors.

## 24. FastAPI Endpoint Plan

**Workspace and access** - `POST /api/v1/workspaces` -
`GET /api/v1/workspaces/{workspace_id}` -
`POST /api/v1/workspaces/{workspace_id}/members` -
`GET /api/v1/workspaces/{workspace_id}/usage`

**Uploads and ingestion** - `POST /api/v1/sources/uploads` -
`POST /api/v1/ingestion/jobs` - `GET /api/v1/ingestion/jobs/{job_id}` -
`GET /api/v1/ingestion/jobs/{job_id}/mapping-review` -
`POST /api/v1/ingestion/jobs/{job_id}/mapping-review` -
`POST /api/v1/sources/{source_id}/reprocess` -
`DELETE /api/v1/sources/{source_id}`

**Integrations** - `GET /api/v1/integrations` -
`POST /api/v1/integrations/{provider}/connect` -
`GET /api/v1/integrations/{provider}/callback` -
`POST /api/v1/integrations/{connection_id}/sync` -
`GET /api/v1/integrations/{connection_id}/status` -
`DELETE /api/v1/integrations/{connection_id}`

**Intelligence** - `POST /api/v1/chat` - `GET /api/v1/campaigns` -
`GET /api/v1/campaigns/{campaign_id}/summary` -
`POST /api/v1/campaigns/compare` -
`GET /api/v1/evidence/{evidence_id}` -
`GET /api/v1/graph/entities/{entity_id}` -
`POST /api/v1/experiments/brief` - `POST /api/v1/reports`

**Operations** - `GET /health` - `GET /ready` -
`POST /api/v1/evaluations/runs`

Use Pydantic models, stable error codes, request IDs, idempotency where
appropriate, and actionable errors without secrets.

## 25. Suggested Repository Structure

``` text
marketing-intelligence-copilot/
├── app/
│   ├── api/
│   │   ├── routes_auth.py
│   │   ├── routes_workspaces.py
│   │   ├── routes_uploads.py
│   │   ├── routes_ingestion.py
│   │   ├── routes_integrations.py
│   │   ├── routes_chat.py
│   │   ├── routes_campaigns.py
│   │   ├── routes_evidence.py
│   │   └── routes_reports.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── tenancy.py
│   │   └── logging.py
│   ├── ingestion/
│   │   ├── inspection.py
│   │   ├── classification.py
│   │   ├── parsers.py
│   │   ├── mapping.py
│   │   ├── validation.py
│   │   ├── normalization.py
│   │   ├── deduplication.py
│   │   └── jobs.py
│   ├── connectors/
│   │   ├── base.py
│   │   ├── oauth.py
│   │   ├── sync.py
│   │   └── providers/
│   ├── retrieval/
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── vector_search.py
│   │   ├── bm25_search.py
│   │   ├── hybrid_search.py
│   │   ├── reranking.py
│   │   └── compression.py
│   ├── graph/
│   │   ├── schema.py
│   │   ├── construction.py
│   │   ├── retrieval.py
│   │   └── evidence_paths.py
│   ├── agents/
│   │   ├── state.py
│   │   ├── workflow.py
│   │   ├── nodes.py
│   │   └── prompts.py
│   ├── tools/
│   │   ├── analytics.py
│   │   ├── feedback.py
│   │   ├── products.py
│   │   └── reports.py
│   ├── mcp/server.py
│   ├── evaluation/
│   ├── cache/
│   └── main.py
├── frontend/src/
├── data/synthetic_demo/
├── tests/
├── evals/
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── README.md
```

## 26. Implementation Roadmap

### Phase 1 --- SaaS foundation

Implement workspaces, users, roles, tenant-aware authorization, file
uploads, object storage, job status, canonical schemas, and metric
contracts.

**Deliverable:** A user can create a workspace, upload a file, and see
its processing status.

### Phase 2 --- Automatic ingestion and mapping

Implement CSV/XLSX/PDF/DOCX parsing, file classification, schema
suggestions, deterministic validation, review UI, versioned mapping
rules, deduplication, provenance, and retryable jobs.

**Deliverable:** Files are automatically classified and normalized; only
unresolved ambiguities require review.

### Phase 3 --- First live integration

Build the connector contract, secure authorization, initial and
incremental sync, canonical normalization, sync history, rate limits,
and retries.

**Deliverable:** File data and live provider data coexist in the same
workspace.

### Phase 4 --- Structured analytics and basic RAG

Implement metric calculations, document chunking, embeddings, vector
retrieval, metadata filtering, citations, campaign summaries, and the
first chat endpoint.

**Deliverable:** Answers grounded in imported records and source
documents.

### Phase 5 --- Advanced retrieval and evaluation

Add BM25, hybrid search, query rewriting, reranking, contextual
compression, retrieval diagnostics, and a repeatable evaluation set.

**Deliverable:** A measurable retrieval pipeline.

### Phase 6 --- Agentic investigations and MCP

Implement LangChain tools, LangGraph orchestration, bounded analytics
calls, graph retrieval, MCP tools, structured evidence assembly, and
claim verification.

**Deliverable:** Investigations combine documents, analytics, and graph
relationships.

### Phase 7 --- Knowledge graph and user experience

Build graph entities and edges, the Campaign Evidence Graph UI, content
variants, recommendations, experiment briefs, and visible
uncertainty/missing-data states.

**Deliverable:** Users can trace recommendations to sources.

### Phase 8 --- Customer-side Ollama connector

Implement the provider-neutral model adapter, model capability checks, secure pairing, outbound TLS connector channel, local Ollama invocation, connector health/status UI, timeout/cancellation, audit-safe diagnostics, and opt-in hosted fallback. Test offline, sleeping, slow, incompatible, and out-of-memory model scenarios.

**Deliverable:** A customer can pair their computer, select an installed Ollama model, and complete a grounded investigation without sending inference requests to a hosted LLM.

### Phase 9 --- Production hardening

Add permission-aware semantic caching, invalidation, observability,
quotas, audit events, tenant isolation tests, prompt-injection tests,
source deletion, schema drift handling, and a second connector.

**Deliverable:** A demonstrable SaaS prototype with repeatable tests and
a path to production.

## 27. MVP Scope

The first usable release should include workspace authentication and
tenant isolation; CSV/XLSX plus selected document uploads; automatic
classification and mapping; ambiguity review; one live integration;
canonical schemas; background jobs; campaign analytics; embeddings;
vector search; BM25 hybrid search; query rewriting; reranking;
contextual compression; metadata filtering; LangChain and LangGraph;
typed tools and MCP; a basic knowledge graph; Campaign Evidence Graph
UI; citations and initial hallucination checks; brand-aware content and
experiment briefs; evaluation; guardrails; semantic caching;
observability; source deletion and reprocessing.

Add connectors according to customer demand and verified provider
capabilities. The initial release must include the customer-side Ollama connector, clear disclosure of cloud-stored data, and no silent hosted-model fallback. Do not trade data correctness or tenant security for a larger connector count.

## 28. Demo Plan

Use clearly labelled synthetic data with multiple campaigns, products,
segments, feedback records, brand guidelines, and known metric
definitions.

1.  Create a workspace.
2.  Upload campaign metrics and customer feedback.
3.  Connect a supported analytics or email platform in a test
    environment.
4.  Show automatic classification and mapping.
5.  Include an ambiguous conversion column and demonstrate the review
    step.
6.  Show normalized data and ingestion quality.
7.  Ask why a campaign had strong engagement but weak purchases.
8.  Compare analytics and a relevant historical campaign.
9.  Open feedback and product evidence.
10. Explore the graph path from campaign to segment, objection, metric,
    and recommendation.
11. Generate brand-compliant message variants.
12. Create an experiment brief with primary and guardrail metrics.
13. Ask an unanswerable question and demonstrate correct abstention.
14. Show evaluation results and a request trace.
15. Update a source and demonstrate reprocessing and cache invalidation.

Do not claim fabricated performance improvements. Treat strategies as
hypotheses until measured.

## 29. Success Criteria

-   Users can upload files and connect at least one supported live
    source.
-   Both paths produce compatible canonical records.
-   Ambiguous mappings cannot silently distort critical metrics.
-   Re-imports and synchronization do not create uncontrolled
    duplicates.
-   Every displayed metric includes definition, date range, and source.
-   Factual claims are cited or explicitly qualified.
-   The system distinguishes facts, interpretations, and hypotheses.
-   Missing data produces a limitation rather than invented output.
-   Tenant data cannot be accessed through another tenant's API, vector
    search, graph, jobs, or cache.
-   Source updates refresh dependent records and invalidate stale
    derived data.
-   Recommendations are traceable through the Evidence Graph.
-   Generated content follows brand constraints and requires approval
    before publication.
-   Tests cover retrieval, citations, numeric correctness, mapping, tool
    use, and prompt injection.
-   Operators can inspect ingestion failures, connector freshness,
    latency, and cost without exposing secrets.

Set numerical quality and latency targets after measuring the selected
providers, models, and deployment environment.

## 30. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Incorrect mapping                   Validate types and semantics;
                                      review consequential ambiguity;
                                      version rules.

  Inconsistent metrics                Maintain metric contracts and
                                      reconcile source definitions.

  Duplicate imports                   Use stable IDs, idempotency, source
                                      versions, and deduplication.

  API changes                         Version adapters, monitor errors,
                                      and test provider schemas.

  Stale answers                       Track source versions and
                                      invalidate dependent indexes and
                                      caches.

  Hallucinated explanations           Require evidence, distinguish
                                      hypotheses, and abstain when
                                      unsupported.

  Correlation mistaken for causation  Use cautious language and
                                      controlled experiments.

  Cross-tenant exposure               Enforce authorization at every
                                      layer and test adversarial cases.

  Prompt injection                    Treat retrieved content as
                                      untrusted and isolate it from
                                      system policy.

  High agent cost                     Bound tool calls, measure cost, and
                                      avoid unnecessary agent steps.

  Graph edges mistaken for facts      Preserve provenance and label
                                      inferred relationships.

  Incorrect product claims            Ground claims in approved sources
                                      and require review.

  Excessive scope                     Build a modular backend, one or two
                                      connectors, and one end-to-end
                                      workflow first.
  -----------------------------------------------------------------------

## 31. Future Enhancements

-   Additional CRM, email, advertising, analytics, support, and
    e-commerce connectors.
-   Scheduled reports and alerts for meaningful metric changes.
-   Automated experiment outcome ingestion and evidence-linked learning.
-   Advanced segment discovery and forecasting with uncertainty.
-   Causal inference when data and experimental design justify it.
-   Multilingual feedback analysis.
-   Approval workflows and versioned campaign plans.
-   Detailed lineage from source records to metrics, graph edges, and
    recommendations.
-   Organization governance, custom retention, and advanced audit
    exports.

## 32. Final Summary

Marketing Intelligence and Campaign Copilot is a multi-tenant SaaS that
turns uploaded files and connected marketing platforms into an
automatically prepared, searchable, connected marketing intelligence
workspace.

Its ingestion layer inspects and classifies sources, proposes mappings,
validates records, requests review only when necessary, normalizes data,
and maintains indexes and graph relationships. Its intelligence layer
uses **LLM, RAG, Agentic RAG, LangChain, LangGraph, Vector Database,
Embeddings, Hybrid Search, BM25, Reranking, Knowledge Graph, Graph
Retrieval, MCP, Tool Calling, Query Rewriting, Contextual Compression,
Semantic Chunking, Metadata Filtering, Citation Grounding, Hallucination
Detection, RAG Evaluation, Guardrails, Semantic Caching, FastAPI, and
Observability**---each with a concrete implementation role.

Its defining feature is the **Campaign Evidence Graph**, which traces
recommendations to campaign metrics, customer statements, product facts,
historical evidence, and proposed experiments. The product does more
than generate marketing copy: it connects performance to customer
intent, explains what is known and uncertain, and turns evidence-backed
recommendations into measurable tests.


## 31. Ollama-Specific Acceptance Criteria

The customer-side Ollama feature is complete only when all of the following
are demonstrated:

- A user can pair and revoke a local connector without exposing an inbound
  port or a public Ollama API.
- The UI shows connector status, selected model, last health check, and
  actionable errors.
- A supported local model can answer a question using SaaS-retrieved evidence
  and produce citations that are verified by the SaaS.
- The application validates tool-call proposals and executes tools only on the
  server after permission checks; the model cannot directly execute tools.
- A model timeout, offline computer, unsupported capability, invalid JSON,
  or memory failure is handled without falsely marking the workflow successful.
- Hosted fallback is disabled unless the user explicitly enables it, and every
  fallback is visible in the UI and audit trail.
- Telemetry excludes prompt text, retrieved source content, and generated
  marketing copy by default.
- Disconnecting the connector prevents further local inference requests.
- Tenant-isolation tests prove that connector sessions cannot receive requests
  belonging to another workspace.
- Product onboarding accurately explains that local inference and cloud data
  storage are separate choices.

## 32. Revised Core Technology Map

| Domain requirement | Concrete role in this project |
|---|---|
| LLM | Generates explanations, summaries, hypotheses, copy, and experiment briefs |
| Ollama | Runs the selected local model on the customer's computer |
| RAG | Grounds answers in the customer's indexed campaign and business data |
| Agentic RAG | Runs bounded, iterative investigations when one retrieval pass is insufficient |
| LangChain | Model adapters, prompts, retrievers, and typed tool wrappers |
| LangGraph | Stateful investigation workflow, branching, retries, verification, and approvals |
| Vector Database | Stores and retrieves semantic embeddings, partitioned by tenant/source permissions |
| Embeddings | Encode source chunks and queries for semantic retrieval |
| Hybrid Search | Combines semantic retrieval and lexical matching |
| BM25 | Finds exact terms, campaign IDs, product names, and phrases |
| Reranking | Reorders candidates for relevance to the current question |
| Knowledge Graph | Represents relationships between campaigns, products, segments, objections, and outcomes |
| Graph Retrieval | Traverses relevant relationships and evidence paths |
| MCP | Exposes narrowly scoped, typed tools to compatible agent workflows |
| Tool Calling | Proposes analytics, search, and report actions; server validates and executes them |
| Query Rewriting | Reframes questions for retrieval and source-specific search |
| Contextual Compression | Removes irrelevant retrieved material while preserving evidence and provenance |
| Semantic Chunking | Splits documents around coherent content units |
| Metadata Filtering | Restricts retrieval by tenant, source, campaign, date, and permissions |
| Citation Grounding | Links claims to source rows, documents, pages, and computed metrics |
| Hallucination Detection | Checks claims, numbers, citations, contradictions, and unsupported causality |
| RAG Evaluation | Measures retrieval and answer quality against a curated test set |
| Guardrails | Enforce authorization, tool allowlists, privacy, brand rules, and approvals |
| Semantic Caching | Reuses eligible results only when permission and freshness checks pass |
| FastAPI | Provides authenticated SaaS APIs and orchestration endpoints |
| Observability | Measures workflow health, connector health, model latency, errors, and evaluation |

All items above are required components, not merely optional buzzwords. Each
must have an implementation, tests, and documented acceptance criteria before
being marked complete. Use the smallest practical model and service footprint
that satisfies the requirements; do not split the first release into many
microservices solely to demonstrate terminology.
