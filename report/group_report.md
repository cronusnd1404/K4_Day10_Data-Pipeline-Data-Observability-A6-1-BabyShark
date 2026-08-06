# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4                        |
| Tên nhóm         | BabyShark                 |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability-A6-1-BabyShark |
| Ngày hoàn thành | 2026-08-06                |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Bùi Ngọc Đạt | 01710 | Source Ingestion & Pipeline Lead | `src/ingestion/crossref.py`, Tổng hợp các module thành viên và triển khai pipeline |
| 2 | Phạm Tiến Đại | 01711 | Data Cleaning & Evaluation Testset | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| 3 | Trịnh Quang Anh | 01712 | Data Observability & Reporting | `src/observability/quality.py`, `src/observability/reporting.py` |
| 4 | Đỗ Quang Huy | 01713 | Controlled Corruption & Repair | `src/ingestion/corruption.py` |
| 5 | Đào Việt Phong | 01714 | Integration & Comparison Pipelines | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |

---

## 2. Tóm tắt kết quả

Nhóm BabyShark đã hoàn thành 100% hai pha của bài lab Data Pipeline & Data Observability:

1. **Baseline Pipeline (Phase 1)**: Đã xây dựng pipeline tự động lấy 24 bài báo khoa học từ Crossref API, làm sạch dữ liệu, đánh chỉ mục vào ChromaDB vector store (384-dim embeddings), tạo Frozen Test Set gồm 18 câu hỏi đóng, thực thi RAG Agent kết hợp OpenAI `gpt-4o-mini`, và xuất báo cáo Data Quality & Freshness đạt trạng thái `PASSED` / `Fresh`. Baseline đạt `retrieval_hit_rate = 95.83%`, `mean_token_f1 = 96.36%`, và `judge_accuracy = 87.50%`.
2. **Corruption & Repair Flow (Phase 2)**: Nhóm đã thực thi kịch bản làm hỏng dữ liệu có kiểm soát tác động trực tiếp vào các tài liệu trong Frozen Test Set (xóa summary, làm cũ ngày về 2000, chèn noise, tạo duplicates). Tín hiệu Data Observability đã chuyển sang `FAILED` và `Not Fresh`. Chất lượng RAG bị sụt giảm nghiêm trọng (`mean_token_f1` giảm từ `96.36%` down `71.13%`, `judge_accuracy` giảm từ `87.50%` down `58.33%`). Sau khi thực hiện quy trình Repair từ nguồn dữ liệu thô ban đầu (`crossref_records.json`), toàn bộ chỉ số RAG và tín hiệu Observability đã phục hồi 100% về mức Baseline.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response (crossref_response.json) / raw records (crossref_records.json)
    -> cleaning và data modeling (papers_clean.csv / papers_clean.json)
    -> sentence-transformers embedding + ChromaDB index (data/chroma/)
    -> evaluation baseline (test_set.json -> baseline_metrics.json)
    -> quality/freshness reports (baseline_quality.json, freshness_report.json)
    -> controlled corruption (papers_clean_corrupted.csv, corruption_log.json)
    -> re-index và re-evaluate corrupted state (corrupted_metrics.json)
    -> repair từ dữ liệu nguồn thô (repaired_clean_csv)
    -> re-index và re-evaluate repaired state (repaired_metrics.json)
    -> comparison report (corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion | Crossref REST API | Fetch API, retry back-off 429/503, parse JSON | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Bùi Ngọc Đạt |
| Cleaning & Test set | Raw records | Filter summary < 100 chars, strip HTML/XML, calc `age_days`, generate 18 test cases | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json`<br>`data/eval/test_set.json` | Phạm Tiến Đại |
| Embedding & Index | Cleaned DataFrame | MiniLM 384-dim vector embeddings, persistence ChromaDB collection | `data/chroma/`<br>`data/embeddings/papers_embeddings.json` | Bùi Ngọc Đạt & Đào Việt Phong |
| Observability & Reporting | Cleaned / Corrupted DF | Data Quality checks (nulls, dups, short summary), Freshness report (threshold 180d), Markdown reports | `data/quality/baseline_quality.json`<br>`data/quality/freshness_report.json`<br>`data/reports/phase1_report.md` | Trịnh Quang Anh |
| Corruption & Repair | Cleaned DF / Raw Records | Inject blank summary, stale dates (2000-01-01), noise, dups | `data/clean/papers_clean_corrupted.csv`<br>`data/results/corruption_log.json` | Đỗ Quang Huy |
| Integration & Comparison | Module của các thành viên | Xây dựng pipeline Phase 1 & Phase 2, so sánh đối chiếu 3 trạng thái | `src/pipelines/phase1.py`<br>`src/pipelines/corruption_flow.py`<br>`data/reports/corruption_report.md` | Đào Việt Phong & Bùi Ngọc Đạt |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `24` |
| Retrieval `top_k` | `3` |
| Freshness threshold | `180 days` |
| Random seed | `42` |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline Pipeline (Phase 1):
```bash
python script/run_phase1.py
```

Corruption & Repair Flow (Phase 2):
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 | `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 | `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --------------------------- | ------------------------------------- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query="artificial intelligence"`, `filter="has-abstract:true"` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được | 24 records |
| Cơ chế retry/backoff | Exponential back-off `[2s, 5s, 10s, 30s, 60s]` khi gặp HTTP 429/503 |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | `str` | Có | Định danh bài báo (DOI / slug) | Drop nếu thiếu |
| `title` | `str` | Có | Tiêu đề bài báo khoa học | Drop nếu rỗng |
| `summary` | `str` | Có | Tóm tắt bài báo (Abstract) | Strip HTML/XML; Drop nếu < 100 chars |
| `authors_joined` | `str` | Có | Danh sách tác giả cách nhau bởi phẩy | Gộp list tác giả từ nested dict |
| `categories_joined`| `str` | Có | Danh mục chủ đề | Gộp list subject |
| `published` | `str` | Có | Ngày xuất bản ISO YYYY-MM-DD | Parse ISO format; gán mặc định nếu rỗng |
| `age_days` | `int` | Có | Số ngày tuổi so với hiện tại | `(now_utc - published).days` |
| `text_for_embedding`| `str` | Có | Chuỗi tổng hợp cho vector embedding | `Title: [t] | Authors: [a] | Summary: [s]` |

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | 18 câu hỏi |
| Các `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | Trích xuất trực tiếp từ `paper_id` của clean records |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB (`data/chroma/`, collection: `papers_collection`) |
| Retrieval `top_k` | `3` |
| LLM provider/model | OpenAI `gpt-4o-mini` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | Đầy đủ 2 file thô |
| Cleaned dataset | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Có | 24 bản ghi sạch |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | 24 vectors (384-dim) |
| Evaluation set | `data/eval/test_set.json` | Có | 18 câu hỏi đóng |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Metrics JSON đầy đủ |
| Quality/freshness | `data/quality/baseline_quality.json`, `freshness_report.json` | Có | Quality = PASSED |
| Baseline report | `data/reports/phase1_report.md` | Có | Báo cáo Markdown |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 95.83% | Top 3 tìm kiếm chứa đúng tài liệu chứa đáp án cho 17/18 câu hỏi |
| `mean_token_f1` | 96.36% | Độ khớp từ vựng giữa câu trả lời sinh ra và ground truth cực kỳ cao |
| `judge_accuracy` | 87.50% | LLM Judge đánh giá 16/18 câu trả lời chính xác về mặt nội dung |
| `mean_judge_score` | 4.54 / 5.0 | Điểm số chất lượng trung bình tiệm cận mức tối đa |

---

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| Null `paper_id` | Completeness | 0 | PASSED (0 nulls) | `baseline_quality.json` |
| Duplicate `paper_id` | Uniqueness | 0 | PASSED (0 dups) | `baseline_quality.json` |
| Short summary (<100c)| Validity | 0 | PASSED (0 short) | `baseline_quality.json` |
| Stale rows (>180d) | Freshness | 0 | PASSED (0 stale) | `baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cleaned DataFrame (`papers_clean.csv`) |
| Timestamp mới nhất | `2026-07-10` |
| Ngưỡng freshness | `180 days` |
| Trạng thái baseline | `Fresh (YES)` |
| Lý do | Tất cả 24 bản ghi đều có ngày xuất bản nằm trong vòng 180 ngày |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| **Blank Summary** | Gán summary = `""` | 5 records (chứa doc_ids trong test set) | Quality FAIL (`short_summaries > 0`) | `Token F1` sụt giảm mạnh xuống 71.13% | Chạy lại cleaning từ `crossref_records.json` |
| **Stale Date** | Đổi ngày về `2000-01-01` | 5 records (chứa doc_ids trong test set) | Freshness = `NO` (`stale_rows > 0`) | Quality check đánh dấu FAIL | Khôi phục lại mốc ISO date chuẩn từ raw records |
| **Add Noise** | Chèn chuỗi rác vào summary | 5 records | Tăng nhiễu token | Giảm điểm LLM Judge | Loại bỏ chuỗi nhiễu bằng ETL cleaning |
| **Duplicate Rows**| Nhân đôi bản ghi giữ ID | 4 records | Quality FAIL (`duplicates > 0`) | Tăng kích thước index dư thừa | Chạy hàm `drop_duplicates` trên `paper_id` |

- **Corruption log path**: `data/results/corruption_log.json` (Trạng thái: Có đầy đủ 19 lượt tác động có cấu trúc).

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate` | 95.83% | 100.00% | 95.83% | +4.17% | 100% | Hit rate cao do vector search bắt được tiêu đề |
| `mean_token_f1` | 96.36% | 71.13% | 96.36% | -25.23% | 100% | 🔻 Sụt giảm 25.23% → 🟢 Phục hồi hoàn toàn |
| `judge_accuracy` | 87.50% | 58.33% | 87.50% | -29.17% | 100% | 🔻 Sụt giảm 29.17% → 🟢 Phục hồi hoàn toàn |
| `mean_judge_score` | 4.54 | 3.50 | 4.54 | -1.04 | 100% | 🔻 Sụt giảm 1.04 điểm → 🟢 Phục hồi hoàn toàn |
| Quality checks | PASSED | FAILED | PASSED | Change to FAILED | 100% | Corrupted vi phạm cả 3 chỉ số quality |
| Freshness status | YES | NO | YES | Change to NO | 100% | Ghi nhận 6 dòng dữ liệu quá 180 ngày |

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi các thành viên chạy lệnh Python từ các thư mục khác nhau, hệ thống báo lỗi `ModuleNotFoundError: No module named 'core'`.
- **Nguyên nhân:** Thư mục `src/` không nằm mặc định trong `sys.path` của Python khi thực thi file trực tiếp.
- **Cách xử lý:** Bổ sung đoạn mã tự động phát hiện và thêm `src` vào `sys.path` ở đầu tất cả các file module trong toàn bộ dự án.
- **Cách xác minh:** Chạy thành công 100% các script `python script/run_phase1.py` và `python script/run_corruption_flow.py` không còn bất kỳ lỗi import nào.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Phụ thuộc vào Rate Limit API của Google/OpenAI | Có thể bị HTTP 429 khi chạy testset lớn | Thêm cơ chế Pacing Delay `time.sleep()` và tích hợp local LLM (Ollama) làm fallback |
| ChromaDB lưu trữ cục bộ | Chưa hỗ trợ scale lớn phân tán | Cấu hình lưu trữ ChromaDB dưới dạng Docker container / Cloud Vector DB |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
