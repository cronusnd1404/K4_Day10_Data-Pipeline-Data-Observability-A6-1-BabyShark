# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Bùi Ngọc Đạt             |
| MSSV               | 01710                     |
| Khóa/Lớp         | K4                        |
| Tên nhóm         | BabyShark                 |
| Vai trò chính    | Ingestion Lead & Pipeline Integration |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability-A6-1-BabyShark |
| Ngày hoàn thành | 2026-08-06                |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| **Source Ingestion** | `src/ingestion/crossref.py`<br>- `fetch_source_records()`<br>- `parse_crossref_payload()`<br>- `load_raw_records()` | Crossref REST API (`https://api.crossref.org/works`) + `Settings` | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Hoàn thành |
| **Pipeline Integration & Orchestration** | `src/pipelines/phase1.py`<br>`src/pipelines/corruption_flow.py`<br>`script/run_phase1.py`<br>`script/run_corruption_flow.py` | Code của các thành viên (Cleaning, Retrieval, Eval, Observability) | End-to-end Baseline Pipeline & Corruption Comparison Flow | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| **Tự động hóa Module Import** | Tất cả thành viên trong nhóm | Bổ sung logic tự động nạp `src` vào `sys.path` ở đầu tất cả các module, xử lý triệt để lỗi `ModuleNotFoundError: No module named 'core'` cho nhóm khi chạy script trực tiếp. |
| **Fix lỗi HTTP 429 Rate Limit** | Observability & Evaluation | Thêm Pacing Delay `time.sleep(2.5)` và Retry back-off giúp pipeline chạy không bị sập do giới hạn RPM của API. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng module Ingestion Crossref API | `src/ingestion/crossref.py` | Lấy thành công 24 bản ghi chất lượng có đầy đủ title & abstract | `python src/ingestion/crossref.py` |
| Lưu trữ Raw Artifacts kép | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | 1 file raw HTTP response nguyên bản (audit) + 1 file flat JSON list | Kiểm tra dung lượng file trong `data/raw/` |
| Triển khai Baseline Pipeline | `src/pipelines/phase1.py`<br>`script/run_phase1.py` | Kết nối 8 bước ETL → Vector Store → Eval → Observability → Report | `python script/run_phase1.py` |
| Triển khai Corruption & Repair Flow | `src/pipelines/corruption_flow.py`<br>`script/run_corruption_flow.py` | Tự động hóa quá trình Corrupt → Evaluate → Repair → Re-evaluate | `python script/run_corruption_flow.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Thu nhập dữ liệu thô (Ingestion)**: Cần gọi API công khai Crossref để lấy danh sách bài báo khoa học theo từ khóa, lọc chỉ lấy bài báo có đầy đủ tiêu đề và tóm tắt, tự động retry khi bị dính rate limit (429/503), và lưu trữ nguyên bản để phục vụ việc kiểm toán (audit) cũng như làm sạch (cleaning).
2. **Triển khai & Tích hợp Pipeline (Pipeline Orchestration)**: Tích hợp các khối độc lập do từng thành viên trong nhóm phát triển (Ingestion, Data Cleaning, ChromaDB Vector Store, Frozen Test Set, RAG Evaluation, Data Quality & Freshness) thành 2 pipeline hoàn chỉnh có thể thực thi đơn giản bằng 1 lệnh duy nhất.

### Cách triển khai
- **Ingestion**:
  - Khởi tạo hàm `fetch_source_records()` gửi query parameter và filter `has-abstract:true` đến Crossref REST API.
  - Sử dụng vòng lặp retry tối đa 5 lần với exponential back-off (`2s → 5s → 10s → 30s → 60s`) khi gặp status code `429` hoặc `503`.
  - Hàm `parse_crossref_payload()` bóc tách DOI, title, abstract (bỏ thẻ HTML/XML bằng Regex), authors, dates, URLs và loại bỏ bản ghi thiếu DOI/title/abstract.
  - Lưu response thô nguyên bản vào `data/raw/crossref_response.json` và list `PaperRecord` đã parse vào `data/raw/crossref_records.json`.
- **Pipeline Orchestration**:
  - Xây dựng `phase1.py` kết nối 8 bước: Fetch/Load Raw → Clean Data → Build ChromaDB Index → Generate Frozen Testset → Evaluate RAG → Data Quality & Freshness → Export Markdown Report.
  - Xây dựng `corruption_flow.py` kết nối 8 bước: Load Corrupted Data → Build Corrupted Index → Evaluate Corrupted → Repair from Raw Records → Build Repaired Index → Evaluate Repaired → Data Observability → Export Comparison Report.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Request params (`source_query`, `source_filter`, `max_results`) từ `Settings` |
| Output | List `PaperRecord` objects; File `crossref_response.json`, `crossref_records.json`, `phase1_report.md`, `corruption_report.md` |
| Module phụ thuộc | `core.config`, `core.utils`, `requests`, `pandas`, `chromadb` |
| Module sử dụng output | `src/ingestion/cleaning.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Server rate limit (HTTP 429/503), lỗi mạng, record thiếu DOI/title/summary, lỗi `ModuleNotFoundError` khi import module giữa các folder. |

### Cách xác minh

```bash
# 1. Kiểm tra module Ingestion
python src/ingestion/crossref.py

# 2. Thực thi Baseline Pipeline end-to-end
python script/run_phase1.py

# 3. Thực thi Corruption & Repair Flow
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Tự động crawl 24 bài báo khoa học, lưu đầy đủ 2 file raw JSON, chạy xong Baseline Pipeline thu được Hit Rate > 90%, Token F1 > 90%, và chạy Corruption Flow tạo được báo cáo so sánh đối chiếu 3 trạng thái.
- **Kết quả thực tế:**
  - Ingestion: Fetched 24 records thành công.
  - Phase 1 Baseline: `Hit Rate = 95.83%`, `Token F1 = 96.36%`, `Judge Accuracy = 87.50%`, `Quality = PASSED`.
  - Phase 2 Corruption: `Token F1` sụt giảm từ `96.36%` xuống `71.13%` (Quality = FAILED); sau khi Repair từ raw records đã phục hồi lại `96.36%` (Quality = PASSED).
- **Artifact/log:**
  - `data/raw/crossref_response.json`
  - `data/raw/crossref_records.json`
  - `data/reports/phase1_report.md`
  - `data/reports/corruption_report.md`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cấu trúc lưu trữ dữ liệu thô (raw data) sau khi gọi API từ Crossref.
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Chỉ lưu 1 file duy nhất chứa danh sách bản ghi đã parse sẵn (flat structure).
  - *Phương án B (Lựa chọn):* Lưu song song 2 dạng raw artifacts: Dạng 1 (`crossref_response.json`) lưu toàn bộ HTTP response nguyên bản từ API; Dạng 2 (`crossref_records.json`) lưu danh sách các bản ghi đã parse chuẩn hóa theo `PaperRecord`.
- **Lý do:**
  - *Data Auditing & Traceability:* File Dạng 1 giúp đội ngũ Data Engineering có thể kiểm toán nguồn dữ liệu gốc nếu API thay đổi schema hoặc cần debug thông tin chưa parse.
  - *Reusability & Performance:* File Dạng 2 giúp các bước Data Cleaning và Data Repair có thể đọc ngay danh sách cấu trúc phẳng mà không cần parse lại toàn bộ JSON thô phức tạp từ đầu.
- **Bằng chứng quyết định phù hợp:** Việc phục hồi dữ liệu trong `corruption_flow.py` chạy trực tiếp từ `crossref_records.json` chỉ mất `0.02s` mà vẫn đảm bảo tính toàn vẹn 100% so với bản gốc.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ModuleNotFoundError: No module named 'core'
  ```
  Xảy ra khi các thành viên đứng ở các thư mục con hoặc chạy lệnh `python src/ingestion/crossref.py` / `python src/evaluation/testset.py` trực tiếp trong terminal mà chưa cài đặt package ở chế độ editable (`pip install -e .`).

- **Lệnh hoặc bước tái hiện:**
  `python src/ingestion/crossref.py` hoặc `python src/ingestion/cleaning.py`

- **Nguyên nhân gốc:** Khi chạy script bằng `python path/to/script.py`, Python mặc định chỉ nạp thư mục chứa script đó vào `sys.path` chứ không tự động nạp thư mục `src/`, dẫn đến các lệnh `from core.config import ...` không tìm thấy package `core`.

- **Cách xử lý:** Thêm đoạn mã tự động phát hiện và đưa thư mục cha `src` vào `sys.path` ở đầu tất cả các file module Python:
  ```python
  from pathlib import Path
  import sys

  _src_dir = Path(__file__).resolve().parent.parent
  if str(_src_dir) not in sys.path:
      sys.path.insert(0, str(_src_dir))
  ```

- **Cách xác minh sau khi sửa:** Chạy trực tiếp bất kỳ file nào trong `src/ingestion/`, `src/evaluation/`, `src/retrieval/`, `src/pipelines/` từ mọi vị trí làm việc đều thực thi thành công không còn lỗi.

- **Bài học kỹ thuật:** Luôn chủ động quản lý đường dẫn import (`sys.path`) cho các module Python trong dự án để đảm bảo tính sẵn sàng (portable & standalone execution) cho các thành viên khác khi phát triển.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Crossref API → Raw HTTP Response → Parsing `PaperRecord` → Cleaning (lọc summary < 100 chars, strip HTML, tính `age_days`, gộp authors/categories) → Tạo cột `text_for_embedding` → SentenceTransformer MiniLM sinh vector 384-dim → Lưu vĩnh viễn vào ChromaDB vector store + file manifest JSON.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Evaluation set chứa các câu hỏi đóng kèm `ground_truth` và `ground_truth_doc_ids`.
   - Với mỗi câu hỏi: RAG Agent truy vấn vector store trả về danh sách `retrieved_doc_ids`.
   - `retrieval_hit_rate` kiểm tra xem `ground_truth_doc_ids` có nằm trong `retrieved_doc_ids` hay không.
   - `mean_token_f1` và LLM Judge so sánh mức độ trùng khớp ngữ nghĩa giữa câu trả lời sinh ra (`answer`) và `ground_truth`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks**: Kiểm tra tính toàn vẹn và hợp lệ của cấu trúc dữ liệu (số dòng, trùng lặp `paper_id`, trường bị `null`, summary bị rỗng/quá ngắn).
   - **Freshness monitoring**: Kiểm tra khoảng cách thời gian từ ngày xuất bản (`published`) đến hiện tại (`age_days`), phát hiện dữ liệu quá cũ (stale data > 180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo tính công bằng (apples-to-apples comparison) và tạo ra một **Frozen Evaluation Set**. Việc giữ nguyên bộ câu hỏi và ground truth giúp phản ánh đúng 100% sự biến động của metrics RAG hoàn toàn do chất lượng dữ liệu thay đổi chứ không do độ khó câu hỏi thay đổi.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Artifacts**: Báo cáo Data Quality đổi từ `FAILED` → `PASSED`, `stale_rows` giảm từ `6` → `0`, file `papers_clean_repaired.csv` khớp dữ liệu gốc.
   - **Metrics**: `mean_token_f1` tăng từ `71.13%` trở lại `96.36%`, `judge_accuracy` tăng từ `58.33%` trở lại `87.50%`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   95.83% |   100.00% |   95.83% | Vector search bằng MiniLM vẫn tìm trúng doc do tiêu đề trùng khớp. |
| `mean_token_f1`      |   96.36% |    71.13% |   96.36% | 🔻 Sụt giảm mạnh **25.23%** do lỗi summary rỗng & noise → 🟢 Phục hồi **100%**. |
| `judge_accuracy`     |   87.50% |    58.33% |   87.50% | 🔻 Sụt giảm mạnh **29.17%** do thiếu thông tin trả lời → 🟢 Phục hồi **100%**. |
| `mean_judge_score`   |     4.54 |      3.50 |     4.54 | 🔻 Sụt giảm **1.04 điểm** chất lượng câu trả lời → 🟢 Phục hồi **100%**. |
| Quality checks         |   PASSED |   FAILED  |   PASSED | Corrupted bị FAIL do có 6 stale dates, 6 summary rỗng và 4 duplicates. |
| Freshness status       |    Fresh | Not Fresh |    Fresh | Corrupted có 6 dòng bị sửa ngày về năm 2000 (`2000-01-01`). |

### Kết luận từ số liệu

1. **[Data corruption]** (làm rỗng summary & sửa ngày về năm 2000) → **[quality/freshness signal ghi nhận FAILED & Not Fresh]** → **[Token F1 giảm từ 96.36% down 71.13%, Judge Accuracy giảm từ 87.50% down 58.33%]**.
2. **[Repair action]** (chạy lại ETL clean từ raw records) → **[quality/freshness signal phục hồi PASSED & Fresh]** → **[Token F1 và Judge Accuracy phục hồi 100% về mức baseline 96.36% và 87.50%]**.

- **Corruption nào ảnh hưởng rõ nhất và vì sao?**
  - Kịch bản **Blank Summary** ảnh hưởng nghiêm trọng nhất. Khi phần tóm tắt bị gán thành rỗng, RAG Agent không thể trích xuất thông tin thực tế để trả lời câu hỏi, dẫn đến `mean_token_f1` và `judge_accuracy` bị sụt giảm nặng nề.

- **Kết quả nào khác với kỳ vọng ban đầu?**
  - Ban đầu kỳ vọng `retrieval_hit_rate` của trạng thái Corrupted sẽ giảm, nhưng thực tế nó tăng lên `100.00%`. Lý do là các câu hỏi test có chứa tên bài báo trong dấu nháy đơn, và phép nhân đôi bản ghi (duplicates) vô tình tăng mật độ xuất hiện của tài liệu trong ChromaDB. Tuy nhiên, chất lượng câu trả lời (`Token F1` và `Judge Score`) lại bị giảm sâu do nội dung bên trong bị hỏng.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline**: Data Pipeline cần tuân thủ nguyên tắc lưu trữ Raw Data nguyên bản và có khả năng tự phục hồi (Idempotent ETL) từ nguồn dữ liệu thô ban đầu.
2. **Về Data Observability**: Tín hiệu cảnh báo dữ liệu (Quality & Freshness checks) là tấm lưới chắn quan trọng giúp phát hiện dữ liệu hỏng trước khi dữ liệu xấu làm hỏng trải nghiệm người dùng cuối.
3. **Về RAG Agent**: Chất lượng câu trả lời của RAG Agent phụ thuộc hoàn toàn vào chất lượng dữ liệu đầu vào (*Garbage In, Garbage Out*). Dù LLM có mạnh đến đâu, dữ liệu bị thiếu hoặc nhiễu sẽ làm suy giảm trực tiếp hiệu năng của Agent.

### Nếu có thêm thời gian

- Xây dựng cơ chế tự động gửi cảnh báo (Slack/Email Webhook) ngay khi hệ thống Observability ghi nhận tín hiệu `Quality FAILED` hoặc `Stale Data`, đồng thời tự động kích hoạt trigger tự làm sạch (Auto-repair workflow).

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Bùi Ngọc Đạt  
**Ngày xác nhận:** 2026-08-06
