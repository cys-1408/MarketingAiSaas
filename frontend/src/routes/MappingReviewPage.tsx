import { useCallback, useEffect, useMemo, useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { request, ApiError } from "../services/api";
import { ArrowRight, Check, SkipForward, ListChecks } from "lucide-react";
import type { MappingReviewResponse, MappingCandidateApi, SourceRecord } from "../types";

type Action = "confirm" | "edit" | "skip" | "leave_unmapped";

interface Decision {
  candidate_id: string;
  action: Action;
  chosen_field: string | null;
}

export default function MappingReviewPage() {
  const [sources, setSources] = useState<SourceRecord[] | null>(null);
  const [activeJob, setActiveJob] = useState<string | null>(null);
  const [review, setReview] = useState<MappingReviewResponse | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ job_id: string; status: string; stage: string } | null>(null);

  const loadSources = useCallback(async () => {
    try {
      const data = await request<{ sources: SourceRecord[] }>("/ingestion/sources");
      setSources(data.sources);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load sources.");
    }
  }, []);

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  const pendingJob = useMemo(
    () => sources?.find((s) => s.review_pending && s.job_id) ?? null,
    [sources],
  );

  useEffect(() => {
    const jobId = pendingJob?.job_id ?? null;
    setActiveJob(jobId);
    setReview(null);
    setDecisions({});
    setResult(null);
    if (!jobId) return;
    let cancelled = false;
    void request<MappingReviewResponse>(`/ingestion/jobs/${jobId}/mapping-review`)
      .then((data) => {
        if (!cancelled) setReview(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Could not load mapping review.");
      });
    return () => { cancelled = true; };
  }, [pendingJob?.job_id, pendingJob]);

  function recordDecision(candidate: MappingCandidateApi, action: Action) {
    setDecisions((prev) => ({
      ...prev,
      [candidate.id]: {
        candidate_id: candidate.id,
        action,
        chosen_field: action === "edit" ? prev[candidate.id]?.chosen_field ?? candidate.proposed_field : null,
      },
    }));
  }

  async function submit() {
    if (!activeJob || !review) return;
    const list = Object.values(decisions);
    if (!list.length) {
      setError("No decisions recorded yet. Confirm, edit, skip, or leave each item unmapped.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const outcome = await request<{ job_id: string; status: string; stage: string }>(
        `/ingestion/jobs/${activeJob}/mapping-review`,
        { method: "POST", body: { decisions: list }, timeoutMs: 120_000 },
      );
      setResult(outcome);
      setReview(null);
      setActiveJob(null);
      setDecisions({});
      await loadSources();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Submitting mapping decisions failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const candidates = review?.candidates ?? [];
  const current = candidates.find((c) => !decisions[c.id]) ?? null;
  const resolvedCount = Object.keys(decisions).length;

  return (
    <DashboardShell title="Data Mapping Review">
      {error && (
        <GlassCard>
          <p role="alert" className="text-xs text-white/85">{error}</p>
        </GlassCard>
      )}

      {!sources ? (
        <GlassCard><p className="text-xs text-white/40">Loading sources…</p></GlassCard>
      ) : !activeJob ? (
        <GlassCard>
          {result ? (
            <div className="space-y-2">
              <p className="text-sm text-white/85 flex items-center gap-2">
                <Check size={14} /> Mapping decisions saved — job "{result.job_id}" resumed.
              </p>
              <p className="text-xs text-white/50">Current job status: <StatusBadge status={result.status} /> · stage: {result.stage.replace(/_/g, " ")}</p>
              <p className="text-xs text-white/40">Sources with further review requests will appear here automatically.</p>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <ListChecks size={16} className="text-white/50" />
              <p className="text-sm text-white/70">
                {sources.some((s) => s.job_status === "awaiting_review")
                  ? "A source is awaiting review; refresh to load it."
                  : "No ingestion jobs are waiting for mapping review right now."}
              </p>
            </div>
          )}
        </GlassCard>
      ) : !review ? (
        <GlassCard><p className="text-xs text-white/40">Loading review items…</p></GlassCard>
      ) : (
        <>
          <GlassCard>
            <p className="text-sm text-white/70">
              Unambiguous fields were mapped automatically. These {candidates.length} fields need a decision because of real ambiguity.
            </p>
            <p className="text-xs text-white/40 mt-2">{resolvedCount} of {candidates.length} reviewed</p>
            <div className="liquid-glass h-1.5 rounded-full overflow-hidden mt-2">
              <div className="h-full bg-white/70 transition-all" style={{ width: `${(resolvedCount / Math.max(candidates.length, 1)) * 100}%` }} />
            </div>
          </GlassCard>

          {current ? (
            <GlassCard strong>
              <div className="flex justify-between text-xs text-white/40 mb-4">
                <span>{activeJob} · {current.sheet}</span>
                <span className="capitalize">{current.confidence} confidence</span>
              </div>

              <div className="grid md:grid-cols-2 gap-4 mb-5">
                <div className="liquid-glass rounded-2xl p-4">
                  <p className="text-xs text-white/45 mb-2">Source column</p>
                  <p className="text-white font-medium mb-3">{current.column}</p>
                  <p className="text-xs text-white/45 mb-1.5">Sample values</p>
                  <div className="flex flex-wrap gap-1.5">
                    {current.sample_values.map((v) => (
                      <span key={v} className="liquid-glass px-2 py-1 rounded-full text-[11px] text-white/70">{v}</span>
                    ))}
                  </div>
                </div>
                <div className="liquid-glass rounded-2xl p-4 flex flex-col">
                  <p className="text-xs text-white/45 mb-2">Proposed canonical field</p>
                  <p className="text-white font-medium mb-3 flex items-center gap-2">
                    <ArrowRight size={14} className="text-white/40" /> {current.proposed_field}
                  </p>
                  <p className="text-xs text-white/45 mb-1.5">Alternatives</p>
                  <div className="flex flex-wrap gap-1.5">
                    {current.alternatives.map((a) => (
                      <button
                        key={a}
                        onClick={() => {
                          recordDecision(current, "edit");
                          setDecisions((prev) => ({
                            ...prev,
                            [current.id]: { candidate_id: current.id, action: "edit", chosen_field: a },
                          }));
                        }}
                        className="liquid-glass px-2 py-1 rounded-full text-[11px] text-white/50 hover:text-white"
                      >
                        {a}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-2 mb-5 text-xs">
                <p className="text-white/50"><span className="text-white/70 font-medium">Why review is needed:</span> {current.reason}</p>
                <p className="text-white/50"><span className="text-white/70 font-medium">Potential impact:</span> {current.impact}</p>
              </div>

              <div className="flex flex-wrap gap-2">
                <GlassButton strong onClick={() => recordDecision(current, "confirm")} disabled={submitting}>
                  <Check size={13} /> Confirm mapping
                </GlassButton>
                <GlassButton onClick={() => recordDecision(current, "edit")} disabled={submitting}>Edit mapping</GlassButton>
                <GlassButton onClick={() => recordDecision(current, "skip")} disabled={submitting}>
                  <SkipForward size={13} /> Skip field
                </GlassButton>
                <GlassButton onClick={() => recordDecision(current, "leave_unmapped")} disabled={submitting}>Leave unmapped</GlassButton>
              </div>
            </GlassCard>
          ) : (
            <GlassCard>
              <p className="text-sm text-white/80">All {candidates.length} items have recorded decisions.</p>
              <GlassButton strong className="mt-3" onClick={() => void submit()} disabled={submitting}>
                {submitting ? "Submitting…" : "Submit decisions & resume ingestion"}
              </GlassButton>
            </GlassCard>
          )}

          <p className="text-[11px] text-white/35">
            Only fields the backend proposes appear here. "Skip" excludes the field from this source mapping; "leave unmapped"
            keeps it out of canonical metrics until decided.
          </p>
        </>
      )}
    </DashboardShell>
  );
}
