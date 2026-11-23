import { postStream } from "../../services/api/stream";
import { metadata } from "../../services/api/decoders";
import type { ImageMetadata } from "../../types/api";

export interface AgentImage {
  image_id: string;
  rank: number;
  score: number | null;
  score_type: string | null;
  image_url: string;
  thumbnail_url: string;
  metadata: ImageMetadata;
}
export interface AgentResponse {
  query_id: string;
  status: string;
  query_success: boolean;
  dataset_status: string;
  results: AgentImage[];
  steps: {
    step_id: string;
    tool: string;
    status: string;
    duration_ms: number;
  }[];
  latency_ms: number;
  logical_hops: number;
  tool_calls: number;
  warnings: string[];
  error_code: string | null;
  relationship_summary: string | null;
  evidence?: { evidence_id: string; source_ref: string; verified: boolean }[];
  resolved_entities?: {
    entity_id: string;
    canonical_name: string;
    entity_type: string;
  }[];
  rag: {
    answer: string;
    error_code: string | null;
    citations: { image_id: string; quote: string }[];
  } | null;
}
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
export function decodeAgent(value: unknown): AgentResponse {
  const invalid = () => {
    throw new Error("Phản hồi Agent không đúng định dạng.");
  };
  if (
    !record(value) ||
    typeof value.query_id !== "string" ||
    typeof value.status !== "string" ||
    typeof value.query_success !== "boolean" ||
    typeof value.dataset_status !== "string" ||
    typeof value.latency_ms !== "number" ||
    !Array.isArray(value.results) ||
    value.results.length > 50 ||
    !Array.isArray(value.steps) ||
    value.steps.length > 6 ||
    !Array.isArray(value.warnings) ||
    !value.warnings.every((w) => typeof w === "string")
  )
    return invalid();
  if (
    value.resolved_entities !== undefined &&
    (!Array.isArray(value.resolved_entities) ||
      !value.resolved_entities.every(
        (item) =>
          record(item) &&
          typeof item.entity_id === "string" &&
          typeof item.canonical_name === "string" &&
          typeof item.entity_type === "string",
      ))
  )
    return invalid();
  const ids = new Set<string>();
  if (
    value.evidence !== undefined &&
    (!Array.isArray(value.evidence) ||
      value.evidence.length > 100 ||
      !value.evidence.every(
        (e) =>
          record(e) &&
          typeof e.evidence_id === "string" &&
          typeof e.source_ref === "string" &&
          typeof e.verified === "boolean",
      ))
  )
    return invalid();
  for (const image of value.results) {
    if (
      !record(image) ||
      typeof image.image_id !== "string" ||
      !/^[a-f0-9-]{36}$/.test(image.image_id) ||
      ids.has(image.image_id) ||
      !metadata(image.metadata) ||
      !Array.isArray(image.metadata.tags) ||
      !(
        image.score === null ||
        (typeof image.score === "number" && Number.isFinite(image.score))
      ) ||
      image.image_url !==
        `/api/v1/images/${image.image_id}/content?variant=original` ||
      image.thumbnail_url !==
        `/api/v1/images/${image.image_id}/content?variant=thumbnail`
    )
      return invalid();
    ids.add(image.image_id);
  }
  if (
    !value.steps.every(
      (s) =>
        record(s) &&
        typeof s.step_id === "string" &&
        typeof s.tool === "string" &&
        typeof s.status === "string" &&
        typeof s.duration_ms === "number",
    )
  )
    return invalid();
  if (
    value.rag !== null &&
    (!record(value.rag) ||
      typeof value.rag.answer !== "string" ||
      !Array.isArray(value.rag.citations) ||
      !value.rag.citations.every(
        (c) =>
          record(c) &&
          typeof c.image_id === "string" &&
          ids.has(c.image_id) &&
          typeof c.quote === "string",
      ))
  )
    return invalid();
  return value as unknown as AgentResponse;
}

export async function searchAgent(
  body: object,
  token: string,
  signal: AbortSignal,
  onProgress: (event: string, data: Record<string, unknown>) => void,
): Promise<AgentResponse> {
  return postStream(
    "/search/agent/stream",
    body,
    token,
    signal,
    (event, data) => {
      if (event === "agent_completed" || event === "agent_partial")
        return decodeAgent(data);
      if (!record(data)) throw new Error("Tiến độ Agent không hợp lệ.");
      if (event === "error" && data.retrieval_preserved === true)
        return undefined;
      if (event === "error")
        throw new Error(
          `Agent dừng: ${typeof data.code === "string" ? data.code : "AGENT_FAILED"}`,
        );
      if (
        [
          "planning_started",
          "planning_completed",
          "tool_started",
          "tool_completed",
          "retrieval_completed",
          "generation_started",
        ].includes(event)
      )
        onProgress(event, data);
      return undefined;
    },
  );
}
