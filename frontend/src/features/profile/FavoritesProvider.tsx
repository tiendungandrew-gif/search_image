import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { FavoritesContext } from "./FavoritesContext";
import { profileAPI } from "./api";

export function FavoritesProvider({
  enabled,
  onSignIn,
  children,
}: {
  enabled: boolean;
  onSignIn: () => void;
  children: ReactNode;
}) {
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const cache = useRef<Record<string, boolean>>({});
  const queued = useRef(new Set<string>());
  const inFlight = useRef(new Set<string>());
  const revisions = useRef<Record<string, number>>({});
  const [pending, setPending] = useState(new Set<string>());
  const mutations = useRef(new Set<string>());
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controller = useRef(new AbortController());
  useEffect(() => {
    const active = new AbortController();
    controller.current = active;
    return () => {
      active.abort();
      if (timer.current) clearTimeout(timer.current);
      timer.current = null;
    };
  }, []);
  const ensure = useCallback(
    (id: string) => {
      if (
        !enabled ||
        cache.current[id] !== undefined ||
        inFlight.current.has(id)
      )
        return;
      queued.current.add(id);
      if (timer.current) return;
      timer.current = setTimeout(async () => {
        timer.current = null;
        const ids = [...queued.current];
        queued.current.clear();
        for (let start = 0; start < ids.length; start += 50) {
          const batch = ids.slice(start, start + 50);
          const versions = batch.map((id) => revisions.current[id] ?? 0);
          batch.forEach((id) => inFlight.current.add(id));
          try {
            const result = await profileAPI.status(
              batch,
              controller.current.signal,
            );
            if (controller.current.signal.aborted) return;
            batch.forEach((id, index) => {
              if (
                (revisions.current[id] ?? 0) === versions[index] &&
                !mutations.current.has(id)
              )
                cache.current[id] = result.includes(id);
            });
            setSaved({ ...cache.current });
          } catch {
            /* Saving retries an individual status if batch loading was unavailable. */
          } finally {
            batch.forEach((id) => inFlight.current.delete(id));
          }
        }
      }, 80);
    },
    [enabled],
  );
  const toggle = async (id: string) => {
    if (!enabled) {
      onSignIn();
      return;
    }
    if (mutations.current.has(id)) return;
    mutations.current.add(id);
    revisions.current[id] = (revisions.current[id] ?? 0) + 1;
    setPending(new Set(mutations.current));
    try {
      const current =
        cache.current[id] ??
        (await profileAPI.status([id], controller.current.signal)).includes(id);
      await profileAPI.save(id, !current);
      if (controller.current.signal.aborted) return;
      cache.current[id] = !current;
      setSaved({ ...cache.current });
      window.dispatchEvent(
        new CustomEvent("synlens:favorites-changed", {
          detail: { id, saved: !current },
        }),
      );
    } finally {
      mutations.current.delete(id);
      if (!controller.current.signal.aborted)
        setPending(new Set(mutations.current));
    }
  };
  return (
    <FavoritesContext.Provider
      value={{ saved, pending, enabled, ensure, toggle }}
    >
      {children}
    </FavoritesContext.Provider>
  );
}
