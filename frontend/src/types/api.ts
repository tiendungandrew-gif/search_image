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
          method: "weighted_rrf";
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
