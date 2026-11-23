import { Avatar } from "../../components/Avatar";
import { ChatEmptyState } from "./ChatEmptyState";
import { RailIcon } from "./RailIcon";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Account } from "../../types/access";
import {
  chatAPI,
  type ChatMessage,
  type ChatUser,
  type Conversation,
} from "./api";

function mergeMessages(current: ChatMessage[], incoming: ChatMessage[]) {
  const messages = new Map(current.map((message) => [message.id, message]));
  for (const message of incoming) messages.set(message.id, message);
  return [...messages.values()].sort((a, b) =>
    BigInt(a.id) < BigInt(b.id) ? -1 : 1,
  );
}
function issueText(error: unknown) {
  return error instanceof Error ? error.message : "Chưa kết nối được tin nhắn.";
}

function AttachmentPreview({ image }: { image: File }) {
  const element = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const url = URL.createObjectURL(image);
    if (element.current) element.current.src = url;
    return () => URL.revokeObjectURL(url);
  }, [image]);
  return <img ref={element} alt="Ảnh sắp gửi" />;
}

function ChatThread({
  conversation,
  userId,
  onBack,
  onRefresh,
}: {
  conversation: { id: string; peer: ChatUser };
  userId: string;
  onBack: () => void;
  onRefresh: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const latest = useRef<string | undefined>(undefined);
  const list = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [older, setOlder] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const nonce = useRef(crypto.randomUUID());
  const file = useRef<HTMLInputElement>(null);
  const mounted = useRef(true);
  const [attempt, setAttempt] = useState(0);
  const [imageViewer, setImageViewer] = useState<string | null>(null);
  const scrollBottom = () =>
    requestAnimationFrame(() => {
      list.current?.scrollTo({ top: list.current.scrollHeight });
    });
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      if (document.visibilityState === "hidden") {
        timer = setTimeout(poll, 3000);
        return;
      }
      try {
        const initial = !latest.current;
        const response = await chatAPI.messages(
          conversation.id,
          latest.current ? { after: latest.current } : {},
          controller.signal,
        );
        if (controller.signal.aborted) return;
        const nearBottom =
          !list.current ||
          list.current.scrollHeight -
            list.current.scrollTop -
            list.current.clientHeight <
            100;
        setMessages((current) => mergeMessages(current, response.messages));
        if (initial) setOlder(response.has_more);
        if (response.messages.length) {
          latest.current = response.messages.at(-1)!.id;
          if (initial || nearBottom) scrollBottom();
          await chatAPI.read(conversation.id, latest.current);
          if (!controller.signal.aborted) onRefresh();
        }
        setError(null);
      } catch (error) {
        if (!controller.signal.aborted) setError(issueText(error));
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          timer = setTimeout(poll, 3000);
        }
      }
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [conversation.id, attempt, onRefresh]);
  async function loadOlder() {
    if (loadingOlder || !messages[0]) return;
    setLoadingOlder(true);
    const height = list.current?.scrollHeight ?? 0;
    try {
      const page = await chatAPI.messages(conversation.id, {
        before: messages[0].id,
      });
      if (!mounted.current) return;
      setMessages((current) => mergeMessages(current, page.messages));
      setOlder(page.has_more);
      requestAnimationFrame(() => {
        if (list.current)
          list.current.scrollTop += list.current.scrollHeight - height;
      });
    } catch (error) {
      if (mounted.current) setError(issueText(error));
    } finally {
      if (mounted.current) setLoadingOlder(false);
    }
  }
  return (
    <>
      <div className="chat-thread-heading">
        <button
          type="button"
          className="chat-icon-button"
          aria-label="Trở về cuộc trò chuyện"
          onClick={onBack}
        >
          ←
        </button>
        <div>
          <strong>{conversation.peer.display_name}</strong>
          <small>@{conversation.peer.username}</small>
        </div>
      </div>
      {error && (
        <div className="chat-error" role="status">
          {error}{" "}
          <button type="button" onClick={() => setAttempt((n) => n + 1)}>
            Thử lại
          </button>
        </div>
      )}
      <div
        className="chat-messages"
        ref={list}
        aria-label="Lịch sử trò chuyện"
        aria-live="polite"
        aria-relevant="additions"
      >
        {older && (
          <button
            type="button"
            className="chat-older"
            onClick={() => void loadOlder()}
            disabled={loadingOlder}
          >
            {loadingOlder ? "Đang tải…" : "Tin nhắn trước đó"}
          </button>
        )}
        {loading && <p role="status">Đang tải tin nhắn…</p>}
        {!loading && !messages.length && !error && (
          <p className="chat-empty">Bắt đầu bằng một lời chào 👋</p>
        )}
        {messages.map((message) => (
          <article
            key={message.id}
            className={`chat-message${message.sender_id === userId ? " is-own" : ""}`}
          >
            {message.image_url && (
              <button
                className="chat-image-button"
                type="button"
                onClick={() => setImageViewer(message.image_url)}
                aria-label="Xem ảnh trong tin nhắn"
              >
                <img
                  src={message.image_url}
                  alt="Ảnh đính kèm tin nhắn"
                  loading="lazy"
                  onLoad={() => {
                    if (
                      list.current &&
                      list.current.scrollHeight -
                        list.current.scrollTop -
                        list.current.clientHeight <
                        250
                    )
                      scrollBottom();
                  }}
                />
              </button>
            )}
            {message.body && <p>{message.body}</p>}
            <time
              dateTime={message.created_at}
              title={new Date(message.created_at).toLocaleString("vi-VN")}
            >
              {new Date(message.created_at).toLocaleTimeString("vi-VN", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </time>
          </article>
        ))}
      </div>
      <form
        className="chat-composer"
        onSubmit={async (event) => {
          event.preventDefault();
          if (sending || (!body.trim() && !image)) return;
          setSending(true);
          setSendError(null);
          try {
            const sent = await chatAPI.send(
              conversation.id,
              body.trim(),
              image,
              nonce.current,
            );
            if (!mounted.current) return;
            setMessages((current) => mergeMessages(current, [sent]));
            // The polling cursor advances only from server pages so concurrent incoming messages cannot be skipped.
            setBody("");
            setImage(null);
            if (file.current) file.current.value = "";
            nonce.current = crypto.randomUUID();
            scrollBottom();
            onRefresh();
          } catch (error) {
            if (mounted.current) setSendError(issueText(error));
          } finally {
            if (mounted.current) setSending(false);
          }
        }}
      >
        {image && (
          <div className="chat-upload-preview">
            <AttachmentPreview image={image} />
            <span>{image?.name}</span>
            <button
              type="button"
              disabled={sending}
              aria-label="Bỏ ảnh đính kèm"
              onClick={() => {
                setImage(null);
                nonce.current = crypto.randomUUID();
                if (file.current) file.current.value = "";
              }}
            >
              ✕
            </button>
          </div>
        )}
        {sendError && (
          <p className="chat-error" role="alert">
            {sendError}
          </p>
        )}
        <label className="sr-only" htmlFor="chat-message-input">
          Nhập tin nhắn
        </label>
        <textarea
          id="chat-message-input"
          value={body}
          maxLength={4000}
          disabled={sending}
          placeholder="Nhắn gì đó…"
          rows={2}
          onChange={(event) => {
            setBody(event.target.value);
            nonce.current = crypto.randomUUID();
          }}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <div className="chat-compose-actions">
          <input
            ref={file}
            id="chat-image-input"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            disabled={sending}
            onChange={(event) => {
              const selected = event.target.files?.[0];
              if (!selected) return;
              if (
                selected.size > 10 * 1024 * 1024 ||
                !["image/jpeg", "image/png", "image/webp"].includes(
                  selected.type,
                )
              ) {
                setSendError("Chọn ảnh JPEG, PNG hoặc WebP tối đa 10 MB.");
                event.target.value = "";
                return;
              }
              setImage(selected);
              nonce.current = crypto.randomUUID();
              setSendError(null);
            }}
          />
          <button
            type="button"
            className="chat-attach"
            onClick={() => file.current?.click()}
            disabled={sending}
            aria-label="Đính kèm ảnh"
          >
            ▧ <span>Gửi ảnh</span>
          </button>
          <button
            type="submit"
            className="chat-send"
            disabled={sending || (!body.trim() && !image)}
          >
            {sending ? "Đang gửi…" : "Gửi ↑"}
          </button>
        </div>
      </form>
      {imageViewer && (
        <div className="chat-image-viewer">
          <button
            type="button"
            aria-label="Đóng ảnh tin nhắn"
            onClick={() => setImageViewer(null)}
          >
            Đóng ✕
          </button>
          <img src={imageViewer} alt="Ảnh trong cuộc trò chuyện" />
        </div>
      )}
    </>
  );
}

export default function ChatWidget({
  user,
  rail = false,
}: {
  user: Account | null;
  rail?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [inboxMode, setInboxMode] = useState<"messages" | "notifications">(
    "messages",
  );
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<{
    id: string;
    peer: ChatUser;
  } | null>(null);
  const [finding, setFinding] = useState(false);
  const [query, setQuery] = useState("");
  const [people, setPeople] = useState<ChatUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const host = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const accountEnabled = Boolean(user && !user.is_demo);
  const unread = conversations.reduce(
    (sum, conversation) => sum + conversation.unread,
    0,
  );
  useEffect(() => {
    if (!accountEnabled) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      if (document.visibilityState !== "hidden")
        try {
          const values = await chatAPI.conversations(controller.signal);
          if (!controller.signal.aborted) {
            setConversations(values);
            setError(null);
          }
        } catch (error) {
          if (!controller.signal.aborted) setError(issueText(error));
        }
      if (!controller.signal.aborted)
        timer = setTimeout(poll, open ? 5000 : 15000);
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [accountEnabled, open, refresh]);
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !host.current?.contains(event.target) &&
        (!rail ||
          (event.target instanceof Element &&
            event.target.closest(".side-rail")))
      )
        setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggle.current?.focus();
      }
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [open, rail]);
  useEffect(() => {
    if (!open || !finding || !accountEnabled) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      void chatAPI
        .users(query.trim(), controller.signal)
        .then((users) => {
          if (!controller.signal.aborted) {
            setPeople(users);
            setError(null);
          }
        })
        .catch((error) => {
          if (!controller.signal.aborted) setError(issueText(error));
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [open, finding, query, accountEnabled]);
  // Stable callback keeps message polling independent of parent renders.
  const refreshInbox = useCallback(() => setRefresh((value) => value + 1), []);
  const visibleConversations =
    inboxMode === "notifications"
      ? conversations.filter((item) => item.unread > 0)
      : conversations;
  return (
    <div ref={host} className={`chat-widget${rail ? " chat-widget-rail" : ""}`}>
      {rail && (
        <button
          type="button"
          className="rail-action rail-notifications"
          aria-label="Thông báo"
          title="Thông báo"
          aria-expanded={open && inboxMode === "notifications"}
          aria-controls="chat-panel"
          onClick={() => {
            setOpen(!(open && inboxMode === "notifications"));
            setInboxMode("notifications");
            setSelected(null);
            setFinding(false);
          }}
        >
          <RailIcon kind="bell" />
          {unread > 0 && (
            <span
              className="rail-notification-dot"
              aria-label="Có tin nhắn chưa đọc"
            />
          )}
        </button>
      )}
      <button
        ref={toggle}
        type="button"
        className={rail ? "rail-action rail-chat" : "chat-menu-toggle"}
        aria-label="Mở tin nhắn"
        aria-expanded={open && inboxMode === "messages"}
        title="Tin nhắn"
        aria-controls="chat-panel"
        onClick={() => {
          setOpen(!(open && inboxMode === "messages"));
          setInboxMode("messages");
        }}
      >
        {rail ? (
          <RailIcon kind="chat" />
        ) : (
          <>
            <RailIcon kind="chat" />
            <span>Tin nhắn</span>
          </>
        )}
        {unread > 0 && (
          <span className="chat-unread">{unread > 99 ? "99+" : unread}</span>
        )}
      </button>
      {open && (
        <aside
          id="chat-panel"
          className="chat-panel"
          aria-label="Tin nhắn riêng"
        >
          <div className="chat-panel-heading">
            <strong>
              {inboxMode === "notifications" ? "Thông báo" : "Tin nhắn"}
            </strong>
            <button
              className="chat-icon-button"
              type="button"
              aria-label="Đóng tin nhắn"
              onClick={() => {
                setOpen(false);
                toggle.current?.focus();
              }}
            >
              ✕
            </button>
          </div>
          {!accountEnabled ? (
            <ChatEmptyState guest demo={user?.is_demo} />
          ) : selected ? (
            <ChatThread
              key={selected.id}
              conversation={selected}
              userId={user!.id}
              onBack={() => setSelected(null)}
              onRefresh={refreshInbox}
            />
          ) : (
            <>
              {inboxMode === "messages" && (
                <div className="chat-inbox-actions">
                  <button
                    type="button"
                    className="chat-new"
                    onClick={() => {
                      setFinding((value) => !value);
                      setQuery("");
                      setPeople([]);
                    }}
                  >
                    <span className="chat-action-icon" aria-hidden="true">
                      {finding ? (
                        "←"
                      ) : (
                        <svg
                          width="23"
                          height="23"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        >
                          <path d="M13 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-8M16 3l5 5m-10 8 3-1L22 7l-5-5-8 8-1 5 3 1Z" />
                        </svg>
                      )}
                    </span>
                    <span>{finding ? "Cuộc trò chuyện" : "Tin nhắn mới"}</span>
                  </button>
                  {!finding && (
                    <button
                      type="button"
                      className="chat-connect"
                      onClick={() => {
                        setFinding(true);
                        setQuery("");
                        setPeople([]);
                      }}
                    >
                      <span className="chat-connect-icon" aria-hidden="true">
                        <svg
                          width="24"
                          height="24"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        >
                          <circle cx="9" cy="7" r="4" />
                          <path d="M2 21v-2a7 7 0 0 1 10-6m5 0v8m-4-4h8" />
                        </svg>
                      </span>
                      <span>
                        <strong>Tìm người dùng</strong>
                        <small>Kết nối và bắt đầu trò chuyện</small>
                      </span>
                    </button>
                  )}
                </div>
              )}
              {finding && (
                <label className="chat-person-search">
                  Tìm người dùng
                  <input
                    autoFocus
                    placeholder="Tên hoặc @tên đăng nhập"
                    value={query}
                    maxLength={120}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </label>
              )}
              {error && (
                <p role="status" className="chat-error">
                  {error}
                  <button type="button" onClick={refreshInbox}>
                    Thử lại
                  </button>
                </p>
              )}
              <div className="chat-contact-list">
                {finding ? (
                  loading ? (
                    <p role="status" className="chat-empty">
                      Đang tìm…
                    </p>
                  ) : people.length ? (
                    people.map((person) => (
                      <button
                        type="button"
                        className="chat-contact"
                        key={person.id}
                        disabled={starting}
                        onClick={async () => {
                          setStarting(true);
                          setError(null);
                          try {
                            const conversation = await chatAPI.start(person.id);
                            setSelected(conversation);
                            setFinding(false);
                            refreshInbox();
                          } catch (error) {
                            setError(issueText(error));
                          } finally {
                            setStarting(false);
                          }
                        }}
                      >
                        <Avatar
                          name={person.display_name}
                          url={person.avatar_url}
                          className="chat-avatar"
                        />
                        <span>
                          <strong>{person.display_name}</strong>
                          <small>@{person.username}</small>
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="chat-empty">
                      Không tìm thấy tài khoản phù hợp.
                    </p>
                  )
                ) : visibleConversations.length ? (
                  visibleConversations.map((conversation) => (
                    <button
                      type="button"
                      className={`chat-contact${conversation.unread ? " has-unread" : ""}`}
                      key={conversation.id}
                      onClick={() => {
                        setSelected(conversation);
                        setInboxMode("messages");
                      }}
                    >
                      <Avatar
                        name={conversation.peer.display_name}
                        url={conversation.peer.avatar_url}
                        className="chat-avatar"
                      />
                      <span>
                        <strong>{conversation.peer.display_name}</strong>
                        <small>
                          {conversation.last_message?.body ||
                            (conversation.last_message?.image_url
                              ? "▧ Đã gửi một ảnh"
                              : "Bắt đầu trò chuyện")}
                        </small>
                      </span>
                      {conversation.unread > 0 && (
                        <span className="chat-unread">
                          {conversation.unread > 99
                            ? "99+"
                            : conversation.unread}
                        </span>
                      )}
                    </button>
                  ))
                ) : inboxMode === "notifications" ? (
                  <div className="chat-empty">
                    <p>Bạn đã đọc hết tin nhắn.</p>
                  </div>
                ) : (
                  <ChatEmptyState />
                )}
              </div>
            </>
          )}
        </aside>
      )}
    </div>
  );
}
