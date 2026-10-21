import { useCallback, useEffect, useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { request, ApiError } from "../services/api";
import type { ProviderMeta } from "../types";

const categories = [
  { key: "web_analytics", label: "Web Analytics" },
  { key: "email", label: "Email Marketing" },
  { key: "crm", label: "CRM" },
  { key: "advertising", label: "Advertising" },
  { key: "other", label: "Other" },
] as const;

interface SyncResult {
  sync_id: string;
  mode: string;
  status: string;
  records_imported: number;
  pages_fetched: number;
  warnings: string[];
}

export default function IntegrationsPage() {
  const [providers, setProviders] = useState<ProviderMeta[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await request<{ providers: ProviderMeta[] }>("/integrations");
      setProviders(data.providers);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load integrations.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function connect(provider: ProviderMeta) {
    setBusy(provider.provider);
    setError(null);
    setMessage(null);
    try {
      if (!provider.server_configured) {
        setError(`${provider.label} is not configured on this server: OAuth client credentials are missing, so real connections cannot be made.`);
        return;
      }
      const result = await request<{ authorize_url: string; connection_id: string }>(
        `/integrations/${provider.provider}/connect`,
        { method: "POST", body: { redirect_uri: "" } },
      );
      setMessage(
        `Authorization started for ${provider.label}. Complete the provider's consent screen in the opened tab, then press Refresh here — connection state comes from the server.`,
      );
      window.open(result.authorize_url, "_blank", "noopener");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Starting authorization failed.");
    } finally {
      setBusy(null);
    }
  }

  async function sync(provider: ProviderMeta) {
    if (!provider.connection_id) {
      setError("No connection id available for this provider.");
      return;
    }
    setBusy(provider.provider);
    setError(null);
    setMessage(null);
    try {
      const result = await request<SyncResult>(`/integrations/${provider.connection_id}/sync`, { method: "POST" });
      setMessage(
        result.status === "success"
          ? `Sync completed: ${result.records_imported} records imported (${result.mode} mode, ${result.pages_fetched} pages).`
          : `Sync run ${result.sync_id} ended with status "${result.status}".${result.warnings.length ? ` Warnings: ${result.warnings.join("; ")}` : ""}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Sync failed.");
    } finally {
      setBusy(null);
    }
  }

  async function doDisconnect() {
    if (!disconnecting) return;
    setBusy(disconnecting);
    setError(null);
    setMessage(null);
    try {
      await request(`/integrations/${disconnecting}`, { method: "DELETE" });
      setMessage("Disconnected by the server. Historical imported data stays available for audit purposes.");
      setDisconnecting(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Disconnect failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <DashboardShell title="Integrations">
      {error && (
        <GlassCard>
          <p role="alert" className="text-xs text-white/85">{error}</p>
        </GlassCard>
      )}
      {message && (
        <GlassCard>
          <p role="status" className="text-xs text-white/80">{message}</p>
        </GlassCard>
      )}

      {!providers ? (
        <GlassCard><p className="text-xs text-white/40">Loading providers…</p></GlassCard>
      ) : providers.length === 0 ? (
        <GlassCard><p className="text-xs text-white/50">No providers are registered on this server build.</p></GlassCard>
      ) : (
        categories.map((cat) => {
          const items = providers.filter((i) => i.category === cat.key);
          if (!items.length) return null;
          return (
            <div key={cat.key}>
              <h2 className="text-sm font-medium text-white/60 mb-2">{cat.label}</h2>
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                {items.map((i) => {
                  const disconnected = i.workspace_status === "disconnected";
                  return (
                    <GlassCard key={i.provider}>
                      <div className="flex items-start justify-between mb-2">
                        <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-xs font-medium text-white/80">
                          {i.label.slice(0, 2).toUpperCase()}
                        </div>
                        <StatusBadge status={i.server_configured ? i.workspace_status : "not_configured"} />
                      </div>
                      <p className="text-sm font-medium text-white/90 mb-1">{i.label}</p>
                      <p className="text-xs text-white/50 mb-3 leading-relaxed">{i.description}</p>
                      {i.last_synced_at && (
                        <p className="text-[11px] text-white/35 mb-3">
                          Last sync: {new Date(i.last_synced_at).toLocaleString()}
                        </p>
                      )}
                      {!i.server_configured && (
                        <p className="text-[11px] text-white/45 mb-3">
                          Server-side OAuth credentials for {i.label} are not configured, so this provider cannot connect yet.
                          An administrator must add the provider's client credentials to the environment.
                        </p>
                      )}
                      <div className="flex gap-2">
                        {i.workspace_status === "connected" ? (
                          <>
                            <GlassButton
                              strong
                              className="text-xs px-3 py-1.5"
                              onClick={() => void sync(i)}
                              disabled={busy === i.provider}
                            >
                              Sync now
                            </GlassButton>
                            <button
                              onClick={() => setDisconnecting(i.connection_id ?? i.provider)}
                              className="liquid-glass px-3 py-1.5 rounded-full text-xs text-white/50 hover:text-white"
                            >
                              Disconnect
                            </button>
                          </>
                        ) : (
                          <GlassButton
                            strong
                            className="text-xs px-3 py-1.5"
                            onClick={() => void connect(i)}
                            disabled={busy === i.provider}
                          >
                            {disconnected ? "Reconnect" : "Connect"}
                          </GlassButton>
                        )}
                      </div>
                    </GlassCard>
                  );
                })}
              </div>
            </div>
          );
        })
      )}

      {disconnecting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setDisconnecting(null)}>
          <div className="liquid-glass-strong rounded-2xl p-6 w-80" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <p className="text-sm text-white mb-2">Disconnect this integration?</p>
            <p className="text-xs text-white/50 mb-5">Historical imported data will remain, but new data will stop syncing. The provider token is revoked where supported.</p>
            <div className="flex gap-2">
              <GlassButton onClick={() => setDisconnecting(null)} className="flex-1 text-xs">Cancel</GlassButton>
              <GlassButton strong onClick={() => void doDisconnect()} disabled={busy === disconnecting} className="flex-1 text-xs">
                {busy === disconnecting ? "Disconnecting…" : "Disconnect"}
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}
