import { createContext, useContext, useState, type ReactNode } from "react";
import { getToken, removeToken, setToken } from "../api/client";
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

  function signIn(authUser: AuthUser) {
    const stored: StoredUser = {
      user_id: authUser.user_id,
      full_name: authUser.full_name,
      email: authUser.email,
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
