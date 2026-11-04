"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken } from "./api";
import type { Me, Profile } from "./types";

interface AuthState {
  me: Me | null;
  profiles: Profile[];
  activeProfile: Profile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; display_name?: string; country: string; accept_terms: boolean; consent_health_data: boolean }) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  setActiveProfile: (id: string) => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null);
      setProfiles([]);
      setLoading(false);
      return;
    }
    try {
      const [m, p] = await Promise.all([api<Me>("/me"), api<Profile[]>("/profiles")]);
      setMe(m);
      setProfiles(p);
    } catch {
      setMe(null);
      setProfiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Defer to a microtask so the session check never sets state synchronously during the effect.
    Promise.resolve().then(refresh);
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ access_token: string }>("/auth/login", { body: { email, password } });
    setToken(r.access_token);
    await refresh();
  }, [refresh]);

  const register = useCallback<AuthState["register"]>(async (data) => {
    const r = await api<{ access_token: string }>("/auth/register", { body: data });
    setToken(r.access_token);
    await refresh();
  }, [refresh]);

  const logout = useCallback(() => {
    setToken(null);
    setMe(null);
    setProfiles([]);
  }, []);

  const setActiveProfile = useCallback(async (id: string) => {
    await api(`/profiles/${id}/activate`, { method: "POST" });
    await refresh();
  }, [refresh]);

  const activeProfile = useMemo(
    () => profiles.find((p) => p.is_active) || profiles.find((p) => p.is_primary) || null,
    [profiles],
  );

  const value = useMemo(
    () => ({ me, profiles, activeProfile, loading, login, register, logout, refresh, setActiveProfile }),
    [me, profiles, activeProfile, loading, login, register, logout, refresh, setActiveProfile],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
