import { useEffect, useRef, useState } from "react";
import type { Account } from "../../types/access";
import { ResultGallery } from "../search/ResultGallery";
import { profileAPI } from "./api";
import type { SearchResult } from "../../types/api";
export default function FavoritesPage({ user }: { user: Account }) {
  const [images, setImages] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    if (user.is_demo) return;
    const controller = new AbortController();
    void profileAPI
      .favorites(undefined, controller.signal)
      .then((page) => {
        if (!controller.signal.aborted) {
          setImages(page.results);
          setTotal(page.total_saved);
          setCursor(page.next_cursor);
          setError(null);
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setError(
            error instanceof Error
              ? error.message
              : "Chưa tải được ảnh yêu thích.",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    const changed = (event: Event) => {
      const detail = (event as CustomEvent<{ id: string; saved: boolean }>)
        .detail;
      if (!detail.saved) {
        setImages((current) =>
          current.filter((image) => image.image_id !== detail.id),
        );
        setTotal((value) => Math.max(0, value - 1));
      }
    };
    window.addEventListener("synlens:favorites-changed", changed);
    return () => {
      controller.abort();
      window.removeEventListener("synlens:favorites-changed", changed);
    };
  }, [user.is_demo, attempt]);
  return (
    <section className="favorites-page">
      <header className="personal-page-heading">
        <div>
          <span className="personal-eyebrow">CẢM HỨNG BẠN LƯU GIỮ</span>
          <h1>Ảnh yêu thích</h1>
          <p>{total} ảnh trong bộ sưu tập của bạn</p>
        </div>
        <a href="/profile" className="profile-favorites-link">
          Hồ sơ của tôi ↗
        </a>
      </header>
      {user.is_demo ? (
        <p>Dùng tài khoản cá nhân để lưu ảnh yêu thích.</p>
      ) : (
        <>
          {error && (
            <div role="alert" className="form-alert">
              {error}{" "}
              <button
                type="button"
                onClick={() => setAttempt((value) => value + 1)}
              >
                Thử lại
              </button>
            </div>
          )}
          {loading ? (
            <p role="status">Đang tải ảnh yêu thích…</p>
          ) : images.length ? (
            <div className="friendly-search">
              <ResultGallery
                images={images}
                token=""
                showDiagnostics={false}
                showRanks={false}
                datasetNames={Object.fromEntries(
                  user.datasets.map((dataset) => [dataset.key, dataset.name]),
                )}
              />
            </div>
          ) : (
            !error && (
              <div className="favorites-empty">
                <span aria-hidden="true">♡</span>
                <h2>Lưu lại những góc nhìn bạn thích</h2>
                <p>
                  Nhấn trái tim trên ảnh để thêm vào bộ sưu tập riêng của bạn.
                </p>
                <a className="primary-button" href="/">
                  Khám phá hình ảnh
                </a>
              </div>
            )
          )}
          {cursor && (
            <div className="discovery-more">
              <button
                className="secondary-button"
                disabled={loadingMore}
                type="button"
                onClick={async () => {
                  if (loadingMore) return;
                  setLoadingMore(true);
                  setError(null);
                  try {
                    const page = await profileAPI.favorites(cursor);
                    if (!alive.current) return;
                    setImages((current) => {
                      const ids = new Set(
                        current.map((image) => image.image_id),
                      );
                      return [
                        ...current,
                        ...page.results.filter(
                          (image) => !ids.has(image.image_id),
                        ),
                      ];
                    });
                    setCursor(page.next_cursor);
                    setTotal(page.total_saved);
                  } catch (error) {
                    if (alive.current)
                      setError(
                        error instanceof Error
                          ? error.message
                          : "Chưa tải được ảnh.",
                      );
                  } finally {
                    if (alive.current) setLoadingMore(false);
                  }
                }}
              >
                {loadingMore ? "Đang tải…" : "Xem thêm ảnh"}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
