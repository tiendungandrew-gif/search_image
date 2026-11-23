import { useState } from "react";
export function Avatar({
  name,
  url,
  className = "avatar",
}: {
  name: string;
  url?: string | null;
  className?: string;
}) {
  const [failed, setFailed] = useState<string | null>(null);
  return (
    <span className={`${className} user-avatar`} aria-hidden="true">
      {url && failed !== url ? (
        <img src={url} alt="" onError={() => setFailed(url)} />
      ) : (
        name.slice(0, 1).toUpperCase()
      )}
    </span>
  );
}
