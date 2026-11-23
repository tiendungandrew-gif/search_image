export function SearchSkeleton() {
  return (
    <div role="status" aria-label="Đang tìm ảnh">
      <p>Đang tìm ảnh…</p>
      <div className="result-grid" aria-hidden="true">
        {[1, 2, 3].map((item) => (
          <div className="result-card skeleton" key={item}>
            <div className="image-shimmer" />
            <div />
            <div />
          </div>
        ))}
      </div>
    </div>
  );
}
