import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { request, ApiError } from "../services/api";
import type { CampaignSummary } from "../types";
import { Sparkles, FileText, RefreshCw } from "lucide-react";

function iso(daysAgo: number): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().slice(0, 10);
}

function formatMetric(name: string, value: number | null, unit: string): string {
  if (value === null) return "undefined";
  if (unit === "ratio") return `${(value * 100).toFixed(2)}%`;
  if (unit === "currency") return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  return value.toLocaleString();
}

export default function CampaignDetailPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [start, setStart] = useState(iso(90));
  const [end, setEnd] = useState(iso(0));
  const [summary, setSummary] = useState<CampaignSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!campaignId) return;
    setLoading(true);
    try {
      const data = await request<CampaignSummary>(
        `/campaigns/${campaignId}/summary?start_date=${start}&end_date=${end}`,
      );
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load the campaign summary.");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [campaignId, start, end]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <DashboardShell title={summary?.campaign_name ?? "Campaign"}>
      <GlassCard className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {summary && (
            <>
              <span className="text-xs text-white/50 capitalize">{summary.channel}</span>
              <span className="text-xs text-white/40">{summary.date_start} → {summary.date_end}</span>
            </>
          )}
        </div>
        <div className="flex gap-2">
          <GlassButton onClick={() => navigate("/app/investigations")}><Sparkles size={13} /> Investigate</GlassButton>
          <GlassButton
            onClick={() =>
              navigate("/app/reports", {
                state: summary ? { campaignId: summary.campaign_id, campaignName: summary.campaign_name, dateStart: summary.date_start, dateEnd: summary.date_end } : null,
              })
            }
          >
            <FileText size={13} /> Generate report
          </GlassButton>
        </div>
      </GlassCard>

      <GlassCard className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="cd-start" className="block text-xs text-white/50 mb-1">Start date (ISO)</label>
          <input id="cd-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} className="liquid-glass rounded-xl px-3 py-2 text-sm text-white outline-none" />
        </div>
        <div>
          <label htmlFor="cd-end" className="block text-xs text-white/50 mb-1">End date (ISO)</label>
          <input id="cd-end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="liquid-glass rounded-xl px-3 py-2 text-sm text-white outline-none" />
        </div>
        <GlassButton strong onClick={() => void load()} disabled={loading}>
          <RefreshCw size={12} /> Apply & refresh
        </GlassButton>
      </GlassCard>

      {error && (
        <GlassCard>
          <p role="alert" className="text-xs text-white/85">{error}</p>
        </GlassCard>
      )}

      {!summary && loading && (
        <GlassCard><p className="text-xs text-white/40">Loading summary…</p></GlassCard>
      )}

      {summary && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {summary.metrics.map((m) => (
              <GlassCard key={`${m.metric_name}-${m.source_id}`}>
                <p className="text-xs text-white/50 mb-1 capitalize">{m.metric_name.replace(/_/g, " ")}</p>
                <p className="text-lg font-medium text-white">{formatMetric(m.metric_name, m.value, m.unit)}</p>
                <p className="text-[10px] text-white/35 mt-1">{m.definition || m.unit} · source {m.source_id.slice(0, 8)} v{m.source_version}</p>
              </GlassCard>
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-3">
            <GlassCard>
              <p className="text-sm font-medium text-white/85 mb-3">Derived rates (backend-computed)</p>
              {summary.derived.length === 0 ? (
                <p className="text-xs text-white/40">No derived metrics for this window.</p>
              ) : (
                <div className="space-y-2">
                  {summary.derived.map((d) => (
                    <div key={d.metric_name} className="liquid-glass rounded-xl px-3 py-2 flex justify-between items-center">
                      <span className="text-xs text-white/70 capitalize">{d.metric_name.replace(/_/g, " ")}</span>
                      <span className="text-xs text-white/85">{formatMetric(d.metric_name, d.value, d.unit)}</span>
                    </div>
                  ))}
                </div>
              )}
              {summary.derived.some((d) => d.value === null) && (
                <p className="text-[10px] text-white/40 mt-2">Missing denominators or numerators are shown as undefined — never as zero.</p>
              )}
            </GlassCard>

            <GlassCard>
              <p className="text-sm font-medium text-white/85 mb-3">Freshness & limitations</p>
              <div className="space-y-1.5 text-xs">
                <Row label="Source" value={summary.freshness.source_name || summary.freshness.source_id} />
                <Row label="Source version" value={`v${summary.freshness.source_version ?? "?"}`} />
                <Row label="Last updated" value={summary.freshness.last_synced_at ? new Date(summary.freshness.last_synced_at).toLocaleString() : "—"} />
              </div>
              {summary.limitations.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {summary.limitations.map((l) => (
                    <p key={l} role="note" className="liquid-glass rounded-lg px-3 py-2 text-[11px] text-white/60">Limitation: {l}</p>
                  ))}
                </div>
              )}
            </GlassCard>
          </div>
        </>
      )}
    </DashboardShell>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between liquid-glass rounded-lg px-3 py-2">
      <span className="text-white/45">{label}</span>
      <span className="text-white/85 truncate max-w-[60%]">{value}</span>
    </div>
  );
}
