import { useCallback, useEffect, useRef, useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { request, request as api, ApiError } from "../services/api";
import { UploadCloud, RotateCcw, RefreshCw, Trash2, X } from "lucide-react";
import type { IngestionJobStatus, SourceRecord } from "../types";

const ACTIVE_STATES = new Set([
  "queued", "inspecting", "mapping", "awaiting_review", "normalizing", "indexing", "graph_updating", "validating",
]);

interface UploadResult {
  source_id: string;
  job_id: string;
  status: string;
  detail: string;
}

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [busySource, setBusySource] = useState<string | null>(null);
  const [selected, setSelected] = useState<SourceRecord | null>(null);
  const [jobDetail, setJobDetail] = useState<IngestionJobStatus | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await request<{ sources: SourceRecord[] }>("/ingestion/sources");
      setSources(data.sources);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load sources.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Bounded polling while at least one job is still in flight.
  useEffect(() => {
    if (!sources?.some((s) => ACTIVE_STATES.has(s.status))) return;
    const timer = setInterval(() => void load(), 4000);
    return () => clearInterval(timer);
  }, [sources, load]);

  async function onUpload(file: File) {
    setUploading(true);
    setUploadMessage(null);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const result = await api<UploadResult>("/sources/uploads", { method: "POST", form, timeoutMs: 120_000 });
      setUploadMessage(
        result.status === "duplicate"
          ? result.detail // duplicate upload: existing source reused
          : `Upload accepted: ingestion job queued (${result.status}).`,
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(source: SourceRecord) {
    if (!window.confirm(`Delete source "${source.name}" and its indexed data? This cannot be undone.`)) return;
    setBusySource(source.source_id);
    setError(null);
    try {
      await request(`/ingestion/sources/${source.source_id}`, { method: "DELETE" });
      await load();
      if (selected?.source_id === source.source_id) setSelected(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Delete failed.");
    } finally {
      setBusySource(null);
    }
  }

  async function onReprocess(source: SourceRecord) {
    setBusySource(source.source_id);
    setError(null);
    try {
      await request(`/ingestion/sources/${source.source_id}/reprocess`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reprocess failed.");
    } finally {
      setBusySource(null);
    }
  }

  function openDetail(source: SourceRecord) {
    setSelected(source);
    setJobDetail(null);
    if (source.job_id) {
      void request<IngestionJobStatus>(`/ingestion/jobs/${source.job_id}`)
        .then(setJobDetail)
        .catch(() => setJobDetail(null));
    }
  }

  return (
    <DashboardShell title="Sources & Files">
      <GlassCard className="border-dashed">
        <div className="flex flex-col items-center justify-center text-center py-8">
          <UploadCloud className="text-white/50 mb-3" size={28} />
          <p className="text-sm text-white/85 mb-1">Upload a file to ingest</p>
          <p className="text-xs text-white/45 mb-4">CSV, TSV, XLSX, PDF, DOCX, Markdown, TXT, HTML, JSON</p>
          <GlassButton strong onClick={() => fileInput.current?.click()} disabled={uploading}>
            {uploading ? "Uploading…" : "Browse Files"}
          </GlassButton>
          <input
            ref={fileInput}
            type="file"
            className="hidden"
            accept=".csv,.tsv,.xlsx,.pdf,.docx,.md,.markdown,.txt,.html,.json"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void onUpload(file);
            }}
          />
        </div>
      </GlassCard>

      {uploadMessage && (
        <GlassCard>
          <p role="status" className="text-xs text-white/80">{uploadMessage}</p>
        </GlassCard>
      )}
      {error && (
        <GlassCard>
          <p role="alert" className="text-xs text-white/85">{error}</p>
        </GlassCard>
      )}

      <GlassCard>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium text-white/85">Sources ({sources?.length ?? 0})</p>
          <button onClick={() => void load()} className="liquid-glass px-3 py-1.5 rounded-full text-[11px] text-white/60 hover:text-white flex items-center gap-1.5" aria-label="Refresh source list">
            <RefreshCw size={11} /> Refresh
          </button>
        </div>
        {!sources ? (
          <p className="text-xs text-white/40">{loading ? "Loading sources…" : "No sources loaded."}</p>
        ) : sources.length === 0 ? (
          <p className="text-xs text-white/40 py-6 text-center">No sources yet. Upload a file above to create the first ingestion job.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/40 text-xs border-b border-white/10">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Type</th>
                  <th className="py-2 pr-4 font-medium">Category</th>
                  <th className="py-2 pr-4 font-medium">Rows</th>
                  <th className="py-2 pr-4 font-medium">Job status</th>
                  <th className="py-2 pr-4 font-medium">Updated</th>
                  <th className="py-2 pr-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.source_id} className="border-b border-white/5 hover:bg-white/[0.03]">
                    <td className="py-3 pr-4 text-white/85 cursor-pointer" onClick={() => openDetail(s)}>
                      {s.name}
                      {s.review_pending && <span className="ml-2 text-[10px] liquid-glass px-2 py-0.5 rounded-full text-white/70">review pending</span>}
                    </td>
                    <td className="py-3 pr-4 text-white/50 uppercase text-xs">{s.file_type}</td>
                    <td className="py-3 pr-4 text-white/60 text-xs">{s.category}</td>
                    <td className="py-3 pr-4 text-white/60 text-xs">{s.row_count != null ? s.row_count.toLocaleString() : "—"}</td>
                    <td className="py-3 pr-4"><StatusBadge status={s.job_status ?? s.status} /></td>
                    <td className="py-3 pr-4 text-white/40 text-xs">{s.updated_at ? new Date(s.updated_at).toLocaleString() : "—"}</td>
                    <td className="py-3 pr-4">
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => void onReprocess(s)}
                          disabled={busySource === s.source_id}
                          className="liquid-glass w-7 h-7 rounded-full flex items-center justify-center text-white/50 hover:text-white disabled:opacity-40"
                          aria-label={`Reprocess ${s.name}`}
                        >
                          <RotateCcw size={12} />
                        </button>
                        <button
                          onClick={() => void onDelete(s)}
                          disabled={busySource === s.source_id}
                          className="liquid-glass w-7 h-7 rounded-full flex items-center justify-center text-white/50 hover:text-white disabled:opacity-40"
                          aria-label={`Delete ${s.name}`}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {sources?.some((s) => ACTIVE_STATES.has(s.status)) && (
          <p className="text-[11px] text-white/35 mt-3">Job statuses refresh automatically while ingestion is in progress.</p>
        )}
      </GlassCard>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/50" onClick={() => setSelected(null)}>
          <div className="w-full max-w-md h-full glass-panel-solid p-6 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <p className="font-medium text-white">{selected.name}</p>
              <button onClick={() => setSelected(null)} className="text-white/50 hover:text-white" aria-label="Close details"><X size={18} /></button>
            </div>
            <div className="space-y-3 text-sm">
              <Row label="Detected format" value={selected.file_type.toUpperCase()} />
              <Row label="Category" value={selected.category} />
              <Row label="Rows" value={selected.row_count != null ? selected.row_count.toLocaleString() : "not reported"} />
              <Row label="Version" value={`v${selected.version}`} />
              <Row label="Status" value={(selected.job_status ?? selected.status).replace(/_/g, " ")} />
              <Row label="Last updated" value={selected.updated_at ? new Date(selected.updated_at).toLocaleString() : "—"} />
            </div>

            {selected.safe_error && (
              <p role="alert" className="liquid-glass rounded-xl px-3 py-2.5 text-xs text-white/80 mt-4">
                Error: {selected.safe_error}
              </p>
            )}

            <div className="mt-5 pt-5 border-t border-white/10">
              <p className="text-xs text-white/50 mb-2">Processing stages</p>
              {!jobDetail ? (
                <p className="text-xs text-white/40">{selected.job_id ? "Loading job stages…" : "No job recorded for this source yet."}</p>
              ) : jobDetail.stages.length === 0 ? (
                <p className="text-xs text-white/40">No stages recorded yet.</p>
              ) : (
                <div className="space-y-1.5">
                  {jobDetail.stages.map((st) => (
                    <div key={`${st.stage}-${st.started_at}`} className="flex items-center justify-between text-xs text-white/70 liquid-glass rounded-lg px-3 py-2">
                      <span className="capitalize">{st.stage.replace(/_/g, " ")}</span>
                      <span className={st.status === " succeeded" || st.status === "ok" || st.status === "success" ? "text-white/60" : undefined}>{st.status}</span>
                    </div>
                  ))}
                </div>
              )}
              {jobDetail && (
                <p className="text-[11px] text-white/35 mt-3">
                  rows {jobDetail.row_count.toLocaleString()} · ready {jobDetail.ready_count.toLocaleString()} · errors {jobDetail.error_count} · warnings {jobDetail.warning_count}
                </p>
              )}
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
