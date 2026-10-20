import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { recommendations } from "../services/mock/fixtures";
import { FlaskConical } from "lucide-react";

export default function RecommendationsPage() {
  const [filter, setFilter] = useState<string | null>(null);
  const navigate = useNavigate();
  const items = recommendations.filter((r) => !filter || r.status === filter);
  const statuses = Array.from(new Set(recommendations.map((r) => r.status)));

  return (
    <DashboardShell title="Recommendations">
      <GlassCard className="flex flex-wrap gap-2">
        <button onClick={() => setFilter(null)} className={`liquid-glass px-3 py-1.5 rounded-full text-xs ${!filter ? "bg-white/15 text-white" : "text-white/55"}`}>All</button>
        {statuses.map((s) => (
          <button key={s} onClick={() => setFilter(s)} className={`liquid-glass px-3 py-1.5 rounded-full text-xs capitalize ${filter === s ? "bg-white/15 text-white" : "text-white/55"}`}>
            {s.replace(/_/g, " ")}
          </button>
        ))}
      </GlassCard>

      {items.map((r) => (
        <GlassCard key={r.id}>
          <div className="flex items-start justify-between gap-3 mb-3">
            <div>
              <p className="text-sm font-medium text-white/90 mb-1">{r.action}</p>
              <p className="text-xs text-white/40">{r.scope}</p>
            </div>
            <StatusBadge status={r.status} />
          </div>

          <div className="grid md:grid-cols-2 gap-3 mb-3">
            <div>
              <p className="text-xs text-white/45 mb-1">Observed facts</p>
              <ul className="space-y-1">
                {r.observedFacts.map((f) => <li key={f} className="text-xs text-white/70">— {f}</li>)}
              </ul>
            </div>
            <div>
              <p className="text-xs text-white/45 mb-1">Hypothesis</p>
              <p className="text-xs text-white/70">{r.hypothesis}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-3 mb-4 text-xs">
            <div><span className="text-white/45">Primary metric: </span><span className="text-white/75">{r.primaryMetric}</span></div>
            <div><span className="text-white/45">Risks: </span><span className="text-white/60">{r.risks.join("; ") || "None noted"}</span></div>
          </div>

          <div className="flex gap-2">
            <GlassButton className="text-xs px-3 py-1.5">View evidence</GlassButton>
            <GlassButton strong className="text-xs px-3 py-1.5" onClick={() => navigate("/app/experiments")}>
              <FlaskConical size={12} /> Convert to experiment
            </GlassButton>
          </div>
        </GlassCard>
      ))}
    </DashboardShell>
  );
}
