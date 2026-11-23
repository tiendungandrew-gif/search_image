# Hiệu năng frontend — Phase 10

## Cách đo

Raw samples: [desktop](../verification/phase10/performance_desktop.json), [mobile](../verification/phase10/performance_mobile.json); [log chạy](../verification/phase10/performance_run.txt). Mỗi viewport có 2 request warmup và 20 request đo, tuần tự, Top-K 10, bốn truy vấn kiểm thử coffee/cat/beach/bicycle, backend thật trên corpus 513 ảnh. Không gọi LLM. Desktop 1440×1000; mobile emulation 390×844; Chromium headless, Vite development, CPU/local network, không throttle mạng/CPU. Không có phép đo trước thay đổi để suy ra phần trăm cải thiện.

Các khoảng thời gian có điểm bắt đầu khác nhau:

- `api_ms`: từ controller thực thi submit đến typed response hợp lệ; gồm HTTP, backend, parse/validate, không gồm upload preview trước đó.
- `first_card_ms`: từ cùng submit tới callback sau hai requestAnimationFrame của gallery. Đây là proxy cho commit/paint của **thẻ kết quả**, không phải tất cả ảnh đã tải hoặc một phép đo pixel paint của trình duyệt.
- `post_api_frame_ms`: khoảng từ response đến callback trên, gồm scheduling/commit/frame; không được gọi toàn bộ là React CPU time.
- `react_ms`: `React.Profiler.actualDuration` của gallery khi mount, đo trong development build.
- `image_fetch_ms`: từ khi ảnh vào vùng quan sát và bắt đầu authenticated fetch đến lúc blob sẵn sàng.
- `image_fetch_decode_ms`: từ cùng thời điểm đến `img.onload`; gồm fetch và decode/load, không tách decode bằng cách trừ các percentile.
- `browser_observed_image_ms`: thời gian Playwright quan sát được ảnh đầu đã load, tính trước thao tác click; gồm automation, cuộn và polling. Không dùng làm API latency.
- `server_ms`: `latency.processing_ms` từ backend response, độc lập với các số đo trên.

## Kết quả đo thực tế

Đơn vị ms; P90/P95 nội suy tuyến tính trên 20 mẫu thành công mỗi viewport.

| Metric | Desktop P90 | Desktop P95 | Mobile P90 | Mobile P95 |
|---|---:|---:|---:|---:|
| API client | 141.78 | 153.48 | 134.68 | 136.50 |
| Thẻ kết quả, proxy sau commit/frame | 216.59 | 230.26 | 216.68 | 217.87 |
| Từ response tới frame callback | 78.77 | 82.19 | 85.97 | 86.65 |
| React gallery render | 13.03 | 13.41 | 13.42 | 13.64 |
| Fetch ảnh đầu sau intersection | 71.54 | 72.91 | 36.08 | 43.68 |
| Fetch + load/decode ảnh đầu | 92.70 | 94.76 | 58.32 | 64.98 |
| Playwright quan sát ảnh đầu từ click | 481.68 | 493.22 | 387.90 | 389.97 |
| Backend processing cùng mẫu | 130.91 | 141.11 | 124.26 | 124.79 |

Test Top-K 50: chỉ **8/50** media request ở desktop và **1/50** ở mobile trong cửa sổ quan sát ban đầu 350 ms. Không assert mọi viewport luôn có cùng số request; invariant là không eager fetch cả 50 ảnh. Khi cuộn, browser mới yêu cầu thêm ảnh. Không chuyển việc tải thumbnail sang public MinIO.

Loading có skeleton, status, nút hủy và stale-response protection được kiểm tra chức năng. Chưa đo riêng thời gian paint đầu tiên của skeleton, INP/LCP trên mạng di động thật, hay hiệu năng thiết bị vật lý. Không suy ra các metric này từ thời gian backend.

## Bundle và lựa chọn triển khai

Production build: entry JS khoảng **272.42 kB / 85.32 kB gzip**, CSS **22.23 kB / 5.79 kB gzip** ở bản nghiệm thu; bốn lazy chunks cho dialog/evaluation/Agent/RAG khoảng 3–3.6 kB mỗi chunk. Log build và artifact size ở bộ bằng chứng Phase10. React.Profiler timing ở trên không đại diện production profiling build.

Ảnh có aspect ratio cố định, lazy network IntersectionObserver, async decode, timeout/MIME/size guard, blob cleanup và placeholder/fallback. Gallery tối đa 50 thẻ nên chưa cần virtualization. Không gọi embedding/AI mỗi keystroke. Dataset polling 30 s không chạy LLM, chỉ chạy khi tab hiện; thay đổi query không làm poll thêm.

`variant=thumbnail` hiện có thể trả original bytes theo contract backend. Đây là giới hạn băng thông còn lại, không tuyên bố đã có pipeline thumbnail derivative. Không thêm cache private media bền vững để bù cho giới hạn này.

## So với mục tiêu dự án

P90 ≤300 ms, P95 ≤500 ms của Fast Search là mục tiêu **backend**; TTLast ≤3 s của augmented generation là ngân sách riêng. Số đo frontend 20 mẫu ở môi trường local không chứng minh SLA tải/concurrency, không thay báo cáo benchmark Phase07/09 và không xác nhận chất lượng Recall@10. Kiểm thử tải frontend production, thiết bị thật và Web Vitals được bàn giao cho phạm vi kiểm tra sâu Phase11 khi có yêu cầu.
