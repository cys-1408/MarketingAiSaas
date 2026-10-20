import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, DemoBadge } from "../components/glass/Glass";

const metrics = [
  { label: "Retrieval relevance", value: "91%" },
  { label: "Evidence coverage", value: "87%" },
  { label: "Citation correctness", value: "96%" },
  { label: "Numeric accuracy", value: "94%" },
  { label: "Faithfulness", value: "93%" },
  { label: "Appropriate abstention", value: "88%" },
];

const runs = [
  { id: "run-214", date: "Oct 19, 2026", model: "copilot-core-v2.3", status: "Passed" },
  { id: "run-213", date: "Oct 12, 2026", model: "copilot-core-v2.3", status: "Passed" },
  { id: "run-212", date: "Oct 5, 2026", model: "copilot-core-v2.2", status: "Flagged" },
];

export default function EvaluationPage() {
  return (
    <DashboardShell title="Evaluation & Quality" actions={<DemoBadge />}>
      <GlassCard>
        <p className="text-xs text-white/50">
          These scores reflect synthetic evaluation examples for demonstration. They do not establish complete prevention of hallucination or error.
        </p>
      </GlassCard>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {metrics.map((m) => (
          <GlassCard key={m.label}>
            <p className="text-xs text-white/50 mb-1.5">{m.label}</p>
            <p className="text-lg font-medium text-white">{m.value}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Evaluation run history</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-white/40 text-xs border-b border-white/10">
                <th className="py-2 pr-4 font-medium">Run</th>
                <th className="py-2 pr-4 font-medium">Date</th>
                <th className="py-2 pr-4 font-medium">Model / prompt version</th>
                <th className="py-2 pr-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-b border-white/5">
                  <td className="py-2.5 pr-4 text-white/80">{r.id}</td>
                  <td className="py-2.5 pr-4 text-white/50 text-xs">{r.date}</td>
                  <td className="py-2.5 pr-4 text-white/50 text-xs">{r.model}</td>
                  <td className="py-2.5 pr-4 text-xs text-white/70">{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </DashboardShell>
  );
}
