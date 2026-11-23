import { api, APIClientError } from "../../services/api/client";
import { record, validId, validAvatarURL } from "../../services/api/decoders";
import type { Account, AccountRole, AuthSnapshot } from "../../types/access";

export function decodeAuth(value: unknown): AuthSnapshot {
  if (!record(value) || typeof value.legacy_enabled !== "boolean")
    throw new APIClientError(
      "INVALID_RESPONSE",
      "Phản hồi đăng nhập không hợp lệ.",
    );
  const user = value.user;
  if (
    user !== null &&
    (!record(user) ||
      !validId(user.id) ||
      typeof user.username !== "string" ||
      typeof user.display_name !== "string" ||
      !validAvatarURL(user.avatar_url, user.id) ||
      !["user", "admin"].includes(String(user.role)) ||
      typeof user.is_active !== "boolean" ||
      (user.is_demo !== undefined && typeof user.is_demo !== "boolean") ||
      !Array.isArray(user.datasets) ||
      user.datasets.length > 1000 ||
      !user.datasets.every(
        (d) =>
          record(d) &&
          validId(d.id) &&
          typeof d.key === "string" &&
          typeof d.name === "string" &&
          (d.is_public === undefined || typeof d.is_public === "boolean") &&
          (d.shared_with_members === undefined ||
            typeof d.shared_with_members === "boolean"),
      ))
  )
    throw new APIClientError(
      "INVALID_RESPONSE",
      "Thông tin tài khoản không hợp lệ.",
    );
  const roles =
    value.quick_login_roles === undefined ? [] : value.quick_login_roles;
  if (
    !Array.isArray(roles) ||
    roles.length > 2 ||
    new Set(roles).size !== roles.length ||
    !roles.every((role) => role === "admin" || role === "user")
  )
    throw new APIClientError(
      "INVALID_RESPONSE",
      "Cấu hình đăng nhập nhanh không hợp lệ.",
    );
  return {
    user: user as Account | null,
    legacy_enabled: value.legacy_enabled,
    quick_login_roles: roles as AccountRole[],
  };
}
export const authAPI = {
  register: (display_name: string, username: string, password: string) =>
    api.request(
      "/auth/register",
      (value: unknown) => {
        if (!record(value) || value.status !== "registered")
          throw new APIClientError(
            "INVALID_RESPONSE",
            "Phản hồi đăng ký không hợp lệ.",
          );
      },
      {
        json: true,
        body: JSON.stringify({ display_name, username, password }),
        timeout: 15_000,
      },
    ),
  me: (signal?: AbortSignal) => api.request("/auth/me", decodeAuth, { signal }),
  login: (username: string, password: string) =>
    api.request("/auth/login", decodeAuth, {
      json: true,
      body: JSON.stringify({ username, password }),
      timeout: 15_000,
    }),
  quickLogin: (role: AccountRole) =>
    api.request("/auth/quick-login", decodeAuth, {
      json: true,
      body: JSON.stringify({ role }),
      timeout: 15_000,
    }),
  logout: () =>
    api.request("/auth/logout", () => undefined, { method: "POST" }),
  password: (current_password: string, password: string) =>
    api.request("/auth/password", () => undefined, {
      json: true,
      body: JSON.stringify({ current_password, password }),
      timeout: 15_000,
    }),
};
