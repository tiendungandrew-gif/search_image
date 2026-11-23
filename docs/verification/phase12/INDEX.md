# Bằng chứng nghiệm thu Phase12

Ngày08/11/2026. Trạng thái kết luận và phạm vi ở [FINAL_PROJECT_REPORT A–T](../../FINAL_PROJECT_REPORT.md). Đây là evidence local, không chứng nhận hosting public hoặc human quality.

[Kết quả cuối dạng JSON](final_verification.json) tổng hợp gates, test counts và các phần chưa xác nhận. [Kiểm tra tài liệu A–T/links](document_checks.json) và [source diff so với baseline](source_diff.json) giữ phạm vi bàn giao rõ ràng.

## Nguồn và release

- [Working tree trước sửa](baseline/git_status.txt), [source baseline](baseline/source.json).
- [Release cuối, source SHA và immutable image IDs](release.json), [source archive cuối](final_source.json).
- [Command history deployment](command_history.json): argv/exit/elapsed và đường dẫn raw log, kể cả các attempt lỗi. [Manual checks](manual_checks.json) ghi lint/compileall/actionlint/Make và các script kiểm chứng riêng.
- [Runtime audit](runtime_audit.json): UID/rootfs/caps/ports/health/resources và bảo toàn513 ảnh/gen3/knowledge4–3–3. [Secret audit](secret_audit.json): exact known values, không thay cho historical pattern/CVE audit.

## QA cuối

- [Backend fast246 pass](qa/20261108T031803_835566_fast.json), [raw log](qa/20261108T031803_835566_fast.log).
- [Services11 pass](qa/20261108T024005_028878_services.json), [raw log](qa/20261108T024005_028878_services.log).
- [CLIP pipeline1 pass](qa/20261108T025045_584524_ai.json), [raw log](qa/20261108T025045_584524_ai.log).
- [Frontend type/lint/44 unit/build](qa/20261108T025706_597303_frontend.json), [raw log](qa/20261108T025706_597303_frontend.log).

## Empty và model

- [HTTP empty](http_20261108T021321_224938.json).
- [Browser empty4 pass/4 indexed-only skip](browser_empty_20261108T021622_004161.json), [raw log](browser_empty_20261108T021622_004161.log).
- [Model artifacts absent](missing_model.json), [RAG not-ready response](rag_disabled_response.json).

## Import, search, SSE, TLS, recovery

- [HTTP indexed7 sau restart/V4](http_20261108T032655_834747.json), [browser indexed8 pass](browser_indexed_20261108T032655_328368.json), [raw log](browser_indexed_20261108T032655_328368.log).
- [HTTP release phase12-final](http_20261108T033503_024266.json), [đối chiếu component bytes V4/final](component_comparison.json).
- [Restore HTTP/private bytes/multimodal7](http_20261108T032405_628956.json); inventory và verify-all commands/raw logs nằm trong command history. Backup được restore:20261108T023457_05fd3337; raw backup private nằm ngoài Git.
- [TLS self-signed/explicit CA và hostname validation](tls_local.json), public certificate NOT_CONFIGURED.
- [Probe worker trước sửa](worker_health_before_optimization.json); timings sau sửa có trong runtime audit.
- [Restore safety guards](restore_guards.json): expected nonzero phải được phân biệt với failure chưa sửa.

## Hiệu năng

[Raw experiment300/300](../../../evaluation/results/phase12/20261108T032218_benchmark_d385b66936/result.json), [provenance](../../../evaluation/results/phase12/20261108T032218_benchmark_d385b66936/experiment.json), [corpus snapshot](../../../evaluation/datasets/manifests/phase12_synthetic_v1.json), [queries](../../../evaluation/queries/phase12_synthetic_v1.jsonl), [config](../../../evaluation/experiments/phase12_proxy_fast.json). Synthetic7 ảnh, C1/warm10, không có human qrels. Baseline513 ảnh ở Phase11 giữ nguyên.

## Phân loại thất bại và giới hạn

Giữ raw logs của Snap no-new-privileges EPERM, empty-browser selector sai, RAG-disabled assertion sai và worker startup/health timeout. Unit regression bắt probe import nặng trước khi sửa; QA log lịch sử nằm thư mục Phase11 runner. Một lần gọi QA trong sandbox bị Snap từ chối, đã chạy lại ngoài sandbox. Runtime audit đầu dùng nhầm tên bảng knowledge đã sửa, chỉ SELECT. Restore guard harness từng chạy cùng update nên bị operation lock chặn trước khi kiểm restore; rerun tuần tự ghi expected rejection.

Remote GitHub workflow/public host/CA tin cậy/GPU/physical devices/quality labels chưa được kiểm chứng. Browser logs có NO_COLOR/FORCE_COLOR warning của môi trường, không có test failure cuối. Những ca này không tính vào pass chỉ vì build thành công.

Sau kiểm chứng đã dọn QA namespace/volumes riêng; project restore8089 được dừng và giữ volumes. Project Phase12 ở8088 và development5173/8000 tiếp tục chạy. Runtime audit ghi trạng thái restore healthy trước khi dừng; không dùng artifact đó để khẳng định8089 còn online.

## Các lệnh deployment thực thi

Bảng sau liên kết từng transcript. Exit codes là mã của commands đã quan sát, không phải kết luận chất lượng toàn hệ thống.

| Transcript | Commands | Nonzero exits |
| --- | ---: | ---: |
| [20261107T162431_339860_image-search-phase12](runs/20261107T162431_339860_image-search-phase12.log) |3|2|
| [20261108T015043_021366_image-search-phase12](runs/20261108T015043_021366_image-search-phase12.log) |6|2|
| [20261108T020025_809154_image-search-phase12](runs/20261108T020025_809154_image-search-phase12.log) |2|1|
| [20261108T020202_487966_image-search-phase12](runs/20261108T020202_487966_image-search-phase12.log) |1|0|
| [20261108T020338_300476_image-search-phase12](runs/20261108T020338_300476_image-search-phase12.log) |3|0|
| [20261108T020436_466367_image-search-phase12](runs/20261108T020436_466367_image-search-phase12.log) |2|0|
| [20261108T020549_647855_image-search-phase12](runs/20261108T020549_647855_image-search-phase12.log) |6|2|
| [20261108T020903_220299_image-search-phase12](runs/20261108T020903_220299_image-search-phase12.log) |18|1|
| [20261108T021126_036217_image-search-phase12](runs/20261108T021126_036217_image-search-phase12.log) |1|0|
| [20261108T021315_567797_image-search-phase12](runs/20261108T021315_567797_image-search-phase12.log) |1|0|
| [20261108T021709_674204_image-search-phase12](runs/20261108T021709_674204_image-search-phase12.log) |3|0|
| [20261108T021844_707083_image-search-phase12](runs/20261108T021844_707083_image-search-phase12.log) |9|0|
| [20261108T022000_906118_image-search-phase12](runs/20261108T022000_906118_image-search-phase12.log) |1|0|
| [20261108T022037_395377_image-search-phase12](runs/20261108T022037_395377_image-search-phase12.log) |1|0|
| [20261108T022513_849202_image-search-phase12](runs/20261108T022513_849202_image-search-phase12.log) |6|2|
| [20261108T022819_125160_image-search-phase12](runs/20261108T022819_125160_image-search-phase12.log) |18|0|
| [20261108T023023_566633_image-search-phase12](runs/20261108T023023_566633_image-search-phase12.log) |10|0|
| [20261108T023457_686050_image-search-phase12](runs/20261108T023457_686050_image-search-phase12.log) |13|0|
| [20261108T023906_224137_image-search-phase12-restore](runs/20261108T023906_224137_image-search-phase12-restore.log) |10|1|
| [20261108T024100_370893_image-search-phase12](runs/20261108T024100_370893_image-search-phase12.log) |2|0|
| [20261108T024221_458741_image-search-phase12-restore](runs/20261108T024221_458741_image-search-phase12-restore.log) |1|0|
| [20261108T024238_133240_image-search-phase12-restore](runs/20261108T024238_133240_image-search-phase12-restore.log) |2|0|
| [20261108T024406_059706_image-search-phase12-restore](runs/20261108T024406_059706_image-search-phase12-restore.log) |1|0|
| [20261108T024628_997087_image-search-phase12](runs/20261108T024628_997087_image-search-phase12.log) |6|2|
| [20261108T024758_347503_image-search-phase12](runs/20261108T024758_347503_image-search-phase12.log) |1|0|
| [20261108T025003_732528_image-search-phase12](runs/20261108T025003_732528_image-search-phase12.log) |18|0|
| [20261108T025011_087807_image-search-phase12-restore](runs/20261108T025011_087807_image-search-phase12-restore.log) |18|0|
| [20261108T025222_781458_image-search-phase12-restore](runs/20261108T025222_781458_image-search-phase12-restore.log) |3|0|
| [20261108T025519_721942_image-search-phase12](runs/20261108T025519_721942_image-search-phase12.log) |3|0|
| [20261108T025555_087388_image-search-phase12](runs/20261108T025555_087388_image-search-phase12.log) |3|0|
| [20261108T030801_317487_image-search-phase12](runs/20261108T030801_317487_image-search-phase12.log) |20|0|
| [20261108T031816_926946_image-search-phase12](runs/20261108T031816_926946_image-search-phase12.log) |18|0|
| [20261108T032358_317250_image-search-phase12-restore](runs/20261108T032358_317250_image-search-phase12-restore.log) |1|0|
| [20261108T032532_326957_image-search-phase12](runs/20261108T032532_326957_image-search-phase12.log) |2|0|
| [20261108T032646_985962_image-search-phase12](runs/20261108T032646_985962_image-search-phase12.log) |1|0|
| [20261108T032750_072898_image-search-phase12](runs/20261108T032750_072898_image-search-phase12.log) |1|0|
| [20261108T032840_293986_image-search-phase12](runs/20261108T032840_293986_image-search-phase12.log) |6|2|
| [20261108T033217_073344_image-search-phase12](runs/20261108T033217_073344_image-search-phase12.log) |18|0|
| [20261108T033435_624969_image-search-phase12-restore](runs/20261108T033435_624969_image-search-phase12-restore.log) |2|1|
| [20261108T033455_611536_image-search-phase12](runs/20261108T033455_611536_image-search-phase12.log) |1|0|
| [20261108T033557_892496_image-search-phase12-restore](runs/20261108T033557_892496_image-search-phase12-restore.log) |2|1|
| [20261108T033730_174820_image-search-phase12-restore](runs/20261108T033730_174820_image-search-phase12-restore.log) |1|0|
| [20261108T033913_721575_image-search-phase12](runs/20261108T033913_721575_image-search-phase12.log) |2|0|
