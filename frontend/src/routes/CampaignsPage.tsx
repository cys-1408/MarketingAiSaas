import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, StatusBadge } from "../components/glass/Glass";
import { request, ApiError } from "../services/api";
import { Search, Sparkles } from "lucide-react";
import type { Campaign } from "../types";

export default function CampaignsPage() {
  const [query, setQuery] = useState("");
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    void request<{ campaigns: Campaign[] }>("/campaigns")
      .then((data) => {
        if (!cancelled) { setCampaigns(data.campaigns); setError(null); }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "Could not load campaigns.");
      });
    return () => { cancelled = true; };
  }, []);

  const filtered = useMemo(
    () => campaigns?.filter((c) => c.name.toLowerCase().includes(query.toLowerCase())) ?? null,
    [campaigns, query],
  );

  return (
    <DashboardShell title="Campaign Analytics">
      <GlassCard className="flex items-center gap-2">
        <Search size={14} className="text-white/40" />
        <input
          value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search campaigns…"
          className="bg-transparent outline-none text-sm text-white/85 placeholder:text-white/35 flex-1"
        />
      </GlassCard>

      {error && (
        <GlassCard>
          <p role="alert" className="text-xs text-white/85">{error}</p>
        </GlassCard>
      )}

      <GlassCard>
        {!filtered ? (
          <p className="text-xs text-white/40 py-4">Loading campaigns…</p>
        ) : filtered.length === 0 ? (
          <p className="text-xs text-white/40 py-6 text-center">
            {query ? "No campaigns match your search." : "No campaigns yet. Ingest a campaign source to populate analytics."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/40 text-xs border-b border-white/10">
                  {["Campaign", "Status", "Channel", "Product", "Period", ""].map((h) => (
                    <th key={h} className="py-2 pr-4 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id} className="border-b border-white/5 hover:bg-white/[0.03] cursor-pointer" onClick={() => navigate(`/app/campaigns/${c.id}`)}>
                    <td className="py-3 pr-4 text-white/85">{c.name}</td>
                    <td className="py-3 pr-4"><StatusBadge status={c.status} /></td>
                    <td className="py-3 pr-4 text-white/60 text-xs capitalize">{c.channel}</td>
                    <td className="py-3 pr-4 text-white/60 text-xs">{c.product ?? "—"}</td>
                    <td className="py-3 pr-4 text-white/45 text-xs">
                      {c.start_date ? `${c.start_date}${c.end_date ? ` – ${c.end_date}` : ""}` : "—"}
                    </td>
                    <td className="py-3 pr-4">
                      <button
                        onClick={(e) => { e.stopPropagation(); navigate("/app/investigations"); }}
                        className="liquid-glass px-2.5 py-1 rounded-full text-[11px] text-white/60 hover:text-white flex items-center gap-1"
                      >
                        <Sparkles size={10} /> Investigate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <p className="text-[11px] text-white/35">
        Metrics (spend, clicks, conversions, revenue) are computed per campaign on the backend with recorded definitions,
        units, and date windows — open a campaign for its real summary. This list shows campaign metadata from persisted records.
      </p>
    </DashboardShell>
  );
}
