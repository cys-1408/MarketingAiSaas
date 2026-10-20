import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard } from "../components/glass/Glass";

const events = [
  { who: "Avery Chen", action: "Confirmed field mapping: deal_stg → pipeline_stage", time: "12 min ago" },
  { who: "System", action: "Meta Ads sync completed (1,204 records updated)", time: "1 hour ago" },
  { who: "Jordan Lee", action: "Invited priya@northfield.io as Analyst", time: "3 hours ago" },
  { who: "System", action: "support_tickets_export.json ingestion failed (retryable)", time: "5 hours ago" },
  { who: "Avery Chen", action: "Approved recommendation: Add pricing summary", time: "yesterday" },
  { who: "Avery Chen", action: "Changed model inference mode to Local (Ollama connector)", time: "2 days ago" },
];

export default function ActivityLogPage() {
  return (
    <DashboardShell title="Activity & Audit Log">
      <GlassCard>
        <div className="space-y-2">
          {events.map((e, i) => (
            <div key={i} className="liquid-glass rounded-xl px-3 py-2.5 flex justify-between items-center gap-3">
              <div className="min-w-0">
                <span className="text-xs text-white/85">{e.who}</span>
                <span className="text-xs text-white/55"> — {e.action}</span>
              </div>
              <span className="text-[11px] text-white/35 shrink-0">{e.time}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </DashboardShell>
  );
}
