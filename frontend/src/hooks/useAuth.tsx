import { createContext, useContext, useState, type ReactNode } from "react";
import { currentUser } from "../services/mock/fixtures";

interface AuthState {
  isAuthenticated: boolean;
  user: typeof currentUser | null;
  login: (email: string, _password: string) => Promise<void>;
  signup: (name: string, email: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<typeof currentUser | null>(null);

  async function login(email: string, _password: string) {
    await new Promise((r) => setTimeout(r, 650));
    setUser({ ...currentUser, email });
    setIsAuthenticated(true);
  }

  async function signup(name: string, email: string) {
    await new Promise((r) => setTimeout(r, 650));
    setUser({ ...currentUser, name, email, avatarInitials: name.slice(0, 2).toUpperCase() });
    setIsAuthenticated(true);
  }

  function logout() {
    setIsAuthenticated(false);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
