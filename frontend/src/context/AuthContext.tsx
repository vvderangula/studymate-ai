import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError, getToken, removeToken, request, setToken } from "../api/client";
import type { AuthUser } from "../api/auth";

interface AuthContextValue {
  user: StoredUser | null;
  isAuthenticated: boolean;
  signIn: (user: AuthUser) => void;
  signOut: () => void;
}

export interface StoredUser {
  user_id: string;
  full_name: string;
  email: string;
  role?: "admin" | "user";
}

const USER_KEY = "studymate_user";

function loadStoredUser(): StoredUser | null {
  try {
    if (!getToken()) return null;
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

function saveStoredUser(user: StoredUser): void {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // Ignore storage errors.
  }
}

function clearStoredUser(): void {
  try {
    localStorage.removeItem(USER_KEY);
  } catch {
    // Ignore storage errors.
  }
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isAuthenticated: false,
  signIn: () => {},
  signOut: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<StoredUser | null>(loadStoredUser);

  // Refresh the profile (and role) from the server once per load, so role
  // changes in ADMIN_EMAILS apply without signing in again.
  useEffect(() => {
    if (!user) return;
    let live = true;
    request<{ id: string; full_name: string; email: string; role: "admin" | "user" }>("GET", "/auth/me")
      .then((me) => {
        if (!live) return;
        const next: StoredUser = { user_id: me.id, full_name: me.full_name, email: me.email, role: me.role };
        saveStoredUser(next);
        setUser(next);
      })
      .catch((err) => {
        if (live && err instanceof ApiError && err.status === 401) {
          removeToken();
          clearStoredUser();
          setUser(null);
        }
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.user_id]);

  function signIn(authUser: AuthUser) {
    const stored: StoredUser = {
      user_id: authUser.user_id,
      full_name: authUser.full_name,
      email: authUser.email,
      role: authUser.role ?? "user",
    };
    setToken(authUser.access_token);
    saveStoredUser(stored);
    setUser(stored);
  }

  function signOut() {
    removeToken();
    clearStoredUser();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: user !== null, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
