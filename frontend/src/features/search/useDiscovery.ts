import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../services/api/client";
import type { DiscoveryResponse } from "../../types/api";

/** Fetch one fresh gallery sample per visit; keep it stable across renders. */
export const DISCOVERY_IMAGE_LIMIT = 24;

export function useDiscovery(
  enabled: boolean,
  token: string,
  limit = DISCOVERY_IMAGE_LIMIT,
) {
  const pending = useRef<AbortController | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [snapshot, setSnapshot] = useState<{
    token: string;
    attempt: number;
    limit: number;
    results: DiscoveryResponse | null;
    error: string | null;
  } | null>(null);
  useEffect(() => {
    if (!enabled) return;
    const request = new AbortController();
    void api
      .discovery(limit, token, request.signal)
      .then((results) => {
        if (!request.signal.aborted) {
          setLoadingMore(false);
          setMoreError(null);
          setSnapshot({ token, attempt, limit, results, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!request.signal.aborted)
          setSnapshot({
            token,
            attempt,
            limit,
            results: null,
            error:
              error instanceof Error
                ? error.message
                : "Chưa tải được ảnh khám phá. Bạn vẫn có thể thử tìm kiếm.",
          });
      });
    return () => {
      request.abort();
      pending.current?.abort();
      pending.current = null;
    };
  }, [enabled, token, attempt, limit]);
  const current =
    enabled &&
    snapshot?.token === token &&
    snapshot.attempt === attempt &&
    snapshot.limit === limit
      ? snapshot
      : null;
  async function loadMore() {
    const page = current?.results;
    if (!page?.has_more || !page.seed || !page.next_cursor || pending.current)
      return;
    const controller = new AbortController();
    pending.current = controller;
    setLoadingMore(true);
    setMoreError(null);
    try {
      const next = await api.discovery(limit, token, controller.signal, {
        seed: page.seed,
        cursor: page.next_cursor,
      });
      if (controller.signal.aborted) return;
      setSnapshot((previous) => {
        if (
          !previous ||
          !previous.results ||
          previous.token !== token ||
          previous.attempt !== attempt ||
          previous.results?.seed !== page.seed
        )
          return previous;
        const seen = new Set(
          previous.results.results.map((image) => image.image_id),
        );
        const images = [
          ...previous.results.results,
          ...next.results.filter((image) => !seen.has(image.image_id)),
        ].map((image, index) => ({ ...image, rank: index + 1 }));
        return {
          ...previous,
          results: { ...next, results: images, total_results: images.length },
        };
      });
    } catch (error) {
      if (!controller.signal.aborted)
        setMoreError(
          error instanceof Error
            ? error.message
            : "Chưa tải được ảnh tiếp theo.",
        );
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setLoadingMore(false);
      }
    }
  }
  const retry = useCallback(() => {
    setLoadingMore(false);
    setMoreError(null);
    setAttempt((value) => value + 1);
  }, []);
  return {
    results: current?.results ?? null,
    error: current?.error ?? null,
    loading: enabled && !current,
    retry,
    hasMore: current?.results?.has_more ?? false,
    loadingMore,
    moreError,
    loadMore,
  };
}
