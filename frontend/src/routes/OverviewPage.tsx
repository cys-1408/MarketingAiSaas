import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, DemoBadge } from "../components/glass/Glass";
import { request } from "../services/api";
import type { SourceRecord } from "../types";
import { Upload, Plug, Sparkles, GitCompareArrows, Network, FlaskConical, ArrowUpRight, ListChecks } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useEffect } from "react";
import type { Campaign, UsageResponse } from "../types";

const quickActions = [
  { label: "Upload Files", icon: Upload, to: "/app/sources" },
  { label: "Connect Platform", icon: Plug, to: "/app/integrations" },
  { label: "Investigate Campaign", icon: Sparkles, to: "/app/investigations" },
  { label: "Compare Campaigns", icon: GitCompareArrows, to: "/app/campaign-comparison" },
  { label: "Explore Evidence Graph", icon: Network, to: "/app/evidence-graph" },
  { label: "Create Experiment Brief", icon: FlaskConical, to: "/app/experiments" },
];

/**
 * Mirrors the real sources-list response (`GET /api/v1/ingestion/sources`).
 * Only statuses that actually mean "processed" count as ready.
 */
const READY_STATES = new Set(["ready", "partially_ready"]);
const ACTIVE_STATES = new Set([
  "queued", "inspecting", "mapping", "awaiting_review", "normalizing", "indexing", "graph_updating", "validating",
]);

export default function OverviewPage() {
  const navigate = useNavigate();
  const { user, workspace } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [sources, setSources] = useState<SourceRecord[] | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [activity, setActivity] = useState<{ id: string; actor: string; action: string; created_at: string | null }[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        // All state comes from the server; failures show error states.
        const [c, s, u, a] = await Promise.all([
          request<{ campaigns: Campaign[] }>("/campaigns"),
          request<{ sources: SourceRecord[] }>("/ingestion/sources"),
          request<UsageResponse>(`/workspaces/${workspace!.id}/usage`),
          request<{ events: { id: string; actor: string; action: string; created_at: string | null }[] }>(
            `/workspaces/${workspace!.id}/activity`,
          ),
        ]);
        if (cancelled) return;
        setCampaigns(c.campaigns);
        setSources(s.sources);
        setUsage(u);
        setActivity(a.events);
        setError(null);
      } catch {
        if (!cancelled) setError("Could not load this workspace's live data. Retry once the service is reachable.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [workspace?.id]);

  const readySources = sources?.filter((s) => READY_STATES.has(s.status)).length ?? 0;
  const reviewPending = sources?.filter((s) => s.review_pending).length ?? 0;
  const activeJobs = sources?.filter((s) => ACTIVE_STATES.has(s.status)).length ?? 0;

  return (
    <DashboardShell title="Overview">
      <GlassCard className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-white/50 text-xs mb-1">Welcome, {user?.name.split(" ")[0] ?? "there"}</p>
          <p className="text-sm text-white/85 flex items-center gap-2">
            <ListChecks size={14} className="text-white/60" />
            {reviewPending > 0 ? (
              <>
                Workspace status: <span className="font-medium">Action needed</span> — {reviewPending} field mapping{reviewPending === 1 ? "" : "s"} need review.
              </>
            ) : (
              <>Workspace status: <span className="font-medium">{loading ? "Checking…" : "No reviews pending"}</span></>
            )}
          </p>
        </div>
        {reviewPending > 0 && (
          <GlassButton onClick={() => navigate("/app/mapping-review")}>
            Review {reviewPending} field mapping{reviewPending === 1 ? "" : "s"}
          </GlassButton>
        )}
      </GlassCard>

      {error && (
        <GlassCard>
          <p role="alert" className="text-sm text-white/75">{error}</p>
        </GlassCard>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-white/70">Workspace totals (live)</h2>
        <DemoBadge />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {[
          { label: "Total Campaigns", value: campaigns ? String(campaigns.length) : "—" },
          { label: "Connected Sources", value: usage ? String(usage.sources) : "—" },
          { label: "Metric Rows", value: usage ? usage.metric_rows.toLocaleString() : "—" },
          { label: "Indexed Chunks", value: usage ? usage.indexed_chunks.toLocaleString() : "—" },
          { label: "Sources Ready", value: sources ? `${readySources} / ${sources.length}` : "—" },
          { label: "Jobs In Progress", value: usage ? String(usage.jobs_in_progress ?? activeJobs) : "—" },
        ].map((k) => (
          <GlassCard key={k.label}>
            <p className="text-xs text-white/50 mb-1.5">{k.label}</p>
            <p className="text-xl font-medium text-white">{k.value}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Recent campaigns</p>
        {!campaigns ? (
          <p className="text-xs text-white/40">Loading campaigns…</p>
        ) : campaigns.length === 0 ? (
          <p className="text-xs text-white/40">No campaigns yet. Upload a source or connect a platform to bring campaign data in.</p>
        ) : (
          <div className="space-y-2">
            {campaigns.slice(0, 5).map((c) => (
              <button
                key={c.id}
                onClick={() => navigate(`/app/campaigns/${c.id}`)}
                className="liquid-glass rounded-xl px-3 py-2.5 flex justify-between items-center w-full text-left"
              >
                <span className="text-xs text-white/80">{c.name}</span>
                <span className="text-[11px] text-white/35 capitalize">{c.channel}{c.start_date ? ` · ${c.start_date}${c.end_date ? ` – ${c.end_date}` : ""}` : ""}</span>
              </button>
            ))}
          </div>
        )}
        <p className="text-[11px] text-white/35 mt-3">
          Totals count persisted workspace records; spend and revenue appear on each campaign's detail page when the
          connected source provides those metrics.
        </p>
      </GlassCard>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Quick actions</p>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2.5">
          {quickActions.map((a) => (
            <button
              key={a.label} onClick={() => navigate(a.to)}
              className="liquid-glass rounded-xl px-3 py-3 text-xs text-white/75 flex flex-col items-center gap-2 hover:bg-white/5 transition-colors text-center"
            >
              <a.icon size={16} />
              {a.label}
            </button>
          ))}
        </div>
      </GlassCard>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Recent activity (audit log)</p>
        {!activity ? (
          <p className="text-xs text-white/40">{loading ? "Loading activity…" : "No activity loaded."}</p>
        ) : activity.length === 0 ? (
          <p className="text-xs text-white/40">No recorded activity yet.</p>
        ) : (
          <div className="space-y-2">
            {activity.slice(0, 5).map((ev) => (
              <div key={ev.id} className="text-xs text-white/60 liquid-glass rounded-xl px-3 py-2.5">
                <span className="text-white/80">{ev.actor}</span> — {ev.action.replace(/[_.]/g, " ")}
                {ev.created_at ? ` · ${new Date(ev.created_at).toLocaleString()}` : ""}
              </div>
            ))}
          </div>
        )}
        <button onClick={() => navigate("/app/activity")} className="text-xs text-white/80 flex items-center gap-1 hover:text-white mt-3">
          Open activity log <ArrowUpRight size={12} />
        </button>
      </GlassCard>
    </DashboardShell>
  );
}
