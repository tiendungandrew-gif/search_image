# Chuẩn hóa repository — 24/11/2026

## Kết quả

- Bỏ theo dõi `datasets/approved_csv_v1/` (48.294 file, khoảng 279 MiB nội dung tại workspace), giữ nguyên toàn bộ file local. Thêm Git/Docker ignore và catalog tổng hợp nhỏ.
- Chuyển 5 tài liệu baseline/spec sang `docs/architecture/archive/`; sửa các liên kết tài liệu đang duy trì. Bằng chứng gốc và báo cáo nghiệm thu lịch sử giữ nguyên.
- Gom 10 thư mục browser suites và 11 configs tại `frontend/tests/e2e/`. Dùng shared defaults; giữ entrypoint `frontend/playwright.config.ts`, project names, URLs và output paths; cập nhật fixtures, TypeScript includes, scripts và CI.
- Lưu source helper bulk import ở `scripts/archive/approved_csv_v1/` (chuẩn hóa imports/format, giữ thứ tự thiết lập env và monkey patches); bản local gốc không đổi.
- File root tên sai chứa terminal diff-stat được giữ nguyên bytes trong `.cache/restructure/accidental-git-stat.txt` rồi bỏ khỏi source.

## Kiểm chứng

- Đối chiếu danh sách dataset từ HEAD: 48.294/48.294 file vẫn có trên đĩa; không còn file nào của corpus trong Git index.
- So sánh Playwright discovery trước/sau: cả 11 configs giữ nguyên tests/projects (130 test instances tổng cộng, không phải 130 kịch bản độc lập).
- Frontend typecheck và ESLint đạt; browser mock 4/4 đạt. Browser mock cần localhost nên chạy ngoài sandbox mạng hạn chế; chỉ dùng mock API và Vite local.
- Ruff cho scripts, format các Python files đã đổi, compileall, Markdown link regressions và git diff whitespace check đạt.
- Chưa chạy real-model benchmark, live acceptance hoặc deployment. Không sửa database, active index hay volumes.

Chi tiết máy đọc được ở [summary.json](summary.json). Các log tạm trước/sau ở `/tmp/synlens-restructure/`; credential placeholder dùng cho discovery không phải tài khoản thực và không được lưu vào report.

## Git và dữ liệu

`git rm --cached` tạo staged deletions cho corpus và file terminal nhầm. Các thay đổi source/docs cần `git add` trước commit. Không commit/push và không rewrite history trong tác vụ này; dữ liệu ở commit cũ vẫn còn trong lịch sử Git.

Clone mới không chứa corpus: cần nguồn/backup được cấp quyền. Xem [quy tắc dữ liệu](../../../datasets/README.md) và [cấu trúc mới](../../REPOSITORY_STRUCTURE.md).
