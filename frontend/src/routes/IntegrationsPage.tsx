import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { integrations } from "../services/mock/fixtures";

const categories = [
  { key: "web_analytics", label: "Web Analytics" },
  { key: "email", label: "Email Marketing" },
  { key: "crm", label: "CRM" },
  { key: "advertising", label: "Advertising" },
  { key: "other", label: "Other" },
] as const;

export default function IntegrationsPage() {
  const [disconnecting, setDisconnecting] = useState<string | null>(null);

  return (
    <DashboardShell title="Integrations">
      {categories.map((cat) => {
        const items = integrations.filter((i) => i.category === cat.key);
        if (!items.length) return null;
        return (
          <div key={cat.key}>
            <h2 className="text-sm font-medium text-white/60 mb-2">{cat.label}</h2>
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
              {items.map((i) => (
                <GlassCard key={i.id}>
                  <div className="flex items-start justify-between mb-2">
                    <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center text-xs font-medium text-white/80">
                      {i.name.slice(0, 2).toUpperCase()}
                    </div>
                    <StatusBadge status={i.status} />
                  </div>
                  <p className="text-sm font-medium text-white/90 mb-1">{i.name}</p>
                  <p className="text-xs text-white/50 mb-3 leading-relaxed">{i.description}</p>
                  {i.lastSync && <p className="text-[11px] text-white/35 mb-3">Last sync: {i.lastSync}</p>}
                  <div className="flex gap-2">
                    {i.status === "connected" || i.status === "syncing" ? (
                      <>
                        <GlassButton className="text-xs px-3 py-1.5">Sync now</GlassButton>
                        <button
                          onClick={() => setDisconnecting(i.id)}
                          className="liquid-glass px-3 py-1.5 rounded-full text-xs text-white/50 hover:text-white"
                        >
                          Disconnect
                        </button>
                      </>
                    ) : i.status === "error" ? (
                      <GlassButton strong className="text-xs px-3 py-1.5">Reconnect</GlassButton>
                    ) : (
                      <GlassButton strong className="text-xs px-3 py-1.5">Connect</GlassButton>
                    )}
                  </div>
                </GlassCard>
              ))}
            </div>
          </div>
        );
      })}

      {disconnecting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setDisconnecting(null)}>
          <div className="liquid-glass-strong rounded-2xl p-6 w-80" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm text-white mb-2">Disconnect this integration?</p>
            <p className="text-xs text-white/50 mb-5">Historical data will remain, but new data will stop syncing.</p>
            <div className="flex gap-2">
              <GlassButton onClick={() => setDisconnecting(null)} className="flex-1 text-xs">Cancel</GlassButton>
              <GlassButton strong onClick={() => setDisconnecting(null)} className="flex-1 text-xs">Disconnect</GlassButton>
            </div>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}
