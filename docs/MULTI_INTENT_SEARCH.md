# Multi-intent Search — Prompt 06

Core fast search Prompt05 được giữ cho explicit text/image hoặc auto single-intent. Query classifier/decomposer trong `backend/app/services/query/` dùng deterministic bounded rules, không gọi LLM. Đây là parser theo mẫu, chưa phải bộ hiểu ngôn ngữ tổng quát.

## Phân loại và fallback

QueryAnalysis gồm original_query, query_type, language heuristic(en/vi/und), typed constraints AST, logical_operator, retrieval_strategy, requires_agent, uncertain và limitations. Các loại: SINGLE_INTENT, MULTI_INTENT, IMAGE_SIMILARITY, TEXT_IMAGE, UNSUPPORTED_RELATIONAL_QUERY. Original query luôn giữ nguyên làm whole-query signal, chỉ normalize NFC/whitespace qua input schema, không xóa dấu tiếng Việt.

Mẫu city where/city in which/where…is located và thành phố nơi/mà/nơi…tọa lạc/nằm bị từ chối409 UNSUPPORTED_RELATIONAL_QUERY. Hệ thống không đoán city, tự gọi agent hoặc trả bằng chứng multi-hop giả. Nhận diện này có giới hạn; không bao phủ mọi relational paraphrase.

Mẫu mơ hồ, dangling operator, unmatched grouping hoặc quoted/compound-color query như “black and white cat” giữ toàn bộ query trên single-vector fallback và warning QUERY_ANALYSIS_UNCERTAIN. Explicit AST không bị mất do router mơ hồ. Khi multi-intent bị tắt, auto text không có explicit constraints/rerank/strict yêu cầu sẽ fallback và cảnh báo; explicit advanced mode trả409. Simple queries không fan-out hoặc tự bật reranker.

## Grammar và giới hạn

- `and`/`và`, `or`/`hoặc`, parentheses; AND ưu tiên hơn OR. `(red motorcycle AND person wearing helmet) OR blue bicycle` giữ nhóm. Giới hạn8 leaves,2 group levels,4 vector channels; overflow trả422, không silent truncate constraints.
- Comma list chỉ mở khi có conjunction rõ ràng; không tách mọi dấu phẩy. Prefix Find images containing/Tìm ảnh có được bỏ khỏi **leaf phrases**, original vẫn giữ.
- Object/attribute/color/scene/action giữ thành nguyên cụm. “a person wearing a red helmet” không bị tách thành person/red/helmet rời nhau. Có/màu/đang/trong/gần/giống không tự tạo Boolean operator. Spatial/action/attribute relationships chỉ là semantic phrase, không được verify bằng parser.
- `preferably`, `optionally`, `ưu tiên`, `nếu có thể` ở đầu leaf đánh dấu required=false. `without`/`không có` tạo negated semantic leaf; low similarity không thành bằng chứng absence.
- Metadata syntax có chủ đích: `tag:cat`, `city:Hanoi`, `source:scikit-image-v0.25.2`. Không tự suy city/category/license từ natural text. Dùng explicit metadata AST khi muốn kiểm soát chính xác filters.
- English/Vietnamese smoke cases tách language/operator trong benchmark. Heuristics vẫn có thể parse sai idioms hoặc scope; chưa có benchmark parser accuracy hay multilingual retrieval labels.

## Constraint AST và evidence

Group `{op:and|or,clauses:[...]}`; leaf có unique id≤64, kind semantic/metadata, required, negated và weight(0,10]. Hai ID whole/image dành cho nhánh nội bộ, bị reject khi dùng cho leaf để không ghi đè whole-query/image signal. Semantic leaf có text; metadata leaf có nonempty filter theo schema hiện có, không vừa text vừa filter. Unicode/control/shape/count/depth được validate tại boundary; metadata expression quá dài trả422. Các leaf IDs dùng trong response/evaluation để liên kết human judgments.

Canonical assessments giữ satisfied/violated/unknown; compatibility constraint_evidence dùng VERIFIED_MATCH/VERIFIED_MISMATCH/UNKNOWN. Metadata numeric dimensions/media/source/city/time chỉ được đánh giá theo giá trị có thật. Missing metadata là UNKNOWN. Tags chưa có exhaustive annotation flag: tag hiện diện chứng minh membership; thiếu tag không chứng minh visual absence, nên là UNKNOWN trong AST evidence. Top-level hard filters vẫn dùng positive-match policy Prompt05: missing field bị loại.

Required AND: violated nếu có required child violated; unknown nếu không violated nhưng còn unknown. Required OR: satisfied nếu có required child satisfied; unknown nếu không satisfied nhưng còn unknown. Optional leaves được bỏ khỏi hard-gate projection để không dùng optional OR branch bypass mandatory condition. Negation đảo satisfied/violated, giữ nguyên unknown. Có thể verify metadata exclusion trên field có dữ liệu; semantic negation vẫn unknown.

Best effort(default): loại required Boolean VIOLATED, giữ UNKNOWN và cảnh báo. Strict require_verified: metadata UNKNOWN bị loại; required semantic leaf trả409 VERIFIER_UNAVAILABLE vì chưa có visual verifier. Không tự nới strict khi reranker bị lỗi. Optional leaves chỉ ảnh hưởng scoring; không chặn kết quả.

## Candidate generation và experiments

Whole-query luôn được retrieve. Per-constraint retrieval chỉ lấy semantic positive leaves trong remaining channel budget; negative leaves vẫn encode để assessment/soft scoring nhưng không tìm “people” rồi coi là absence. Candidate union/fusion, PG authoritative eligibility và metadata logic, optional reranker, private object checks và finalK dùng shared service với Prompt05. Candidate cap có thể làm thiếu eligible images; không bù fake results.

E1 explicit text baseline; E2 whole+per-clause union rồi rescore whole cosine; E3 RRF/weighted-score fusion; E4 fusion+constraint rerank; E5 paired fusion với method comparison. E2 không dùng RRF làm final relevance score; RRF chỉ giới hạn preliminary union pool, vì bounded candidate budget vẫn cần tie/order policy. Xem [RERANKING_DESIGN](RERANKING_DESIGN.md), [API](ADVANCED_SEARCH_API.md), [test report](ADVANCED_SEARCH_TEST_REPORT.md).
