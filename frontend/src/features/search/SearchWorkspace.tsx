import { lazy, Suspense, useState, useEffect, Profiler } from "react";
import { createPortal } from "react-dom";
import { Icon } from "../../components/Icon";
import type {
  HealthSummary,
  SearchMode,
  WorkspaceStatus,
} from "../../types/api";
import { DiscoveryMore } from "./DiscoveryMore";
import { GalleryView } from "./DiscoveryHero";
import { DISCOVERY_IMAGE_LIMIT, useDiscovery } from "./useDiscovery";
import { SearchForm } from "./SearchForm";
import { QueryAnalysis } from "./QueryAnalysis";
import { ResultGallery } from "./ResultGallery";
import { SearchSkeleton } from "./SearchSkeleton";
import { useSearchSession } from "./useSearchSession";
import type { DatasetReference } from "../../types/access";
const ExplanationPanel = lazy(() =>
  import("../rag/ExplanationPanel").then((module) => ({
    default: module.ExplanationPanel,
  })),
);
const AgentResults = lazy(() =>
  import("../agent/AgentResults").then((module) => ({
    default: module.AgentResults,
  })),
);

export function SearchWorkspace({
  token,
  onTokenChange,
  available = false,
  agentAvailable = false,
  capabilities,
  workspace,
  authenticated = false,
  guest = false,
  onRequestLogin,
  showDiagnostics = true,
  datasets,
  searchHost,
}: {
  searchHost?: HTMLElement | null;
  token: string;
  onTokenChange: (value: string) => void;
  available?: boolean;
  agentAvailable?: boolean;
  capabilities?: HealthSummary["capabilities"];
  workspace?: WorkspaceStatus | null;
  authenticated?: boolean;
  guest?: boolean;
  onRequestLogin?: () => void;
  showDiagnostics?: boolean;
  datasets?: DatasetReference[];
}) {
  const friendly = (authenticated || guest) && !showDiagnostics;
  const [mode, setMode] = useState<SearchMode>("auto");
  const [query, setQuery] = useState("");
  const [compact, setCompact] = useState(false);
  const session = useSearchSession(token);
  const discovery = useDiscovery(
    friendly &&
      workspace?.dataset.state === "ready" &&
      workspace.capabilities.text_search,
    token,
    Math.min(
      DISCOVERY_IMAGE_LIMIT,
      workspace?.limits.top_k ?? DISCOVERY_IMAGE_LIMIT,
    ),
  );
  const browsing = friendly && session.state === "IDLE";
  const loading = session.state === "SEARCHING";
  const ragAvailable =
    (workspace?.capabilities ?? capabilities)?.explanations ?? false;
  const result = session.results;
  const totalResults =
    result?.pagination?.total_results ?? result?.total_results;
  useEffect(() => {
    if (!result) return;
    const frame = requestAnimationFrame(() => {
      const heading = document.getElementById("results-heading");
      if (friendly)
        heading?.scrollIntoView?.({ block: "start", behavior: "instant" });
      heading?.focus({ preventScroll: friendly });
    });
    return () => cancelAnimationFrame(frame);
  }, [result, friendly]);
  const form = (
    <SearchForm
      token={token}
      onTokenChange={onTokenChange}
      available={available}
      agentAvailable={agentAvailable}
      capabilities={capabilities}
      workspace={workspace}
      mode={mode}
      onModeChange={setMode}
      session={session}
      authenticated={authenticated}
      guest={guest}
      onRequestLogin={onRequestLogin}
      showDiagnostics={showDiagnostics}
      datasets={datasets}
      headerSearch={searchHost !== undefined}
      queryValue={friendly ? query : undefined}
      onQueryChange={friendly ? setQuery : undefined}
    />
  );
  return (
    <div
      className={
        friendly
          ? `friendly-search commercial-workspace${compact ? " gallery-compact" : ""}`
          : undefined
      }
    >
      {friendly &&
        searchHost &&
        createPortal(
          <div className="friendly-search navbar-search">{form}</div>,
          searchHost,
        )}
      {(!friendly || searchHost === undefined) && form}
      <div className="session-status" role="status" aria-live="polite">
        {session.state === "CANCELLED"
          ? "Đã hủy yêu cầu. Bạn có thể tiếp tục tìm kiếm."
          : loading
            ? "Đang tìm kiếm…"
            : result
              ? `Đã nhận ${totalResults} kết quả.${result.pagination ? ` Trang ${result.pagination.page} trên ${result.pagination.total_pages}.` : ""}`
              : ""}
      </div>
      <div
        id={friendly ? "explore-gallery" : undefined}
        className={browsing ? "discovery-feed" : undefined}
      >
        {mode === "agent" ? (
          <Suspense fallback={<p role="status">Đang mở Agent…</p>}>
            <AgentResults
              response={session.agent}
              progress={session.progress}
              loading={loading}
              token={token}
              showDiagnostics={showDiagnostics}
              datasetNames={Object.fromEntries(
                (datasets ?? []).map((d) => [d.key, d.name]),
              )}
            />
          </Suspense>
        ) : (
          <section
            className="results-section"
            aria-labelledby="results-heading"
            data-state={session.state}
            data-search-started={session.metrics.started}
            data-api-ms={session.metrics.apiMs?.toFixed(2)}
            data-first-result-ms={session.metrics.visibleMs?.toFixed(2)}
            data-render-ms={session.metrics.renderMs?.toFixed(2)}
            data-react-ms={session.metrics.reactMs?.toFixed(2)}
          >
            <div className={browsing ? "sr-only" : "section-title"}>
              <div>
                {friendly && (
                  <span className="shop-section-eyebrow">
                    {browsing
                      ? "CẢM HỨNG TỪ THƯ VIỆN CỦA BẠN"
                      : "DÀNH CHO TÌM KIẾM CỦA BẠN"}
                  </span>
                )}
                <h2 id="results-heading" tabIndex={-1}>
                  {browsing ? "Khám phá thư viện" : "Kết quả tìm kiếm"}
                </h2>
              </div>
              {!browsing && (
                <div className="gallery-toolbar">
                  <span>
                    {result
                      ? showDiagnostics
                        ? `${totalResults} kết quả · ${result.latency.processing_ms.toFixed(1)} ms xử lý`
                        : `${totalResults} kết quả`
                      : browsing && discovery.results
                        ? `${discovery.results.total_results} ảnh gợi ý`
                        : friendly
                          ? "Khám phá theo cách của bạn"
                          : "Chưa có kết quả"}
                  </span>
                  {friendly &&
                  (result?.results.length ||
                    (browsing && discovery.results?.results.length)) ? (
                    <GalleryView compact={compact} onChange={setCompact} />
                  ) : null}
                </div>
              )}
            </div>
            {friendly && result && (
              <div className="results-summary">
                <p>
                  {session.submittedQuery ? (
                    <>
                      Kết quả cho <strong>“{session.submittedQuery}”</strong>
                    </>
                  ) : (
                    "Những hình ảnh gần với ảnh bạn đã chọn."
                  )}
                </p>
                <a href="#search-heading">Sửa tìm kiếm</a>
              </div>
            )}
            {result?.warnings
              .filter((warning) => warning.code === "QUERY_ACCENTS_RESTORED")
              .map((warning) => (
                <p
                  className="availability-note"
                  role="status"
                  key={warning.code}
                >
                  {warning.message}
                </p>
              ))}
            {loading ? (
              <SearchSkeleton />
            ) : result && result.results.length > 0 ? (
              <>
                {showDiagnostics && <QueryAnalysis response={result} />}
                <Profiler id="results" onRender={session.markReact}>
                  <ResultGallery
                    key={result.query_id}
                    images={result.results}
                    token={token}
                    onVisible={session.markVisible}
                    showDiagnostics={showDiagnostics}
                    datasetNames={Object.fromEntries(
                      (datasets ?? []).map((d) => [d.key, d.name]),
                    )}
                  />
                </Profiler>
                {result.pagination && result.pagination.total_pages > 1 && (
                  <nav
                    className="search-pagination"
                    aria-label="Phân trang kết quả tìm kiếm"
                  >
                    <p>
                      {totalResults === result.pagination.result_limit
                        ? "Hiển thị tối đa "
                        : ""}
                      {totalResults} kết quả · {result.pagination.page_size} ảnh
                      mỗi trang
                    </p>
                    <div className="pagination-buttons">
                      <button
                        type="button"
                        disabled={loading || result.pagination.page === 1}
                        onClick={() =>
                          session.goToPage(result.pagination!.page - 1)
                        }
                      >
                        Trước
                      </button>
                      {Array.from(
                        { length: result.pagination.total_pages },
                        (_, i) => i + 1,
                      )
                        .filter(
                          (page) =>
                            page === 1 ||
                            page === result.pagination!.total_pages ||
                            Math.abs(page - result.pagination!.page) <= 2,
                        )
                        .map((page, i, pages) => (
                          <span key={page}>
                            {i > 0 && page - pages[i - 1] > 1 && (
                              <span
                                className="pagination-gap"
                                aria-hidden="true"
                              >
                                …
                              </span>
                            )}
                            <button
                              type="button"
                              aria-label={`Trang ${page}`}
                              aria-current={
                                page === result.pagination!.page
                                  ? "page"
                                  : undefined
                              }
                              disabled={
                                loading || page === result.pagination!.page
                              }
                              onClick={() => session.goToPage(page)}
                            >
                              {page}
                            </button>
                          </span>
                        ))}
                      <button
                        type="button"
                        disabled={
                          loading ||
                          result.pagination.page ===
                            result.pagination.total_pages
                        }
                        onClick={() =>
                          session.goToPage(result.pagination!.page + 1)
                        }
                      >
                        Sau
                      </button>
                    </div>
                  </nav>
                )}
                {ragAvailable ? (
                  <Suspense fallback={<p role="status">Đang mở giải thích…</p>}>
                    <ExplanationPanel
                      key={result.query_id}
                      results={result}
                      token={token}
                      query={session.submittedQuery}
                      streaming={workspace?.rag.streaming ?? false}
                    />
                  </Suspense>
                ) : (
                  <p className="availability-note">
                    {friendly
                      ? "Bạn có thể mở từng ảnh để xem đầy đủ thông tin."
                      : "Giải thích AI chưa khả dụng. Bạn vẫn có thể xem ảnh và metadata."}
                  </p>
                )}
              </>
            ) : browsing && discovery.loading ? (
              <SearchSkeleton />
            ) : browsing && discovery.results?.results.length ? (
              <>
                <ResultGallery
                  images={discovery.results.results}
                  token={token}
                  showDiagnostics={false}
                  showRanks={false}
                  datasetNames={Object.fromEntries(
                    (datasets ?? []).map((d) => [d.key, d.name]),
                  )}
                />
                <DiscoveryMore
                  hasMore={discovery.hasMore}
                  loading={discovery.loadingMore}
                  error={discovery.moreError}
                  onLoad={() => void discovery.loadMore()}
                />
              </>
            ) : browsing && discovery.error ? (
              <div className="discovery-error" role="status">
                <p>
                  Chưa tải được ảnh khám phá. Bạn vẫn có thể tìm bằng mô tả hoặc
                  ảnh phía trên.
                </p>
                <p className="muted">{discovery.error}</p>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={discovery.retry}
                >
                  Tải lại ảnh khám phá
                </button>
              </div>
            ) : (
              <div className="empty-results" role="status">
                <span className="empty-icon">
                  <Icon kind="layers" />
                </span>
                <h3>
                  {workspace?.dataset.state === "empty_dataset"
                    ? guest
                      ? "Chưa có ảnh công khai."
                      : "Chưa có dữ liệu ảnh."
                    : session.state === "ERROR" ||
                        session.state === "INDEX_NOT_READY"
                      ? "Chưa nhận được kết quả."
                      : result
                        ? "Không tìm thấy ảnh phù hợp."
                        : friendly
                          ? "Ảnh bạn cần đang chờ được tìm thấy"
                          : "Một không gian cho những điều bạn tìm."}
                </h3>
                <p>
                  {workspace?.dataset.state === "empty_dataset"
                    ? guest
                      ? "Hiện chưa có thư viện ảnh công khai. Đăng nhập để xem các thư viện được cấp cho bạn."
                      : authenticated
                        ? "Thư viện được chia sẻ với bạn hiện chưa có ảnh có thể tìm kiếm. Liên hệ quản trị viên nếu bạn cần thêm quyền truy cập."
                        : "Nhập dataset theo hướng dẫn vận hành, sau đó làm mới trạng thái. Giao diện sẽ tự nhận dữ liệu mới."
                    : result
                      ? friendly
                        ? "Thử mô tả ngắn hơn hoặc bỏ bớt bộ lọc. Một chi tiết khác có thể giúp bạn tìm được ảnh."
                        : "Dataset đang có dữ liệu. Thử nới bộ lọc hoặc đổi mô tả."
                      : guest
                        ? "Nhập mô tả bằng tiếng Việt hoặc tiếng Anh để tìm trong thư viện công khai."
                        : authenticated
                          ? "Chọn cách tìm phía trên. Bạn cũng có thể thử một gợi ý có sẵn để bắt đầu."
                          : "Nhập token và bắt đầu bằng lời mô tả hoặc ảnh tham chiếu."}
                </p>
                {friendly && result && (
                  <a
                    className="secondary-button empty-action"
                    href={mode === "image" ? "#search-heading" : "#query"}
                  >
                    Đổi mô tả tìm kiếm
                  </a>
                )}
              </div>
            )}
            {result?.warnings
              .filter((warning) => warning.code !== "QUERY_ACCENTS_RESTORED")
              .map((warning, i) => (
                <p className="availability-note" key={`${warning.code}-${i}`}>
                  {warning.message}
                </p>
              ))}
            {showDiagnostics && session.metrics.visibleMs !== null && (
              <p className="performance-note">
                API {session.metrics.apiMs?.toFixed(0)} ms · Hiển thị thẻ kết
                quả {session.metrics.visibleMs.toFixed(0)} ms từ lúc gửi · Ảnh
                tải theo vùng nhìn thấy.
              </p>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
