"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useFetch<T>(path: string | null, deps: unknown[] = []): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(() => Boolean(path));
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const refetch = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    if (!path) return;

    let active = true;
    const kickoff = setTimeout(() => {
      if (!active) return;
      setLoading(true);
      setError(null);
    }, 0);

    api
      .get<T>(path)
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message || "Failed to load");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      clearTimeout(kickoff);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, nonce, ...deps]);

  return {
    data: path ? data : null,
    loading: path ? loading : false,
    error: path ? error : null,
    refetch,
  };
}
