export function RailIcon({
  kind,
  active = false,
}: {
  kind:
    | "home"
    | "library"
    | "plus"
    | "bell"
    | "chat"
    | "admin"
    | "heart"
    | "person";
  active?: boolean;
}) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {kind === "heart" && (
        <path
          d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"
          fill={active ? "currentColor" : "none"}
        />
      )}
      {kind === "person" && (
        <>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21v-2a8 8 0 0 1 16 0v2" />
        </>
      )}
      {kind === "home" && (
        <>
          <path
            d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"
            fill={active ? "currentColor" : "none"}
          />
          <path
            d="M9 16h6"
            stroke={active ? "var(--surface)" : "currentColor"}
          />
        </>
      )}
      {kind === "library" && (
        <>
          <rect x="3" y="3" width="18" height="18" rx="3" />
          <path d="M11 3v18m0-10h10" />
        </>
      )}
      {kind === "plus" && (
        <>
          <rect x="3" y="3" width="18" height="18" rx="3" />
          <path d="M12 7v10M7 12h10" />
        </>
      )}
      {kind === "bell" && (
        <>
          <path d="M18 8a6 6 0 0 0-12 0c0 8-3 8-3 10h18c0-2-3-2-3-10Zm-9 13h6" />
        </>
      )}
      {kind === "chat" && (
        <>
          <path d="M21 11.5a9 9 0 1 0-4 7.5l4 2v-9.5Z" />
          <circle cx="8" cy="11" r=".6" fill="currentColor" />
          <circle cx="12" cy="11" r=".6" fill="currentColor" />
          <circle cx="16" cy="11" r=".6" fill="currentColor" />
        </>
      )}
      {kind === "admin" && (
        <>
          <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" />
          <path d="m8 12 3 3 5-6" />
        </>
      )}
    </svg>
  );
}
