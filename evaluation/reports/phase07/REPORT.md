# Kết quả thí nghiệm Phase 07

Số đo từ raw artifacts; latency successful-only đi kèm số lỗi. Không cộng component percentiles hoặc suy SLA từ corpus nhỏ.

| Experiment | Status | N / errors | P90 ms | P95 ms | Success req/s |
| --- | --- | --- | --- | --- | --- |
| fast_before_head1 | measured | 500 / 0 | 142.19110799967893 | 144.77099899977475 | 7.439503408981376 |
| opt_head1_rep1 | measured | 300 / 0 | 148.97180700063473 | 154.33651999956055 | 8.447517861829452 |
| opt_head2_rep1 | measured | 300 / 0 | 149.53161500125134 | 152.058292998845 | 7.912356783848697 |
| opt_head2_rep2 | measured | 300 / 0 | 147.00525799889874 | 150.01614399989194 | 7.914138806995527 |
| opt_head1_rep2 | measured | 300 / 0 | 147.04450799945334 | 152.60654100165993 | 8.254657076624975 |
| fast_after_head2 | measured | 500 / 0 | 146.39579799950297 | 148.84286100095778 | 7.7453183790961235 |
| image_after | measured | 300 / 0 | 130.55785999858927 | 138.0780910003523 | 8.014245379077474 |
| A0_whole | measured | 300 / 0 | 148.33100000032573 | 152.41063599933113 | 7.694186197288188 |
| A1_multiquery | measured | 300 / 0 | 160.4948099993635 | 163.75255700040725 | 6.83109721532957 |
| A2_rrf | measured | 300 / 0 | 153.3901219991094 | 155.64776099927258 | 7.264111672110006 |
| A3_nonsel_filter | measured | 300 / 0 | 153.43070200106013 | 156.66399800102226 | 7.347646196989326 |
| A4_rerank | measured | 300 / 0 | 162.02432499994757 | 164.5708520009066 | 6.717202598665938 |
| A5_text_only | measured | 300 / 0 | 147.81973099889 | 150.23107699926186 | 7.575371302601085 |
| A5_paired_rrf | measured | 300 / 0 | 167.34887799975695 | 179.90981899856706 | 6.587361188900298 |
| A5_paired_score | measured | 300 / 0 | 156.18868399906205 | 167.772184999194 | 6.823992586054536 |
| load_fast_c1 | measured | 300 / 0 | 147.43153900053585 | 148.9490530002513 | 7.6988177205810295 |
| load_fast_c5 | measured | 500 / 22 | 184.5845210009429 | 194.53968900052132 | 33.15788218032597 |
| load_fast_c10 | measured | 500 / 283 | 229.4674170007056 | 241.15317499854427 | 30.082550513906956 |
| load_fast_c20 | measured | 500 / 432 | 312.7685460003704 | 372.6566589994036 | 19.500891051342904 |
| load_mixed_open8 | measured | 160 / 0 | 140.42035400052555 | 151.41676399980497 | 8.010420249443658 |
| clip | measured | None / None | None | None | None |
| siglip2 | measured | None / None | None | None | None |
| None | measured | None / None | None | None | None |
| optimization-analysis | measured | None / None | None | None | None |
| evaluate | partial_semantic_labels_unavailable | None / None | None | None | None |
| fast_default_head1 | measured | 500 / 0 | 145.7980340001086 | 150.9010939989821 | 8.653715953514089 |
| clip | measured | None / None | None | None | None |
| siglip2 | measured | None / None | None | None | None |
| None | measured | None / None | None | None | None |
| None | valid | None / None | None | None | None |
| optimization-analysis | measured | None / None | None | None | None |
| A4_rerank | partial_semantic_labels_unavailable | None / None | None | None | None |

## Chất lượng và giới hạn

Không tự tạo human judgments; thiếu nhãn phải giữ unavailable. Identity/ANN overlap không thay semantic quality. Không có GPU comparison khi thiếu GPU.

## Provenance

- `20261104T084629_benchmark_0255e8a3fd` → [raw artifact](../../results/phase07/20261104T084629_benchmark_0255e8a3fd/result.json)
- `20261104T093937_benchmark_97b3d12a34` → [raw artifact](../../results/phase07/20261104T093937_benchmark_97b3d12a34/result.json)
- `20261104T094027_benchmark_c337f7cf84` → [raw artifact](../../results/phase07/20261104T094027_benchmark_c337f7cf84/result.json)
- `20261104T094121_benchmark_85202e75a0` → [raw artifact](../../results/phase07/20261104T094121_benchmark_85202e75a0/result.json)
- `20261104T094214_benchmark_5dcd341f50` → [raw artifact](../../results/phase07/20261104T094214_benchmark_5dcd341f50/result.json)
- `20261104T094305_benchmark_17af8a9c27` → [raw artifact](../../results/phase07/20261104T094305_benchmark_17af8a9c27/result.json)
- `20261104T094413_benchmark_016c347034` → [raw artifact](../../results/phase07/20261104T094413_benchmark_016c347034/result.json)
- `20261104T094452_benchmark_bb696f814c` → [raw artifact](../../results/phase07/20261104T094452_benchmark_bb696f814c/result.json)
- `20261104T094533_benchmark_833ec7552e` → [raw artifact](../../results/phase07/20261104T094533_benchmark_833ec7552e/result.json)
- `20261104T094620_benchmark_01151f1a21` → [raw artifact](../../results/phase07/20261104T094620_benchmark_01151f1a21/result.json)
- `20261104T094703_benchmark_ff869c8d80` → [raw artifact](../../results/phase07/20261104T094703_benchmark_ff869c8d80/result.json)
- `20261104T094747_benchmark_53a3137b7f` → [raw artifact](../../results/phase07/20261104T094747_benchmark_53a3137b7f/result.json)
- `20261104T094834_benchmark_e060438714` → [raw artifact](../../results/phase07/20261104T094834_benchmark_e060438714/result.json)
- `20261104T094916_benchmark_eaee1c2363` → [raw artifact](../../results/phase07/20261104T094916_benchmark_eaee1c2363/result.json)
- `20261104T095004_benchmark_3cec04222f` → [raw artifact](../../results/phase07/20261104T095004_benchmark_3cec04222f/result.json)
- `20261104T095051_benchmark_09d9264c9f` → [raw artifact](../../results/phase07/20261104T095051_benchmark_09d9264c9f/result.json)
- `20261104T095132_benchmark_6fe8167b67` → [raw artifact](../../results/phase07/20261104T095132_benchmark_6fe8167b67/result.json)
- `20261104T095149_benchmark_f713978774` → [raw artifact](../../results/phase07/20261104T095149_benchmark_f713978774/result.json)
- `20261104T095159_benchmark_1bff5d5b0d` → [raw artifact](../../results/phase07/20261104T095159_benchmark_1bff5d5b0d/result.json)
- `20261104T095205_benchmark_ddf52692ff` → [raw artifact](../../results/phase07/20261104T095205_benchmark_ddf52692ff/result.json)
- `20261104T100605_model-comparison_71387ec40e` → [raw artifact](../../results/phase07/20261104T100605_model-comparison_71387ec40e/result.json)
- `20261104T100731_model-comparison_60ac9facaa` → [raw artifact](../../results/phase07/20261104T100731_model-comparison_60ac9facaa/result.json)
- `20261104T100817_profile_d086c7b75d` → [raw artifact](../../results/phase07/20261104T100817_profile_d086c7b75d/result.json)
- `20261104T100945_optimization-analysis_358dbd0c6f` → [raw artifact](../../results/phase07/20261104T100945_optimization-analysis_358dbd0c6f/result.json)
- `20261104T101005_evaluate_f6a6877b9f` → [raw artifact](../../results/phase07/20261104T101005_evaluate_f6a6877b9f/result.json)
- `20261104T101019_benchmark_c505f295d7` → [raw artifact](../../results/phase07/20261104T101019_benchmark_c505f295d7/result.json)
- `20261104T101257_model-comparison_ace1b38e21` → [raw artifact](../../results/phase07/20261104T101257_model-comparison_ace1b38e21/result.json)
- `20261104T101307_model-comparison_4c67e77ccf` → [raw artifact](../../results/phase07/20261104T101307_model-comparison_4c67e77ccf/result.json)
- `20261104T101319_profile_344aa63687` → [raw artifact](../../results/phase07/20261104T101319_profile_344aa63687/result.json)
- `20261104T101345_validate-dataset_e9b865b57c` → [raw artifact](../../results/phase07/20261104T101345_validate-dataset_e9b865b57c/result.json)
- `20261104T101633_optimization-analysis_8b0e4c6291` → [raw artifact](../../results/phase07/20261104T101633_optimization-analysis_8b0e4c6291/result.json)
- `20261104T101840_evaluate_aea01ea3c5` → [raw artifact](../../results/phase07/20261104T101840_evaluate_aea01ea3c5/result.json)
