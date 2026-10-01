"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, clearOrgId, setOrgId } from "@/lib/api";
import type { MeResponse, Membership, Organization, User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  memberships: Membership[];
  currentOrganization: Organization | null;
  currentMembership: Membership | null;
  loading: boolean;
  refresh: () => Promise<MeResponse | null>;
  continueWithEmail: (opts: {
    email: string;
    remember_device?: boolean;
    invite_token?: string | null;
    return_path?: string;
  }) => Promise<{ message: string }>;
  devLogin: (email: string, full_name: string) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  switchOrg: (orgId: string) => Promise<void>;
  acceptInvitation: (token: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function applyMe(
  me: MeResponse | null,
  setters: {
    setUser: (u: User | null) => void;
    setMemberships: (m: Membership[]) => void;
    setCurrentOrganization: (o: Organization | null) => void;
    setCurrentMembership: (m: Membership | null) => void;
  }
) {
  if (!me) {
    setters.setUser(null);
    setters.setMemberships([]);
    setters.setCurrentOrganization(null);
    setters.setCurrentMembership(null);
    return;
  }
  setters.setUser(me.user);
  setters.setMemberships(me.memberships ?? []);
  setters.setCurrentOrganization(me.current_organization);
  setters.setCurrentMembership(me.current_membership);
  if (me.current_organization?.id) {
    setOrgId(me.current_organization.id);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [currentOrganization, setCurrentOrganization] = useState<Organization | null>(null);
  const [currentMembership, setCurrentMembership] = useState<Membership | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  async function refresh(): Promise<MeResponse | null> {
    try {
      const me = await api.get<MeResponse>("/auth/me");
      applyMe(me, { setUser, setMemberships, setCurrentOrganization, setCurrentMembership });
      return me;
    } catch {
      applyMe(null, { setUser, setMemberships, setCurrentOrganization, setCurrentMembership });
      return null;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function continueWithEmail(opts: {
    email: string;
    remember_device?: boolean;
    invite_token?: string | null;
    return_path?: string;
  }) {
    const data = await api.post<{
      authorization_url: string;
      mode: string;
      domain: string;
      message: string;
    }>("/auth/continue", {
      email: opts.email,
      remember_device: !!opts.remember_device,
      invite_token: opts.invite_token || null,
      return_path: opts.return_path || "/auth/callback",
    });
    window.location.href = data.authorization_url;
    return { message: data.message };
  }

  async function devLogin(email: string, full_name: string) {
    const me = await api.post<MeResponse>("/auth/dev-login", { email, full_name });
    applyMe(me, { setUser, setMemberships, setCurrentOrganization, setCurrentMembership });
    setLoading(false);
    if (me.current_organization) {
      router.push("/mission-control");
    } else {
      router.push("/onboarding");
    }
  }

  async function logout() {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore */
    }
    clearOrgId();
    applyMe(null, { setUser, setMemberships, setCurrentOrganization, setCurrentMembership });
    router.push("/login");
  }

  async function logoutAll() {
    try {
      await api.post("/auth/logout-all");
    } catch {
      /* ignore */
    }
    clearOrgId();
    applyMe(null, { setUser, setMemberships, setCurrentOrganization, setCurrentMembership });
    router.push("/login");
  }

  async function switchOrg(orgId: string) {
    const me = await api.post<MeResponse>("/auth/switch-org", { organization_id: orgId });
    setOrgId(orgId);
    applyMe(me, { setUser, setMemberships, setCurrentOrganization, setCurrentMembership });
  }

  async function acceptInvitation(token: string) {
    await api.post("/orgs/invitations/accept", { token });
    const me = await refresh();
    if (me?.current_organization) {
      router.push("/mission-control");
    } else if (me?.memberships?.length) {
      const first = me.memberships[0];
      await switchOrg(first.organization_id);
      router.push("/onboarding/plan");
    } else {
      router.push("/onboarding");
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        memberships,
        currentOrganization,
        currentMembership,
        loading,
        refresh,
        continueWithEmail,
        devLogin,
        logout,
        logoutAll,
        switchOrg,
        acceptInvitation,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** True when the membership role can mutate operational data (not viewer). */
export function canWriteRole(roleSlug: string | null | undefined): boolean {
  if (!roleSlug) return false;
  return roleSlug !== "viewer";
}

/** Roles that can update shipments / recompute risk / manage ops. */
export function canOperateRole(roleSlug: string | null | undefined): boolean {
  if (!roleSlug) return false;
  return ["owner", "admin", "operations_director", "operations_manager", "analyst"].includes(
    roleSlug
  );
}

export function canManageSecurity(roleSlug: string | null | undefined): boolean {
  if (!roleSlug) return false;
  return ["owner", "admin"].includes(roleSlug);
}

export function isPlatformAdmin(user: { is_platform_admin?: boolean } | null | undefined): boolean {
  return !!user?.is_platform_admin;
}
