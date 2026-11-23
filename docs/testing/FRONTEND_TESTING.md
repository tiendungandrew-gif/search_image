# Kiểm thử frontend — Phase 10

## Phân loại bằng chứng

`IMPLEMENTED`: có source. `TESTED_WITH_MOCKS`: transport/capability/lỗi được điều khiển bằng fixtures. `VERIFIED_WITH_REAL_BACKEND`: gọi FastAPI thực. `VERIFIED_WITH_REAL_DATA`: dùng ảnh/metadata/vector/quan hệ có nguồn thực. `NOT_VERIFIED`: chưa có bằng chứng tương ứng. Không cộng điểm relevance hay faithfulness từ test chức năng.

## Kiểm tra tĩnh và unit

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm test
npm run build
```

Ở workspace nghiệm thu, Node nằm trong `.tools/node/bin`; có thể thêm đường dẫn này vào PATH. Chỉ thêm `@axe-core/playwright` 4.14.0 ở dev dependency, lockfile pin phiên bản; không thêm runtime state/router/UI framework.

40 frontend unit tests: auth/error/status mapping, JSON malformed, timeout/cancel, multipart đúng boundary/options; component health/readiness/preview; image MIME/empty/size, drop nhiều file, blob replacement/unmount; deferred authenticated image fetch và URL không an toàn; superseded/cancel/token-change race; RAG retry/cancel/late result/unknown citation/terminal SSE/incomplete stream; Agent public progress, chunk UTF-8, unsafe URL, partial quota và fatal error. Unit tests dùng mocks, không coi fake bytes của upload test là ảnh decode thật.

Backend suite **211 tests** gồm 199 unit và 12 integration, dùng PostgreSQL/Qdrant/MinIO/model thật với các cờ opt-in. Bổ sung 11 unit cho workspace state, auth và allowlisted evaluation reader. Integration suite trước đó tiếp tục kiểm tra migration, ingestion, actual search, RAG/Agent và dataset isolation. [Log backend](../verification/phase10/backend_tests.txt) ghi rõ các warning Qdrant HTTP trong mạng nội bộ dev; không có failure chưa xử lý.

## Browser/E2E

Khởi động stack chính và fixture rỗng theo [FRONTEND_EMPTY_DATASET_MODE.md](../features/FRONTEND_EMPTY_DATASET_MODE.md), sau đó:

```bash
cd frontend
npx playwright install chromium firefox webkit
cd ..
RUN_RAG_E2E=1 RUN_AGENT_E2E=1 RUN_AGENT_PUBLIC_DATA=1 \
  backend/.venv/bin/python scripts/checks/check_frontend.py
RUN_FRONTEND_PERF=1 backend/.venv/bin/python scripts/checks/check_frontend.py \
  phase10-performance.spec.ts --project=desktop --project=mobile
```

Runner chỉ lấy read token từ `.env` cho child process, không log key. Trace tắt vì có thể chứa Authorization header. App không tự đọc `.env` hoặc lưu token. Test AI thật là opt-in, không retry hoặc tự tăng tải provider khi quota.

Ma trận chức năng có 74 ca: **72 pass**, **2 performance skip có chủ đích**, **0 fail/flaky**; hai ca performance chạy riêng và đều pass. Trong 72 ca có 14 ca mock/hybrid rõ tên: 10 ca empty-refresh/backend-unavailable, 2 Agent empty SSE, 2 Agent quota SSE giữ real image IDs. Các ca còn lại gồm API/data thật và 2 trang annotation dùng artifact thật. Không gộp mock branch với kiểm chứng provider thật. Báo cáo raw ở [browser_final.json](../verification/phase10/browser_final.json).

| Project | Engine / viewport | Phạm vi |
|---|---|---|
| desktop | Chromium, 1440×1000 | Toàn bộ core, image/multimodal/multi-intent, Agent, RAG, detail, filters, dashboard, accessibility |
| mobile | Chromium mobile emulation, 390×844 | Cùng luồng desktop, upload/overflow/lazy scroll |
| tablet | Chromium touch emulation, 820×1180 | Status, detail/keyboard, filters, dashboard, axe, unavailable/refresh |
| firefox | Firefox, 1366×900 | Core text/image/multimodal/multi-intent, detail, filters, dashboard, axe và controlled errors |
| webkit | WebKit mobile emulation, 390×844 | Cùng nhóm core/Phase10 như Firefox |
| empty-desktop/mobile | Chromium, backend rỗng riêng | DB thực 0 ảnh, collection 0 điểm, bucket 0 object, features tắt và benchmark empty |

Firefox/WebKit là binary Playwright trên Linux. Chromium không đồng nghĩa đã chạy Google Chrome hoặc Microsoft Edge bản phát hành; WebKit Linux emulation không thay kiểm tra Safari/iPhone/iPad thật. Thiết bị Android/iOS và screen reader thực còn `NOT_VERIFIED`.

### Môi trường WebKit trong IDE Snap

Máy nghiệm thu thiếu libevent/libavif và dependencies libgav1/libyuv. Đã tải package Ubuntu vào `.cache/browser-libs`, extract local và liên kết thư viện trong cache WebKit; không cài global. Môi trường IDE Snap còn inject GIO module/libpthread không tương thích; runner chỉ lọc các biến đường dẫn Snap ở child process. Có thể dùng Playwright install-deps theo quyền quản trị của môi trường CI khác. Không bỏ qua test lỗi bằng cách tắt project WebKit. Các failure ban đầu được lưu trong `browser_initial.json`; final matrix đã pass sau sửa môi trường và các lỗi thật tìm được.

## Accessibility và visual review

Axe chạy các tag WCAG 2 A/AA, 2.1 AA, 2.2 AA ở search sáng, dialog, search tối, evaluation tối trên 5 viewport/engine project; thêm 2 màn hình empty thật. Không có violation tự động trong các scope này. Dialog kiểm tra focus/Tab/Escape/arrow/return focus, các workflow kiểm tra không tràn ngang, ảnh private có naturalWidth >0. Đã xem screenshot gallery desktop và mobile/WebKit trong quá trình nghiệm thu. Kết quả là kiểm tra tự động có giới hạn, không phải chứng nhận toàn bộ WCAG.

Manual QA còn lại: NVDA/VoiceOver, touch/IME trên thiết bị thật, màn hình phóng đại và các trường hợp tương phản với nội dung mới. Nhãn relevance/faithfulness do người đánh giá tiếp tục chờ theo quyết định trước của người dùng; không tự tạo nhãn để đóng acceptance.
