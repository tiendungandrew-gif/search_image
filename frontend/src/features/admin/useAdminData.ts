import { useCallback, useEffect, useRef, useState } from "react";

export function useAdminData<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const sequence = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++sequence.current;
    setLoading(true);
    setError(null);
    try {
      const value = await load();
      if (id === sequence.current) setData(value);
    } catch (issue) {
      if (id === sequence.current)
        setError(
          issue instanceof Error ? issue.message : "Không tải được dữ liệu.",
        );
    } finally {
      if (id === sequence.current) setLoading(false);
    }
  }, [load]);
  useEffect(() => {
    const timer = setTimeout(() => void refresh(), 0);
    const invalidate = () => { ++sequence.current; };
    return () => {
      clearTimeout(timer);
      invalidate();
    };
  }, [refresh]);
  return { data, loading, error, refresh };
}
