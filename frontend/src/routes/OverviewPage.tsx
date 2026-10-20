import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, DemoBadge } from "../components/glass/Glass";
import { currentUser, campaigns } from "../services/mock/fixtures";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Upload, Plug, Sparkles, GitCompareArrows, Network, FlaskConical, ArrowUpRight, ListChecks } from "lucide-react";
import { useNavigate } from "react-router-dom";

const trend = [
  { d: "Sep 1", spend: 1800, revenue: 2400 }, { d: "Sep 8", spend: 2100, revenue: 3100 },
  { d: "Sep 15", spend: 2600, revenue: 4200 }, { d: "Sep 22", spend: 2300, revenue: 3800 },
  { d: "Sep 29", spend: 3100, revenue: 5200 },
];

const kpis = [
  { label: "Total Campaigns", value: campaigns.length.toString() },
  { label: "Tracked Spend", value: "$57.7K" },
  { label: "Attributed Revenue", value: "$252.6K" },
  { label: "Conversion Rate", value: "3.1%" },
  { label: "Avg. CTR", value: "1.9%" },
  { label: "Connected Sources", value: "2" },
];

const quickActions = [
  { label: "Upload Files", icon: Upload, to: "/app/sources" },
  { label: "Connect Platform", icon: Plug, to: "/app/integrations" },
  { label: "Investigate Campaign", icon: Sparkles, to: "/app/investigations" },
  { label: "Compare Campaigns", icon: GitCompareArrows, to: "/app/campaign-comparison" },
  { label: "Explore Evidence Graph", icon: Network, to: "/app/evidence-graph" },
  { label: "Create Experiment Brief", icon: FlaskConical, to: "/app/experiments" },
];

export default function OverviewPage() {
  const navigate = useNavigate();
  return (
    <DashboardShell title="Overview">
      <GlassCard className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-white/50 text-xs mb-1">Good morning, {currentUser.name.split(" ")[0]}</p>
          <p className="text-sm text-white/85 flex items-center gap-2">
            <ListChecks size={14} className="text-white/60" />
            Workspace status: <span className="font-medium">Partially ready</span> — 3 field mappings need review.
          </p>
        </div>
        <GlassButton onClick={() => navigate("/app/mapping-review")}>Review 3 field mappings</GlassButton>
      </GlassCard>

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-white/70">Key metrics</h2>
        <DemoBadge />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {kpis.map((k) => (
          <GlassCard key={k.label}>
            <p className="text-xs text-white/50 mb-1.5">{k.label}</p>
            <p className="text-xl font-medium text-white">{k.value}</p>
          </GlassCard>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-3">
        <GlassCard className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-white/85">Spend vs. attributed revenue</p>
            <span className="text-[11px] text-white/40">Sep 1 – Sep 30 · Demo data</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="d" stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "rgba(10,10,10,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, fontSize: 12 }} />
              <Line type="monotone" dataKey="spend" stroke="rgba(255,255,255,0.4)" strokeWidth={2} dot={false} name="Spend" />
              <Line type="monotone" dataKey="revenue" stroke="rgba(255,255,255,0.95)" strokeWidth={2} dot={false} name="Revenue" />
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard>
          <p className="text-sm font-medium text-white/85 mb-3">Insight</p>
          <p className="text-xs text-white/50 mb-2">Observed fact</p>
          <p className="text-sm text-white/80 mb-3">Autumn Acquisition Push CTR is 1.73%, above the account median.</p>
          <p className="text-xs text-white/50 mb-2">Hypothesis</p>
          <p className="text-sm text-white/70 mb-3">Creative refresh may be contributing to the lift — not yet confirmed.</p>
          <button onClick={() => navigate("/app/investigations")} className="text-xs text-white/80 flex items-center gap-1 hover:text-white">
            Open investigation <ArrowUpRight size={12} />
          </button>
        </GlassCard>
      </div>

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
        <p className="text-sm font-medium text-white/85 mb-3">Recent activity</p>
        <div className="space-y-2">
          {[
            "paid_social_q3.csv finished indexing · 2 hours ago",
            "crm_contacts_export.xlsx awaiting mapping review · 4 hours ago",
            "Meta Ads sync completed · 1 hour ago",
            "Investigation: \"Why did CTR increase?\" completed · yesterday",
          ].map((a) => (
            <div key={a} className="text-xs text-white/60 liquid-glass rounded-xl px-3 py-2.5">{a}</div>
          ))}
        </div>
      </GlassCard>
    </DashboardShell>
  );
}
