# Nghiệm thu dữ liệu rỗng — Phase11

> Tài liệu lịch sử theo phase; lệnh trong nội dung giữ tên đường dẫn cũ. Hướng dẫn hiện hành tại [danh mục tài liệu](../README.md) và [scripts](../../scripts/README.md).

Môi trường QA tách riêng hỗ trợ khởi động không có production dataset, không captions/knowledge/benchmark/provider. Không xóa dữ liệu hệ thống hiện có để thực hiện test này.

## Trình tự

1. Sinh `.env.qa` riêng; dựng PostgreSQL/Qdrant/MinIO/API/frontend bằng `scripts/qa.py up`.
2. Migrate database mới; xác nhận live/ready200 dù chưa có dataset.
3. API workspace báo `empty_dataset`, images0/indexed0, không active index; vectors null khi chưa có runtime để đếm. Null không được coi là lỗi hay số đo0 giả.
4. Frontend hiển thị “Chưa có dữ liệu ảnh”, vô hiệu hóa search chưa sẵn sàng, navigation/health vẫn dùng được; không render ảnh hardcoded.
5. Evaluation chưa cấu hình/không có artifacts không render bảng số liệu giả. RAG/Agent tắt được thể hiện bằng capabilities.
6. Import6 ảnh tổng hợp và knowledge hư cấu trong namespace QA bằng seed; chạy CLIP thật, verify receipts và activate generation1; UI chuyển sang ready.
7. Thử ngắt/restart dịch vụ; dataset/index không thay đổi. Sau đó dọn riêng QA và dựng lại để kiểm tra deployment hoàn toàn rỗng lần cuối.

## Hành vi API

| Trạng thái | Kết quả mong đợi/đã kiểm tra |
| --- | --- |
| Không có dataset, search disabled | POST hợp lệ trả409 FEATURE_DISABLED; process không chết |
| Search bật nhưng chưa có active compatible index | NOT_READY/INDEX_NOT_READY có envelope; unit và fixture tests |
| Có dataset nhưng filter không khớp | 200 với results rỗng; không trình bày là dataset rỗng |
| Dependency chết | unavailable/503; không biến unknown thành empty_dataset |
| Thiếu RAG evidence | insufficient_evidence, không bịa generation/citation |
| Thiếu Agent entity/relation | insufficient_evidence, không bịa ảnh/quan hệ |
| Không benchmark/qrels | Empty/not_available UI; quality chưa xác nhận |

## Bằng chứng và giới hạn

Empty browser4 ca pass trên3 engines; indexed browser8 ca pass sau chuyển trạng thái. Integration fixture tự tạo DB rỗng kiểm tra health/auth/API; CLIP integration tái hiện đầy đủ empty→indexed→search. [runs](../verification/phase11/runs) và `verification/phase11/empty_api.json` ghi snapshot cuối.

Ảnh là fixture tổng hợp có6 mẫu, không phải import dataset thực tự động. Các tests không yêu cầu internet dataset hoặc Gemini key. Việc import tương lai dùng API/CLI/manifest sẵn có, có nguồn/license, dimension/manifest tương thích, consistency verification trước active-index switch. Xem [IMAGE_INDEXING](../features/IMAGE_INDEXING.md), [DATASET_AND_GROUND_TRUTH](../research/DATASET_AND_GROUND_TRUTH.md).

Human quality labels vẫn chờ theo lựa chọn của người dùng. Dataset rỗng không chặn milestone phần mềm này, nhưng không cho phép tuyên bố retrieval quality đã đạt mục tiêu.
