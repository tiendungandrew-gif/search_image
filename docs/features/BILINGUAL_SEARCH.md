# Tìm kiếm ảnh bằng tiếng Việt và tiếng Anh

Cùng một ô nhập hỗ trợ hai ngôn ngữ tự động. Toàn bộ văn bản đi qua
`sentence-transformers/clip-ViT-B-32-multilingual-v1`, revision
`58edf8cada9e398793dca955574a48cbb7f18be2`. Không có bộ chọn ngôn ngữ,
không cần dịch bằng dịch vụ ngoài, không dùng danh sách từ khóa để giả lập tiếng Việt.
Text trong truy vấn kết hợp ảnh cũng dùng cùng encoder này.

Tiếng Việt không dấu được tự khôi phục theo ngữ cảnh trước khi encode, ví dụ
`con meo` → `con mèo`, `con cho` → `con chó`, `bai bien` → `bãi biển`.
Giao diện giữ nguyên ô nhập và hiển thị câu hệ thống đã hiểu phía trên ảnh.
Không yêu cầu người dùng chọn ngôn ngữ hoặc tự thêm dấu.

Với tên có ít nhất ba từ đã khớp trong thư viện, hệ thống tra cứu metadata trước,
hỗ trợ không dấu và giữ phân biệt dấu khi đã nhập, thay vì đoán lại dấu hoặc phụ thuộc vào nhận diện hình
ảnh. Ví dụ `pho 10 ly quoc su` khớp `Phở 10 Lý Quốc Sư Hà Nội`. Caption/mô tả cũng
tham gia tìm kiếm text; các bộ lọc, quyền thư viện và trạng thái ẩn vẫn được áp dụng.

Accent restorer dùng [Claví](https://huggingface.co/ai4irl/clavi-accent-restoration),
revision `940c6d81842f88c0ca70b166a3031e0dd54e5dec` (Apache-2.0), BiLSTM ký tự
3 lớp, khoảng 63 MB. Inference viết trong repo, chỉ tải config/vocab/safetensors,
kiểm tra SHA256 cố định trước khi nạp; không thực thi Python từ model repository.
[py3langid 0.4.0](https://github.com/adbar/py3langid) (BSD-3-Clause) và vocab CLIP
giúp giữ nguyên câu tiếng Anh. Cả hai model đều chạy local; không gửi truy vấn
đến dịch vụ dịch hoặc sửa chính tả ngoài.

Model là DistilBERT → mean pooling có attention mask → Dense 768→512 → L2.
Nó được distill để khớp không gian ảnh CLIP ViT-B/32, theo
[model card chính thức](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1)
và [tài liệu Sentence Transformers](https://sbert.net/docs/sentence_transformer/pretrained_models.html).
Image encoder, fingerprint và index CLIP hiện có được giữ nguyên. Không dùng chung
với image encoder khác chỉ vì cùng số chiều. Text model có manifest/hash riêng,
trả ở `effective_settings.text_encoder_manifest_sha256` và search trace.

## Chuẩn bị model

Model chỉ tải khi chạy CLI, cố định revision và chỉ dùng safetensors; backend
kiểm tra receipt/file SHA256 và kiến trúc trước khi load local. Không bật
`trust_remote_code`. Model thiếu/hỏng thì search chưa sẵn sàng, không âm thầm
fallback sang encoder chỉ hỗ trợ tiếng Anh. Image-only ingestion vẫn dùng CLIP.

Trên máy đã có CLIP, tải thêm một lần (~600 MB):

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.cli.download_multilingual --output .cache/clip/multilingual-text
sg docker -c 'docker compose restart backend'
```

Nâng cấp từ bản song ngữ cũ đã có model 540 MB: chỉ cần tải accent restorer:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.cli.download_accents --output .cache/clip/multilingual-text/vi-accent
```

Dependency `py3langid==0.4.0` đã khóa trong `backend/uv.lock`. Cài ML extra theo
hướng dẫn setup hoặc build lại backend trước khi chạy code mới. Không chỉ restart
image cũ nếu image đó chưa có dependency này.

Setup mới: CLI `app.cli.download_model --output PATH` chuẩn bị cả image model và
thư mục con `PATH/multilingual-text`. Các Compose mount thư mục CLIP sẵn có nên
không cần mount thêm. Bản deployment cũ phải chuẩn bị model trong `DEPLOY_MODEL_PATH`
trước khi chạy release mới. Thay đổi này chưa triển khai lên bản nghiệm thu 8088.

## Độ trễ và giới hạn

Model được nạp và warm up một lần. LRU 256 câu đã chuẩn hóa Unicode NFC lưu
vector trong RAM, không lưu kết quả tìm kiếm hay quyền truy cập. Cache chỉ giảm
chi phí encode câu lặp; các bước truy vấn, lọc quyền và kiểm tra ảnh vẫn chạy lại.
Không có cache trên đĩa, không cache ảnh upload. Inference dùng worker duy nhất
hiện có. Văn bản vượt 128 token bị trả 422 `TEXT_TOKEN_LIMIT`, không cắt âm thầm.
Accent restorer cũng có cache RAM 256 câu và chạy trước phân tích điều kiện.
`QUERY_ACCENTS_RESTORED` chứa cách hiểu đã dùng; nguyên văn giữ trong query analysis.

Bộ thêm dấu xử lý truy vấn ASCII ngắn (tối đa 256 ký tự), giữ nguyên văn bản
đã có dấu, cú pháp bộ lọc và mã định danh. Những trường hợp ít tin cậy được giữ
nguyên. Tên riêng, từ viết tắt, từ đa nghĩa, văn bản lẫn một phần dấu hoặc câu
dài vẫn có thể hiểu sai. Ngưỡng confidence là chính sách suy luận, không phải
xác suất đã được hiệu chuẩn hoặc bảo đảm chính xác.

Không bảo đảm hai ngôn ngữ có thứ hạng giống hệt, hoặc truy vấn không dấu luôn
chính xác như có dấu. Cần bộ đánh giá EN/VI có nhãn trên corpus thực để kết luận
Recall/nDCG; các kiểm tra mẫu ở đây chỉ chứng minh tính năng hoạt động.

## Kiểm chứng

```bash
backend/.venv/bin/python scripts/checks/check_bilingual_model.py
backend/.venv/bin/python scripts/checks/check_bilingual_api.py
QA_USE_SG=1 python3 scripts/qa.py fast
backend/.venv/bin/python scripts/checks/check_consumer_browser.py
```

[Model smoke](../verification/bilingual/model.json): 5 cặp câu EN/VI trên 10 ảnh
mẫu local, mỗi ngôn ngữ đều đưa ảnh mục tiêu lên đầu; có đối chiếu English CLIP
gốc. Kiểm tra thêm padding, NFC/NFD, cache copy/eviction và token limit. Đây là
bộ mẫu nhỏ được chọn thủ công, không phải benchmark chất lượng đại diện.
Kiểm tra thêm 11 cặp không dấu/có dấu: câu không dấu phải được khôi phục đúng và
có vector giống câu có dấu; 7 câu English phải giữ nguyên.
[API smoke](../verification/bilingual/api.json) kiểm tra session User, phạm vi
thư viện, ảnh private và cache qua API đang chạy. Browser acceptance gửi nguyên
câu `con meo` nguyên văn từ giao diện, yêu cầu ảnh đầu có caption mèo và thông báo
đã hiểu `con mèo`; phần khám phá vẫn gửi câu English.
