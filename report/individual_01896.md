# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đỗ Quang Huy             |
| MSSV               | 2A202601896                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | A6-1-BabyShark (nhóm 5 thành viên)     |
| Vai trò chính    | Thành viên 4 — Corruption & Repair owner                 |
| Repository         | https://github.com/cronusnd1404/K4_Day10_Data-Pipeline-Data-Observability-A6-1-BabyShark |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Corruption có kiểm soát trên clean dataset | `src/ingestion/corruption.py` — `corrupt_clean_dataframe()` | Cleaned DataFrame (`data/clean/papers_clean.csv`) + frozen test set (`data/eval/test_set.json`) | `data/clean/papers_clean_corrupted.csv/json`, `data/results/corruption_log.json` | Hoàn thành |
| Kiểm tra corruption có tác động đo được lên agent | `data/results/corruption_log.json` đối chiếu `data/results/corrupted_metrics.json`, `data/quality/corrupted.json` | Corruption log + baseline/corrupted metrics | Bằng chứng số liệu cho comparison report | Hoàn thành |

Ghi chú trung thực về quá trình làm: bản đầu tiên của `corrupt_clean_dataframe` (commit `0bcc246`) do tôi viết với chữ ký `(df, output_log_path)`, gồm 6 kịch bản lỗi (drop latest record, blank summary, inject noise, truncate title, stale date, duplicate) chọn ngẫu nhiên theo seed cố định. Sau đó thành viên phụ trách tích hợp (`cronusnd1404`) đã sửa lại hàm này trong commit `81a7687 "Checkpoint C4"` để đổi chữ ký thành `(df, output_csv_path, output_json_path, output_log_path, test_set_path=None, seed=42)`, rút còn 4 kịch bản (blank summary, stale date, inject noise, duplicate) nhưng thêm cơ chế **ưu tiên corrupt các `paper_id` nằm trong `ground_truth_doc_ids` của frozen test set**, để đảm bảo corruption luôn đo được ảnh hưởng lên metric thay vì có thể "trượt" các record không được hỏi tới. Bản đang chạy trên `main` hiện tại là bản đã được mở rộng này; tôi xác nhận lại logic, chạy thử và đối chiếu artifact/log để đảm bảo đúng hành vi trước khi báo cáo.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đọc contract clean schema (`paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding`) từ `retrieval/index.py` và `observability/quality.py` trước khi cleaning.py hoàn thiện | Thành viên 2 (cleaning.py) | Viết được `corrupt_clean_dataframe` đúng schema mà không cần chờ cleaning.py xong |
| Xử lý xung đột push lên `main` | Cả nhóm | `git fetch` + `git pull --rebase` để không mất commit của thành viên khác khi cùng push |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Corrupt 24 record clean bằng 4 kịch bản có kiểm soát, có seed=42 để tái lập | `src/ingestion/corruption.py`, `data/results/corruption_log.json` | 28 dòng corrupted (24 gốc + 4 duplicate); 5 blank_summary, 5 stale_date, 5 inject_noise, 4 duplicate_row | `uv run python script/run_corruption_flow.py`, đọc `data/results/corruption_log.json` |
| Corruption làm data quality check chuyển từ pass sang fail | `data/quality/baseline_quality.json`, `data/quality/corrupted.json` | `passed: true → false`; `paper_id_duplicates: 0 → 4`; `short_summaries: 0 → 6`; `stale_rows: 0 → 6` | So khớp hai file JSON |
| Corruption làm agent trả lời sai/kém hơn dù retrieval vẫn "hit" | `data/results/baseline_answers.json`, `data/results/corrupted_answers.json` (câu `q1`) | Câu `q1` baseline: `judge.score = 5`, `correct = true`; sau corruption: `answer` bị chèn `"broken_encoding_data"`, `judge.score = 1`, `correct = false`, dù `retrieval_hit` vẫn `true` và `token_f1` chỉ giảm nhẹ 1.0 → 0.98 | So khớp bản ghi `id: "q1"` ở hai file answers |

Output cụ thể: `data/results/corruption_log.json` — log JSON ghi rõ từng bản ghi bị tác động (loại lỗi, `paper_id`, giá trị trước/sau), là bằng chứng chính để chứng minh corruption có chủ đích chứ không phải lỗi ngẫu nhiên vô căn cứ, đồng thời là input cho `observability/reporting.py` khi dựng `corruption_report.md`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Sau khi có baseline pipeline chạy sạch trên dữ liệu tốt, bài lab cần một bước tạo lỗi dữ liệu **có chủ đích và đo được**, để phần evaluation/observability phía sau có thể chứng minh bằng số liệu rằng dữ liệu xấu làm giảm chất lượng agent, và repair giúp phục hồi. Nếu corrupt ngẫu nhiên toàn bộ dataset mà không quan tâm dataset đó có được test set "hỏi tới" hay không, corruption có thể không tạo ra khác biệt metric nào — mất hết ý nghĩa của bài lab.

### Cách triển khai

`corrupt_clean_dataframe(df, output_csv_path, output_json_path, output_log_path, test_set_path=None, seed=42)` nhận vào cleaned DataFrame và (tuỳ chọn) đường dẫn `test_set.json`:

1. Đọc `test_set.json`, gom toàn bộ `ground_truth_doc_ids` thành tập `target_test_doc_ids`.
2. Chia index của DataFrame thành `test_target_indices` (nằm trong tập trên) và `non_test_indices`, shuffle theo `random.Random(seed)` để tái lập được.
3. Áp lần lượt 4 kịch bản, mỗi kịch bản ưu tiên lấy 2 record từ `test_target_indices` trước khi lấy phần còn lại từ `non_test_indices`:
   - **Blank summary** (20%): xoá `summary`, set `summary_chars = 0`.
   - **Stale date** (20%): đổi `published` thành `2000-01-01`, `age_days = 9500`.
   - **Inject noise** (20%): chèn một trong 5 chuỗi rác cố định (`NOISE_SNIPPETS`) vào đầu `summary`.
   - **Duplicate row** (15%): nhân bản nguyên dòng, giữ nguyên `paper_id` để phá vỡ tính duy nhất.
4. Rebuild lại `text_for_embedding` cho toàn bộ DataFrame sau khi đã corrupt (`Title: ... | Authors: ... | Summary: ...`) để đảm bảo embedding sau này phản ánh đúng dữ liệu đã hỏng.
5. Ghi CSV/JSON corrupted và một log JSON gồm `seed`, `original_row_count`, `corrupted_row_count`, `target_test_doc_ids_count`, `corruption_counts` (đếm theo loại lỗi) và `entries` (chi tiết từng bản ghi, có before/after).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `pd.DataFrame` clean schema (`paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding`, ...) + `test_set.json` (optional nhưng cần để corruption có overlap với test set) |
| Output                         | `pd.DataFrame` đã corrupt (trả về) + 3 file ghi ra đĩa: corrupted CSV, corrupted JSON, corruption log JSON |
| Module phụ thuộc             | `ingestion/cleaning.py` (schema đầu vào), `core/config.py` (đường dẫn artifact), `core/utils.py` (`write_csv`, `write_json`, `read_json`) |
| Module sử dụng output        | `pipelines/corruption_flow.py` (đọc corrupted CSV để build index và evaluate), `observability/quality.py` + `observability/reporting.py` (đọc corrupted dataset và log để dựng comparison report) |
| Điều kiện lỗi cần xử lý | `test_set_path` không tồn tại → log warning và fallback về corrupt ngẫu nhiên toàn dataset; `clean_csv` chưa tồn tại (chưa chạy baseline) → báo lỗi rõ ràng thay vì chạy tiếp |

### Cách xác minh

```bash
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** sinh ra `data/clean/papers_clean_corrupted.csv/json`, `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md`; `data/quality/corrupted.json` phải có `passed: false`.
- **Kết quả thực tế:** đúng như mong đợi — `corruption_log.json` ghi 19 sự kiện lỗi (5+5+5+4) trên 24 record gốc, ra 28 dòng corrupted; `data/quality/corrupted.json` có `passed: false`, `paper_id_duplicates: 4`, `short_summaries: 6`, `stale_rows: 6`.
- **Artifact/log:** `data/results/corruption_log.json`, `data/quality/corrupted.json`, `data/quality/corrupted_freshness_report.json` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách chọn record để corrupt — random đều trên toàn bộ 24 record, hay ưu tiên nhắm vào các `paper_id` nằm trong `ground_truth_doc_ids` của frozen test set.
- **Các phương án đã cân nhắc:**
  1. Random uniform toàn dataset (cách tôi làm ở bản đầu) — đơn giản, mô phỏng lỗi "tự nhiên", nhưng với chỉ 24 record và test set nhỏ, có xác suất không record nào bị hỏi tới bị corrupt, khiến metric evaluation gần như không đổi.
  2. Ưu tiên corrupt các `paper_id` có mặt trong test set trước, phần còn lại mới lấy ngẫu nhiên (bản mở rộng của đồng đội) — đảm bảo luôn có overlap giữa corruption và evaluation.
- **Phương án đã chọn:** Phương án 2, đã được đồng đội tích hợp và tôi xác nhận lại là hợp lý sau khi đối chiếu kết quả.
- **Lý do:** Mục tiêu cốt lõi của bài lab là "chứng minh bằng artifact và metrics rằng chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng RAG". Với dataset nhỏ (24 record) và test set cũng nhỏ, corrupt ngẫu nhiên thuần tuý có rủi ro thực nghiệm không cho thấy tác động rõ ràng — làm mất mục đích của toàn bộ Phase 2.
- **Bằng chứng quyết định phù hợp:** Sau khi áp dụng phương án 2, `mean_token_f1` giảm từ `0.9636` (baseline) xuống `0.7113` (corrupted), `judge_accuracy` giảm từ `0.875` xuống `0.5833`, `mean_judge_score` giảm từ `4.54` xuống `3.50` — corruption có tác động rõ ràng, đo được. Riêng `retrieval_hit_rate` lại **tăng** nhẹ từ `0.9583` lên `1.0`, vì duplicate row làm tăng khả năng một trong các bản sao được retrieve — một quan sát thú vị cho thấy không phải mọi corruption đều làm mọi metric xấu đi theo cùng một chiều.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```
  ! [rejected]        main -> main (fetch first)
  error: failed to push some refs to 'https://github.com/cronusnd1404/K4_Day10_Data-Pipeline-Data-Observability-A6-1-BabyShark.git'
  ```
- **Lệnh hoặc bước tái hiện:** `git commit ...` rồi `git push origin main` ngay sau khi hoàn thành `corrupt_clean_dataframe`.
- **Nguyên nhân gốc:** Cả 5 thành viên trong nhóm push thẳng lên `main`, không qua branch/PR. Trong lúc tôi code local, một thành viên khác đã push commit mới (cleaning/testset) lên `origin/main` trước, khiến local `main` bị lùi lại so với remote.
- **Cách xử lý:** Chạy `git fetch origin`, dùng `git diff --stat main origin/main` để xác nhận thay đổi trên remote không đụng tới `src/ingestion/corruption.py` (tránh conflict logic), sau đó `git pull --rebase origin main` để replay commit của mình lên trên các commit mới, rồi `git push origin main` lại.
- **Cách xác minh sau khi sửa:** `git push origin main` trả về `b1f80a7..0bcc246 main -> main` không còn lỗi; `git log --oneline` xác nhận commit của tôi nằm đúng thứ tự sau các commit của đồng đội.
- **Điều học được:** Khi cả nhóm cùng push thẳng `main`, luôn `fetch` + so diff trước khi push để biết chắc có đụng file người khác hay không, và ưu tiên `pull --rebase` thay vì `merge` để giữ lịch sử tuyến tính, dễ đọc.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` gọi Crossref REST API, lưu raw response và raw records (có `paper_id` ổn định dựa trên DOI) vào `data/raw/`. `cleaning.py` đọc raw records, chuẩn hoá title/summary/authors/categories, tính `age_days` từ `published`, và build cột `text_for_embedding`, ghi ra `data/clean/papers_clean.csv/json`. `retrieval/index.py` đọc cleaned DataFrame, dùng MiniLM (`sentence-transformers/all-MiniLM-L6-v2`) để encode `text_for_embedding` thành vector, nạp vào một collection ChromaDB riêng cho từng trạng thái (`papers-baseline`, `papers-corrupted`, `papers-repaired`) và ghi manifest JSON tương ứng.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `testset.py` sinh câu hỏi (`factual`, ...) kèm `ground_truth` và `ground_truth_doc_ids` lấy từ chính cleaned dataset, đóng băng trong `data/eval/test_set.json`. Khi evaluate, agent trả lời từng câu hỏi và trả về `retrieved_doc_ids`; `retrieval_hit_rate` kiểm tra `ground_truth_doc_ids` có nằm trong top-k retrieve hay không, `token_f1` so khớp câu trả lời với `ground_truth`, và một LLM-judge chấm `judge_accuracy`/`mean_judge_score` dựa trên mức độ đúng về nội dung.
3. **Quality checks khác freshness monitoring ở điểm nào?** Quality checks (`run_data_quality_checks`) kiểm tra tính toàn vẹn cấu trúc: số dòng, `paper_id` null/duplicate, `title` null, độ dài `summary`, cho ra `passed: true/false`. Freshness monitoring (`build_freshness_report`) chỉ tập trung vào trục thời gian: `latest_published`, `oldest_published`, số dòng `stale_rows` theo `freshness_threshold_days` (180 ngày), và cờ `is_fresh`. Một dataset có thể `quality passed = true` nhưng vẫn `is_fresh = false` nếu dữ liệu toàn vẹn nhưng đã cũ, và ngược lại.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để phép so sánh có ý nghĩa: nếu đổi câu hỏi hoặc ground truth giữa các trạng thái, chênh lệch metric có thể do test set khác nhau chứ không phải do chất lượng dữ liệu. Dùng cùng `test_set.json` (đóng băng từ đầu, do `testset.py` tạo một lần) đảm bảo mọi khác biệt về `retrieval_hit_rate`/`token_f1`/`judge_accuracy` giữa baseline–corrupted–repaired chỉ phản ánh khác biệt về dữ liệu bên dưới.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** `corruption_flow.py` repair bằng cách gọi lại `build_clean_dataframe()` trực tiếp từ `raw_records_json` (nguồn gốc, không sửa tay dữ liệu đã corrupt), build lại index `papers-repaired`, evaluate lại trên cùng test set. Repair được coi là thành công khi: `data/quality/repaired.json` có `passed: true` (ở đây `paper_id_duplicates: 0`, `stale_rows: 0`, giống hệt baseline_quality), `repaired_freshness_report.json` có `is_fresh: true`, và `repaired_metrics.json` khớp lại với `baseline_metrics.json` (`retrieval_hit_rate 0.9583`, `mean_token_f1 0.9636`, `judge_accuracy 0.875`, `mean_judge_score 4.54` — phục hồi hoàn toàn về đúng giá trị baseline).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   0.9583 |    1.0000 |   0.9583 | Tăng nhẹ khi corrupted vì duplicate row làm tăng cơ hội một bản sao của tài liệu đúng được retrieve — không phải dấu hiệu "tốt hơn" mà là tác dụng phụ của duplicate. |
| `mean_token_f1`      |   0.9636 |    0.7113 |   0.9636 | Giảm mạnh nhất trong các metric — nhạy với blank summary và inject noise vì câu trả lời agent trực tiếp lấy nội dung từ `summary`. |
| `judge_accuracy`     |   0.8750 |    0.5833 |   0.8750 | Giảm rõ rệt; LLM-judge phạt nặng các câu trả lời có chuỗi rác (`broken_encoding_data`, `<<<DATA_CORRUPTED_ERROR>>>`, ...) dù nội dung gốc vẫn còn. |
| `mean_judge_score`   |     4.54 |      3.50 |     4.54 | Cùng xu hướng với `judge_accuracy`. |
| Quality checks         |   passed |    failed |   passed | `corrupted.json`: `paper_id_duplicates=4`, `short_summaries=6`, `stale_rows=6`. |
| Freshness status       | is_fresh | not fresh | is_fresh | `corrupted_freshness_report.json`: `stale_rows=6`, `oldest_published=2000-01-01` (do kịch bản stale_date). |

### Kết luận từ số liệu

1. **Blank summary + inject noise (corruption)** → **`short_summaries` tăng 0→6 trong quality check, `summary` chứa chuỗi rác** → **`mean_token_f1` giảm 0.9636→0.7113 và `judge_accuracy` giảm 0.875→0.5833**, minh chứng rõ nhất bằng câu `q1`: baseline `judge.score=5, correct=true`; corrupted `answer` bị chèn `"broken_encoding_data"`, `judge.score=1, correct=false`, dù `retrieval_hit` vẫn `true`.
2. **Repair bằng cách build lại từ `raw_records_json` (repair action)** → **`data/quality/repaired.json` trở lại `passed=true`, `repaired_freshness_report.json` trở lại `is_fresh=true`** → **toàn bộ 4 metric agent (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) phục hồi về đúng giá trị baseline**, chứng minh repair-from-raw là chiến lược hiệu quả và không để lại "vết" của corruption.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Blank summary và inject noise ảnh hưởng rõ nhất lên `mean_token_f1`/`judge_accuracy`, vì câu trả lời factual của agent bám sát nội dung `summary` trong `text_for_embedding` — xoá hoặc làm nhiễu summary trực tiếp làm hỏng nội dung câu trả lời, trong khi retrieval (dựa trên vector similarity của toàn bộ `text_for_embedding`, gồm cả title/authors) vẫn có thể tìm đúng tài liệu nên `retrieval_hit_rate` ít bị ảnh hưởng hơn.

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu tôi kỳ vọng `retrieval_hit_rate` sẽ giảm khi corrupt dữ liệu, nhưng thực tế nó tăng nhẹ (0.9583 → 1.0). Giả thuyết: `duplicate_row` tạo thêm một bản sao của record đúng trong index, làm tăng xác suất record đó xuất hiện trong top-k kết quả trả về. Đã kiểm tra bằng cách đối chiếu `corruption_log.json` (4 `duplicate_row`, trong đó có `10.2118/234689-pa` — chính là ground truth của câu `q1`) với `corrupted_answers.json` (câu `q1` có `retrieved_doc_ids` chứa `10.2118/234689-pa` cùng bản duplicate `10.21203/rs.3.rs-9770645/v1` lặp 2 lần) — khớp với giả thuyết.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Corruption phải "nhắm" vào dữ liệu thực sự được test set sử dụng thì mới đo được tác động lên metric — corrupt ngẫu nhiên thuần tuý trên dataset nhỏ có thể không tạo ra khác biệt có ý nghĩa thống kê.
2. Các metric không di chuyển cùng chiều: `retrieval_hit_rate` (đo retrieval) và `judge_accuracy`/`token_f1` (đo answer quality) có thể phản ứng khác nhau, thậm chí ngược nhau, với cùng một loại lỗi dữ liệu — cần đọc nhiều metric cùng lúc thay vì chỉ một con số.
3. Repair-from-raw (build lại từ nguồn gốc thay vì sửa tay bản corrupted) là cách chứng minh phục hồi đáng tin cậy nhất, vì nó loại bỏ hoàn toàn khả năng "sửa số liệu cho đẹp" — kết quả `repaired_metrics.json` khớp chính xác với `baseline_metrics.json` là bằng chứng khách quan.

### Nếu có thêm thời gian

Muốn thêm một corruption scenario "missing latest record" (đã có trong bản đầu tôi viết nhưng bị bỏ khi đồng đội viết lại hàm) song song với 4 kịch bản hiện tại, để đo riêng ảnh hưởng của việc raw ingestion bị thiếu dữ liệu mới nhất lên `freshness_report` — hiện `stale_rows` chỉ phản ánh corruption "làm cũ ngày xuất bản", chưa phản ánh corruption "thiếu hẳn record mới". Cách đo: so `latest_published` giữa baseline và corrupted trước/sau khi thêm lại kịch bản drop-latest-record.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Quang Huy
**Ngày xác nhận:** 2026-08-06
