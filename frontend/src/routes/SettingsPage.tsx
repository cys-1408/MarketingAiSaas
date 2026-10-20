import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton } from "../components/glass/Glass";
import { currentUser, currentWorkspace } from "../services/mock/fixtures";

const tabs = ["Profile", "Workspace", "Integrations", "Data & Privacy", "Notifications"];

export default function SettingsPage() {
  const [tab, setTab] = useState(tabs[0]);
  return (
    <DashboardShell title="Settings">
      <GlassCard className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`liquid-glass px-3 py-1.5 rounded-full text-xs ${tab === t ? "bg-white/15 text-white" : "text-white/55"}`}>
            {t}
          </button>
        ))}
      </GlassCard>

      {tab === "Profile" && (
        <GlassCard className="space-y-3 max-w-lg">
          <div className="w-14 h-14 rounded-full liquid-glass-strong flex items-center justify-center text-sm font-medium text-white">
            {currentUser.avatarInitials}
          </div>
          <Field label="Name" value={currentUser.name} />
          <Field label="Email" value={currentUser.email} />
          <GlassButton className="text-xs">Manage sessions</GlassButton>
        </GlassCard>
      )}

      {tab === "Workspace" && (
        <GlassCard className="space-y-3 max-w-lg">
          <Field label="Workspace name" value={currentWorkspace.name} />
          <Field label="Plan" value={currentWorkspace.plan} />
          <Field label="Members" value={`${currentWorkspace.memberCount} members`} />
          <GlassButton strong className="text-xs">Invite member</GlassButton>
        </GlassCard>
      )}

      {tab === "Integrations" && (
        <GlassCard><p className="text-sm text-white/60">Manage connected providers from the Integrations page.</p></GlassCard>
      )}

      {tab === "Data & Privacy" && (
        <GlassCard className="space-y-3 max-w-lg">
          <SettingRow label="Data export" action="Request export" />
          <SettingRow label="Source deletion" action="Manage sources" />
          <SettingRow label="Workspace data deletion" action="Request deletion" />
          <SettingRow label="Hosted model fallback consent" action="Review" />
        </GlassCard>
      )}

      {tab === "Notifications" && (
        <GlassCard className="space-y-2 max-w-lg">
          {["Ingestion failures", "Mapping reviews pending", "Integration failures", "Report completion"].map((n) => (
            <label key={n} className="flex items-center justify-between liquid-glass rounded-xl px-3 py-2.5 text-sm text-white/75">
              {n}
              <input type="checkbox" defaultChecked className="accent-white/80" />
            </label>
          ))}
        </GlassCard>
      )}
    </DashboardShell>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-white/50 mb-1">{label}</p>
      <input defaultValue={value} className="w-full liquid-glass rounded-xl px-3 py-2 text-sm text-white outline-none" />
    </div>
  );
}

function SettingRow({ label, action }: { label: string; action: string }) {
  return (
    <div className="flex items-center justify-between liquid-glass rounded-xl px-3 py-2.5">
      <span className="text-sm text-white/75">{label}</span>
      <button className="text-xs text-white/60 hover:text-white">{action}</button>
    </div>
  );
}
