export function AdminFeedback({
  loading,
  error,
  message,
}: {
  loading?: boolean;
  error?: string | null;
  message?: string | null;
}) {
  return (
    <>
      {loading && (
        <p className="muted" role="status">
          Đang tải dữ liệu…
        </p>
      )}
      {error && (
        <p className="form-alert" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="success-message" role="status">
          {message}
        </p>
      )}
    </>
  );
}
