export function ChatEmptyState({
  guest = false,
  demo = false,
}: {
  guest?: boolean;
  demo?: boolean;
}) {
  return (
    <div className="chat-welcome">
      <svg
        className="chat-welcome-art"
        viewBox="0 0 200 180"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="98" cy="89" r="74" fill="#e9f2ff" />
        <circle cx="158" cy="48" r="14" fill="#caddff" />
        <path d="m40 80 77-31 37 76-77 31Z" fill="#fff" />
        <path d="m40 80 57 27 20-58" fill="#d8e8ff" />
        <path d="m77 156 19-47 58 16" fill="#c5dcff" />
        <rect x="42" y="55" width="78" height="57" rx="17" fill="#1559d7" />
        <path d="m56 107-5 17 23-15" fill="#1559d7" />
        <circle cx="63" cy="84" r="4" fill="white" />
        <circle cx="81" cy="84" r="4" fill="white" />
        <circle cx="99" cy="84" r="4" fill="white" />
        <path d="m132 46 15-16 11 10-15 16-16 6 5-16Z" fill="#88b6ff" />
        <path d="m147 30 7-7 11 10-7 7Z" fill="#1559d7" />
        <path d="m127 62 5-16 11 10-16 6Z" fill="#fff" />
        <path
          d="m46 38 3-8m-9 4 8 3m114 106 3-8m-9 4 8 3"
          stroke="#88b6ff"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <h2>Bắt đầu trò chuyện</h2>
      <p>
        {guest
          ? demo
            ? "Đăng nhập bằng tài khoản cá nhân để nhắn tin và chia sẻ hình ảnh với mọi người."
            : "Đăng nhập để nhắn tin, chia sẻ hình ảnh và kết nối với mọi người."
          : "Nhắn tin, chia sẻ hình ảnh và kết nối với mọi người. Các cuộc trò chuyện của bạn sẽ xuất hiện ở đây."}
      </p>
      {guest && (
        <a className="chat-signin" href="/login">
          Đăng nhập
        </a>
      )}
    </div>
  );
}
