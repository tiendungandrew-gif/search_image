import { useContext, useEffect, useId, useRef, useState } from "react";
import { Avatar } from "../../components/Avatar";
import { CurrentAccountContext } from "../auth/CurrentAccountContext";
import { commentsAPI, type CommentsPage } from "./commentsApi";

export function ImageComments({ imageId }: { imageId: string }) {
  const user = useContext(CurrentAccountContext);
  const inputId = useId();
  const [page, setPage] = useState<CommentsPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [deleting, setDeleting] = useState(new Set<string>());
  const nonce = useRef(crypto.randomUUID());
  const busy = useRef(false);
  const active = useRef(true);
  const canPost = Boolean(user && !user.is_demo);
  const message = (error: unknown) =>
    error instanceof Error
      ? error.message
      : "Chưa xử lý được bình luận. Vui lòng thử lại.";
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void commentsAPI
      .list(imageId, undefined, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          setPage(value);
          setLoadError(null);
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) setLoadError(message(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [imageId, attempt]);
  return (
    <section className="image-comments" aria-labelledby={`${inputId}-heading`}>
      <header className="image-comments-heading">
        <h3 id={`${inputId}-heading`}>
          Bình luận{page ? <span>{page.total}</span> : null}
        </h3>
        <button
          type="button"
          className="comments-refresh"
          title="Làm mới bình luận"
          aria-label="Làm mới bình luận"
          disabled={loading || sending || loadingMore || deleting.size > 0}
          onClick={() => {
            setLoading(true);
            setAttempt((value) => value + 1);
          }}
        >
          ↻
        </button>
      </header>
      {canPost ? (
        <form
          className="comment-composer"
          onSubmit={async (event) => {
            event.preventDefault();
            if (busy.current || loading || !page || !body.trim()) return;
            busy.current = true;
            setSending(true);
            setError(null);
            try {
              const comment = await commentsAPI.add(
                imageId,
                body.trim(),
                nonce.current,
              );
              if (!active.current) return;
              setPage((current) =>
                current
                  ? {
                      ...current,
                      comments: [
                        comment,
                        ...current.comments.filter(
                          (item) => item.id !== comment.id,
                        ),
                      ],
                      total:
                        current.total +
                        (current.comments.some((item) => item.id === comment.id)
                          ? 0
                          : 1),
                    }
                  : current,
              );
              setBody("");
              nonce.current = crypto.randomUUID();
            } catch (error) {
              if (active.current) setError(message(error));
            } finally {
              busy.current = false;
              if (active.current) setSending(false);
            }
          }}
        >
          <Avatar
            name={user!.display_name}
            url={user!.avatar_url}
            className="comment-avatar"
          />
          <div className="comment-compose-fields">
            <label className="sr-only" htmlFor={inputId}>
              Viết bình luận
            </label>
            <textarea
              id={inputId}
              placeholder="Chia sẻ cảm nhận của bạn…"
              value={body}
              maxLength={2000}
              rows={3}
              disabled={sending || loading}
              onChange={(event) => {
                setBody(event.target.value);
                nonce.current = crypto.randomUUID();
              }}
            />
            <div className="comment-compose-actions">
              <small>{body.length}/2000</small>
              <button
                type="submit"
                disabled={sending || loading || !page || !body.trim()}
              >
                {sending ? "Đang gửi…" : "Gửi bình luận"}
              </button>
            </div>
          </div>
        </form>
      ) : (
        <p className="comment-signin">
          {user?.is_demo ? (
            <>
              Dùng <a href="/profile">tài khoản cá nhân</a> để bình luận.
            </>
          ) : (
            <>
              <a href="/login">Đăng nhập</a> để chia sẻ cảm nhận của bạn.
            </>
          )}
        </p>
      )}
      {error && (
        <p className="comment-error" role="alert">
          {error}
        </p>
      )}
      {loading && (
        <p className="comment-status" role="status">
          Đang tải bình luận…
        </p>
      )}
      {loadError && (
        <p className="comment-error" role="alert">
          {loadError}{" "}
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setAttempt((value) => value + 1);
            }}
          >
            Thử lại
          </button>
        </p>
      )}
      {!loading && !loadError && page?.comments.length === 0 && (
        <p className="comment-status">
          Chưa có bình luận. Hãy là người đầu tiên chia sẻ cảm nhận!
        </p>
      )}
      <div
        className="image-comments-list"
        aria-live="polite"
        aria-relevant="additions removals"
      >
        {page?.comments.map((comment) => (
          <article className="image-comment" key={comment.id}>
            <Avatar
              name={comment.author.display_name}
              url={comment.author.avatar_url}
              className="comment-avatar"
            />
            <div className="comment-content">
              <div className="comment-author">
                <strong>{comment.author.display_name}</strong>
                <time
                  dateTime={comment.created_at}
                  title={new Date(comment.created_at).toLocaleString("vi-VN")}
                >
                  {new Date(comment.created_at).toLocaleDateString("vi-VN", {
                    day: "numeric",
                    month: "numeric",
                  })}
                </time>
              </div>
              <p>{comment.body}</p>
              {canPost && comment.can_delete && (
                <button
                  type="button"
                  className="comment-delete"
                  disabled={deleting.has(comment.id)}
                  aria-label={`Xóa bình luận của ${comment.author.display_name}`}
                  onClick={async () => {
                    setError(null);
                    setDeleting((current) => new Set(current).add(comment.id));
                    try {
                      await commentsAPI.remove(imageId, comment.id);
                      if (!active.current) return;
                      setPage((current) =>
                        current
                          ? {
                              ...current,
                              comments: current.comments.filter(
                                (item) => item.id !== comment.id,
                              ),
                              total: Math.max(0, current.total - 1),
                            }
                          : current,
                      );
                    } catch (error) {
                      if (active.current) setError(message(error));
                    } finally {
                      if (active.current)
                        setDeleting((current) => {
                          const next = new Set(current);
                          next.delete(comment.id);
                          return next;
                        });
                    }
                  }}
                >
                  {deleting.has(comment.id) ? "Đang xóa…" : "Xóa"}
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
      {page?.next_cursor && (
        <button
          type="button"
          className="comments-more"
          disabled={loadingMore || loading}
          onClick={async () => {
            if (loadingMore) return;
            setLoadingMore(true);
            setError(null);
            try {
              const next = await commentsAPI.list(imageId, page.next_cursor!);
              if (!active.current) return;
              setPage((current) => {
                if (!current) return current;
                const ids = new Set(current.comments.map((item) => item.id));
                return {
                  ...current,
                  comments: [
                    ...current.comments,
                    ...next.comments.filter((item) => !ids.has(item.id)),
                  ],
                  has_more: next.has_more,
                  next_cursor: next.next_cursor,
                };
              });
            } catch (error) {
              if (active.current) setError(message(error));
            } finally {
              if (active.current) setLoadingMore(false);
            }
          }}
        >
          {loadingMore ? "Đang tải…" : "Xem bình luận trước đó"}
        </button>
      )}
    </section>
  );
}
