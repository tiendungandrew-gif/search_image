import { useState } from "react";
export function useAdminAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  async function run(
    action: () => Promise<unknown>,
    success: string,
    refresh?: () => Promise<unknown>,
  ) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(success);
      await refresh?.();
      return true;
    } catch (issue) {
      setError(
        issue instanceof Error
          ? issue.message
          : "Không thực hiện được thao tác.",
      );
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, message, run };
}
