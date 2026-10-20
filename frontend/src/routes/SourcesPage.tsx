import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { dataSources } from "../services/mock/fixtures";
import { UploadCloud, RotateCcw, Trash2, X } from "lucide-react";
import type { DataSource } from "../types";

export default function SourcesPage() {
  const [selected, setSelected] = useState<DataSource | null>(null);
  return (
    <DashboardShell title="Sources & Files">
      <GlassCard className="border-dashed">
        <div className="flex flex-col items-center justify-center text-center py-8">
          <UploadCloud className="text-white/50 mb-3" size={28} />
          <p className="text-sm text-white/85 mb-1">Drag and drop files here</p>
          <p className="text-xs text-white/45 mb-4">CSV, TSV, XLSX, PDF, DOCX, Markdown, TXT, HTML, JSON</p>
          <GlassButton strong>Browse Files</GlassButton>
        </div>
      </GlassCard>

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Sources ({dataSources.length})</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-white/40 text-xs border-b border-white/10">
                <th className="py-2 pr-4 font-medium">Name</th>
                <th className="py-2 pr-4 font-medium">Type</th>
                <th className="py-2 pr-4 font-medium">Category</th>
                <th className="py-2 pr-4 font-medium">Records</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Updated</th>
                <th className="py-2 pr-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {dataSources.map((s) => (
                <tr key={s.id} className="border-b border-white/5 hover:bg-white/[0.03]">
                  <td className="py-3 pr-4 text-white/85 cursor-pointer" onClick={() => setSelected(s)}>{s.name}</td>
                  <td className="py-3 pr-4 text-white/50 uppercase text-xs">{s.type}</td>
                  <td className="py-3 pr-4 text-white/60 text-xs">{s.category}</td>
                  <td className="py-3 pr-4 text-white/60 text-xs">{s.records.toLocaleString()}</td>
                  <td className="py-3 pr-4"><StatusBadge status={s.status} /></td>
                  <td className="py-3 pr-4 text-white/40 text-xs">{s.updatedAt}</td>
                  <td className="py-3 pr-4">
                    <div className="flex gap-1.5">
                      <button className="liquid-glass w-7 h-7 rounded-full flex items-center justify-center text-white/50 hover:text-white" aria-label="Reprocess"><RotateCcw size={12} /></button>
                      <button className="liquid-glass w-7 h-7 rounded-full flex items-center justify-center text-white/50 hover:text-white" aria-label="Remove"><Trash2 size={12} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/50" onClick={() => setSelected(null)}>
          <div className="w-full max-w-md h-full glass-panel-solid p-6 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <p className="font-medium text-white">{selected.name}</p>
              <button onClick={() => setSelected(null)} className="text-white/50 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3 text-sm">
              <Row label="Detected format" value={selected.type.toUpperCase()} />
              <Row label="Category" value={selected.category} />
              <Row label="Records" value={selected.records.toLocaleString()} />
              <Row label="Version" value={`v${selected.version}`} />
              <Row label="Status" value={selected.status.replace(/_/g, " ")} />
              <Row label="Last updated" value={selected.updatedAt} />
            </div>
            <div className="mt-5 pt-5 border-t border-white/10">
              <p className="text-xs text-white/50 mb-2">Processing stages</p>
              <div className="space-y-1.5">
                {["Inspecting", "Mapping", "Normalizing", "Indexing", "Updating graph", "Validating"].map((stg) => (
                  <div key={stg} className="flex items-center gap-2 text-xs text-white/70">
                    <span className="w-1.5 h-1.5 rounded-full bg-white/70" /> {stg}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-white/45">{label}</span>
      <span className="text-white/85 capitalize">{value}</span>
    </div>
  );
}
