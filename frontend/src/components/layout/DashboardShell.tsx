import { type ReactNode, useState } from "react";
import { Bell, HelpCircle, Search, Menu, X, LogOut } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { currentWorkspace } from "../../services/mock/fixtures";
import { useAuth } from "../../hooks/useAuth";
import { useNavigate, NavLink } from "react-router-dom";

export function DashboardShell({ children, title, actions }: { children: ReactNode; title?: string; actions?: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex bg-ink-950 text-white">
      <Sidebar />
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div className="w-72 glass-panel-solid m-3 rounded-3xl p-4 flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <span className="font-semibold text-sm">Marketing Copilot</span>
              <button onClick={() => setMobileOpen(false)} className="text-white/60"><X size={18} /></button>
            </div>
            <div className="text-white/60 text-sm">Use desktop width for full navigation.</div>
          </div>
          <div className="flex-1 bg-black/60" onClick={() => setMobileOpen(false)} />
        </div>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="liquid-glass m-3 rounded-3xl px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <button className="md:hidden text-white/70" onClick={() => setMobileOpen(true)} aria-label="Open menu">
              <Menu size={18} />
            </button>
            <div className="min-w-0">
              <p className="text-xs text-white/40 truncate">{currentWorkspace.name}</p>
              <h1 className="text-base font-medium text-white/95 truncate">{title ?? "Overview"}</h1>
            </div>
          </div>
          <div className="hidden lg:flex items-center liquid-glass rounded-full px-3 py-1.5 gap-2 text-white/50 w-72">
            <Search size={14} />
            <input
              placeholder="Search campaigns, evidence, reports…"
              className="bg-transparent outline-none text-sm placeholder:text-white/35 w-full text-white/80"
            />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {actions}
            <button className="liquid-glass w-9 h-9 rounded-full flex items-center justify-center text-white/60 hover:text-white" aria-label="Notifications">
              <Bell size={15} />
            </button>
            <button className="liquid-glass w-9 h-9 rounded-full flex items-center justify-center text-white/60 hover:text-white" aria-label="Help">
              <HelpCircle size={15} />
            </button>
            <NavLink to="/app/settings" className="liquid-glass w-9 h-9 rounded-full flex items-center justify-center text-xs font-medium text-white/80">
              {user?.avatarInitials ?? "AC"}
            </NavLink>
            <button
              onClick={() => { logout(); navigate("/"); }}
              className="liquid-glass w-9 h-9 rounded-full flex items-center justify-center text-white/60 hover:text-white"
              aria-label="Log out"
            >
              <LogOut size={15} />
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto px-3 pb-6 space-y-4">{children}</main>
      </div>
    </div>
  );
}
