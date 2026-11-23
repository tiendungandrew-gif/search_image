import { useEffect, useRef, useState } from "react";
import type { Account } from "../../types/access";
import { Avatar } from "../../components/Avatar";
import { profileAPI, type Profile } from "./api";
function Preview({ image }: { image: File }) {
  const ref = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const url = URL.createObjectURL(image);
    if (ref.current) ref.current.src = url;
    return () => URL.revokeObjectURL(url);
  }, [image]);
  return (
    <span className="profile-avatar user-avatar">
      <img ref={ref} alt="Ảnh đại diện sắp cập nhật" />
    </span>
  );
}
export default function ProfilePage({
  user,
  onSaved,
}: {
  user: Account;
  onSaved: () => void;
}) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [name, setName] = useState(user.display_name);
  const [bio, setBio] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [image, setImage] = useState<File | null>(null);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (user.is_demo) return;
    const controller = new AbortController();
    void profileAPI
      .me(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          setProfile(value);
          setName(value.user.display_name);
          setBio(value.bio);
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setError(
            error instanceof Error ? error.message : "Chưa tải được hồ sơ.",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [user.is_demo, attempt]);
  if (user.is_demo)
    return (
      <section className="personal-page">
        <h1>Hồ sơ cá nhân</h1>
        <p>
          Đăng nhập bằng tài khoản cá nhân để cập nhật hồ sơ và lưu ảnh yêu
          thích.
        </p>
      </section>
    );
  const current = profile?.user ?? user;
  return (
    <section className="personal-page">
      <header className="personal-page-heading">
        <div>
          <span className="personal-eyebrow">KHÔNG GIAN CỦA BẠN</span>
          <h1>Hồ sơ cá nhân</h1>
          <p>Một chút về bạn, một góc nhìn riêng.</p>
        </div>
        <a href="/favorites" className="profile-favorites-link">
          ♡ {profile?.favorite_count ?? 0} ảnh yêu thích
        </a>
      </header>
      <div className="profile-layout">
        <section
          className="profile-preview-card"
          aria-label="Thông tin cá nhân"
        >
          {image ? (
            <Preview image={image} />
          ) : (
            <Avatar
              name={current.display_name}
              url={current.avatar_url}
              className="profile-avatar"
            />
          )}
          <h2>{current.display_name}</h2>
          <p className="profile-handle">@{user.username}</p>
          {profile?.bio && <p className="profile-bio">{profile.bio}</p>}
          {profile && (
            <small>
              Tham gia{" "}
              {new Date(profile.created_at).toLocaleDateString("vi-VN", {
                month: "long",
                year: "numeric",
              })}
            </small>
          )}
          <input
            ref={file}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            disabled={busy}
            onChange={(event) => {
              const value = event.target.files?.[0];
              if (!value) return;
              setNotice(null);
              if (
                value.size > 5 * 1024 * 1024 ||
                !["image/jpeg", "image/png", "image/webp"].includes(value.type)
              ) {
                setError("Chọn ảnh JPEG, PNG hoặc WebP tối đa 5 MB.");
                event.target.value = "";
                return;
              }
              setError(null);
              setImage(value);
            }}
          />
          <button
            type="button"
            className="secondary-button"
            disabled={busy}
            onClick={() => file.current?.click()}
          >
            Thay ảnh đại diện
          </button>
          <small>JPG, PNG hoặc WebP · tối đa 5 MB</small>
          {image && (
            <div className="profile-avatar-actions">
              <button
                className="primary-button"
                type="button"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError(null);
                  setNotice(null);
                  try {
                    const updated = await profileAPI.avatar(image);
                    setProfile(updated);
                    setImage(null);
                    if (file.current) file.current.value = "";
                    setNotice("Đã cập nhật ảnh đại diện.");
                    onSaved();
                  } catch (error) {
                    setError(
                      error instanceof Error
                        ? error.message
                        : "Chưa cập nhật được ảnh đại diện.",
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {busy ? "Đang lưu…" : "Lưu ảnh đại diện"}
              </button>
              <button
                type="button"
                className="profile-cancel"
                disabled={busy}
                onClick={() => {
                  setImage(null);
                  if (file.current) file.current.value = "";
                }}
              >
                Hủy
              </button>
            </div>
          )}
        </section>
        <section className="profile-edit-card">
          <h2>Chỉnh sửa hồ sơ</h2>
          {loading && <p role="status">Đang tải hồ sơ…</p>}
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (busy || loading) return;
              setBusy(true);
              setError(null);
              setNotice(null);
              try {
                setProfile(await profileAPI.update(name.trim(), bio.trim()));
                setNotice("Đã lưu hồ sơ của bạn.");
                onSaved();
              } catch (error) {
                setError(
                  error instanceof Error
                    ? error.message
                    : "Chưa lưu được hồ sơ.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Tên hiển thị
              <input
                value={name}
                required
                maxLength={120}
                autoComplete="name"
                disabled={busy || loading}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label>
              Tên đăng nhập
              <input value={user.username} readOnly autoComplete="username" />
            </label>
            <label>
              Giới thiệu
              <textarea
                value={bio}
                maxLength={500}
                rows={5}
                disabled={busy || loading}
                placeholder="Chia sẻ đôi điều về bạn…"
                onChange={(event) => setBio(event.target.value)}
              />
            </label>
            <small className="profile-character-count">
              {bio.length}/500 ký tự
            </small>
            {error && (
              <p role="alert" className="form-alert">
                {error}
                {!profile && (
                  <button
                    type="button"
                    onClick={() => {
                      setLoading(true);
                      setError(null);
                      setAttempt((value) => value + 1);
                    }}
                  >
                    Thử lại
                  </button>
                )}
              </p>
            )}
            {notice && (
              <p role="status" className="profile-success">
                {notice}
              </p>
            )}
            <div className="profile-form-actions">
              <button
                className="primary-button"
                disabled={busy || loading || !profile || !name.trim()}
              >
                {busy ? "Đang lưu…" : "Lưu thay đổi"}
              </button>
              <a href="/account">Đổi mật khẩu</a>
            </div>
          </form>
        </section>
      </div>
    </section>
  );
}
