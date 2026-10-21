import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { BRAND_NAME } from "../brand";
import { ShieldAlert } from "lucide-react";

export default function ModelSettingsPage() {
  const [connected, setConnected] = useState(false);
  const [pairing, setPairing] = useState(false);
  const [hostedFallback, setHostedFallback] = useState(false);

  function pair() {
    setPairing(true);
    setTimeout(() => { setPairing(false); setConnected(true); }, 1400);
  }

  return (
    <DashboardShell title="Model & Ollama Connector">
      <GlassCard>
        <p className="text-sm text-white/80 mb-2">Inference architecture</p>
        <p className="text-xs text-white/50 leading-relaxed">
          Application services and workspace data are hosted in the cloud. Model inference can run locally on your computer
          through the Ollama connector, or optionally fall back to hosted inference if you explicitly opt in. Local inference
          does not mean all workspace data stays local — retrieved context relevant to a query is sent to your local connector
          to generate a response.
        </p>
      </GlassCard>

      <GlassCard className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-sm text-white/85 mb-1">Connector status</p>
          <StatusBadge status={pairing ? "processing" : connected ? "connected" : "not_connected"} />
        </div>
        {!connected ? (
          <GlassButton strong onClick={pair} disabled={pairing}>{pairing ? "Pairing…" : "Pair Device"}</GlassButton>
        ) : (
          <GlassButton onClick={() => setConnected(false)}>Disconnect</GlassButton>
        )}
      </GlassCard>

      {connected && (
        <GlassCard>
          <p className="text-sm font-medium text-white/85 mb-3">Connected device</p>
          <div className="grid md:grid-cols-2 gap-3 text-xs">
            <Row label="Selected model" value="llama3.1:8b" />
            <Row label="Last health check" value="30 seconds ago" />
            <Row label="Response latency" value="~420ms" />
            <Row label="Capability status" value="All supported" />
          </div>
        </GlassCard>
      )}

      <GlassCard>
        <p className="text-sm font-medium text-white/85 mb-3">Current inference mode</p>
        <div className="flex items-center justify-between liquid-glass rounded-xl px-4 py-3">
          <span className="text-sm text-white/75">{connected ? "Local (Ollama connector)" : "Not configured"}</span>
          <StatusBadge status={connected ? "connected" : "not_connected"} />
        </div>
      </GlassCard>

      <GlassCard>
        <div className="flex items-start gap-3">
          <ShieldAlert size={16} className="text-white/50 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-white/85 mb-1">Hosted model fallback</p>
            <p className="text-xs text-white/50 mb-3 leading-relaxed">
              Opt-in only. {BRAND_NAME} never silently switches from local to hosted inference. Never expose your local
              Ollama instance directly to the public internet.
            </p>
            <label className="flex items-center gap-2 text-xs text-white/70">
              <input type="checkbox" checked={hostedFallback} onChange={(e) => setHostedFallback(e.target.checked)} className="accent-white/80" />
              I explicitly consent to hosted-model fallback when local inference is unavailable.
            </label>
          </div>
        </div>
      </GlassCard>
    </DashboardShell>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between liquid-glass rounded-lg px-3 py-2">
      <span className="text-white/45">{label}</span>
      <span className="text-white/85">{value}</span>
    </div>
  );
}
