# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phạm Tiến Đại             |
| MSSV               | 2A202601610                |
| Khóa/Lớp         | K4                        |
| Tên nhóm         | BabyShark                 |
| Vai trò chính    | Data Cleaning & Evaluation Testset |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability-A6-1-BabyShark |
| Ngày hoàn thành | 2026-08-06                |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| **Data Cleaning & Modeling** | `src/ingestion/cleaning.py`<br>- `clean_text()`<br>- `build_clean_dataframe()`<br>- `save_clean_dataset()` | List `PaperRecord` thô từ Ingestion | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Hoàn thành |
| **Frozen Evaluation Testset** | `src/evaluation/testset.py`<br>- `build_test_set()` | Cleaned DataFrame (`papers_clean.json`) | `data/eval/test_set.json` (18 câu hỏi factual) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| **Đóng băng Test Set (Frozen Benchmark)** | Integration & Corruption Team | Đảm bảo bộ 18 câu hỏi test cases không bị thay đổi trong quá trình thử nghiệm baseline, corrupted và repaired để làm thước đo công bằng. |
| **Tự động làm sạch thẻ HTML/XML** | Ingestion & Vector Index Team | Loại bỏ hoàn toàn thẻ dư thừa như `<jats:p>`, `<b>`, `<italic>` trong tiêu đề và tóm tắt, nâng cao chất lượng vector embeddings. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Loại bỏ bản ghi rác & Strip HTML/XML | `src/ingestion/cleaning.py` | Lọc bỏ 100% bản ghi thiếu title hoặc tóm tắt < 100 chars; làm sạch text | `python src/ingestion/cleaning.py` |
| Tính toán Freshness & Cột embedding | `papers_clean.csv`<br>`papers_clean.json` | Tính `age_days`, `published` ISO format, tạo cột `text_for_embedding` | Kiểm tra cột trong `data/clean/papers_clean.csv` |
| Khởi tạo Frozen Evaluation Set | `src/evaluation/testset.py`<br>`data/eval/test_set.json` | Sinh 18 câu hỏi thực tế (summary, authors, date, categories) | `python src/evaluation/testset.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Làm sạch dữ liệu khoa học (Data Cleaning)**: Dữ liệu thô từ Crossref chứa nhiều thẻ HTML/XML rác (`<jats:p>`, `<b>`), danh sách tác giả bị lồng lấp dạng dictionary, ngày xuất bản chưa chuẩn hóa. Cần đưa về dạng bảng chuẩn hóa, lọc bỏ tóm tắt quá ngắn (< 100 ký tự) và tính độ tuổi dữ liệu (`age_days`).
2. **Xây dựng bộ kiểm thử cố định (Frozen Test Set)**: Để so sánh chính xác chất lượng của 3 trạng thái hệ thống (Baseline, Corrupted, Repaired), cần một bộ câu hỏi đánh giá thực tế (18 câu) đóng băng cố định có chứa trực tiếp `ground_truth` và `ground_truth_doc_ids`.

### Cách triển khai
- **Cleaning**:
  - Hàm `clean_text()` sử dụng Regex `re.sub(r"<[^>]+>", " ", text)` để xóa toàn bộ thẻ XML/HTML.
  - Loại bỏ các bản ghi không có `title` hoặc phần `summary` dưới 100 ký tự.
  - Gộp danh sách tác giả thành chuỗi `authors_joined` phân cách bởi dấu phẩy (tương tự với `categories_joined`).
  - Chuyển đổi ngày xuất bản về ISO `YYYY-MM-DD` và tính `age_days = (now_utc - published).days`.
  - Tạo cột biểu diễn ngữ nghĩa `text_for_embedding` bằng cách kết hợp: `Title: [title] | Authors: [authors] | Summary: [summary]`.
- **Evaluation Test Set**:
  - Hàm `build_test_set()` duyệt qua tập dữ liệu làm sạch `papers_clean.json` và tạo ra 18 câu hỏi bao phủ 4 nhóm dạng hỏi: `summary`, `authors`, `date`, `categories`.
  - Mỗi câu hỏi tuân thủ đúng schema: `{"id": "q1", "question_type": "...", "question": "...", "ground_truth": "...", "ground_truth_doc_ids": ["..."]}`.
  - Đóng băng bộ câu hỏi này vào `data/eval/test_set.json`.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | List `PaperRecord` thô; `papers_clean.json` |
| Output | `papers_clean.csv`, `papers_clean.json`, `data/eval/test_set.json` |
| Module phụ thuộc | `core.config`, `core.utils`, `re`, `pandas` |
| Module sử dụng output | `src/retrieval/index.py`, `src/evaluation/metrics.py`, `src/pipelines/phase1.py` |
| Điều kiện lỗi cần xử lý | Thẻ XML/HTML phức tạp lồng nhau, tác giả bị rỗng, ngày xuất bản không đúng định dạng ISO, câu hỏi bị trùng lặp ID. |

### Cách xác minh

```bash
# 1. Kiểm tra module Data Cleaning
python src/ingestion/cleaning.py

# 2. Kiểm tra module Frozen Test Set
python src/evaluation/testset.py
```

- **Kết quả mong đợi:** Lọc sạch 24 bản ghi chuẩn, xuất file CSV/JSON làm sạch không chứa thẻ HTML, và sinh file `data/eval/test_set.json` chứa 18 câu hỏi đóng.
- **Kết quả thực tế:**
  - `papers_clean.csv`: 24 hàng (98.7 KB), 0 thẻ HTML/XML.
  - `test_set.json`: 18 câu hỏi có đầy đủ ground_truth và ground_truth_doc_ids.
- **Artifact/log:**
  - `data/clean/papers_clean.csv`
  - `data/clean/papers_clean.json`
  - `data/eval/test_set.json`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách đại diện thông tin bài báo trong cột ngữ nghĩa `text_for_embedding` phục vụ cho việc nhúng vector vào ChromaDB.
- **Các phương án đã cân nhắc:**
  - *Phương án A:* Chỉ nhúng riêng phần tóm tắt (`summary`).
  - *Phương án B (Lựa chọn):* Nhúng cấu trúc tổng hợp kết hợp: `Title: [title] | Authors: [authors] | Summary: [summary]`.
- **Lý do:**
  - Tiêu đề (`title`) và tác giả (`authors`) chứa nhiều từ khóa factual quan trọng mà người dùng thường hỏi trực tiếp (ví dụ: *"Ai là tác giả của bài báo X?"*). Nếu chỉ nhúng phần summary, vector search sẽ bỏ sót các truy vấn tìm theo tên tác giả hoặc tên bài báo.
- **Bằng chứng quyết định phù hợp:** `retrieval_hit_rate` của hệ thống RAG đạt **95.83%**, giúp RAG Agent dễ dàng tìm trúng tài liệu khi được hỏi về tác giả hoặc tên nghiên cứu.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ModuleNotFoundError: No module named 'core'
  ```
  Xảy ra khi chạy trực tiếp `python src/ingestion/cleaning.py` hoặc `python src/evaluation/testset.py`.

- **Lệnh hoặc bước tái hiện:**
  `python src/ingestion/cleaning.py`

- **Nguyên nhân gốc:** Thư mục `src/` không tự động có sẵn trong `sys.path` của Python khi chạy lệnh từ thư mục gốc của dự án.

- **Cách xử lý:** Thêm đoạn code tự động nạp `sys.path` ở đầu file `cleaning.py` và `testset.py`:
  ```python
  from pathlib import Path
  import sys

  _src_dir = Path(__file__).resolve().parent.parent
  if str(_src_dir) not in sys.path:
      sys.path.insert(0, str(_src_dir))
  ```

- **Cách xác minh sau khi sửa:** Chạy trực tiếp `python src/ingestion/cleaning.py` và `python src/evaluation/testset.py` thành công 100%.

- **Bài học kỹ thuật:** Khi xây dựng các module trong dự án Python nhiều thư mục, cần đảm bảo khả năng nạp path độc lập để mọi script có thể chạy standalone.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Crossref API → Raw Records → Cleaning (strip HTML, filter summary < 100 chars, calc `age_days`) → Tạo cột `text_for_embedding` → MiniLM Vector Embedding → ChromaDB Vector Store.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Test set chứa 18 câu hỏi đi kèm `ground_truth` và `ground_truth_doc_ids`.
   - RAG Agent tìm kiếm vector store trả về `retrieved_doc_ids`.
   - So sánh `ground_truth_doc_ids` với `retrieved_doc_ids` để tính `retrieval_hit_rate`.
   - So sánh câu trả lời sinh ra với `ground_truth` để tính `mean_token_f1` và điểm LLM Judge.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - Quality checks: Đo tính hợp lệ của cấu trúc dữ liệu (số hàng, null, trùng lặp ID, summary ngắn).
   - Freshness monitoring: Đo độ tươi mới của dữ liệu dựa trên ngày xuất bản (tuổi bài báo <= 180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để giữ biến độc lập (câu hỏi) cố định, đảm bảo mọi sự thay đổi của chỉ số RAG hoàn toàn phản ánh sự tác động của chất lượng dữ liệu (Baseline vs Corrupted vs Repaired).

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Data Quality đổi từ `FAILED` → `PASSED`, `stale_rows` giảm về `0`.
   - `mean_token_f1` tăng từ `71.13%` trở lại `96.36%`, `judge_accuracy` tăng từ `58.33%` trở lại `87.50%`.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   95.83% |   100.00% |   95.83% | Hit rate giữ ở mức cao nhờ vector search tiêu đề. |
| `mean_token_f1`      |   96.36% |    71.13% |   96.36% | 🔻 Giảm **25.23%** do lỗi summary rỗng & noise → 🟢 Phục hồi **100%**. |
| `judge_accuracy`     |   87.50% |    58.33% |   87.50% | 🔻 Giảm **29.17%** do thiếu ngữ cảnh trả lời → 🟢 Phục hồi **100%**. |
| `mean_judge_score`   |     4.54 |      3.50 |     4.54 | 🔻 Giảm **1.04 điểm** chất lượng câu trả lời → 🟢 Phục hồi **100%**. |
| Quality checks         |   PASSED |   FAILED  |   PASSED | Corrupted bị FAILED do có short summary, duplicates và stale dates. |
| Freshness status       |    Fresh | Not Fresh |    Fresh | Corrupted phát hiện 6 dòng bị sửa ngày xuất bản về năm 2000. |

### Kết luận từ số liệu

1. **[Data corruption]** (xóa tóm tắt & sửa ngày về 2000) → **[Quality checks FAILED & Not Fresh]** → **[Token F1 giảm 25.23%, Judge Accuracy giảm 29.17%]**.
2. **[Repair action]** (chạy lại cleaning chuẩn từ raw records) → **[Quality checks PASSED & Fresh]** → **[Token F1 và Judge Accuracy phục hồi 100% về 96.36% và 87.50%]**.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Cleaning**: Việc loại bỏ ký tự rác (HTML/XML) và định dạng thông tin ngữ nghĩa đúng chuẩn giúp nâng cao đáng kể độ chính xác của Vector Search.
2. **Về Evaluation**: Xây dựng Frozen Test Set đóng vai trò quyết định trong việc đánh giá và đo lường sự biến động hiệu năng của RAG Agent.
3. **Về Data Quality**: Dữ liệu tóm tắt bị rỗng hoặc lỗi thời làm sụt giảm ngay lập tức chất lượng câu trả lời của LLM.

### Nếu có thêm thời gian

- Tự động hóa quá trình tự động sinh Frozen Test Set đa dạng hơn bằng LLM (Synthetic Testset Generation) với nhiều cấp độ câu hỏi suy luận phức tạp.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Tiến Đại  
**Ngày xác nhận:** 2026-08-06
