import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, StatusBadge, DemoBadge } from "../components/glass/Glass";
import { campaigns } from "../services/mock/fixtures";
import { Search, Sparkles } from "lucide-react";

export default function CampaignsPage() {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const filtered = campaigns.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <DashboardShell
      title="Campaign Analytics"
      actions={<DemoBadge />}
    >
      <GlassCard className="flex items-center gap-2">
        <Search size={14} className="text-white/40" />
        <input
          value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search campaigns…"
          className="bg-transparent outline-none text-sm text-white/85 placeholder:text-white/35 flex-1"
        />
      </GlassCard>

      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-white/40 text-xs border-b border-white/10">
                {["Campaign", "Status", "Channel", "Period", "Spend", "Clicks", "Conversions", "Revenue", ""].map((h) => (
                  <th key={h} className="py-2 pr-4 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} className="border-b border-white/5 hover:bg-white/[0.03] cursor-pointer" onClick={() => navigate(`/app/campaigns/${c.id}`)}>
                  <td className="py-3 pr-4 text-white/85">{c.name}</td>
                  <td className="py-3 pr-4"><StatusBadge status={c.status} /></td>
                  <td className="py-3 pr-4 text-white/60 text-xs">{c.channel}</td>
                  <td className="py-3 pr-4 text-white/45 text-xs">{c.period}</td>
                  <td className="py-3 pr-4 text-white/75 text-xs">${c.spend.toLocaleString()}</td>
                  <td className="py-3 pr-4 text-white/75 text-xs">{c.clicks.toLocaleString()}</td>
                  <td className="py-3 pr-4 text-white/75 text-xs">{c.conversions}</td>
                  <td className="py-3 pr-4 text-white/75 text-xs">${c.revenue.toLocaleString()}</td>
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
      </GlassCard>
    </DashboardShell>
  );
}
