import { useParams, useNavigate } from "react-router-dom";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, StatusBadge, GlassButton } from "../components/glass/Glass";
import { campaigns, evidenceRecords } from "../services/mock/fixtures";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from "recharts";
import { Sparkles, FileText } from "lucide-react";

const weekly = [
  { w: "W1", conv: 120 }, { w: "W2", conv: 145 }, { w: "W3", conv: 160 }, { w: "W4", conv: 187 },
];

export default function CampaignDetailPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const campaign = campaigns.find((c) => c.id === campaignId) ?? campaigns[0];
  const evidence = evidenceRecords.filter((e) => e.relatedCampaign === campaign.id);

  return (
    <DashboardShell title={campaign.name}>
      <GlassCard className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <StatusBadge status={campaign.status} />
          <span className="text-xs text-white/50">{campaign.channel} · {campaign.audience} · {campaign.period}</span>
        </div>
        <div className="flex gap-2">
          <GlassButton onClick={() => navigate("/app/investigations")}><Sparkles size={13} /> Investigate</GlassButton>
          <GlassButton onClick={() => navigate("/app/reports")}><FileText size={13} /> Generate report</GlassButton>
        </div>
      </GlassCard>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Spend", value: `$${campaign.spend.toLocaleString()}` },
          { label: "Impressions", value: campaign.impressions.toLocaleString() },
          { label: "Clicks", value: campaign.clicks.toLocaleString() },
          { label: "Revenue", value: `$${campaign.revenue.toLocaleString()}` },
        ].map((m) => (
          <GlassCard key={m.label}>
            <p className="text-xs text-white/50 mb-1">{m.label}</p>
            <p className="text-lg font-medium text-white">{m.value}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Weekly conversions</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={weekly}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
            <XAxis dataKey="w" stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="rgba(255,255,255,0.4)" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: "rgba(10,10,10,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, fontSize: 12 }} />
            <Bar dataKey="conv" fill="rgba(255,255,255,0.75)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </GlassCard>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Related evidence</p>
        <div className="space-y-2">
          {evidence.map((e) => (
            <div key={e.id} className="liquid-glass rounded-xl p-3">
              <div className="flex justify-between text-[11px] text-white/40 mb-1">
                <span>{e.sourceName} · v{e.sourceVersion}</span>
                <span>{e.dateRange}</span>
              </div>
              <p className="text-sm text-white/75">{e.excerpt}</p>
            </div>
          ))}
          {!evidence.length && <p className="text-xs text-white/40">No linked evidence yet.</p>}
        </div>
      </GlassCard>
    </DashboardShell>
  );
}
