import type {
  APIError,
  DiscoveryResponse,
  AdvancedSearchInput,
  HealthSummary,
  Readiness,
  SearchResponse,
} from "../../types/api";
import {
  decodeDetail,
  decodeEvaluation,
  decodeWorkspace,
  decodeRag,
  validId,
  validMediaURL,
  metadata,
  finite,
  validConstraint,
} from "./decoders";
import { accessHeaders } from "./security";

export class APIClientError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status = 0,
    public readonly requestId?: string,
    public readonly retryable = false,
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
export function decodeDiscovery(value: unknown): DiscoveryResponse {
  if (
    record(value) &&
    ((value.seed !== undefined && !validId(value.seed)) ||
      (value.has_more !== undefined && typeof value.has_more !== "boolean") ||
      (value.next_cursor != null &&
        (typeof value.next_cursor !== "string" ||
          !/^[0-9a-f]{32}:[0-9a-f-]{36}$/.test(value.next_cursor))) ||
      (value.has_more === true && (!value.seed || !value.next_cursor)))
  )
    return invalidResponse();

  if (
    !record(value) ||
    !Array.isArray(value.results) ||
    value.results.length > 50 ||
    !Number.isInteger(value.total_results) ||
    value.total_results !== value.results.length
  ) {
    return invalidResponse();
  }
  for (const item of value.results) {
    if (
      !record(item) ||
      !validId(item.image_id) ||
      !metadata(item.metadata) ||
      !Number.isInteger(item.rank) ||
      Number(item.rank) < 1 ||
      !finite(item.score) ||
      !validMediaURL(item.thumbnail_url, item.image_id, "thumbnail") ||
      !validMediaURL(item.image_url, item.image_id, "original")
    )
      return invalidResponse();
  }
  if (
    new Set(value.results.map((item) => item.image_id)).size !==
    value.results.length
  )
    return invalidResponse();
  return value as unknown as DiscoveryResponse;
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
    !finite(value.latency.processing_ms) ||
    !Array.isArray(value.results) ||
    value.results.length > 50 ||
    !Array.isArray(value.warnings) ||
    !value.warnings.every(
      (warning) =>
        record(warning) &&
        typeof warning.code === "string" &&
        typeof warning.message === "string",
    )
  )
    return invalidResponse();
  if (value.pagination != null) {
    const p = value.pagination;
    if (
      !record(p) ||
      ![
        "page",
        "page_size",
        "total_results",
        "total_pages",
        "result_limit",
      ].every(
        (key) =>
          Number.isInteger(p[key]) &&
          Number(p[key]) >=
            (key === "total_results" || key === "total_pages" ? 0 : 1),
      ) ||
      Number(p.result_limit) > 500 ||
      Number(p.total_results) > Number(p.result_limit) ||
      Number(p.total_pages) !==
        Math.ceil(Number(p.total_results) / Number(p.page_size)) ||
      Number(p.page) > Math.max(1, Number(p.total_pages))
    )
      return invalidResponse();
  }
  if (value.query_analysis != null) {
    const analysis = value.query_analysis;
    if (
      !record(analysis) ||
      typeof analysis.query_type !== "string" ||
      typeof analysis.language !== "string" ||
      typeof analysis.uncertain !== "boolean" ||
      !Array.isArray(analysis.limitations) ||
      !analysis.limitations.every((item) => typeof item === "string") ||
      !(analysis.constraints === null || validConstraint(analysis.constraints))
    )
      return invalidResponse();
  }
  if (
    value.effective_settings != null &&
    (!record(value.effective_settings) ||
      typeof value.effective_settings.route !== "string")
  )
    return invalidResponse();
  for (const item of value.results) {
    if (
      !record(item) ||
      typeof item.image_id !== "string" ||
      typeof item.score !== "number" ||
      !Number.isFinite(item.score) ||
      !validId(item.image_id) ||
      !Number.isInteger(item.rank) ||
      Number(item.rank) < 1 ||
      !["cosine", "rrf", "weighted_score", "reranker"].includes(
        String(item.score_type),
      ) ||
      !metadata(item.metadata) ||
      typeof item.image_url !== "string" ||
      typeof item.thumbnail_url !== "string" ||
      !validMediaURL(item.thumbnail_url, item.image_id, "thumbnail") ||
      !validMediaURL(item.image_url, item.image_id, "original") ||
      !Array.isArray(item.constraint_assessments) ||
      !item.constraint_assessments.every(
        (a) =>
          record(a) &&
          typeof a.clause_id === "string" &&
          ["satisfied", "violated", "unknown"].includes(String(a.status)) &&
          (a.evidence_ref === null || typeof a.evidence_ref === "string") &&
          (a.semantic_score == null || finite(a.semantic_score)),
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
      timeout?: number;
      method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
      headers?: Record<string, string>;
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
    }, options.timeout ?? timeoutMs);
    try {
      const headers: Record<string, string> = {
        Accept: "application/json",
        ...accessHeaders(options.token),
        ...options.headers,
      };
      if (options.json) headers["Content-Type"] = "application/json";
      if (options.token) headers.Authorization = `Bearer ${options.token}`;
      const response = await fetch(`${baseURL.replace(/\/$/, "")}${path}`, {
        headers,
        method: options.method ?? (options.body ? "POST" : "GET"),
        credentials: "same-origin",
        body: options.body,
        signal: controller.signal,
      });
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        if (response.ok) return invalidResponse();
        payload = null;
      }
      if (!response.ok && !(options.degraded && response.status === 503)) {
        if (
          response.status === 401 &&
          !options.token &&
          !path.startsWith("/auth/")
        )
          window.dispatchEvent(new Event("lens:auth-expired"));
        const error =
          record(payload) && record(payload.error) ? payload.error : null;
        throw new APIClientError(
          typeof error?.code === "string" ? error.code : "HTTP_ERROR",
          typeof error?.message === "string"
            ? error.message
            : `Không thể xử lý yêu cầu (HTTP ${response.status}).`,
          response.status,
          typeof error?.request_id === "string" ? error.request_id : undefined,
          error?.retryable === true,
        );
      }
      try {
        return decode(payload);
      } catch (error) {
        if (error instanceof APIClientError) throw error;
        return invalidResponse();
      }
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
    request,
    explain: (
      body: object,
      ids: string[],
      token: string,
      signal?: AbortSignal,
    ) =>
      request("/rag/explain", (value) => decodeRag(value, new Set(ids)), {
        body: JSON.stringify(body),
        json: true,
        token,
        signal,
        timeout: 65_000,
      }),
    discovery: (
      limit: number,
      token = "",
      signal?: AbortSignal,
      page?: { seed: string; cursor: string },
    ) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (page) {
        params.set("seed", page.seed);
        params.set("cursor", page.cursor);
      }
      return request(`/search/discovery?${params}`, decodeDiscovery, {
        token,
        signal,
      });
    },
    workspace: (token: string, signal?: AbortSignal) =>
      request("/system/workspace", decodeWorkspace, { token, signal }),
    publicWorkspace: (signal?: AbortSignal) =>
      request("/public/workspace", decodeWorkspace, { signal }),
    evaluation: (token: string, signal?: AbortSignal) =>
      request("/system/evaluation", decodeEvaluation, { token, signal }),
    relatedImages: (id: string, token = "", signal?: AbortSignal) => {
      if (!validId(id))
        return Promise.reject(
          new APIClientError("INVALID_INPUT", "Mã ảnh không hợp lệ."),
        );
      return request(`/images/${id}/related?limit=24`, decodeSearch, {
        token,
        signal,
      });
    },
    imageDetail: (id: string, token: string, signal?: AbortSignal) => {
      if (!validId(id))
        return Promise.reject(
          new APIClientError("INVALID_INPUT", "Mã ảnh không hợp lệ."),
        );
      return request(
        `/images/${id}`,
        (value) => {
          const detail = decodeDetail(value);
          if (detail.image_id !== id) return invalidResponse();
          return detail;
        },
        { token, signal },
      );
    },
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
    transcribeVoice: (audio: Blob, token = "", signal?: AbortSignal) => {
      const body = new FormData();
      const ext = audio.type.includes("ogg")
        ? "ogg"
        : audio.type.includes("wav")
          ? "wav"
          : audio.type.includes("mp4")
            ? "m4a"
            : "webm";
      body.append("audio", audio, `voice.${ext}`);
      return request(
        "/search/voice",
        (value) => {
          if (!record(value) || typeof value.transcript !== "string")
            return invalidResponse();
          return { transcript: value.transcript };
        },
        {
          token,
          signal,
          body,
          timeout: 12_000,
        },
      );
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
