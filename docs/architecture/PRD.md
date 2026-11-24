# PRD — Đặc tả yêu cầu sản phẩm Synlens

| Thuộc tính | Giá trị |
| --- | --- |
| Phiên bản | 2.0 — bản rà soát thiết kế |
| Ngày cập nhật | 23/11/2026 |
| Sản phẩm | Synlens — tìm kiếm và quản lý thư viện ảnh bằng AI |
| Phạm vi | Web, API, quản trị, lập chỉ mục, đánh giá và vận hành |
| Đối tượng đọc | Chủ sản phẩm, phát triển, kiểm thử, vận hành, người nghiệm thu |
| Trạng thái | Dự thảo kỹ thuật để rà soát; chưa phải cam kết SLA hoặc biên bản nghiệm thu |
| Tài liệu đi kèm | [SAD](SAD.md), [phân quyền](ACCESS_CONTROL.md), [API](API_SPECIFICATION.md), [database](DATABASE_DESIGN.md) |

## 1. Mục đích và quy ước

PRD xác định người dùng cần gì, quy tắc nghiệp vụ và cách nghiệm thu. SAD mô tả cách hệ thống đáp ứng các yêu cầu đó. Bản này đối chiếu với source tại workspace ngày 23/11/2026; không khẳng định phiên bản đang chạy trên máy nghiệm thu đã có toàn bộ source mới.

Quy ước: **P0** bắt buộc cho luồng cốt lõi; **P1** mở rộng trải nghiệm/quản trị; **P2** tùy chọn có điều kiện. Ưu tiên không biểu thị tiến độ. “Có trong source” chỉ xác nhận có mã xử lý; kết quả chạy thực phải có báo cáo tương ứng. Mọi ngưỡng hiệu năng đề xuất cần workload, phần cứng và phê duyệt trước khi trở thành điều kiện phát hành.

Giữ ID `FR-001…024`, `NFR-001…012` từ [baseline](archive/PRD_BASELINE_20261103.md) để truy vết. Các quy tắc token của baseline được thay bằng tài khoản/session trong bản này; các mục tiêu cũ vẫn là mục tiêu, không được chuyển thành số đo thực tế.

## 2. Bài toán và giá trị sản phẩm

Người dùng thường nhớ nội dung, ngữ cảnh hoặc hình ảnh tương tự nhưng không biết tên file. Thư viện chỉ tìm theo từ khóa khó phục vụ truy vấn mô tả tự nhiên và ảnh tham chiếu. Người quản trị đồng thời cần kiểm soát ai có thể xem ảnh, nguồn dữ liệu, quyền sử dụng và tình trạng lập chỉ mục.

Synlens cung cấp một nơi tìm ảnh theo ngữ nghĩa, xem metadata, quản lý thư viện và chia sẻ có quyền. Tìm kiếm cơ bản chạy với model local; RAG/Agent bổ sung giải thích và quan hệ khi được cấu hình, có bằng chứng và đủ ngân sách xử lý.

### 2.1 Mục tiêu sản phẩm

| ID | Mục tiêu | Cách đánh giá |
| --- | --- | --- |
| GOAL-01 | Tìm được ảnh phù hợp từ mô tả Việt–Anh hoặc ảnh tham chiếu | Bộ truy vấn có nhãn, Recall@10/nDCG@10 và đánh giá tác vụ |
| GOAL-02 | Chỉ đưa dữ liệu đúng quyền tới người dùng | Kiểm thử quyền ở search, metadata, media, bình luận, RAG và Agent |
| GOAL-03 | Quản trị ảnh/index có khả năng theo dõi, retry và phục hồi | Jobs, receipts, kiểm chứng nhất quán và thử lỗi worker |
| GOAL-04 | Cài đặt và vận hành có thể tái lập | Lockfiles, manifests, clean setup, backup/restore |
| GOAL-05 | Hiển thị rõ giới hạn AI và trạng thái hệ thống | UI phân biệt empty/unavailable; score có loại; evidence có nguồn |

### 2.2 Phạm vi và giới hạn

Trong phạm vi: tìm kiếm text/image/multimodal, metadata filters, tài khoản, thư viện, quản trị ảnh/index, hồ sơ, yêu thích, bình luận và chat hai người. RAG, Agent và nhập giọng nói là chức năng tùy cấu hình.

Ngoài phạm vi hiện hành: ứng dụng mobile native, tự huấn luyện foundation model, nhận diện danh tính khuôn mặt, crawling URL tùy ý, chat nhóm, gọi thoại/video, SSO/MFA, hệ thống billing và cô lập multi-tenant cấp tổ chức. Admin/User là vai trò trong một hệ thống; thư viện không phải tenant độc lập.

## 3. Người dùng và quyền

| Vai trò | Nhu cầu | Quyền chính |
| --- | --- | --- |
| Guest | Khám phá ảnh công khai trước khi đăng ký | Tìm text và đọc dữ liệu công khai theo quota; không upload ảnh truy vấn, gọi RAG/Agent hoặc quản trị |
| User | Tìm ảnh, xem chi tiết, lưu yêu thích và trao đổi | Dùng thư viện public/chung/grant riêng đang hoạt động; chức năng cá nhân cần tài khoản phù hợp |
| Admin | Quản lý nội dung, người dùng và index | Quyền quản trị toàn hệ thống; không mặc nhiên có quyền đọc chat riêng của người khác |
| Operator | Cài đặt, model, cấu hình, backup và phát hành | CLI/host được tin cậy; không phải vai trò người dùng web thứ ba |
| Evaluator | Đánh giá chất lượng và hiệu năng | Bộ dữ liệu có quyền sử dụng, cấu hình cố định và artifacts có thể kiểm tra |

Phạm vi đọc của User là hợp các thư viện đang hoạt động thuộc ba nguồn: công khai, chia sẻ thành viên, grant riêng. Guest chỉ dùng thư viện công khai đang hoạt động. Tạm dừng thư viện chặn các nguồn quyền này. Admin có quyền toàn hệ thống theo chính sách quản trị; vẫn cần xác thực cho API quản trị.

## 4. Các hành trình sử dụng

### UC-01 — Khách tìm ảnh công khai

Điều kiện: guest search bật, có thư viện public và search runtime sẵn sàng. Khách nhập text → hệ thống validate/quota → truy xuất trong phạm vi public → hiển thị ảnh và metadata. Không có ảnh phù hợp trả trạng thái rỗng. Thiếu model/index phải báo chưa sẵn sàng, không giả làm rỗng. Khi chọn tìm bằng ảnh, giao diện yêu cầu đăng nhập.

### UC-02 — Thành viên tìm bằng ảnh hoặc kết hợp

User đăng nhập → chọn ảnh tham chiếu, xem preview → nhập mô tả nếu cần → chọn bộ lọc → gửi tìm kiếm → xem kết quả và chi tiết. Hệ thống kiểm tra quyền của ảnh tham chiếu theo ID. Upload để truy vấn không tự đưa ảnh vào corpus. Rerank hoặc giải thích chỉ chạy khi được chọn và có capability.

### UC-03 — Admin nhập và xuất bản thư viện

Admin tạo thư viện → chọn quyền public/chung hoặc grant riêng → nhập ảnh có metadata/quyền sử dụng → nhận job → theo dõi từng item → xử lý lỗi/retry → kiểm tra index trước khi kích hoạt. Quyền truy cập độc lập với trạng thái lập chỉ mục: chia sẻ thư viện không làm ảnh lỗi trở thành searchable.

### UC-04 — Quản lý tài khoản và quyền

Người dùng đăng ký tài khoản User, đăng nhập và đổi mật khẩu. Admin tạo/khóa tài khoản, cấp quyền, thu hồi session hoặc reset mật khẩu. Từ request tiếp theo, server đọc lại quyền hiện hành; request đang xử lý dùng snapshot quyền của request đó. Dữ liệu đã tải về thiết bị không thể thu hồi từ xa.

### UC-05 — Giải thích và truy vấn quan hệ

User chọn giải thích/Agent → hệ thống kiểm tra feature/quota → truy xuất ảnh hoặc tri thức được phép → gọi provider nếu cấu hình yêu cầu → kiểm tra citation/budget → trả evidence hoặc thông báo thiếu bằng chứng. Provider lỗi không làm core search mất khả năng trả ảnh.

### UC-06 — Tương tác cá nhân

User cập nhật hồ sơ, lưu ảnh yêu thích, bình luận ảnh được phép và mở chat hai người. Khi mất quyền thư viện, ảnh yêu thích/bình luận liên quan không được dùng làm đường vòng để đọc ảnh. Attachment chat chỉ cho thành viên hội thoại, không tự tham gia search/RAG.

## 5. Quy tắc nghiệp vụ

| ID | Quy tắc |
| --- | --- |
| BR-01 | Mặc định thư viện không public và không chia sẻ chung; bật hai quyền là hai thao tác riêng. |
| BR-02 | Chỉ Admin được thay quyền thư viện, quản trị tài khoản, nhập/sửa/ẩn ảnh và quản lý index. |
| BR-03 | Không được khóa hoặc hạ quyền Admin cá nhân hoạt động cuối cùng. |
| BR-04 | Đăng ký chỉ tạo User; dữ liệu gửi từ client không được tự cấp role/grant. |
| BR-05 | Ảnh ẩn hoặc không đủ điều kiện lifecycle/index không được trả qua search/media. Ẩn có thể khôi phục, không đồng nghĩa xóa vật lý. |
| BR-06 | Cosine/RRF/reranker score là điểm xếp hạng, không phải xác suất ảnh đúng yêu cầu. |
| BR-07 | Kết quả tối đa K và có thể ít hơn; không chèn ảnh sai quyền để đủ số lượng. |
| BR-08 | Model/query/index phải tương thích manifest; cùng số chiều không đủ chứng minh tương thích. |
| BR-09 | Mỗi request dùng một snapshot index; không trộn generation trong cùng kết quả. |
| BR-10 | Chỉ xác nhận điều kiện/claim khi có evidence phù hợp; unknown không được trình bày thành verified. |
| BR-11 | Demo login chỉ opt-in ở development/test; không thay tài khoản cá nhân và không dùng ở production public. |
| BR-12 | Secret chỉ ở backend/host, không nằm trong Git, URL, frontend bundle hoặc log mặc định. |
| BR-13 | Dedup bytes không được tự ghi đè metadata hoặc cấp quyền đọc asset ngoài thư viện được phép. |
| BR-14 | Quota và cờ tính năng được kiểm tra server-side; UI chỉ giúp người dùng hiểu trạng thái. |

## 6. Yêu cầu chức năng và tiêu chí nghiệm thu

Các cột nghiệm thu là điều kiện cần kiểm tra trong QA; không có nghĩa các kiểm thử đã chạy trong lần sửa tài liệu này. “Hướng xử lý hiện hành” mô tả source hoặc chính sách thiết kế được kế thừa.

### 6.1 Tìm kiếm, dữ liệu và AI — giữ ID baseline

| ID | Ưu tiên | Yêu cầu và hướng xử lý hiện hành | Tiêu chí nghiệm thu |
| --- | --- | --- | --- |
| FR-001 | P0 | Tìm text Việt–Anh bằng encoder đa ngôn ngữ tương thích CLIP | Query hợp lệ trả ID/rank/score có loại; fast path không gọi LLM; kiểm tra cả có dấu/không dấu |
| FR-002 | P0 | Tìm ảnh tương tự từ upload hoặc image ID | Ảnh hợp lệ được encode; ID ngoài quyền bị chặn; ảnh hỏng không được trả kết quả giả |
| FR-003 | P0 | Top-K có giới hạn, dedup và thứ tự ổn định | Mặc định K=10; runtime mặc định tối đa 50; boundary được validate; không trùng image ID |
| FR-004 | P0 | Nhận ảnh vào corpus bằng quy trình ingestion có job | Chấp nhận bền vững trước khi báo thành công; object/metadata/vector có identity nhất quán |
| FR-005 | P0 | Dedup và idempotency cho nhập ảnh | Gửi lặp/concurrent không tạo identity/job live trùng trái constraint; không lộ dữ liệu khác quyền |
| FR-006 | P0 | Đọc metadata, ảnh và provenance đúng quyền | Search/detail/media cùng áp quyền và trạng thái ẩn; không lộ key nội bộ hoặc credentials |
| FR-007 | P0 | Job bền vững, retry hữu hạn và tiến độ từng item | Worker chết/retry không publish ready sai; hết retry có lỗi rõ và item có thể kiểm tra |
| FR-008 | P0 | Đăng ký, verify, activate và rollback index/model | Manifest mismatch bị từ chối; chỉ activate index hợp lệ; generation truy được |
| FR-009 | P0 | API `/api/v1`, DTO và lỗi thống nhất | Input sai có HTTP/code/request ID; schema phù hợp OpenAPI của phiên bản triển khai |
| FR-010 | P0 | Web responsive và trạng thái tương tác rõ | Form, preview, grid, detail dùng được bằng bàn phím; loading/empty/error riêng biệt |
| FR-011 | P0 | Đánh giá retrieval bằng dữ liệu có nhãn | Metric khớp mẫu tính tay; qrels/split/version/hash được ghi; không thay nhãn thật bằng nhãn giả |
| FR-012 | P0 | Đo latency, load và tài nguyên | Có samples, percentiles, concurrency, lỗi và cấu hình; phân biệt server/client/cold/warm |
| FR-013 | P1 | Tìm text+image bằng fusion có cấu hình | Thực thi cả hai nhánh; trả method/weights; ablation chứng minh hành vi khi đổi modality |
| FR-014 | P1 | Router theo input và mode | Query đơn không tự gọi Agent/LLM; requested/executed mode truy được |
| FR-015 | P1 | Nhiều điều kiện AND/OR, required/optional | Evidence thể hiện satisfied/violated/unknown; strict verification không coi unknown là đạt |
| FR-016 | P1 | Lọc metadata có kiểu và kiểm tra lại ở PG | AND giữa fields; tags_any/tags_all đúng; null/stale payload không vượt hard filter |
| FR-017 | P1 | Candidate/rerank có giới hạn và policy lỗi | C không nhỏ hơn K; rerank chỉ khi bật; fallback có warning theo policy |
| FR-018 | P1 | Tìm metadata kết hợp semantic cho tên/caption | Có metadata ranking trong source; cần benchmark ablation trước khi tuyên bố tốt hơn baseline |
| FR-019 | P2 | Giải thích có evidence và citation | Citation chỉ tới ảnh được phép trong evidence; thiếu chứng cứ trả trạng thái phù hợp |
| FR-020 | P0 | Core retrieval độc lập RAG/provider | Tắt/làm lỗi provider vẫn tìm core khi model/index sẵn sàng |
| FR-021 | P2 | Agent nhiều bước hữu hạn | Không vượt hop/call/replan/deadline; quan hệ không biết được trả unresolved/fallback rõ |
| FR-022 | P2 | Tools và knowledge có nguồn, kiểm quyền | Chỉ tool allowlist; entity/relation/image đều đúng phạm vi; evidence không điều khiển hệ thống |
| FR-023 | P1 | UI dựa vào capabilities | Feature tắt không dẫn người dùng tới thao tác không dùng được; gọi thẳng API vẫn bị kiểm soát |
| FR-024 | P0 | Embedding hữu hạn, chuẩn hóa và có version | Reject NaN/zero/mismatch; image/text manifests và hashes truy được |

### 6.2 Tài khoản, quản trị và trải nghiệm hiện hành

| ID | Ưu tiên | Yêu cầu | Tiêu chí nghiệm thu |
| --- | --- | --- | --- |
| FR-025 | P0 | Đăng ký/đăng nhập/đăng xuất, session và đổi mật khẩu | Đăng ký role User; password không trả về; logout/đổi mật khẩu thu hồi session theo chính sách |
| FR-026 | P0 | Admin quản lý tài khoản và session | Mọi `/admin/*` cần Admin; last Admin được bảo vệ; thay đổi nhạy cảm có audit |
| FR-027 | P0 | Catalog thư viện, public/chung/grant riêng | Ma trận Guest/User/Admin đúng ở search, media và evidence; thu hồi áp dụng request tiếp theo |
| FR-028 | P0 | Guest text search có quota | Chỉ public đang hoạt động; không gọi chức năng cần account qua endpoint khác để vượt quyền |
| FR-029 | P1 | Khám phá, gợi ý truy vấn và ảnh liên quan | Tất cả nguồn gợi ý/kết quả tuân quyền; cursor/seed hợp lệ; dữ liệu rỗng không crash |
| FR-030 | P1 | Hồ sơ cá nhân và avatar | Chỉ chủ tài khoản sửa hồ sơ; avatar được validate, giới hạn 5 MB; secret không xuất trong response |
| FR-031 | P1 | Lưu/xóa/liệt kê yêu thích | Unique user/image; thao tác lặp an toàn; đọc lại luôn kiểm quyền ảnh hiện tại |
| FR-032 | P1 | Bình luận ảnh | Nội dung 1–2000 ký tự; client_id chống gửi lặp; chỉ chủ bình luận hoặc Admin được xóa theo API |
| FR-033 | P1 | Chat riêng hai người và attachment | Chỉ thành viên truy cập; body tối đa 4000 ký tự; sender/client_id idempotent; ảnh không vào corpus |
| FR-034 | P2 | Giọng nói thành text tìm kiếm | Source có endpoint Gemini; audio tối đa 5 MB; thiếu provider báo unavailable; transcript cho phép người dùng xem/sửa |
| FR-035 | P0 | Sửa metadata, ẩn/khôi phục ảnh | Sửa làm tăng revision và tạo job cần thiết; ảnh chưa đồng bộ receipt không được coi là indexed đúng |
| FR-036 | P0 | Chẩn đoán và audit an toàn | Health tách live/ready/search; audit có actor/action/resource; không log password/token/raw query mặc định |
| FR-037 | P0 | Cài đặt, cấu hình, backup/restore và release | Development/QA/deploy tách biệt; giữ volumes khi down; restore drill trên môi trường độc lập |
| FR-038 | P1 | Đăng nhập nhanh local có kiểm soát | Mặc định tắt; không bật ở production/public origin; tắt vô hiệu session demo theo chính sách |

## 7. Dữ liệu đầu vào và giới hạn

Giá trị sau là mặc định/constraint trong source, không phải capacity đã chứng minh. Cấu hình runtime có thể siết chặt hơn DTO; lấy schema/config của release thực làm contract thực thi.

| Đầu vào hoặc ngân sách | Giá trị hiện hành | Kết quả khi vi phạm |
| --- | --- | --- |
| Text tìm kiếm | Không rỗng, tối đa 2000 ký tự; text encoder tối đa 128 token | Validation/token-limit error, không cắt âm thầm |
| Top-K | DTO 1–100; runtime mặc định tối đa 50; guest mặc định tối đa 50 | Từ chối vượt giới hạn hiệu lực |
| Candidate count | DTO 1–1000 và không nhỏ hơn K | Validation error |
| Ảnh ingestion/query | JPEG/PNG/WebP theo decoder; mặc định 20 MB, 25 triệu pixel, cạnh 10.000 | 413/415/422 tùy lỗi |
| Filter | Dataset, image IDs, media type, tags, city, kích thước, khoảng thời gian | Không nhận field/operator tùy ý; khoảng đảo bị từ chối |
| Mật khẩu | 12–128 ký tự khi tạo/reset theo account policy | Không hợp lệ bị từ chối; không tiết lộ mật khẩu |
| Quota mặc định | Guest 20 search/phút; User 60 search/phút, 20 RAG/ngày, 20 Agent/ngày | Rate-limit; Admin không áp quota User |
| Agent | Tối đa 3 hops, 6 tool calls, 1 replan; deadline mặc định 15 s | Dừng/fallback theo policy, không tiếp tục vô hạn |
| RAG | 5 evidence items, context 2048 token, output 128 token mặc định | Giới hạn context/output; provider lỗi trả lỗi/trạng thái an toàn |

Quota RAG/Agent theo ngày UTC của backend, không theo timezone trình duyệt. Tìm text chạy local; audio gửi tới Gemini và evidence RAG có thể gửi tới provider đã cấu hình. Cần mô tả luồng dữ liệu này trong thông tin sử dụng trước phát hành public.

## 8. Yêu cầu phi chức năng

| ID | Yêu cầu | Tiêu chí và cách xác minh |
| --- | --- | --- |
| NFR-001 | Độ trễ core search | Mục tiêu kế thừa P90 ≤300 ms, P95 ≤500 ms cho workload warm được duyệt; chưa là SLA. Đo full ASGI và client riêng |
| NFR-002 | Độ trễ AI tùy chọn | Mục tiêu trải nghiệm ≤3 s cần benchmark; không đồng nhất với timeout RAG 8 s/Agent 15 s. Đo first/last event và completion |
| NFR-003 | Tính đúng khi lỗi | Input sai, outage, overload, timeout không giả thành empty success; fault-injection kiểm từng nhóm |
| NFR-004 | Tài nguyên hữu hạn | Upload, queue, concurrency, candidates, retries và tool budgets có giới hạn; saturation không tăng RAM vô hạn |
| NFR-005 | Nhất quán và phục hồi | Không publish ready trước receipts; retry không phá identity; kiểm crash giữa các kho và reconcile |
| NFR-006 | Khả năng bảo trì | Module có trách nhiệm rõ, DTO typed, checks lint/type/build phù hợp release; thay adapter không đổi nghiệp vụ quyền |
| NFR-007 | Tái lập triển khai | Lockfiles, migrations, manifests, env separation; clean setup và restore drill có evidence |
| NFR-008 | Capacity có bằng chứng | Mọi QPS/corpus/concurrency claim gắn hardware, cấu hình và error rate; chưa cam kết scale nhiều replica |
| NFR-009 | Cô lập chức năng tùy chọn | RAG/Agent/voice lỗi không bắt buộc làm core search lỗi; xác minh flags off/provider down |
| NFR-010 | Health đúng ý nghĩa | Process sống khác infrastructure ready và search ready; model thiếu phải thể hiện được |
| NFR-011 | Minh bạch ranking | Không trùng ID, có score_type/ranking_version, index/model manifests và warnings |
| NFR-012 | Riêng tư và an toàn dữ liệu | Least privilege theo luồng, không lộ secrets, private media, input validation, quyền sử dụng corpus và retention được chốt |

Chất lượng retrieval phải đo trên nhãn thật. Chưa đặt ngưỡng Recall/nDCG, uptime, RTO/RPO hoặc số người dùng đồng thời khi chưa có corpus/workload và quyết định của chủ sản phẩm.

## 9. Yêu cầu giao diện

- Trang đầu cho Guest thấy khám phá và tìm text; luồng cần account dẫn tới đăng nhập rõ ràng.
- Một ô nhập Việt–Anh; khi khôi phục dấu, hiển thị cách hệ thống hiểu để người dùng sửa.
- Có preview ảnh, thao tác bỏ/thay ảnh, trạng thái đang xử lý và chống response cũ ghi đè truy vấn mới.
- Kết quả có ảnh, metadata, chi tiết và điểm xếp hạng có ý nghĩa rõ; không dùng phần trăm “độ chính xác” thay score.
- Loading, không có kết quả, thư viện chưa có dữ liệu, model chưa sẵn sàng và lỗi kết nối phải phân biệt.
- Admin có khu quản trị riêng với phản hồi lưu/thất bại và trạng thái job; thao tác ẩn/quyền có mô tả tác động.
- Mục tiêu accessibility: label, focus nhìn thấy, thứ tự tab, đóng dialog bằng bàn phím, văn bản thay thế và thông báo lỗi đọc được. Cần kiểm tra thực trước khi công bố mức tuân thủ accessibility.

## 10. Đánh giá và điều kiện nghiệm thu

### 10.1 Bộ dữ liệu và thước đo

Chia bộ query thành text EN, text VI có dấu/không dấu, image, multimodal, nhiều điều kiện và quan hệ có evidence. Mỗi query có tập liên quan hoặc grade được người đánh giá xác nhận. Tách dev/test trước tuning; ghi nguồn/license, snapshot corpus, qrels, index/model/config hash.

Báo cáo Recall@10, nDCG@10 theo nhóm và tổng hợp; ghi cách xử lý unjudged/zero-relevant. So semantic với metadata/hybrid và fusion/rerank bằng cùng corpus. Với RAG, đánh giá correctness, citation support và faithfulness riêng; citation hợp lệ không tự chứng minh câu trả lời đúng.

Hiệu năng phải báo cold/warm, input size, concurrency, số mẫu, p50/p90/p95, throughput, errors/timeouts và tài nguyên. Không bỏ requests lỗi khỏi báo cáo để làm đẹp percentile.

### 10.2 Bộ kiểm tra bắt buộc cho phát hành

| Gate | Điều kiện | Bằng chứng |
| --- | --- | --- |
| AC-01 Core | Text/image chạy qua API và UI với model/index thật | Integration + browser + model manifest |
| AC-02 Quyền | Không vượt ACL qua ID, media, metadata, gợi ý, favorite, comment, evidence/chat | Ma trận quyền positive/negative và thu hồi |
| AC-03 Jobs | Ingest, retry, crash, revision, verify/activate đúng | Item receipts, recovery tests, consistency report |
| AC-04 An toàn | Session/CSRF/quota/upload/secrets và last Admin đúng | Security tests và kiểm tra cấu hình release |
| AC-05 Vận hành | Setup mới, down/up giữ dữ liệu, backup/restore độc lập | Logs/artifacts có phiên bản |
| AC-06 AI tùy chọn | Provider off/timeout, thiếu evidence và budgets có xử lý | Fault tests + đánh giá người dùng nếu claim quality |
| AC-07 Chất lượng/hiệu năng | Gate số được chốt trước benchmark | Qrels và báo cáo workload; chưa chốt thì ghi chưa đạt điều kiện công bố |

### 10.3 Truy vết yêu cầu sang thiết kế và kiểm thử

| Nhóm FR | SAD | Nơi kiểm chứng hiện có hoặc cần mở rộng |
| --- | --- | --- |
| 001–003, 013–018, 024, 029 | §5, §7 | `test_search.py`, `test_advanced_search.py`, `test_real_search.py`, `test_metadata_search.py`, bilingual checks |
| 004–008, 035 | §6, §7 | `test_indexing.py`, reliability tests, consistency verification |
| 009–010, 023 | §4, §8, §10 | API/schema tests, frontend unit và QA browser |
| 011–012 | §12 | Evaluation tests/harness, real benchmark có nhãn |
| 019–022, 034 | §9 | `test_real_rag.py`, `test_real_agent.py`; voice cần kiểm chứng provider riêng |
| 025–028, 036, 038 | §10 | `test_accounts.py`, `test_guest_search.py`, `test_quick_login.py` |
| 030–033 | §8, §10 | `test_profiles.py`, `test_comments.py`, `test_chat.py` và frontend tests |
| 037 | §11–12 | QA isolated, deployment check và backup/restore drill |

Các tên test là điểm truy cập trong [backend/tests](../../backend/tests/), không phải tuyên bố pass. Các nguồn lịch sử xem [báo cáo bàn giao](../bao_cao_nghiem_thu/FINAL_HANDOVER.md).

## 11. Phụ thuộc, rủi ro và quyết định còn mở

| Vấn đề | Tác động | Hướng xử lý/điều kiện chốt |
| --- | --- | --- |
| Chưa có corpus/nhãn đại diện | Không suy ra chất lượng từ demo | Chủ sản phẩm + evaluator chốt dữ liệu, nhóm query, qrels và ngưỡng |
| CPU inference và nhiều process model | RAM/latency tăng khi concurrency tăng | Benchmark trên máy đích trước khi tăng replica hoặc hứa SLA |
| Quyền dùng ảnh/evidence/audio | Rủi ro chia sẻ hoặc gửi provider ngoài ý muốn | Xác nhận license, notice, egress và retention trước public |
| Provider bên ngoài | Chi phí, timeout, chất lượng thay đổi | Optional, caps, safe fallback và cấu hình server-side |
| Nhiều kho dữ liệu | Partial failure và payload stale | Receipts, PG recheck, jobs/reconciliation và restore drill |
| Multi-replica index activation | Runtime giữa replicas có thể lệch generation | Giữ một API process hiện hành; thiết kế rollout/reload trước scale |
| Nội dung bình luận/chat | Spam, report, retention chưa thành sản phẩm đầy đủ | Chốt quy trình xử lý abuse, lưu/xóa dữ liệu và quyền hỗ trợ |
| Public hosting | Local test chưa chứng minh bảo mật/capacity public | HTTPS, proxy trust, firewall, secrets và kiểm thử trên môi trường đích |

## 12. Quản lý thay đổi và phê duyệt

Mỗi thay đổi cần nêu FR/NFR bị ảnh hưởng, cập nhật SAD/API/schema nếu cần và chỉ ra evidence. Không đổi ý nghĩa ID cũ mà không ghi mapping. Chốt release dựa trên commit, cấu hình, model/data manifest và test run cùng phiên bản.

Các mục cần chủ sản phẩm xác nhận: persona/corpus đích, ngưỡng quality, workload/SLO, retention, quyền gửi dữ liệu ra provider và phạm vi public deployment. Trong khi chưa xác nhận, dùng mặc định hiện hành và giữ rõ các mục chưa kiểm chứng; không xem bản PRD này là phê duyệt kinh doanh tự động.
