import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Sparkles, BarChart3, GitCompareArrows, Network,
  FolderUp, ListChecks, Plug, ShieldCheck, Wand2, Lightbulb, FlaskConical,
  FileText, Gauge, Server, History, Settings, ChevronsLeft, ChevronsRight,
} from "lucide-react";
import { useState } from "react";
import clsx from "clsx";

import { BRAND_NAME } from "../../brand";

const sections = [
  {
    label: "Workspace",
    items: [
      { to: "/app/overview", label: "Overview", icon: LayoutDashboard },
      { to: "/app/investigations", label: "AI Investigations", icon: Sparkles },
      { to: "/app/campaigns", label: "Campaign Analytics", icon: BarChart3 },
      { to: "/app/campaign-comparison", label: "Campaign Comparison", icon: GitCompareArrows },
      { to: "/app/evidence-graph", label: "Evidence Graph", icon: Network },
    ],
  },
  {
    label: "Data",
    items: [
      { to: "/app/sources", label: "Sources & Files", icon: FolderUp },
      { to: "/app/mapping-review", label: "Mapping Review", icon: ListChecks },
      { to: "/app/integrations", label: "Integrations", icon: Plug },
      { to: "/app/data-quality", label: "Data Quality", icon: ShieldCheck },
    ],
  },
  {
    label: "Marketing Studio",
    items: [
      { to: "/app/content-studio", label: "Content Studio", icon: Wand2 },
      { to: "/app/recommendations", label: "Recommendations", icon: Lightbulb },
      { to: "/app/experiments", label: "Experiments", icon: FlaskConical },
      { to: "/app/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/app/evaluation", label: "Evaluation & Quality", icon: Gauge },
      { to: "/app/settings/model", label: "Model & Connector", icon: Server },
      { to: "/app/activity", label: "Activity & Audit Log", icon: History },
      { to: "/app/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <aside
      className={clsx(
        "hidden md:flex flex-col liquid-glass m-3 mr-0 rounded-3xl transition-all duration-300 shrink-0",
        collapsed ? "w-[76px]" : "w-64"
      )}
    >
      <div className="flex items-center justify-between px-4 py-4">
        {!collapsed && (
          <span className="font-semibold tracking-tight text-white/90 text-sm">{BRAND_NAME}</span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="liquid-glass w-8 h-8 rounded-full flex items-center justify-center text-white/60 hover:text-white"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronsRight size={14} /> : <ChevronsLeft size={14} />}
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-4 space-y-5">
        {sections.map((sec) => (
          <div key={sec.label}>
            {!collapsed && (
              <p className="px-3 mb-1.5 text-[10px] uppercase tracking-wider text-white/35 font-medium">
                {sec.label}
              </p>
            )}
            <div className="space-y-1">
              {sec.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  title={collapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-colors",
                      isActive ? "bg-white/10 text-white" : "text-white/55 hover:text-white hover:bg-white/5"
                    )
                  }
                >
                  <item.icon size={16} className="shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
