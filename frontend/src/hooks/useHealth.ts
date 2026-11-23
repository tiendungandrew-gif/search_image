import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api/client";
import type { HealthSummary } from "../types/api";

export function useHealth() {
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const load = useCallback((controller: AbortController) => {
    return api
      .health(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setHealth(data);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Lỗi kết nối API");
          setHealth(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
  }, []);
  const refresh = useCallback(() => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    return load(controller);
  }, [load]);
  useEffect(() => {
    const controller = new AbortController();
    request.current = controller;
    void load(controller);
    return () => {
      request.current?.abort();
      request.current = null;
    };
  }, [load]);
  return { health, loading, error, refresh };
}
