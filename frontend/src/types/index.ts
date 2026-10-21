/** Types mirroring the backend OpenAPI response shapes (real contract). */

export interface Campaign {
  id: string;
  name: string;
  status: string;
  channel: string;
  audience: string | null;
  product: string | null;
  start_date: string | null;
  end_date: string | null;
  external_key: string | null;
}

export interface MetricValue {
  metric_name: string;
  value: number | null;
  unit: string;
  definition: string;
  note?: string;
  source_id?: string | null;
  source_version?: number | null;
  date_min?: string | null;
  date_max?: string | null;
}

export interface CampaignSummary {
  campaign_id: string;
  campaign_name: string;
  channel: string;
  date_start: string;
  date_end: string;
  metrics: MetricValue[];
  derived: MetricValue[];
  freshness: {
    source_id: string;
    source_name: string;
    source_version: number | null;
    last_synced_at: string | null;
  };
  limitations: string[];
}

export interface SourceRecord {
  source_id: string;
  name: string;
  file_type: string;
  category: string;
  status: string;
  version: number;
  size_bytes: number;
  record_count: number | null;
  origin: string;
  updated_at: string | null;
  job_id: string | null;
  job_status: string | null;
  review_pending: boolean;
  row_count: number | null;
  ready_count: number | null;
  error_count: number | null;
  warning_count: number | null;
  safe_error: string | null;
}

export interface IngestionJobStatus {
  job_id: string;
  source_id: string;
  status: string;
  stage: string;
  row_count: number;
  ready_count: number;
  error_count: number;
  warning_count: number;
  review_pending: boolean;
  stages: { stage: string; status: string; detail: unknown; started_at: string }[];
}

export interface MappingCandidateApi {
  id: string;
  sheet: string;
  column: string;
  sample_values: string[];
  proposed_field: string;
  alternatives: string[];
  confidence: string;
  reason: string;
  impact: string;
}

export interface MappingReviewResponse {
  job_id: string;
  status: string;
  candidates: MappingCandidateApi[];
  actions_available: string[];
}

export interface ProviderMeta {
  provider: string;
  label: string;
  category: string;
  description: string;
  supported_objects: string[];
  server_configured: boolean;
  workspace_status: string;
  last_synced_at: string | null;
  connection_id?: string;
}

export interface ChatResponse {
  conversation_id: string | null;
  cached?: boolean;
  status: string;
  observed_facts: string[];
  supporting_evidence: string[];
  contradictory_evidence: string[];
  interpretations: string[];
  hypotheses: string[];
  recommendations: string[];
  measurement_plan: string[];
  limitations: string[];
  abstention_reason: string | null;
  citations: string[];
  model_id: string;
  latency_ms: number | null;
  ai_generated: boolean;
}

export interface EvidenceDetail {
  id: string;
  evidence_type: string;
  source: { source_id: string; source_version: number | null; source_name: string };
  campaign_id: string | null;
  metric: { name: string; value: number | null; unit: string; definition: string } | null;
  date_range: { start: string | null; end: string | null };
  excerpt: string;
  locator: string | null;
  distinguishes: { direct_observation: boolean; inferred_or_derived: boolean };
}

export interface GraphNodeApi {
  id: string;
  node_type: string;
  label: string;
  props: Record<string, unknown>;
  source_id: string;
  source_version: number | null;
  evidence: { chunk_id: string; source_id: string; source_version: number | null; locator: string | null }[];
  evidence_available: boolean;
}

export interface GraphPathPayload {
  nodes: Record<string, GraphNodeApi>;
  paths: { node_ids: string[]; relations: { target: string; relation: string; observed?: boolean }[] }[];
  supporting_node_ids: string[];
  contradicting_node_ids: string[];
  missing_links: { kind: string; detail: string }[];
  notes: string[];
}

export interface ReportRecord {
  id: string;
  campaign_id: string | null;
  date_start: string | null;
  date_end: string | null;
  status: string;
  created_at: string | null;
  payload: Record<string, unknown>;
}

export interface ExperimentRecord {
  id: string;
  name: string;
  hypothesis: string;
  control: string;
  variant: string;
  primary_metric: string;
  guardrail_metrics: string[];
  stopping_rules: string;
  confounders: string[];
  status: string;
}

export interface RecommendationRecord {
  id: string;
  campaign_id: string;
  action: string;
  observed_facts: string[];
  interpretation: string;
  hypothesis: string;
  supporting_evidence: string[];
  contradictory_evidence: string[];
  primary_metric: string;
  risks: string[];
  missing_data: string[];
  status: string;
}

export interface UsageResponse {
  sources: number;
  metric_rows: number;
  indexed_chunks: number;
  ingestion_jobs: number;
  jobs_in_progress: number;
  members: number;
  storage_bytes: number;
  notes: string;
}

export interface AuditEventRecord {
  id: string;
  actor: string;
  action: string;
  detail: Record<string, unknown>;
  created_at: string | null;
}

export interface EvaluationRunRecord {
  id: string;
  dataset_version: string;
  mode: string;
  created_at: string;
  metrics: Record<string, unknown>;
}

export interface ModelStatus {
  connectors: {
    id: string;
    status: string;
    selected_model: string | null;
    capabilities: string[];
    paired_at: string | null;
    last_seen_at: string | null;
  }[];
  privacy: string;
  [key: string]: unknown;
}
