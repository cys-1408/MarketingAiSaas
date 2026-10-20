import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton } from "../components/glass/Glass";
import { FileText, Download, Loader2 } from "lucide-react";

const reportTypes = ["Campaign performance", "Campaign comparison", "Customer objections", "Investigation summary", "Experiment results", "Evidence summary"];
const past = [
  { name: "Autumn Acquisition — Performance Report", date: "Oct 2" },
  { name: "Q3 Customer Objections Summary", date: "Sep 28" },
];

export default function ReportsPage() {
  const [type, setType] = useState(reportTypes[0]);
  const [generating, setGenerating] = useState(false);
  const [ready, setReady] = useState(false);

  function onGenerate() {
    setGenerating(true);
    setReady(false);
    setTimeout(() => { setGenerating(false); setReady(true); }, 1200);
  }

  return (
    <DashboardShell title="Reports">
      <div className="grid lg:grid-cols-[320px_1fr] gap-3 items-start">
        <GlassCard strong className="space-y-4">
          <div>
            <p className="text-xs text-white/50 mb-1.5">Report type</p>
            <select value={type} onChange={(e) => setType(e.target.value)} className="w-full liquid-glass rounded-xl px-3 py-2 text-sm text-white bg-transparent outline-none">
              {reportTypes.map((t) => <option key={t} value={t} className="bg-ink-900">{t}</option>)}
            </select>
          </div>
          <div>
            <p className="text-xs text-white/50 mb-1.5">Reporting period</p>
            <input defaultValue="Sep 1 – Sep 30, 2026" className="w-full liquid-glass rounded-xl px-3 py-2 text-sm text-white outline-none" />
          </div>
          <GlassButton strong className="w-full" onClick={onGenerate} disabled={generating}>
            {generating ? <Loader2 size={13} className="animate-spin" /> : <FileText size={13} />}
            {generating ? "Generating…" : "Generate report"}
          </GlassButton>
        </GlassCard>

        <div className="space-y-3">
          {ready && (
            <GlassCard>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <p className="text-sm font-medium text-white">{type} Report</p>
                  <p className="text-xs text-white/40">Sep 1 – Sep 30, 2026 · Demo data</p>
                </div>
                <GlassButton className="text-xs px-3 py-1.5"><Download size={12} /> Download</GlassButton>
              </div>
              <p className="text-xs text-white/60 leading-relaxed mb-2">
                This preview includes citations, metric definitions, and clear fact-versus-hypothesis labeling. Limitations and missing
                data are disclosed at the end of the report.
              </p>
              <div className="liquid-glass rounded-xl p-3 text-xs text-white/50">
                3 observed facts · 2 hypotheses · 1 limitation noted
              </div>
            </GlassCard>
          )}
          <GlassCard>
            <p className="text-sm font-medium text-white/85 mb-3">Previous reports</p>
            <div className="space-y-2">
              {past.map((p) => (
                <div key={p.name} className="liquid-glass rounded-xl px-3 py-2.5 flex justify-between items-center">
                  <span className="text-xs text-white/75">{p.name}</span>
                  <span className="text-[11px] text-white/35">{p.date}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </DashboardShell>
  );
}
