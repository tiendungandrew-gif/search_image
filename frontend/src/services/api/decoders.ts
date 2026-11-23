import type {
  EvaluationSummary,
  ImageDetail,
  ImageMetadata,
  WorkspaceStatus,
  RagAnswer,
} from "../../types/api";

export function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
export const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);
export const nullableString = (value: unknown) =>
  value === null || typeof value === "string";
export const validId = (value: unknown): value is string =>
  typeof value === "string" &&
  /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(value);
export function validMediaURL(
  value: unknown,
  id: string,
  variant: "original" | "thumbnail",
) {
  return value === `/api/v1/images/${id}/content?variant=${variant}`;
}
export function metadata(value: unknown): value is ImageMetadata {
  return (
    record(value) &&
    nullableString(value.title) &&
    (value.caption === undefined || nullableString(value.caption)) &&
    finite(value.width) &&
    value.width > 0 &&
    finite(value.height) &&
    value.height > 0 &&
    ["image/jpeg", "image/png", "image/webp"].includes(
      String(value.media_type),
    ) &&
    Array.isArray(value.tags) &&
    value.tags.every((tag) => typeof tag === "string") &&
    ["source_dataset", "city", "license"].every((key) =>
      nullableString(value[key]),
    )
  );
}
export function decodeWorkspace(value: unknown): WorkspaceStatus {
  if (
    !record(value) ||
    !record(value.dataset) ||
    !record(value.capabilities) ||
    !record(value.rag) ||
    !record(value.agent) ||
    !record(value.limits) ||
    !record(value.dependencies)
  )
    throw new Error("Trạng thái dataset không hợp lệ.");
  const { dataset, capabilities, rag } = value;
  if (
    value.public_datasets !== undefined &&
    (!Array.isArray(value.public_datasets) ||
      value.public_datasets.length > 1000 ||
      !value.public_datasets.every(
        (d) =>
          record(d) &&
          validId(d.id) &&
          typeof d.key === "string" &&
          typeof d.name === "string",
      ))
  )
    throw new Error("Danh sách thư viện công khai không hợp lệ.");
  if (
    ![
      "empty_dataset",
      "index_building",
      "index_not_ready",
      "ready",
      "unavailable",
    ].includes(String(value.dataset.state)) ||
    ![
      "images",
      "available_images",
      "indexed_images",
      "vectors",
      "generation",
    ].every(
      (key) =>
        dataset[key] === null || (finite(dataset[key]) && dataset[key] >= 0),
    ) ||
    !nullableString(value.dataset.index_id) ||
    !nullableString(value.dataset.index_status) ||
    ![
      "text_search",
      "image_search",
      "multimodal",
      "multi_intent",
      "rerank",
      "explanations",
      "agent",
    ].every((key) => typeof capabilities[key] === "boolean") ||
    !["enabled", "configured", "streaming"].every(
      (key) => typeof rag[key] === "boolean",
    ) ||
    typeof value.agent.enabled !== "boolean" ||
    typeof value.agent.llm_planning !== "boolean" ||
    !finite(value.limits.top_k) ||
    value.limits.top_k < 1 ||
    value.limits.top_k > 50 ||
    !finite(value.limits.image_bytes) ||
    value.limits.image_bytes <= 0 ||
    !Object.values(value.dependencies).every((item) => typeof item === "string")
  )
    throw new Error("Trạng thái dataset không hợp lệ.");
  return value as unknown as WorkspaceStatus;
}
export function decodeDetail(value: unknown): ImageDetail {
  if (
    !record(value) ||
    !validId(value.image_id) ||
    !metadata(value.metadata) ||
    typeof value.status !== "string" ||
    typeof value.created_at !== "string" ||
    !Array.isArray(value.indexing) ||
    !value.indexing.every(
      (item) =>
        record(item) &&
        validId(item.index_id) &&
        typeof item.status === "string",
    ) ||
    !(
      value.image_url === null ||
      validMediaURL(value.image_url, value.image_id, "original")
    ) ||
    !(
      value.thumbnail_url === null ||
      validMediaURL(value.thumbnail_url, value.image_id, "thumbnail")
    )
  )
    throw new Error("Chi tiết ảnh không hợp lệ.");
  return value as unknown as ImageDetail;
}
export function decodeEvaluation(value: unknown): EvaluationSummary {
  if (
    !record(value) ||
    !["available", "empty", "not_available"].includes(String(value.state)) ||
    !finite(value.skipped) ||
    !Array.isArray(value.experiments) ||
    value.experiments.length > 200 ||
    !value.experiments.every(
      (item) =>
        record(item) &&
        ["id", "phase", "kind", "status", "quality_status"].every(
          (key) => typeof item[key] === "string",
        ) &&
        [
          "attempted",
          "successful",
          "failed",
          "p90_ms",
          "p95_ms",
          "recall_at_10",
        ].every((key) => item[key] === null || finite(item[key])),
    )
  )
    throw new Error("Báo cáo đánh giá không hợp lệ.");
  return value as unknown as EvaluationSummary;
}

export function decodeRag(value: unknown, allowedIds: Set<string>): RagAnswer {
  const rag = record(value) ? value.rag : null;
  if (
    !record(rag) ||
    typeof rag.answer !== "string" ||
    typeof rag.generated !== "boolean" ||
    !nullableString(rag.error_code) ||
    ![
      "supported",
      "partially_supported",
      "insufficient_evidence",
      "generation_unavailable",
    ].includes(String(rag.grounding_status)) ||
    !Array.isArray(rag.citations) ||
    !rag.citations.every(
      (item) =>
        record(item) &&
        typeof item.image_id === "string" &&
        allowedIds.has(item.image_id) &&
        typeof item.quote === "string" &&
        typeof item.evidence_field === "string",
    )
  )
    throw new Error("Phản hồi giải thích không đúng định dạng.");
  return rag as unknown as RagAnswer;
}

export function validConstraint(value: unknown, depth = 0): boolean {
  if (!record(value) || depth > 2) return false;
  if ("op" in value)
    return (
      ["and", "or"].includes(String(value.op)) &&
      Array.isArray(value.clauses) &&
      value.clauses.length >= 2 &&
      value.clauses.length <= 8 &&
      value.clauses.every((clause) => validConstraint(clause, depth + 1))
    );
  return (
    typeof value.id === "string" &&
    typeof value.required === "boolean" &&
    (value.kind === "semantic"
      ? typeof value.text === "string"
      : value.kind === "metadata" && record(value.filter))
  );
}

export function validAvatarURL(value: unknown, userId: unknown): boolean {
  if (value == null) return true;
  const prefix = `/api/v1/profiles/${userId}/avatar?v=`;
  return (
    typeof value === "string" &&
    value.startsWith(prefix) &&
    /^[a-f0-9]{32}$/.test(value.slice(prefix.length))
  );
}
