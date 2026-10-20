export interface User { id: string; name: string; email: string; role: string; avatarInitials: string; }
export interface Workspace { id: string; name: string; plan: string; memberCount: number; }

export type SourceStatus =
  | "queued" | "inspecting" | "mapping" | "awaiting_review" | "normalizing"
  | "indexing" | "updating_graph" | "validating" | "ready" | "partial"
  | "retryable_failure" | "failed" | "cancelled";

export interface DataSource {
  id: string; name: string; type: "csv" | "xlsx" | "pdf" | "docx" | "json" | "html" | "txt";
  category: string; records: number; status: SourceStatus;
  updatedAt: string; version: number;
}

export interface MappingCandidate {
  id: string; sourceFile: string; sheet: string; column: string; sampleValues: string[];
  proposedField: string; alternatives: string[]; confidence: "high" | "medium" | "low";
  reason: string; impact: string; resolved: boolean;
}

export interface Integration {
  id: string; name: string; category: "web_analytics" | "email" | "crm" | "advertising" | "other";
  description: string; status: "connected" | "not_connected" | "error" | "syncing";
  lastSync?: string;
}

export interface Campaign {
  id: string; name: string; status: "active" | "paused" | "completed" | "draft";
  channel: string; audience: string; product: string; period: string;
  spend: number; impressions: number; clicks: number; conversions: number; revenue: number;
}

export interface EvidenceRecord {
  id: string; sourceName: string; sourceVersion: number; dateRange: string;
  excerpt: string; evidenceType: string; relatedCampaign?: string;
}

export interface Recommendation {
  id: string; action: string; scope: string; observedFacts: string[]; interpretation: string;
  hypothesis: string; supportingEvidence: string[]; contradictoryEvidence: string[];
  primaryMetric: string; risks: string[]; missingData: string[];
  status: "new" | "under_review" | "accepted" | "rejected" | "experiment_planned" | "completed";
}

export interface Experiment {
  id: string; name: string; hypothesis: string; control: string; variant: string;
  primaryMetric: string; guardrailMetrics: string[];
  status: "draft" | "under_review" | "approved" | "running" | "completed" | "cancelled";
  duration: string; relatedRecommendation?: string;
}

export interface InvestigationMessage {
  id: string; role: "user" | "assistant"; content: string;
  summary?: string; observedFacts?: string[]; supportingEvidence?: string[];
  contradictoryEvidence?: string[]; hypotheses?: string[]; nextSteps?: string[];
  limitations?: string[];
}

export interface GNode { id: string; label: string; type: string; x: number; y: number; }
export interface GEdge { id: string; source: string; target: string; relation: string; observed: boolean; }
