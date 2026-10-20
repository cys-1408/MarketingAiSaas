import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard } from "../components/glass/Glass";
import { AlertTriangle, AlertOctagon, RotateCcw } from "lucide-react";

const issues = [
  { label: "crm_contacts_export.xlsx has 3 unresolved field mappings", level: "warning", link: "/app/mapping-review" },
  { label: "support_tickets_export.json failed ingestion (retryable)", level: "error", link: "/app/sources" },
  { label: "2 duplicate campaign records detected in paid_social_q3.csv", level: "warning", link: "/app/sources" },
  { label: "Metric definition conflict: 'conversion' differs between GA4 and CRM", level: "error", link: "/app/integrations" },
];

export default function DataQualityPage() {
  return (
    <DashboardShell title="Data Quality & Freshness">
      <div className="grid md:grid-cols-3 gap-3">
        {[
          { label: "Sources ready", value: "4 / 6" },
          { label: "Unresolved reviews", value: "3" },
          { label: "Last full sync", value: "18 min ago" },
        ].map((k) => (
          <GlassCard key={k.label}>
            <p className="text-xs text-white/50 mb-1">{k.label}</p>
            <p className="text-lg font-medium text-white">{k.value}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Open issues</p>
        <div className="space-y-2">
          {issues.map((i) => (
            <div key={i.label} className="liquid-glass rounded-xl px-3 py-2.5 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                {i.level === "error" ? <AlertOctagon size={14} className="text-white/70 shrink-0" /> : <AlertTriangle size={14} className="text-white/50 shrink-0" />}
                <span className="text-xs text-white/75 truncate">{i.label}</span>
              </div>
              <button className="liquid-glass px-2.5 py-1 rounded-full text-[11px] text-white/60 hover:text-white flex items-center gap-1 shrink-0">
                <RotateCcw size={10} /> Resolve
              </button>
            </div>
          ))}
        </div>
      </GlassCard>
    </DashboardShell>
  );
}
