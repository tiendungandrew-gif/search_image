# Model comparison — CLIP và SigLIP 2

CLIP active baseline là `openai/clip-vit-base-patch32`, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`,512 float32/L2/Cosine. Alternative được chọn là `google/siglip2-base-patch16-224`, pinned revision `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2`; official model card cho image-text retrieval và license Apache-2.0. [Google model card](https://huggingface.co/google/siglip2-base-patch16-224), [Transformers documentation](https://huggingface.co/docs/transformers/model_doc/siglip2).

## Availability và compatibility

Đã kiểm disk>400GiB trống, RAM15.11GiB, CPU16 logical cores, CUDA unavailable. Model/processor/tokenizer files khoảng1.54GB được tải explicit vào `.cache/siglip2`, SHA256 receipt và revision riêng. Lượt đầu gặp timeout/DNS/certificate error; retry dùng CA hệ thống và xác minh TLS, không tắt certificate checks. Không tải corpus lớn hoặc model không pin.

Adapter dùng official AutoModel/AutoProcessor, local_files_only/safetensors, eval/inference mode, kiểm finite/shape/L2 và paired text/image dimensions từ actual warmup, không mặc định dimension từ tên model. Checkpoint này có model_type=siglip trong config; không giả mọi SigLIP2 checkpoint là NaFlex hoặc có cùng interface. Text padding=max_length64/truncation=false theo checkpoint; CLIP dùng tokenizer77 positions. Không coi sigmoid/classification logits và cosine hai models là calibrated relevance probabilities.

Encoder manifest ghi source/decoder/processor/tokenizer/weights hashes, package versions, precision/device/dimension và license. Dedicated registry/index/collection dùng lại CollectionManager/durable reindex worker Prompt04; giữ originals, source metadata và prior CLIP collection. Không activate SigLIP2 qua production API hoặc trộn SigLIP text với CLIP vectors. CLIP active generation phải được kiểm không đổi sau research job.

## Protocol

Chạy mỗi model trong fresh research process trên cùng10 images/28 cases/K10/CPU4threads. Whole-query text retrieval và independent image retrieval dùng cùng query set, paired fusion dùng cùng rule; đây là encoder/collection comparison, không full advanced API latency. Source bytes/RGB decode dùng pipeline cũ, mỗi model dùng preprocessing riêng đúng checkpoint.

Model cold initialization bao gồm weight hash/load/warmup; filesystem cache không bị giả là cold. Ghi encoding/search timings và process peak RSS riêng với full HTTP benchmark. ANN-vs-exact overlap có label riêng; K=N10 và possible plain scans không chứng minh HNSW quality. Exact-byte identity checks có ground truth độc lập hashes; semantic VI/EN scores chỉ được tính khi human labels đã xác nhận.

## Commands

```bash
backend/.venv/bin/python -m app.cli.download_evaluation_model --output .cache/siglip2
# Runner chuẩn bị network/mounts/UID, không đổi active index.
bash scripts/evaluation/run_evaluation_container.sh clip
bash scripts/evaluation/run_evaluation_container.sh siglip2
```

Model commands chạy trong container/network có PostgreSQL/Qdrant/MinIO như worker và ghi immutable evaluation/results artifacts; không truyền token vào command. Cần mount corpus cache/results và chọn UID có quyền ghi. [Test report](../archive/PHASE07_TEST_REPORT.md) ghi actual executed commands/outcomes; [EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md) tổng hợp actual results/unavailable experiments.

Chưa có human qrels; không thể kết luận SigLIP2 tốt hơn CLIP, đặc biệt tiếng Việt. Việc tạo được embeddings/collection và trả self-match không đóng semantic quality gate. Production vẫn giữ CLIP/index hiện tại; model-specific resource cost và future annotation coverage phải được cân nhắc trước đổi model.

## Số đo đã thực hiện

| Model | Chiều | Khởi tạo process mới ms | Encoding P50 / P90 ms | Peak RSS MiB | Kiểm tra index |
| --- | --- | --- | --- | --- | --- |
| [clip](../../evaluation/results/phase07/20261104T101257_model-comparison_ace1b38e21/result.json) | 512 | 3859.78 | 22.35 / 63.80 | 1174.41 | 10/10, CLIP active giữ nguyên |
| [siglip2](../../evaluation/results/phase07/20261104T101307_model-comparison_4c67e77ccf/result.json) | 768 | 6219.71 | 41.15 / 163.13 | 1855.54 | 10/10, CLIP active giữ nguyên |

Đây là lượt cuối của từng checkpoint/revision; các lượt trước vẫn lưu immutable. Hai model có4/4 exact identities rank1, ANN-vs-exact overlap được ghi riêng, không là semantic relevance. Ngôn ngữ EN12/VI12 chưa có human judgments, nên không công bố Recall/nDCG theo ngôn ngữ. CLIP revision/index baseline giữ nguyên; SigLIP collection `images_siglip2_phase07_v1_7c8f7207b4d1`, model `4a5caa23-4932-469f-a781-4b8bd7a9c756`, index `3c7b23e3-4c73-4082-aa09-34df3bc70208`,768 Cosine đã verify10/10.

`--labels evaluation/relevance_labels/reviewed.json` chỉ dùng sau human sign-off; model evaluator validate cùng frozen qrels rồi xuất per-task/per-language metrics và label SHA. Không cần activate research model để chấm. CLI model comparisons không phải advanced constraint verifier; quality–latency recommendation hiện giữ CLIP đang phục vụ.
