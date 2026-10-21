import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  clearToken,
  getToken,
  request,
  setToken,
  UNAUTHORIZED_EVENT,
} from "../services/api";

/** Matches the backend AuthResponse / /auth/me safe user shape. */
export interface SessionUser {
  id: string;
  email: string;
  name: string;
  avatar_initials: string;
}

export interface SessionWorkspace {
  id: string;
  name: string;
  plan: string;
}

interface AuthState {
  /** null = still restoring, true/false = resolved */
  ready: boolean;
  isAuthenticated: boolean;
  user: SessionUser | null;
  workspace: SessionWorkspace | null;
  role: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    name: string,
    email: string,
    password: string,
    workspaceName: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
}

interface MeResponse {
  user: SessionUser;
  workspace: SessionWorkspace;
  role: string;
}

interface AuthResponse {
  token: string;
  user: SessionUser;
  workspace: SessionWorkspace;
  role: string;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [workspace, setWorkspace] = useState<SessionWorkspace | null>(null);
  const [role, setRole] = useState<string | null>(null);

  function apply(me: MeResponse) {
    setUser(me.user);
    setWorkspace(me.workspace);
    setRole(me.role);
    setIsAuthenticated(true);
  }

  function reset() {
    setUser(null);
    setWorkspace(null);
    setRole(null);
    setIsAuthenticated(false);
  }

  // Restore an existing session from the stored bearer token (real /me call;
  // an invalid or revoked token results in a logged-out state, never a mock).
  useEffect(() => {
    let cancelled = false;
    async function restore() {
      const token = getToken();
      if (!token) {
        setReady(true);
        return;
      }
      try {
        const me = await request<MeResponse>("/auth/me");
        if (!cancelled) apply(me);
      } catch {
        clearToken();
        if (!cancelled) reset();
      } finally {
        if (!cancelled) setReady(true);
      }
    }
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleUnauthorized = useCallback(() => {
    reset();
  }, []);

  useEffect(() => {
    const listener = () => handleUnauthorized();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, listener);
  }, [handleUnauthorized]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await request<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setToken(response.token);
    apply({ user: response.user, workspace: response.workspace, role: response.role });
  }, []);

  const signup = useCallback(
    async (
      name: string,
      email: string,
      password: string,
      workspaceName: string,
    ) => {
      const response = await request<AuthResponse>("/auth/signup", {
        method: "POST",
        body: { name, email, password, workspace_name: workspaceName },
      });
      setToken(response.token);
      apply({ user: response.user, workspace: response.workspace, role: response.role });
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await request("/auth/logout", { method: "POST" });
    } catch {
      // Revoked/expired tokens already behave as logged out; never block logout.
    }
    clearToken();
    reset();
  }, []);

  return (
    <AuthContext.Provider
      value={{ ready, isAuthenticated, user, workspace, role, login, signup, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
