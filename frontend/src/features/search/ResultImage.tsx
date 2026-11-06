import { useEffect, useState } from "react";

export function ResultImage({
  url,
  token,
  alt,
}: {
  url: string;
  token: string;
  alt: string;
}) {
  const [image, setImage] = useState<string | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let blobURL: string | null = null;
    const timer = setTimeout(() => {
      setError(true);
      controller.abort();
    }, 5000);
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (
          !response.ok ||
          !["image/jpeg", "image/png", "image/webp"].includes(
            response.headers.get("content-type")?.split(";")[0] ?? "",
          )
        )
          throw new Error("image_unavailable");
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        blobURL = URL.createObjectURL(blob);
        setImage(blobURL);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      })
      .finally(() => clearTimeout(timer));
    return () => {
      clearTimeout(timer);
      controller.abort();
      if (blobURL) URL.revokeObjectURL(blobURL);
    };
  }, [url, token]);
  return image && !error ? (
    <img src={image} alt={alt} loading="lazy" onError={() => setError(true)} />
  ) : (
    <div className="image-placeholder" role="status">
      {error ? "Không tải được ảnh" : "Đang tải ảnh…"}
    </div>
  );
}
