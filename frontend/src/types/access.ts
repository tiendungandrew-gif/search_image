export type AccountRole = "user" | "admin";
export interface DatasetReference {
  is_public?: boolean;
  shared_with_members?: boolean;
  id: string;
  key: string;
  name: string;
}
export interface Account {
  avatar_url?: string | null;
  id: string;
  username: string;
  display_name: string;
  role: AccountRole;
  is_active: boolean;
  is_demo?: boolean;
  datasets: DatasetReference[];
}
export interface AuthSnapshot {
  user: Account | null;
  legacy_enabled: boolean;
  quick_login_roles: AccountRole[];
}
export interface AdminUser {
  id: string;
  username: string;
  display_name: string;
  role: AccountRole;
  is_active: boolean;
  is_demo?: boolean;
  dataset_ids: string[];
}
export interface CatalogDataset extends DatasetReference {
  shared_with_members: boolean;
  description: string;
  is_active: boolean;
  images: number;
}
export interface AdminImage {
  id: string;
  title: string | null;
  caption: string | null;
  source_dataset: string | null;
  status: string;
  hidden: boolean;
  width: number;
  height: number;
  tags: string[];
  thumbnail_url: string;
}
export interface IndexRecord {
  id: string;
  model_id: string;
  model: string;
  dimension: number;
  version: string;
  status: string;
  collection: string;
  active: boolean;
}
export interface JobRecord {
  id: string;
  kind: string;
  status: string;
  total: number;
  index_id: string | null;
}
export interface AuditRecord {
  id: string;
  actor: string;
  action: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}
