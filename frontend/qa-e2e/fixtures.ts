export const id = "30000000-0000-4000-8000-000000000001";
export const capabilities = {
  text_search: true,
  image_search: true,
  multimodal: true,
  multi_intent: true,
  rerank: true,
  explanations: true,
  agent: true,
};
export const workspace = {
  dataset: {
    state: "ready",
    images: 1,
    available_images: 1,
    indexed_images: 1,
    vectors: 1,
    index_id: id,
    index_status: "ready",
    generation: 1,
  },
  dependencies: { postgresql: "healthy", qdrant: "healthy", minio: "healthy" },
  capabilities,
  rag: { enabled: true, configured: true, streaming: true },
  agent: { enabled: true, llm_planning: true },
  limits: { top_k: 50, image_bytes: 20971520 },
};
export const image = {
  image_id: id,
  rank: 1,
  score: 0.25,
  score_type: "cosine",
  ranking_version: "fixture-v1",
  image_url: `/api/v1/images/${id}/content?variant=original`,
  thumbnail_url: `/api/v1/images/${id}/content?variant=thumbnail`,
  metadata: {
    title: "Explicit mock fixture",
    caption: "Synthetic pixel for UI testing only",
    width: 1,
    height: 1,
    media_type: "image/png",
    tags: [],
    source_dataset: "mock_ui_fixture",
    city: null,
    license: "generated",
  },
  constraint_assessments: [],
};
export const search = {
  query_id: id,
  request_id: id,
  index_id: id,
  model_id: id,
  manifest_sha256: "0".repeat(64),
  search_mode: "text",
  results: [image],
  total_results: 1,
  latency: { processing_ms: 1, server_response_ms: null, stages: {} },
  warnings: [],
  query_analysis: null,
};
export const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9L8AAAAASUVORK5CYII=",
  "base64",
);
