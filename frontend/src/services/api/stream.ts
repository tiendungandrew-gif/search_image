import { APIClientError } from "./client";
import { record } from "./decoders";
import { accessHeaders } from "./security";

/** Bounded POST SSE reader. Only terminal frames become application results. */
export async function postStream<T>(
  path: string,
  body: object,
  token: string,
  signal: AbortSignal,
  frame: (event: string, value: unknown) => T | undefined,
): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal.addEventListener("abort", abort, { once: true });
  if (signal.aborted) controller.abort();
  const timer = setTimeout(abort, 65_000);
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  try {
    const base = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const response = await fetch(`${base.replace(/\/$/, "")}${path}`, {
      method: "POST",
      body: JSON.stringify(body),
      signal: controller.signal,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...accessHeaders(token),
      },
    });
    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);
      const error =
        record(payload) && record(payload.error) ? payload.error : null;
      throw new APIClientError(
        typeof error?.code === "string" ? error.code : "HTTP_ERROR",
        typeof error?.message === "string"
          ? error.message
          : `Yêu cầu thất bại (HTTP ${response.status}).`,
        response.status,
        typeof error?.request_id === "string" ? error.request_id : undefined,
        error?.retryable === true,
      );
    }
    if (
      !response.body ||
      !response.headers.get("content-type")?.startsWith("text/event-stream")
    )
      throw new APIClientError(
        "INVALID_RESPONSE",
        "API không trả luồng tiến độ hợp lệ.",
      );
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "",
      received = 0;
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      received += chunk.value.byteLength;
      if (received > 2 * 1024 ** 2)
        throw new APIClientError("INVALID_RESPONSE", "Phản hồi vượt giới hạn.");
      buffer += decoder.decode(chunk.value, { stream: true });
      let boundary: number;
      while ((boundary = buffer.search(/\r?\n\r?\n/)) >= 0) {
        const separator = buffer.slice(boundary).match(/^\r?\n\r?\n/)![0];
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + separator.length);
        const lines = block.split(/\r?\n/);
        const event = lines
          .find((line) => line.startsWith("event:"))
          ?.slice(6)
          .trim();
        const raw = lines
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (!event || !raw) continue;
        let value: unknown;
        try {
          value = JSON.parse(raw);
        } catch {
          throw new APIClientError(
            "INVALID_RESPONSE",
            "Dữ liệu streaming không hợp lệ.",
          );
        }
        const terminal = frame(event, value);
        if (terminal !== undefined) return terminal;
      }
    }
    throw new APIClientError(
      "INCOMPLETE_STREAM",
      "Luồng kết thúc khi chưa có kết quả xác nhận.",
    );
  } catch (error) {
    if (signal.aborted) throw new APIClientError("ABORTED", "Đã hủy yêu cầu.");
    if (controller.signal.aborted)
      throw new APIClientError("TIMEOUT", "Yêu cầu đã hết thời gian chờ.");
    if (error instanceof TypeError)
      throw new APIClientError(
        "NETWORK_ERROR",
        "Kết nối streaming bị gián đoạn.",
      );
    throw error;
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", abort);
    await reader?.cancel().catch(() => undefined);
    reader?.releaseLock();
  }
}
