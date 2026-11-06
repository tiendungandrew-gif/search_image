import { useEffect, useRef, useState } from "react";
import { Icon } from "../components/Icon";
import { SearchWorkspace } from "../features/search/SearchWorkspace";
import { useHealth } from "../hooks/useHealth";
import { api } from "../services/api/client";
import type { Readiness } from "../types/api";

export function App() {
  const { health, loading, error, refresh } = useHealth();
  const [token, setToken] = useState("");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [checking, setChecking] = useState(false);
  const [readinessError, setReadinessError] = useState<string | null>(null);
  const checkController = useRef<AbortController | null>(null);
  useEffect(() => () => checkController.current?.abort(), []);
  async function checkInfrastructure() {
    checkController.current?.abort();
    const controller = new AbortController();
    checkController.current = controller;
    setChecking(true);
    setReadinessError(null);
    setReadiness(null);
    try {
      const data = await api.readiness(token, controller.signal);
      if (!controller.signal.aborted) setReadiness(data);
    } catch (err) {
      if (!controller.signal.aborted)
        setReadinessError(
          err instanceof Error ? err.message : "Lỗi kiểm tra dịch vụ",
        );
    } finally {
      if (!controller.signal.aborted) setChecking(false);
    }
  }
  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="brand" href="/" aria-label="Lens trang chủ">
          <span className="brand-mark">
            <Icon kind="search" />
          </span>
          <span>
            lens<span className="brand-period">.</span>
          </span>
        </a>
        <span className="header-caption">TÌM KIẾM ẢNH ĐA PHƯƠNG THỨC</span>
        <span className="version-badge">
          Multimodal Search <span>v0.6</span>
        </span>
      </header>
      <main>
        <section className="hero">
          <div className="hero-eyebrow">
            <span /> MỘT CÁCH KHÁC ĐỂ KHÁM PHÁ
          </div>
          <h1>
            Đi từ ý tưởng
            <br />
            đến <span>hình ảnh.</span>
          </h1>
          <p>
            Tìm bằng lời mô tả hoặc bằng hình ảnh.
            <br />
            Một không gian tìm kiếm được xây dựng trên sự thấu hiểu ngữ nghĩa.
          </p>
        </section>
        <div className="workspace-layout">
          <div className="min-w-0">
            <SearchWorkspace
              token={token}
              onTokenChange={setToken}
              available={health?.capabilities.text_search ?? false}
            />
          </div>
          <aside className="sidebar" aria-label="Trạng thái ứng dụng">
            <section className="connection-card">
              <div className="sidebar-title">
                <h2>Kết nối hệ thống</h2>
                <button
                  className="icon-button"
                  onClick={() => void refresh()}
                  disabled={loading}
                  aria-label="Kiểm tra lại kết nối"
                >
                  <Icon kind="refresh" />
                </button>
              </div>
              <div
                className={`connection-status ${health ? "connected" : ""}`}
                role="status"
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    Đang kiểm tra API…
                  </>
                ) : (
                  <>
                    <span className="status-dot" />
                    {health ? "API đang hoạt động" : "Chưa kết nối API"}
                  </>
                )}
              </div>
              {error && (
                <p role="alert" className="error-message">
                  {error}
                </p>
              )}
              <p className="sidebar-description">
                Trạng thái API được lấy trực tiếp từ backend. Chọn văn bản hoặc
                ảnh để tìm kiếm.
              </p>
              <details className="diagnostics">
                <summary>Kiểm tra hạ tầng</summary>
                <p>
                  Nhập token của phiên vận hành để kiểm tra các dịch vụ. Token
                  chỉ giữ trong memory, không lưu trên trình duyệt.
                </p>
                <label className="field-label" htmlFor="api-token">
                  Bearer token
                </label>
                <input
                  id="api-token"
                  type="password"
                  autoComplete="off"
                  value={token}
                  onChange={(e) => {
                    checkController.current?.abort();
                    setChecking(false);
                    setToken(e.target.value);
                    setReadiness(null);
                    setReadinessError(null);
                  }}
                />
                <button
                  className="diagnostic-button"
                  disabled={!token || checking}
                  onClick={() => void checkInfrastructure()}
                >
                  {checking ? "Đang kiểm tra…" : "Kiểm tra dịch vụ"}
                </button>
                {readinessError && (
                  <p className="error-message" role="alert">
                    {readinessError}
                  </p>
                )}
                {readiness && (
                  <ul className="service-list">
                    {Object.entries(readiness.dependencies).map(
                      ([name, value]) => (
                        <li key={name}>
                          <span>{name}</span>
                          <span
                            className={
                              value === "healthy" ? "service-ok" : "service-bad"
                            }
                          >
                            {value === "healthy"
                              ? "Sẵn sàng"
                              : value === "timeout"
                                ? "Hết thời gian"
                                : "Không khả dụng"}
                          </span>
                        </li>
                      ),
                    )}
                  </ul>
                )}
              </details>
            </section>
            <section className="guide-card">
              <span className="guide-icon">
                <Icon kind="image" />
              </span>
              <h2>
                Để hình ảnh
                <br />
                kể câu chuyện.
              </h2>
              <p>
                Một khung cảnh, một màu sắc, một cảm giác. Bắt đầu từ những chi
                tiết bạn nhớ.
              </p>
              <div className="guide-divider" />
              <span className="guide-caption">
                VĂN BẢN · HÌNH ẢNH · NGỮ NGHĨA
              </span>
            </section>
          </aside>
        </div>
      </main>
      <footer>
        <span>AI Multimodal Image Search System</span>
        <span>Semantic retrieval · Nền tảng phát triển</span>
      </footer>
    </div>
  );
}
