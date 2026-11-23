import { api, APIClientError } from "../../services/api/client";
import { record, validId } from "../../services/api/decoders";
import type {
  AdminImage,
  AdminUser,
  AuditRecord,
  CatalogDataset,
  IndexRecord,
  JobRecord,
} from "../../types/access";

function invalid(): never {
  throw new APIClientError(
    "INVALID_RESPONSE",
    "Dữ liệu quản trị không hợp lệ.",
  );
}
function result(value: unknown): Record<string, unknown> {
  return record(value) ? value : invalid();
}
function list<T>(
  key: string,
  check: (value: Record<string, unknown>) => boolean,
) {
  return (value: unknown): T[] => {
    const root = result(value);
    const rows = root[key];
    if (
      !Array.isArray(rows) ||
      rows.length > 1000 ||
      !rows.every((row) => record(row) && check(row))
    )
      return invalid();
    return rows as T[];
  };
}
const decodeUsers = list<AdminUser>(
  "users",
  (u) =>
    validId(u.id) &&
    typeof u.username === "string" &&
    typeof u.display_name === "string" &&
    ["admin", "user"].includes(String(u.role)) &&
    typeof u.is_active === "boolean" &&
    Array.isArray(u.dataset_ids) &&
    u.dataset_ids.every(validId),
);
const decodeDatasets = list<CatalogDataset>(
  "datasets",
  (d) =>
    validId(d.id) &&
    typeof d.key === "string" &&
    typeof d.name === "string" &&
    typeof d.description === "string" &&
    typeof d.is_active === "boolean" &&
    typeof d.shared_with_members === "boolean" &&
    (d.is_public === undefined || typeof d.is_public === "boolean") &&
    Number.isInteger(d.images) &&
    Number(d.images) >= 0,
);
const decodeImages = list<AdminImage>(
  "images",
  (i) =>
    validId(i.id) &&
    (i.title === null || typeof i.title === "string") &&
    (i.caption === null || typeof i.caption === "string") &&
    (i.source_dataset === null || typeof i.source_dataset === "string") &&
    typeof i.status === "string" &&
    typeof i.hidden === "boolean" &&
    Array.isArray(i.tags) &&
    i.tags.every((t) => typeof t === "string") &&
    typeof i.thumbnail_url === "string",
);
const decodeIndexes = list<IndexRecord>(
  "indexes",
  (i) =>
    validId(i.id) &&
    validId(i.model_id) &&
    typeof i.version === "string" &&
    typeof i.model === "string" &&
    typeof i.status === "string" &&
    typeof i.active === "boolean",
);
const decodeJobs = list<JobRecord>(
  "jobs",
  (j) =>
    validId(j.id) &&
    typeof j.kind === "string" &&
    typeof j.status === "string" &&
    Number.isInteger(j.total),
);
const decodeAudit = list<AuditRecord>(
  "events",
  (e) =>
    validId(e.id) &&
    typeof e.action === "string" &&
    typeof e.actor === "string" &&
    typeof e.created_at === "string" &&
    record(e.details),
);
function mutate(
  path: string,
  body?: object,
  method: "POST" | "PATCH" | "PUT" | "DELETE" = "POST",
) {
  return api.request(path, result, {
    method,
    ...(body ? { body: JSON.stringify(body), json: true } : {}),
    timeout: 35_000,
  });
}

export const adminAPI = {
  users: (offset = 0) =>
    api.request(`/admin/users?offset=${offset}&limit=50`, (value) => ({
      rows: decodeUsers(value),
      total: Number(result(value).total),
    })),
  createUser: (body: object) => mutate("/admin/users", body),
  updateUser: (id: string, body: object) =>
    mutate(`/admin/users/${id}`, body, "PATCH"),
  revokeSessions: (id: string) => mutate(`/admin/users/${id}/sessions/revoke`),
  grants: (id: string, dataset_ids: string[]) =>
    mutate(`/admin/users/${id}/datasets`, { dataset_ids }, "PUT"),
  password: (id: string, password: string) =>
    mutate(`/admin/users/${id}/password`, { password }),
  datasets: () => api.request("/admin/datasets", decodeDatasets),
  createDataset: (body: object) => mutate("/admin/datasets", body),
  updateDataset: (id: string, body: object) =>
    mutate(`/admin/datasets/${id}`, body, "PATCH"),
  images: (dataset: string, offset = 0) =>
    api.request(
      `/admin/images?limit=30&offset=${offset}${dataset ? `&dataset_id=${dataset}` : ""}`,
      (value) => ({
        rows: decodeImages(value),
        total: Number(result(value).total),
      }),
    ),
  editImage: (id: string, body: object) =>
    mutate(`/admin/images/${id}`, body, "PATCH"),
  moderate: (id: string, hidden: boolean) =>
    mutate(
      `/admin/images/${id}${hidden ? "" : "/restore"}`,
      undefined,
      hidden ? "DELETE" : "POST",
    ),
  upload: (file: File, dataset: string, metadata: object, key: string) => {
    const body = new FormData();
    body.append("image", file);
    body.append("dataset_id", dataset);
    body.append("metadata", JSON.stringify(metadata));
    return api.request("/admin/images/upload", result, {
      body,
      headers: { "Idempotency-Key": key },
      timeout: 35_000,
    });
  },
  indexes: () =>
    api.request("/admin/indexes", (value) => ({
      indexes: decodeIndexes(value),
      jobs: decodeJobs(value),
    })),
  createIndex: (model_id: string, version: string) =>
    mutate("/admin/indexes", { model_id, version }),
  reindex: (target_index_id: string) =>
    mutate("/admin/indexes/reindex", { target_index_id }),
  verify: (index_id: string) => mutate("/admin/indexes/verify", { index_id }),
  activate: (index_id: string) =>
    mutate("/admin/indexes/activate", { index_id }),
  audit: (offset = 0) =>
    api.request(`/admin/audit?offset=${offset}`, decodeAudit),
  knowledge: (dataset_id: string, knowledge: object, apply: boolean) =>
    mutate("/admin/knowledge", { dataset_id, knowledge, apply }),
};
