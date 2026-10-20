import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { campaigns } from "../services/mock/fixtures";
import { Sparkles } from "lucide-react";

export default function CampaignComparisonPage() {
  const [selected, setSelected] = useState<string[]>([campaigns[0].id, campaigns[1].id]);
  const navigate = useNavigate();

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 4 ? [...prev, id] : prev));
  }

  const chosen = campaigns.filter((c) => selected.includes(c.id));
  const metrics = ["spend", "clicks", "conversions", "revenue"] as const;

  return (
    <DashboardShell title="Campaign Comparison">
      <GlassCard>
        <p className="text-sm text-white/70 mb-3">Select up to 4 campaigns to compare (max 4).</p>
        <div className="flex flex-wrap gap-2">
          {campaigns.map((c) => (
            <button
              key={c.id} onClick={() => toggle(c.id)}
              className={`liquid-glass px-3 py-1.5 rounded-full text-xs ${selected.includes(c.id) ? "bg-white/15 text-white" : "text-white/55"}`}
            >
              {c.name}
            </button>
          ))}
        </div>
      </GlassCard>

      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-white/40 text-xs border-b border-white/10">
                <th className="py-2 pr-4 font-medium">Metric</th>
                {chosen.map((c) => <th key={c.id} className="py-2 pr-4 font-medium">{c.name}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-white/5">
                <td className="py-2.5 pr-4 text-white/50 text-xs">Status</td>
                {chosen.map((c) => <td key={c.id} className="py-2.5 pr-4"><StatusBadge status={c.status} /></td>)}
              </tr>
              {metrics.map((m) => (
                <tr key={m} className="border-b border-white/5">
                  <td className="py-2.5 pr-4 text-white/50 text-xs capitalize">{m}</td>
                  {chosen.map((c) => (
                    <td key={c.id} className="py-2.5 pr-4 text-white/85 text-xs">
                      {m === "spend" || m === "revenue" ? `$${c[m].toLocaleString()}` : c[m].toLocaleString()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-white/35 mt-4">
          Differences shown are observational. Better performance does not imply that channel or creative choices caused the outcome.
        </p>
      </GlassCard>

      <GlassButton strong onClick={() => navigate("/app/investigations")}>
        <Sparkles size={14} /> Investigate differences
      </GlassButton>
    </DashboardShell>
  );
}
