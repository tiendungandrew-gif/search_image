/** Session cookies remain HttpOnly; only the session-bound CSRF cookie is read. */
export function accessHeaders(token = ""): Record<string, string> {
  if (token) return { Authorization: `Bearer ${token}` };
  const cookies =
    typeof document === "undefined" ? [] : document.cookie.split(";");
  const found = cookies
    .map((value) => value.trim())
    .find(
      (value) =>
        value.startsWith("__Host-lens_csrf=") || value.startsWith("lens_csrf="),
    );
  if (!found) return {};
  try {
    return {
      "X-CSRF-Token": decodeURIComponent(found.slice(found.indexOf("=") + 1)),
    };
  } catch {
    return {};
  }
}
