export type SearchMode =
  "auto" | "text" | "image" | "multi_intent" | "multimodal" | "agent";
export interface APIError {
  code: string;
  message: string;
  request_id: string;
  retryable: boolean;
  details: { field: string; reason: string }[];
}
export interface ImageMetadata {
  title: string | null;
  caption?: string | null;
  width: number;
  height: number;
  media_type: string;
  tags: string[];
  source_dataset: string | null;
  city: string | null;
  license: string | null;
}
export interface MetadataFilters {
  source_dataset?: string;
  media_types?: ("image/jpeg" | "image/png" | "image/webp")[];
  tags_any?: string[];
  tags_all?: string[];
  city?: string;
  min_width?: number;
  max_width?: number;
  min_height?: number;
  max_height?: number;
  captured_from?: string;
  captured_to?: string;
}
export type Constraint =
  | { id: string; kind: "semantic"; text: string; required: boolean }
  | { id: string; kind: "metadata"; filter: MetadataFilters; required: boolean }
  | { op: "and" | "or"; clauses: Constraint[] };
export interface SearchOptions {
  top_k?: number;
  page?: number;
  candidate_count?: number;
  filters?: MetadataFilters;
  constraints?: Constraint;
  require_verified?: boolean;
  rerank?: {
    enabled: boolean;
    on_failure?: "error" | "skip";
    candidate_limit?: number;
    timeout_ms?: number;
  };
  explain?: { enabled: boolean; on_failure?: "error" | "omit" };
}
export interface AdvancedSearchInput extends SearchOptions {
  mode: SearchMode;
  text?: string;
  fusion?: {
    method: "rrf" | "weighted_rrf" | "weighted_score";
    text_weight: number;
    image_weight: number;
  };
}
export type SearchRequest = SearchOptions &
  (
    | { mode: "auto" | "text" | "multi_intent"; text: string; image_id?: never }
    | { mode: "auto" | "image"; image_id: string; text?: never }
    | {
        mode: "multimodal";
        text: string;
        image_id: string;
        fusion?: {
          method: "rrf" | "weighted_rrf" | "weighted_score";
          text_weight: number;
          image_weight: number;
        };
      }
  );
export interface UploadedSearchRequest {
  options: SearchOptions & { mode: "image" | "multimodal"; text?: string };
  image: File;
}
export interface SearchResult {
  image_id: string;
  rank: number;
  image_url: string;
  thumbnail_url: string;
  score: number;
  score_type: "cosine" | "rrf" | "weighted_score" | "reranker";
  ranking_version: string;
  metadata: ImageMetadata;
  constraint_assessments: {
    clause_id: string;
    status: "satisfied" | "violated" | "unknown";
    evidence_ref: string | null;
    semantic_score?: number | null;
  }[];
}
export type DependencyStatus = "healthy" | "unhealthy" | "timeout";
export interface Readiness {
  status: "ready" | "not_ready";
  dependencies: Record<"postgresql" | "qdrant" | "minio", DependencyStatus>;
}
export interface HealthSummary {
  status: "ok" | "not_ready";
  check: "live" | "ingest" | "search";
  capabilities: Record<
    | "text_search"
    | "image_search"
    | "multimodal"
    | "multi_intent"
    | "rerank"
    | "explanations"
    | "agent",
    boolean
  >;
  worker: { state: "unknown" | "fresh" | "stale" };
  dependencies?: Record<string, string>;
}

export interface SearchResponse {
  query_id: string;
  request_id: string;
  search_mode: "text" | "image" | "multi_intent" | "multimodal";
  index_id: string;
  model_id: string;
  manifest_sha256: string;
  results: SearchResult[];
  total_results: number;
  pagination?: {
    page: number;
    page_size: number;
    total_results: number;
    total_pages: number;
    result_limit: number;
  } | null;
  query_analysis?: {
    query_type: string;
    language: string;
    uncertain: boolean;
    limitations: string[];
    constraints: Constraint | null;
  } | null;
  effective_settings?: {
    route: string;
    channels: number;
    rerank_applied: boolean;
    fusion_version: string | null;
  };
  latency: {
    processing_ms: number;
    server_response_ms: null;
    stages: Record<string, number>;
  };
  warnings: { code: string; message: string }[];
}

export type DatasetState =
  | "empty_dataset"
  | "index_building"
  | "index_not_ready"
  | "ready"
  | "unavailable";
export interface WorkspaceStatus {
  public_datasets?: { id: string; key: string; name: string }[];
  dataset: {
    state: DatasetState;
    images: number | null;
    available_images: number | null;
    indexed_images: number | null;
    vectors: number | null;
    index_id: string | null;
    index_status: string | null;
    generation: number | null;
  };
  dependencies: Record<string, string>;
  capabilities: HealthSummary["capabilities"];
  rag: { enabled: boolean; configured: boolean; streaming: boolean };
  agent: { enabled: boolean; llm_planning: boolean };
  limits: { top_k: number; image_bytes: number };
}
export interface ImageDetail {
  image_id: string;
  status: string;
  metadata: ImageMetadata;
  created_at: string;
  indexing: { index_id: string; status: string }[];
  image_url: string | null;
  thumbnail_url: string | null;
}
export interface EvaluationSummary {
  state: "available" | "empty" | "not_available";
  skipped: number;
  experiments: {
    id: string;
    phase: string;
    kind: string;
    status: string;
    attempted: number | null;
    successful: number | null;
    failed: number | null;
    p90_ms: number | null;
    p95_ms: number | null;
    recall_at_10: number | null;
    quality_status: string;
  }[];
}
export interface RagAnswer {
  answer: string;
  grounding_status:
    | "supported"
    | "partially_supported"
    | "insufficient_evidence"
    | "generation_unavailable";
  generated: boolean;
  error_code: string | null;
  citations: { image_id: string; evidence_field: string; quote: string }[];
}

export interface DiscoveryResponse {
  seed?: string;
  has_more?: boolean;
  next_cursor?: string | null;
  results: SearchResult[];
  total_results: number;
}
