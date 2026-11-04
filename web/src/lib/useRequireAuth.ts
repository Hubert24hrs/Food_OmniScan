"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./auth";

/** Client-side redirect for UX only; the API enforces authorization on every request. */
export function useRequireAuth() {
  const auth = useAuth();
  const router = useRouter();
  const path = usePathname();
  useEffect(() => {
    if (!auth.loading && !auth.me) router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [auth.loading, auth.me, router, path]);
  return auth;
}
