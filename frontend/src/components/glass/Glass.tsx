import type { ButtonHTMLAttributes, ReactNode, CSSProperties } from "react";
import clsx from "clsx";

export function GlassButton({
  children, strong, className, ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode; strong?: boolean }) {
  return (
    <button
      {...props}
      className={clsx(
        strong ? "liquid-glass-strong" : "liquid-glass",
        "px-5 py-2.5 rounded-full text-sm font-medium text-white/90 transition-all duration-200",
        "hover:scale-[1.05] active:scale-[0.95] inline-flex items-center gap-2 justify-center",
        className
      )}
    >
      {children}
    </button>
  );
}

export function GlassPill({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        "liquid-glass px-4 py-1.5 rounded-full text-xs font-medium text-white/80 inline-flex items-center gap-1.5",
        className
      )}
    >
      {children}
    </span>
  );
}

export function GlassCard({
  children, className, strong, style,
}: { children: ReactNode; className?: string; strong?: boolean; style?: CSSProperties }) {
  return (
    <div style={style} className={clsx(strong ? "liquid-glass-strong" : "liquid-glass", "p-5", className)}>
      {children}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ready: "bg-white/15 text-white", connected: "bg-white/15 text-white",
    active: "bg-white/15 text-white", running: "bg-white/15 text-white",
    processing: "bg-white/10 text-white/70", indexing: "bg-white/10 text-white/70",
    syncing: "bg-white/10 text-white/70", awaiting_review: "bg-white/10 text-white/80",
    partial: "bg-white/10 text-white/70", draft: "bg-white/5 text-white/50",
    paused: "bg-white/5 text-white/50", not_connected: "bg-white/5 text-white/50",
    failed: "bg-white/5 text-white/40 line-through", error: "bg-white/5 text-white/40",
    retryable_failure: "bg-white/10 text-white/60", completed: "bg-white/10 text-white/70",
    cancelled: "bg-white/5 text-white/40",
  };
  return (
    <span className={clsx("liquid-glass px-2.5 py-1 rounded-full text-[11px] font-medium capitalize", map[status] ?? "bg-white/10 text-white/70")}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function DemoBadge() {
  return (
    <span className="liquid-glass px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider text-white/60 font-medium">
      Demo data
    </span>
  );
}
