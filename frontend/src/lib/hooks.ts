"use client";

import { useCallback, useEffect, useState } from "react";
import { apiClient, ApiError } from "@/lib/api";

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => setReloadKey((value) => value + 1), []);

  useEffect(() => {
    if (!path) return;
    let active = true;
    setLoading(true);
    setError(null);
    apiClient
      .get<T>(path)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof ApiError ? err.message : "Request failed");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, reloadKey]);

  return { data, error, loading, reload };
}

export function useActiveWorkspaceId(): string | null {
  const [id, setId] = useState<string | null>(null);
  useEffect(() => {
    setId(window.localStorage.getItem("rg_workspace_id"));
    const onChange = () => setId(window.localStorage.getItem("rg_workspace_id"));
    window.addEventListener("rg-workspace-changed", onChange);
    return () => window.removeEventListener("rg-workspace-changed", onChange);
  }, []);
  return id;
}
