import { Icon } from "../../components/Icon";
import type { DatasetReference } from "../../types/access";

export function SearchGuide({
  datasets,
  guest = false,
}: {
  datasets: DatasetReference[];
  guest?: boolean;
}) {
  return (
    <aside className="search-guide" aria-label="Hướng dẫn và thư viện">
      <section className="guide-steps-card" id="how-it-works">
        <span className="guide-symbol" aria-hidden="true">
          <Icon kind="image" />
        </span>
        <h2>Từ ý tưởng đến hình ảnh</h2>
        <ol>
          <li>
            <span aria-hidden="true">1</span>
            <div>
              <strong>Chọn cách tìm</strong>
              <p>
                {guest
                  ? "Tìm ảnh bằng tiếng Việt có dấu, không dấu hoặc tiếng Anh."
                  : "Viết mô tả, dùng ảnh hoặc kết hợp cả hai."}
              </p>
            </div>
          </li>
          <li>
            <span aria-hidden="true">2</span>
            <div>
              <strong>Thêm điều bạn nhớ</strong>
              <p>Màu sắc, chủ thể hay khung cảnh bạn đang tìm.</p>
            </div>
          </li>
          <li>
            <span aria-hidden="true">3</span>
            <div>
              <strong>Mở ảnh bạn thích</strong>
              <p>Xem ảnh lớn, chú thích và thông tin nguồn.</p>
            </div>
          </li>
        </ol>
      </section>
      <section className="library-card" id="my-libraries">
        <h2>{guest ? "Thư viện công khai" : "Thư viện của bạn"}</h2>
        {datasets.length ? (
          <>
            <p>
              Bạn có thể tìm trong <strong>{datasets.length} thư viện</strong>{" "}
              {guest ? "công khai." : "được chia sẻ."}
            </p>
            <details className="library-access">
              <summary>Xem các thư viện</summary>
              <ul className="library-list">
                {datasets.map((d) => (
                  <li key={d.id}>
                    <Icon kind="layers" />
                    <span>
                      {d.name}
                      {d.shared_with_members && (
                        <small> · Chung cho thành viên</small>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          </>
        ) : (
          <p>
            {guest
              ? "Chưa có thư viện công khai. Bạn có thể đăng nhập để xem các thư viện được cấp."
              : "Bạn chưa được cấp thư viện. Hãy liên hệ quản trị viên để bắt đầu tìm ảnh."}
          </p>
        )}
      </section>
    </aside>
  );
}
