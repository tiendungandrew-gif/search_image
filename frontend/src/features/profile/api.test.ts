import { validAvatarURL } from "../../services/api/decoders";
import { decodeProfile } from "./api";
const id = "12345678-1234-4234-8234-123456789abc";
test("avatar URLs are scoped to the expected user and safe media route", () => {
  const url = `/api/v1/profiles/${id}/avatar?v=${"a".repeat(32)}`;
  expect(validAvatarURL(url, id)).toBe(true);
  expect(validAvatarURL(null, id)).toBe(true);
  expect(validAvatarURL("https://external.example/avatar.jpg", id)).toBe(false);
  expect(validAvatarURL(`/api/v1/profiles/${id}/avatar?v=bad`, id)).toBe(false);
  expect(validAvatarURL(url, "22345678-1234-4234-8234-123456789abc")).toBe(
    false,
  );
});
test("profile decodes a valid account and rejects unsafe avatar data", () => {
  const profile = {
    user: {
      id,
      username: "alice",
      display_name: "Alice",
      role: "user",
      is_active: true,
      datasets: [],
      avatar_url: null,
    },
    bio: "Photographer",
    created_at: "2026-11-23T00:00:00Z",
    favorite_count: 3,
  };
  expect(decodeProfile(profile).favorite_count).toBe(3);
  expect(() =>
    decodeProfile({
      ...profile,
      user: { ...profile.user, avatar_url: "javascript:alert(1)" },
    }),
  ).toThrow();
  expect(() => decodeProfile({ ...profile, bio: "x".repeat(501) })).toThrow();
});
