import type {
  APIError,
  AdvancedSearchInput,
  HealthSummary,
  Readiness,
  SearchResponse,
} from "../../types/api";

export class APIClientError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status = 0,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "APIClientError";
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function invalidResponse(): never {
  throw new APIClientError(
    "INVALID_RESPONSE",
    "Phản hồi API không đúng định dạng.",
  );
}
export function decodeHealth(value: unknown): HealthSummary {
  if (!record(value)) return invalidResponse();
  const capabilities = value.capabilities;
  const names = [
    "text_search",
    "image_search",
    "multimodal",
    "multi_intent",
    "rerank",
    "explanations",
    "agent",
  ];
  if (
    !["ok", "not_ready"].includes(String(value.status)) ||
    value.check !== "live" ||
    !record(capabilities) ||
    !names.every((k) => typeof capabilities[k] === "boolean") ||
    !record(value.worker) ||
    !["unknown", "fresh", "stale"].includes(String(value.worker.state))
  )
    return invalidResponse();
  return value as unknown as HealthSummary;
}
function decodeReadiness(value: unknown): Readiness {
  if (!record(value)) return invalidResponse();
  const dependencies = value.dependencies;
  if (
    !["ready", "not_ready"].includes(String(value.status)) ||
    !record(dependencies) ||
    !["postgresql", "qdrant", "minio"].every((k) =>
      ["healthy", "unhealthy", "timeout"].includes(String(dependencies[k])),
    )
  )
    return invalidResponse();
  return value as unknown as Readiness;
}

export function decodeSearch(value: unknown): SearchResponse {
  if (
    !record(value) ||
    !["text", "image", "multi_intent", "multimodal"].includes(
      String(value.search_mode),
    ) ||
    typeof value.query_id !== "string" ||
    typeof value.request_id !== "string" ||
    !record(value.latency) ||
    typeof value.latency.processing_ms !== "number" ||
    !Array.isArray(value.results) ||
    !Array.isArray(value.warnings)
  )
    return invalidResponse();
  for (const item of value.results) {
    if (
      !record(item) ||
      typeof item.image_id !== "string" ||
      typeof item.score !== "number" ||
      !Number.isFinite(item.score) ||
      !record(item.metadata) ||
      !Array.isArray(item.metadata.tags) ||
      typeof item.image_url !== "string" ||
      typeof item.thumbnail_url !== "string" ||
      !/^\/api\/v1\/images\/[0-9a-f-]+\/content\?variant=(original|thumbnail)$/.test(
        item.thumbnail_url,
      ) ||
      !/^\/api\/v1\/images\/[0-9a-f-]+\/content\?variant=(original|thumbnail)$/.test(
        item.image_url,
      )
    )
      return invalidResponse();
  }
  return value as unknown as SearchResponse;
}

export function createAPIClient(
  baseURL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeoutMs = 4000,
) {
  async function request<T>(
    path: string,
    decode: (value: unknown) => T,
    options: {
      signal?: AbortSignal;
      token?: string;
      degraded?: boolean;
      body?: BodyInit;
      json?: boolean;
    } = {},
  ): Promise<T> {
    const controller = new AbortController();
    let timedOut = false;
    const abort = () => controller.abort();
    options.signal?.addEventListener("abort", abort, { once: true });
    if (options.signal?.aborted) controller.abort();
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    try {
      const headers: Record<string, string> = { Accept: "application/json" };
      if (options.json) headers["Content-Type"] = "application/json";
      if (options.token) headers.Authorization = `Bearer ${options.token}`;
      const response = await fetch(`${baseURL.replace(/\/$/, "")}${path}`, {
        headers,
        method: options.body ? "POST" : "GET",
        body: options.body,
        signal: controller.signal,
      });
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        return invalidResponse();
      }
      if (!response.ok && !(options.degraded && response.status === 503)) {
        const error =
          record(payload) && record(payload.error) ? payload.error : null;
        throw new APIClientError(
          typeof error?.code === "string" ? error.code : "HTTP_ERROR",
          typeof error?.message === "string"
            ? error.message
            : "Không thể xử lý yêu cầu.",
          response.status,
          typeof error?.request_id === "string" ? error.request_id : undefined,
        );
      }
      return decode(payload);
    } catch (error) {
      if (timedOut)
        throw new APIClientError(
          "TIMEOUT",
          "Kết nối API đã hết thời gian chờ.",
        );
      if (error instanceof APIClientError) throw error;
      if (options.signal?.aborted)
        throw new APIClientError("ABORTED", "Yêu cầu đã được hủy.");
      throw new APIClientError(
        "NETWORK_ERROR",
        "Chưa kết nối được API. Kiểm tra backend và thử lại.",
      );
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener("abort", abort);
    }
  }
  return {
    searchAdvanced: (
      options: AdvancedSearchInput,
      image: File | null,
      token: string,
      signal?: AbortSignal,
    ) => {
      if (image) {
        const body = new FormData();
        body.append("image", image);
        body.append(
          "options",
          JSON.stringify({ ...options, exclude_self: false }),
        );
        return request("/search/multimodal", decodeSearch, {
          token,
          signal,
          body,
        });
      }
      return request("/search", decodeSearch, {
        token,
        signal,
        json: true,
        body: JSON.stringify(options),
      });
    },
    searchText: (
      text: string,
      topK: number,
      token: string,
      signal?: AbortSignal,
    ) =>
      request("/search", decodeSearch, {
        token,
        signal,
        json: true,
        body: JSON.stringify({ mode: "text", text, top_k: topK }),
      }),
    searchImage: (
      image: File,
      topK: number,
      token: string,
      signal?: AbortSignal,
    ) => {
      const body = new FormData();
      body.append("image", image);
      body.append(
        "options",
        JSON.stringify({ mode: "image", top_k: topK, exclude_self: false }),
      );
      return request("/search/multimodal", decodeSearch, {
        token,
        signal,
        body,
      });
    },
    health: (signal?: AbortSignal) =>
      request("/health", decodeHealth, { signal }),
    readiness: (token: string, signal?: AbortSignal) =>
      request("/health/ready", decodeReadiness, {
        token,
        signal,
        degraded: true,
      }),
  };
}
export const api = createAPIClient();
export type ErrorEnvelope = { error: APIError };
