"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { ErrorState, LoadingState } from "@/components/shared/states";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) return <LoadingState label="Checking operator access…" />;
  if (!user?.is_platform_admin) {
    return (
      <ErrorState message="This area is restricted to ATLASOPS platform administrators." />
    );
  }
  return <div className="space-y-6">{children}</div>;
}
