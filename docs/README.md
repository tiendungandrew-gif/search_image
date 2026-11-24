# Tài liệu dự án

Cập nhật 08/11/2026: [Tài khoản và phân quyền](operations/ACCOUNTS.md) — Admin/User, quyền theo thư viện và khu quản trị riêng.
Cập nhật 10/11/2026: [Giao diện khám phá ảnh](features/USER_INTERFACE.md) — trang chủ có ảnh thật, lưới lớn/gọn và ba cách tìm, hỗ trợ bàn phím/điện thoại.
Bắt đầu từ [bàn giao hiện tại](bao_cao_nghiem_thu/FINAL_HANDOVER.md), [hướng dẫn chạy](operations/DEPLOYMENT_GUIDE.md) hoặc [cấu trúc repository](REPOSITORY_STRUCTURE.md).

| Thư mục | Nội dung |
| --- | --- |
| [architecture/](architecture/) | Yêu cầu, PRD/SAD, database/API, quyết định và kiến trúc |
| [operations/](operations/) | Setup, deploy, cấu hình, dataset/model, backup/recovery, vận hành và bảo mật |
| [features/](features/) | Search/indexing/multimodal, RAG, Agent và frontend |
| [research/](research/) | Phương pháp đánh giá, datasets, benchmark, model comparison và các giới hạn |
| [testing/](testing/) | Chiến lược/lớp kiểm thử và browser workflow |
| [bao_cao_nghiem_thu/](bao_cao_nghiem_thu/) | Toàn bộ báo cáo nghiệm thu theo Phase, kiểm toán và đánh giá |
| [verification/](verification/) | Bằng chứng gốc, commands, JSON/logs và snapshots thực thi |
| [diagrams/](diagrams/) | Mermaid diagrams |
| [adr/](adr/) | Architecture decision records |

Tài liệu hiện hành: [PRD](architecture/PRD.md), [SAD](architecture/SAD.md), [API](architecture/API_SPECIFICATION.md), [database](architecture/DATABASE_DESIGN.md). Baseline/spec qua các phase được giữ tại [kho thiết kế lịch sử](architecture/archive/README.md); `FINAL_SYSTEM_ARCHITECTURE` là snapshot bàn giao, không thay SAD hiện hành.

## Điểm vào thường dùng

- [PRD — yêu cầu sản phẩm](architecture/PRD.md) và [SAD — thiết kế kiến trúc](architecture/SAD.md): bản 2.0 đối chiếu source, có tiêu chí nghiệm thu và truy vết yêu cầu.

- [Chạy development trên Linux](operations/SETUP.md), [workflow phát triển](operations/DEVELOPMENT.md).
- [Triển khai](operations/DEPLOYMENT_GUIDE.md), [cấu hình](operations/CONFIGURATION_REFERENCE.md), [thêm ảnh](operations/DATASET_IMPORT_GUIDE.md).
- [Kiến trúc cuối](architecture/FINAL_SYSTEM_ARCHITECTURE.md), [API](architecture/API_SPECIFICATION.md), [database](architecture/DATABASE_DESIGN.md).
- [Kiểm thử](operations/TESTING_AND_VERIFICATION.md), [phương pháp đánh giá](research/EVALUATION_METHODOLOGY.md).
- [Báo cáo Phase12 A–T](bao_cao_nghiem_thu/FINAL_PROJECT_REPORT.md) và [bằng chứng tái cấu trúc](verification/restructure/).

Raw artifacts giữ nguyên đường dẫn/nội dung để đối chiếu lịch sử. References bên trong JSON/logs/archives phản ánh layout ở thời điểm chạy; dùng các hướng dẫn hiện hành ở trên cho lệnh vận hành mới.
