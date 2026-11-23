import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api/client";
import type { WorkspaceStatus } from "../types/api";

export function useWorkspaceStatus(
  token: string,
  authenticated = false,
  scope = "",
  guest = false,
) {
  const key = `${token}:${authenticated}:${guest}:${scope}`;
  const [snapshot, setSnapshot] = useState<{
    token: string;
    data: WorkspaceStatus;
  } | null>(null);
  const [error, setError] = useState<{ token: string; message: string } | null>(
    null,
  );
  const [requestToken, setRequestToken] = useState(token);
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const refresh = useCallback(async () => {
    controller.current?.abort();
    if (!token.trim() && !authenticated && !guest) {
      setLoading(false);
      return;
    }
    const request = new AbortController();
    controller.current = request;
    setRequestToken(key);
    setLoading(true);
    setError(null);
    try {
      const data = guest
        ? await api.publicWorkspace(request.signal)
        : await api.workspace(token, request.signal);
      if (controller.current === request && !request.signal.aborted)
        setSnapshot({ token: key, data });
    } catch (issue) {
      if (controller.current === request && !request.signal.aborted) {
        setSnapshot(null);
        setError({
          token: key,
          message:
            issue instanceof Error
              ? issue.message
              : "Chưa đọc được trạng thái dataset.",
        });
      }
    } finally {
      if (controller.current === request) setLoading(false);
    }
  }, [token, authenticated, guest, key]);
  useEffect(() => {
    controller.current?.abort();
    const timer = setTimeout(() => void refresh(), 800);
    const poll = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 30_000);
    return () => {
      clearTimeout(timer);
      clearInterval(poll);
      controller.current?.abort();
      controller.current = null;
    };
  }, [refresh]);
  return {
    workspace: snapshot?.token === key ? snapshot.data : null,
    error: error?.token === key ? error.message : null,
    loading: requestToken === key && loading,
    refresh,
  };
}
