"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

/** Minimal data hook: loading / error / data with reload. `deps` are extra values that should trigger a refetch. */
export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const depsKey = JSON.stringify(deps);

  const fetchData = useCallback(async () => {
    if (!path) return;
    try {
      const d = await api<T>(path);
      setData(d);
      setError(null);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    let alive = true;
    if (!path) return;
    api<T>(path)
      .then((d) => alive && (setData(d), setError(null)))
      .catch((e) => alive && setError(e as Error))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path, depsKey]);

  const reload = useCallback(async () => {
    setLoading(true);
    await fetchData();
  }, [fetchData]);

  return { data, error, loading, reload, setData };
}
