import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

/**
 * Client-side guard for usability only. Server authorization (workspace
 * capability checks in every backend route) remains the security authority.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { ready, isAuthenticated } = useAuth();
  if (!ready) {
    return (
      <div className="min-h-screen bg-ink-950 flex items-center justify-center text-white/50 text-sm">
        Restoring session…
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
