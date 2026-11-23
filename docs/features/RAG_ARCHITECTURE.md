# Kiến trúc RAG tùy chọn — Prompt08

Cập nhật06/11/2026: đã có corpus510 ảnh/500 captions; phần mềm đạt152 backend tests,13 frontend unit và16 browser cases. Human quality review chờ xác nhận theo lựa chọn của người dùng. [Báo cáo hiện hành](../archive/PHASE08_COMPLETION_REPORT.md); các số liệu05/11 bên dưới là lịch sử. Không tự chuyển Prompt09.

React tìm kiếm bình thường → SearchService hiện hành → PostgreSQL/Qdrant/MinIO → kết quả ảnh. Người dùng chủ động yêu cầu giải thích; không có LLM call trong Fast Search.

RAG chạy trong cùng modular monolith: RagService → SearchService hoặc danh sách IDs đã truy xuất → EvidenceRetriever → ContextBuilder → Generator → ChatProvider → CitationValidator → RagResponse. Không thêm vector engine, queue, microservice, agent hoặc multi-hop. Với Explain Existing, client chỉ gửi IDs/index/question; mọi metadata được đọc lại từ kho, không nhận caption/score do client cung cấp.

## Sơ đồ thành phần

```mermaid
flowchart LR
    UI[React: tìm ảnh] --> Search[SearchService: CLIP / advanced]
    UI --> RAG[RagService: giải thích tùy chọn]
    RAG --> Search
    RAG --> Evidence[EvidenceRetriever: current ready receipts]
    Evidence --> PG[(PostgreSQL)]
    Evidence --> Q[(Qdrant: active model/index)]
    Evidence --> M[(MinIO: original stat)]
    Evidence --> Context[ContextBuilder: bounded facts + provenance]
    Context --> Gen[Generator: bounded HTTP streaming]
    Gen --> LLM[Gemini / OpenAI / compatible endpoint]
    Gen --> Validate[CitationValidator: closed fact IDs]
    Validate --> Response[RagResponse + ảnh đã truy xuất]
```

Core/model/index/generation giữ nguyên. Generator khởi tạo connection pool riêng ở lifespan, không tải local LLM. Config/provider lỗi làm RAG unavailable; search vẫn chạy. Remote model không nhận ảnh nhị phân, credentials của data services, storage keys hoặc lịch sử người dùng. [Triển khai](RAG_IMPLEMENTATION.md), [API](RAG_API.md), [prompt](RAG_PROMPT_DESIGN.md), [nghiệm thu](../archive/PHASE08_TEST_REPORT.md).

## Sequence giải thích kết quả

```mermaid
sequenceDiagram
    actor User
    participant UI as React
    participant API as RagService
    participant Stores as PG Qdrant MinIO
    participant LLM as Gemini
    User->>UI: Yêu cầu giải thích ảnh đã tìm
    UI->>API: image_ids, expected_index_id, question
    API->>Stores: Batch current eligibility và provenance
    Stores-->>API: Metadata có thật hoặc missing
    alt Có facts hữu ích và provider được bật
        API->>LLM: Bounded context và selection prompt
        LLM-->>API: Fact IDs theo streaming
        API->>API: Validate IDs và dựng exact quotes
    else Thiếu evidence hoặc RAG unavailable
        API->>API: Trạng thái thiếu bằng chứng hoặc unavailable
    end
    API-->>UI: Ảnh và RagResponse
    UI-->>User: Hiển thị câu đã validate, links tới ảnh
```
