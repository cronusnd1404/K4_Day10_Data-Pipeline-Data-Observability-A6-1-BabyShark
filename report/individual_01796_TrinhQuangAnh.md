# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trịnh Quang Anh |
| MSSV               | 2A202601796        |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | A6-1-BabyShark             |
| Vai trò chính    | Thành viên 3 — Observability & Reporting (`quality.py`, `reporting.py`) |
| Repository         | https://github.com/cronusnd1404/K4_Day10_Data-Pipeline-Data-Observability-A6-1-BabyShark |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Data quality checks | `src/observability/quality.py` → `run_data_quality_checks()` | cleaned DataFrame + `Settings` | JSON report trong `data/quality/` | **Hoàn thành**  |
| Freshness monitoring | `src/observability/quality.py` → `build_freshness_report()` | cleaned DataFrame + `Settings` | `data/quality/freshness_report.json` | **Hoàn thành**  |
| Markdown reporting | `src/observability/reporting.py` → `generate_phase1_report()`, `generate_corruption_report()` | source summary, metrics, quality, freshness (dict) | `data/reports/phase1_report.md`, `corruption_report.md` | **Hoàn thành**  |
| Frozen evaluation set | `src/evaluation/testset.py` → `build_test_set()` | `data/clean/papers_clean.json` | `data/eval/test_set.json` (24 sample) | **Hoàn thành** — đã sinh và validate |
| Chạy end-to-end 3 trạng thái | `script/run_phase1.py`, `script/run_corruption_flow.py` | repo sau merge + `.env` | `data/results/*_metrics.json`, `*_answers.json`, `data/quality/*.json`, `data/reports/*.md` | **Hoàn thành** — baseline, corrupted, repaired đều chạy trọn vẹn, judge là LLM thật (0/24 fallback ở cả ba) |
| Gỡ blocker môi trường | `.venv/pywin/` | venv dựng trên nền Anaconda | interpreter nạp được torch + ChromaDB | **Hoàn thành** — chi tiết ở mục 6 |
| Xác minh artifact CP1 | `data/raw/`, `data/clean/`, `data/eval/` | artifact của TV1 + TV2 | biên bản kiểm tra lineage + schema | **Hoàn thành** |

Ba module đầu bảng đã hết `NotImplementedError` và sinh được artifact thật. Code hiện tại trong repo đến từ commit `cc821e5` ("Checkpoint C3 done"); phần đóng góp của tôi trên ba module này nằm ở tầng vận hành và kiểm chứng — gỡ blocker khiến pipeline không chạy được, chạy trọn vẹn cả ba trạng thái, và đối chiếu từng con số ở mục 8 với artifact tương ứng.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------ | ------------------------------------ | ---------- |
| Cài đặt và sửa lỗi `build_test_set()` | TV2 — `src/evaluation/testset.py` | Sinh được `data/eval/test_set.json` 24 sample, sửa 4 lỗi làm sai lệch metrics |
| Kiểm tra lineage raw → clean | TV1, TV2 — `data/raw/`, `data/clean/` | Xác nhận 24 → 24 record, drop 0, `paper_id` unique, CSV/JSON khớp nhau |
| Phát hiện `categories_joined` null 100% | TV1 — `crossref.py` | Crossref không trả field `subject`; nhánh `"what categories"` trong `qa.py` thành code chết |
| Phát hiện prefix JATS còn trong `summary` | TV2 — `cleaning.py` | 8/24 row còn `"Abstract "` / `"Summary "` ở đầu abstract |
| Khôi phục sau merge làm mất artifact | TV5 và cả nhóm | Xác định `origin/main@2c0b847` đã revert `cleaning.py`, `corruption.py` và xoá `data/clean/*`; xác định cách khôi phục |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | --------------- |
| Sinh frozen evaluation set 24 câu trên 6 paper | `src/evaluation/testset.py`, `data/eval/test_set.json` | 24 sample đúng schema, `id` liên tục `q1..q24`, `question_type = "factual"` | `./.venv/Scripts/python.exe src/evaluation/testset.py` |
| Kiểm chứng `ground_truth` khớp evaluator | `src/retrieval/qa.py` (`_extract_answer`) | 24/24 sample khớp nhánh harness sẽ chọn | Script mô phỏng thứ tự nhánh của `_extract_answer`, so từng `ground_truth` |
| Sửa 4 lỗi làm sai lệch metrics | `src/evaluation/testset.py` | Không còn `ground_truth` rỗng hoặc `"nan"` | Test trên DataFrame synthetic 7 row cắm sẵn case xấu → `ALL CHECKS PASSED` |
| Xác minh minh chứng CP1 | `data/raw/`, `data/clean/`, `data/eval/` | Bảng kiểm tra size, số record, lineage, tính hợp lệ | Đọc và parse từng file, đối chiếu tập `paper_id` giữa 3 tầng |
| Xác định coverage của test set so với corpus | `data/eval/test_set.json` vs `data/clean/papers_clean.json` | 6/24 paper (25% corpus), đúng là 6 paper mới nhất | So `set(df.head(6).paper_id)` với tập `ground_truth_doc_ids` |
| Truy vết nguyên nhân mất artifact sau `git pull` | `data/clean/`, `src/ingestion/cleaning.py` | Xác định commit gây lỗi và cách khôi phục | `git status`, `git log --graph`, `git grep -n "NotImplementedError" -- src/` |
| Chạy trọn ba trạng thái và thu số liệu mục 8 | `script/run_phase1.py`, `script/run_corruption_flow.py` | 3 bộ metrics + 3 bộ quality/freshness + 2 markdown report | `./.venv/pywin/python.exe script/run_phase1.py` rồi `script/run_corruption_flow.py`; kiểm tra `judge.reasoning` không chứa `"Fallback heuristic"` |
| Truy nguyên `WinError 1114` chặn toàn bộ pipeline | `.venv/pywin/` | torch nạp được, không sửa file nào của Anaconda | So version `VCRUNTIME140.dll` giữa `D:\App\anaconda` và `System32`; nạp thử `c10.dll` bằng `ctypes` |

Nêu một output cụ thể mà phần việc của tôi tạo ra hoặc giúp xác minh:

`data/eval/test_set.json` — 10.9 KB, 24 sample, 6 paper. Đây là mốc cố định cho toàn bộ phần so sánh baseline / corrupted / repaired. Tôi xác minh được mọi `ground_truth_doc_ids` tồn tại **đồng thời** trong `data/clean/papers_clean.json` và `data/raw/crossref_records.json`. Điều kiện thứ hai quan trọng riêng cho pha repair: mọi paper bị corruption xoá đều còn nguồn để dựng lại, nên repair là khả thi về mặt dữ liệu chứ không chỉ về mặt code.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Bài lab so sánh cùng một agent trên ba trạng thái dữ liệu. Phép so sánh chỉ có giá trị khi bộ câu hỏi, ground truth, evaluator và `top_k` đều giữ nguyên. Nếu bộ câu hỏi trôi theo dữ liệu thì delta metrics trộn hai nguyên nhân — dữ liệu xấu đi hay câu hỏi khó lên — và không quy được trách nhiệm cho nguyên nhân nào.

Cạm bẫy cụ thể trong repo này: `build_test_set()` trích `ground_truth` **từ chính DataFrame truyền vào**. Nếu sinh lại test set từ dữ liệu đã corrupt thì `ground_truth` sẽ là summary đã bị blank và title đã bị truncate. Hệ thống hỏng được chấm bằng đáp án hỏng, và nó đạt điểm cao. Corruption trở nên vô hình.

### Cách triển khai

Ba quyết định chính:

**Câu hỏi phải khớp evaluator.** `retrieval/qa.py::_extract_answer` không phải LLM tự do, nó là chuỗi `if` match keyword tiếng Anh theo thứ tự: `who authored` / `list the authors` → trả `authors_joined`; `when was` / `publication date` / `published on` → trả `published`; `what categories` → trả `categories_joined`; không khớp gì → trả `first_sentence(summary)`. Vì vậy `ground_truth` của mỗi câu phải lấy đúng field mà nhánh tương ứng trả về. Tôi thêm hàm `_harness_branch()` mô phỏng lại đúng thứ tự đó, và `_add()` chỉ ghi sample khi câu hỏi rơi đúng nhánh nhắm tới — chặn trường hợp title tự chứa từ khoá làm câu hỏi bị đọc sai nhánh.

**Hai nhóm câu hỏi có độ nhạy khác nhau.** Nhóm thứ nhất bọc title trong dấu nháy đơn, kích hoạt exact lookup ở `qa.py:33` nên retrieval xác định, dùng để đo chất lượng câu trả lời. Nhóm thứ hai (`Which indexed paper studies <chủ đề>...`) không bọc title nên bỏ qua exact lookup, buộc hệ thống dùng semantic retrieval thật. Nhóm thứ hai nhạy hơn với corruption embedding, nên nó là bằng chứng mạnh hơn cho phần so sánh.

**Lọc row không tạo được ground truth kiểm chứng được.** `_is_usable()` loại row thiếu `paper_id`/`title`/`summary`, row có `summary` ngắn hơn 120 ký tự, và row có title chứa dấu nháy đơn — vì `re.search(r"'([^']+)'", question)` trong `qa.py` sẽ bắt sai đoạn text khi title có apostrophe.

Chọn paper là deterministic (6 row đầu của clean DataFrame đã sort theo `published` giảm dần), không dùng random, để bộ câu hỏi thật sự đóng băng.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | ------- |
| Input | `data/clean/papers_clean.json` → DataFrame 24 row, 16 cột. Các cột được dùng: `paper_id`, `title`, `summary`, `authors_joined`, `published`, `categories_joined` |
| Output | `data/eval/test_set.json` — list 24 object, mỗi object gồm `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| Module phụ thuộc | `ingestion/cleaning.py` (sinh clean schema), `core/utils.py` (`first_sentence`, `write_json`, `normalize_whitespace`), `core/config.py` (`paths.eval_testset`) |
| Module sử dụng output | `evaluation/metrics.py::evaluate_pipeline` đọc test set để tính `retrieval_hit_rate` / `token_f1` / judge; `pipelines/phase1.py` và `pipelines/corruption_flow.py` gọi lại cùng file |
| Điều kiện lỗi cần xử lý | Cột `authors_joined`/`categories_joined` chưa tồn tại (fallback sang `authors`/`categories`/`primary_category`); giá trị `NaN` (là truthy trong Python, sẽ sinh `ground_truth = "nan"` nếu không lọc); title chứa apostrophe; `summary` rỗng hoặc quá ngắn; corpus nhỏ hơn `MIN_DOCUMENTS`; sinh ra ít hơn `MIN_QUESTIONS` sample; `ground_truth_doc_ids` trỏ tới `paper_id` không tồn tại |

### Cách xác minh

```bash
# 1. Sinh test set từ clean data thật
./.venv/Scripts/python.exe src/evaluation/testset.py

# 2. Kiểm tra syntax
./.venv/Scripts/python.exe -m py_compile src/evaluation/testset.py

# 3. Đối chiếu từng ground_truth với nhánh mà _extract_answer sẽ chọn,
#    kiểm tra schema, tính liên tục của id, và sự tồn tại của mọi doc_id
./.venv/Scripts/python.exe -c "<script đối chiếu test_set.json vs papers_clean.json>"

# 4. Kiểm tra module nào còn là stub
git grep -n "NotImplementedError" -- src/

# 5. Chạy trọn ba trạng thái (cần interpreter đã gỡ blocker DLL, xem mục 6)
./.venv/pywin/python.exe script/run_phase1.py
./.venv/pywin/python.exe script/run_corruption_flow.py

# 6. Kiểm tra judge có phải LLM thật không, phải ra 0/24 ở cả ba trạng thái
#    (khi Gemini free tier trả 429, metrics.py:65-71 im lặng rơi về heuristic judge)
./.venv/pywin/python.exe -c "<đếm 'Fallback heuristic' trong data/results/*_answers.json>"
```

- **Kết quả mong đợi:** 24 sample đúng schema; mọi `ground_truth` khớp field mà evaluator sẽ trả về; mọi `ground_truth_doc_ids` tồn tại trong cả clean và raw; không có `ground_truth` rỗng hoặc `"nan"`.
- **Kết quả thực tế:** `samples=24  papers=6  type={'factual'}`, `ids lien tuc: True`, `VALIDATION: ALL PASSED`. Test trên DataFrame synthetic 7 row (cắm sẵn title có apostrophe, `authors_joined = NaN`, summary quá ngắn, title rỗng) loại đúng 3 row xấu và sinh 15 sample hợp lệ.
- **Artifact/log:** `data/eval/test_set.json` (10.9 KB, 24 sample). Không chứa secret. `.env` đã nằm trong `.gitignore` và chưa bị git track.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Đề bài gợi ý câu hỏi dạng tiếng Việt tự nhiên (*"Tác giả của bài viết về [Chủ đề] là ai?"*). Nhưng evaluator `_extract_answer` chỉ nhận diện keyword tiếng Anh. Câu hỏi tiếng Việt luôn rơi vào nhánh fallback và trả về câu đầu của summary thay vì danh sách tác giả.
- **Các phương án đã cân nhắc:**
  1. Giữ câu hỏi tiếng Việt đúng như ví dụ trong đề.
  2. Viết câu hỏi tiếng Anh khớp keyword của evaluator.
  3. Sửa `qa.py::_extract_answer` để nó hiểu tiếng Việt.
- **Phương án đã chọn:** Phương án 2, cộng thêm một câu hỏi dạng chủ đề không bọc title để giữ tinh thần "câu hỏi thực tế" của đề.
- **Lý do:** Phương án 1 làm `mean_token_f1` và `judge_accuracy` sụp trên **cả ba** trạng thái, không phải vì dữ liệu xấu mà vì câu hỏi lệch harness — baseline mất giá trị làm mốc, toàn bộ phép so sánh vô nghĩa. Phương án 3 sửa code đã được cung cấp sẵn, làm baseline không còn tái lập được với repo gốc và mở rộng phạm vi ra ngoài phần việc của tôi. Phương án 2 giữ nguyên evaluator, chỉ điều chỉnh phần tôi sở hữu.
- **Bằng chứng quyết định phù hợp:** Script đối chiếu độc lập cho kết quả 24/24 sample có `ground_truth` khớp đúng field mà `_extract_answer` sẽ trả về. Nếu chọn phương án 1, con số này sẽ là 6/24 — chỉ nhóm câu hỏi summary tình cờ khớp nhánh fallback.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `build_test_set()` sinh sample có `"ground_truth": "nan"`, và sample khác có `ground_truth` rỗng. Ngoài ra `row["authors_joined"]` ném `KeyError` khi cột chưa tồn tại.
- **Lệnh hoặc bước tái hiện:** Gọi `build_test_set()` trên DataFrame có `authors_joined = float("nan")`, hoặc trên DataFrame chưa có cột `authors_joined`.
- **Nguyên nhân gốc:** Ba nguyên nhân độc lập. Thứ nhất, `float("nan")` là **truthy** trong Python, nên `if row["authors_joined"]:` cho `True` và `str(nan)` cho chuỗi `"nan"` — đây là lỗi im lặng, không exception. Thứ hai, truy cập `row["cột"]` trực tiếp giả định cột luôn tồn tại, nhưng cột dẫn xuất do `cleaning.py` sinh nên có thể chưa có. Thứ ba, không có kiểm tra `ground_truth` rỗng, nên row có `summary` rỗng sinh ra sample với `token_f1 = 0` vĩnh viễn, kéo metrics xuống mà không phải lỗi của hệ thống RAG.
- **Cách xử lý:** Thêm `_field(row, *keys)` đọc text theo danh sách cột ưu tiên, lọc `None`/`NaN`/cột thiếu và trả `""`; thêm `_is_usable()` loại row không tạo được ground truth kiểm chứng được; `_add()` bỏ qua sample có `ground_truth` rỗng; thêm kiểm tra cuối cùng rằng số sample đạt `MIN_QUESTIONS` và mọi `paper_id` tồn tại thật.
- **Cách xác minh sau khi sửa:** Test trên DataFrame synthetic 7 row cắm sẵn 4 loại case xấu → `ALL CHECKS PASSED`; loại đúng 3 row không dùng được, row có `authors_joined = NaN` sinh 3 câu thay vì 4. Sau đó chạy trên clean data thật → 24 sample, `VALIDATION: ALL PASSED`.
- **Điều học được:** `NaN` truthy là loại lỗi không bao giờ crash, nó chỉ làm bẩn artifact và kéo metrics xuống — đúng loại lỗi mà data quality check phải bắt được. Đây cũng là lý do một quality check tốt phải kiểm tra **giá trị**, không chỉ kiểm tra sự tồn tại của cột.

### Blocker thứ hai: `WinError 1114` chặn toàn bộ pipeline

Đây là blocker khiến mục 8 trống ở bản nộp đầu. Nó đã được xử lý xong, và cách truy nguyên đáng ghi lại vì hai giả thuyết đầu đều sai.

- **Triệu chứng/lỗi nguyên văn:** `OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed. Error loading "...\.venv\Lib\site-packages\torch\lib\c10.dll" or one of its dependencies.` Hệ quả: không `import torch` → không có `sentence_transformers` → không build được vector index → `phase1.py` và `corruption_flow.py` đều không chạy.
- **Lệnh tái hiện:** `./.venv/Scripts/python.exe -c "import torch"`.
- **Những gì đã loại trừ (theo thứ tự):**
  1. *Thiếu package* — loại trừ: `numpy`, `pandas`, `chromadb`, `tokenizers`, `sklearn` đều import bình thường.
  2. *Wheel torch hỏng* — loại trừ: đối chiếu hash của cả 27 file trong `torch/lib` với `RECORD` của wheel, `checked=27 bad=0 missing=0`. Việc này tránh được một lần cài lại torch 250 MB vô ích.
  3. *Thiếu RAM* — giả thuyết ban đầu, và nó **sai**. Máy 7.6 GB chỉ còn 0.6 GB trống nên rất giống nguyên nhân. Tôi gọi `EmptyWorkingSet` để nâng lên 1.95 GB rồi thử lại: lỗi y hệt. Loại trừ.
  4. *CPU thiếu AVX / Exploit Protection / `AppInit_DLLs` / IFEO cho `python.exe`* — loại trừ: CPU i5-12450H có đủ AVX2, các mục mitigation đều `NOTSET`.
- **Nguyên nhân gốc:** `.venv` được `uv` dựng trên nền Anaconda (`sys.base_prefix = D:\App\anaconda`), nên process nạp `python311.dll` và `VCRUNTIME140.dll` **từ thư mục Anaconda**. Anaconda ship kèm MSVC runtime **14.27** (bản 2020), trong khi `c10.dll` của torch 2.12 được build với **14.44**. Vì thư mục ứng dụng đứng trước `System32` trong thứ tự tìm DLL của Windows, bản 14.27 cũ được nạp trước và `DllMain` của `c10.dll` fail. Cùng nguyên nhân đó làm `onnxruntime` chết y hệt.
- **Bằng chứng xác nhận trước khi sửa:** copy `python.exe` sang thư mục scratch kèm `VCRUNTIME140.dll` / `MSVCP140.dll` bản 14.44 lấy từ `System32`, rồi nạp `c10.dll` bằng `ctypes` → `RESULT: c10.dll LOADED OK`. Đây là bước tách biến, để chắc chắn đúng nguyên nhân trước khi thay đổi bất cứ thứ gì.
- **Cách xử lý:** tạo `.venv/pywin/` chứa bản copy `python.exe` + `python311.dll` + MSVC runtime 14.44 từ `System32`. Vì thư mục này nằm bên trong `.venv/`, Python vẫn đọc `pyvenv.cfg` của venv nên dùng đúng `site-packages` cũ, không phải cài lại gói nào. Chọn cách này thay vì ghi đè DLL trong `D:\App\anaconda` để không đụng vào cài đặt dùng chung của các project khác, và thay vì dựng lại venv trên CPython độc lập để khỏi tải lại vài GB.
- **Cách xác minh sau khi sửa:** `torch 2.12.0+cpu`, `sentence-transformers 5.5.1`, `chromadb 1.5.9` đều import được; sau đó `run_phase1.py` và `run_corruption_flow.py` chạy hết, exit code 0, sinh đủ artifact ở mục 8.
- **Điều học được:** giả thuyết nghe hợp lý nhất chưa chắc đúng. Thiếu RAM khớp với mọi triệu chứng quan sát được, nhưng chỉ một phép thử rẻ tiền (giải phóng RAM rồi chạy lại) đã bác bỏ nó. Nếu tin theo giả thuyết đó thì đã đi sửa nhầm hướng. Bài học chung với mục 4: cả `NaN` truthy lẫn DLL conflict đều là lỗi **im lặng ở tầng dưới** — không có exception nào chỉ đúng nguyên nhân, phải tự dựng phép đo để phân biệt.

### Phần đã xử lý trước đó

Mất `data/clean/*` sau `git pull`: đã loại trừ `.gitignore` (không ignore `data/`) và lỗi thao tác local. Nguyên nhân thật là commit `origin/main@2c0b847` — một merge commit của thành viên khác resolve conflict theo phía họ, đã revert `cleaning.py`, `corruption.py` về stub và xoá `data/clean/*`. Hiện repo đã hết `NotImplementedError` và `data/clean/` đã đầy đủ trở lại.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` gọi Crossref REST API với query và filter lấy từ `Settings` (`has-abstract:true`, `from-pub-date` = hôm nay trừ 180 ngày, `max_results=24`), lưu nguyên response vào `data/raw/crossref_response.json` **trước khi** parse — đây là điểm khôi phục duy nhất đáng tin cho pha repair. Sau đó parse thành `PaperRecord` (DOI làm `paper_id`) và lưu `data/raw/crossref_records.json`. `cleaning.py` chuẩn hoá text, parse ngày, tính `age_days`, dedupe theo `paper_id`, ghép `text_for_embedding`, và ghi `data/clean/papers_clean.{csv,json}` — 24 row, 16 cột. `index.py::LocalEmbeddingIndex.build` biến mỗi row thành document (`content = text_for_embedding`, metadata giữ `paper_id`/`title`/`published`/`authors_joined`/`summary`), embed bằng MiniLM-L6-v2, và nạp vào collection Chroma `papers-baseline`, đồng thời ghi manifest `data/embeddings/papers_embeddings.json`.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Hai chỉ số tách biệt. `retrieval_hit_rate` chỉ hỏi: trong các doc trả về có doc nào thuộc `ground_truth_doc_ids` không — nó đo **tầng retrieval**, không quan tâm câu trả lời. `mean_token_f1` và điểm judge so `answer` với `ground_truth` — chúng đo **tầng sinh câu trả lời**. Tách hai tầng cho phép quy trách nhiệm: hit_rate tụt nghĩa là dữ liệu bị mất hoặc embedding bị hỏng; hit_rate giữ nguyên mà token_f1 tụt nghĩa là tài liệu vẫn tìm được nhưng nội dung bên trong đã bị bẩn.

**3. Quality checks khác freshness monitoring ở điểm nào?** Quality checks đo tính toàn vẹn **nội tại** của một snapshot: số row, `paper_id` null/trùng, `title`/`summary` thiếu, độ dài summary. Nó trả lời "bảng dữ liệu này có tự nhất quán không". Freshness đo quan hệ giữa dữ liệu và **thời gian**: `published` mới nhất, cũ nhất, số row vượt ngưỡng 180 ngày, `is_fresh`. Một dataset có thể sạch hoàn hảo mà vẫn cũ mèm — quality không bắt được, chỉ freshness bắt được. Trong bài lab này, corruption dạng blank summary và duplicate bị quality bắt, còn corruption dạng làm cũ ngày xuất bản chỉ freshness bắt được. Baseline hiện tại có `age_days` từ 5 đến 175, tất cả dưới ngưỡng, nên `stale_rows = 0` — đó là mốc để đối chiếu sau corruption.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì `build_test_set()` trích `ground_truth` từ chính DataFrame truyền vào. Sinh lại test set từ dữ liệu đã corrupt nghĩa là chấm hệ thống hỏng bằng đáp án hỏng — nó sẽ đạt điểm cao và corruption trở nên vô hình. Ngoài ra, đổi câu hỏi làm delta metrics trộn hai biến nên không quy được nguyên nhân, và `ground_truth_doc_ids` là **nhãn** của retrieval: đóng băng nhãn thì `retrieval_hit_rate` đo "hệ thống còn tìm được tài liệu không", đổi nhãn theo dữ liệu hiện tại thì nó chỉ đo "nhãn còn tồn tại không" — một câu hỏi vô nghĩa. Repo đã có sẵn cơ chế cho việc này: `refresh_test_set` mặc định `False` để pipeline load lại file cũ chứ không build lại.

**5. Repair được xem là thành công dựa trên artifact và metric nào?** Ở hai tầng. Tầng dữ liệu: số `ground_truth_doc_ids` còn thiếu trong dataset trở lại 0, row count và quality checks quay về mức baseline, `stale_rows` trở lại 0. Tầng agent: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` phục hồi về xấp xỉ baseline trên **cùng** test set. Bằng chứng ở tầng dữ liệu mạnh hơn vì nó không phụ thuộc độ nhiễu của LLM judge. Và điều kiện tiên quyết để repair khả thi là dựng lại từ `data/raw/`, không sửa tay `answers` hoặc `metrics` — tôi đã xác minh mọi `ground_truth_doc_ids` đều còn trong `crossref_records.json` nên mọi paper bị xoá đều khôi phục được.

## 8. Phân tích kết quả

### Metrics chính

Số liệu dưới đây là kết quả tôi tự chạy trên máy mình ngày 2026-08-06, bằng `./.venv/pywin/python.exe script/run_phase1.py` rồi `script/run_corruption_flow.py`, trên **cùng một** `data/eval/test_set.json` cho cả ba trạng thái.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `samples` | 24 | 24 | 24 | Test set đóng băng, không sinh lại giữa ba lần chạy |
| `retrieval_hit_rate` | 0.9583 | **1.0000** | 0.9583 | **Tăng** khi dữ liệu hỏng — xem phần giải thích bên dưới |
| `mean_token_f1` | 0.9636 | **0.7113** | 0.9636 | Tín hiệu nhạy nhất và deterministic hoàn toàn |
| `judge_accuracy` | 0.8750 | **0.7083** | 0.8750 | 21/24 → 17/24 câu được judge chấm `correct` |
| `mean_judge_score` | 4.50 | **3.75** | 4.50 | Judge là LLM thật, `Fallback heuristic` = 0/24 ở cả ba |
| Quality `passed` | True | **False** | True | Nguồn: `data/quality/{baseline_quality,corrupted,repaired}.json` |
| `total_rows` | 24 | 28 | 24 | +4 do duplicate |
| `paper_id_duplicates` | 0 | **4** | 0 | |
| `short_summaries` | 0 | **6** | 0 | Cả 6 đều rỗng hoàn toàn (0 ký tự): 5 row `blank_summary` + 1 bản duplicate của một trong số đó |
| `stale_rows` | 0 | **6** | 0 | 5 `paper_id` khác nhau + 1 bản duplicate — duplicate nhân bản cả lỗi, không chỉ nhân bản dữ liệu tốt |
| Freshness `is_fresh` | True | **False** | True | Nguồn: `data/quality/*freshness_report.json` |
| `oldest_published` | 2026-02-12 | **2000-01-01** | 2026-02-12 | `age_days` baseline 5–175, đều dưới ngưỡng 180 |

Cấu hình corruption (`data/results/corruption_log.json`): `seed = 42`, 24 → 28 row, `blank_summary 5`, `stale_date 5`, `inject_noise 5`, `duplicate_row 4`. Cả **6/6 paper trong test set đều bị đánh trúng** — đúng theo cơ chế ưu tiên `ground_truth_doc_ids` ở `corruption.py:85-94`.

### Kết luận từ số liệu

**1. `retrieval_hit_rate` tăng lên 1.0 trong khi dữ liệu đang hỏng.** Đây là kết quả đáng chú ý nhất và nó không phải nghịch lý. Corruption nhân bản 4 row nhưng **giữ nguyên `paper_id`**, nên số document mang nhãn đúng trong index tăng lên, và top-4 có thêm cơ hội chạm nhãn. Cụ thể: đúng một câu trượt ở baseline là q24 (`retrieval_hit = False`), và ở corrupted nó thành `True` — 23/24 lên 24/24. Nói cách khác: tầng retrieval trông *tốt lên* đúng lúc nội dung bên trong hỏng đi. Nếu chỉ theo dõi `retrieval_hit_rate` thì kết luận sẽ là "dữ liệu vẫn ổn". Đây là bằng chứng đo được cho luận điểm ở mục 7 câu 2 — hit_rate đo tầng tìm kiếm, `token_f1` đo tầng nội dung, và phải đọc cả hai mới quy được trách nhiệm.

**2. Tụt điểm là nhị phân, không phải suy giảm dần.** Trung bình `0.9636 → 0.7113` che mất cấu trúc thật. Đối chiếu từng câu: 9/24 câu bị ảnh hưởng, 15 câu **không đổi một chút nào**. Trong 9 câu đó, 6 câu tụt thẳng từ 1.000 xuống 0.000, 3 câu chỉ giảm khoảng 0.02.

| Loại corruption | Paper trong test set bị dính | Câu bị ảnh hưởng | `token_f1` | Cơ chế |
| ---------------- | ---------------------------: | ----------------- | ---------- | -------- |
| `blank_summary` | 2 | q5, q8, q13, q16 | 1.000 → **0.000** | Evaluator trả `first_sentence("")` = rỗng, `_token_f1` trả 0 tuyệt đối |
| `stale_date` | 2 | q11, q19 | 1.000 → **0.000** | Nhánh `"when was"` trả `published` = `2000-01-01`, không giao token nào với ground truth |
| `inject_noise` | 2 | q1, q4, q21 | 1.000 → 0.980–0.986 | Noise chèn vào đầu `summary` nên `first_sentence` chỉ lệch vài token |
| `duplicate_row` | 1 (chồng lên `inject_noise`) | không câu nào | không đổi | Không đổi nội dung, chỉ đẩy `retrieval_hit_rate` lên |

Mỗi paper có 4 câu hỏi, nhưng chỉ những câu **đọc đúng field bị hỏng** mới tụt: paper bị `blank_summary` vẫn trả lời đúng câu hỏi tác giả và ngày xuất bản. Đó là lý do `blank_summary` gây thiệt hại gấp đôi `stale_date` dù cùng 5 row — nó đánh vào 2 trong 4 loại câu hỏi, còn `stale_date` chỉ đánh vào 1.

**3. Repair khôi phục chính xác tuyệt đối, không phải xấp xỉ.** Cả ba metric deterministic của repaired trùng baseline tới từng chữ số (0.9583 / 0.9636), quality `passed = True`, `stale_rows = 0`, `total_rows = 24`. Lý do: `corruption_flow.py:98-99` dựng lại từ `data/raw/crossref_records.json` qua đúng `build_clean_dataframe()` đã sinh ra baseline — nên đây là tái tạo bit-for-bit, không phải sửa chữa gần đúng. Điều này xác nhận điều kiện tiên quyết tôi nêu ở mục 7 câu 5: repair khả thi vì raw response được lưu **trước khi** parse.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`blank_summary` — 4/9 câu bị ảnh hưởng và cả 4 đều về 0. Nhưng con số đó chỉ đúng **với test set này**, và lý do nằm ở một ràng buộc cấu trúc tôi đã xác minh từ trước: test set chỉ phủ **6/24 paper (25% corpus)**, và do clean DataFrame sort theo `published` giảm dần, 6 paper đó đúng là 6 paper mới nhất (`set(df.head(6).paper_id)` bằng đúng tập `ground_truth_doc_ids`).

Lần chạy này corruption nhắm có chủ đích vào đúng 6 paper đó nên mới đo được gì. Nếu `corruption.py` chọn row ngẫu nhiên, phần lớn corruption sẽ rơi vào 18 row **không được test** và bảng metrics sẽ gần như không đổi dù dữ liệu đã hỏng thật. Nói cách khác: mức sụt 0.9636 → 0.7113 không phải thước đo mức độ hỏng của dữ liệu, nó là thước đo mức độ **chồng lấn giữa corruption và test set**. Đây là điểm tôi đã trao đổi với TV4 trước khi chạy.

Kết quả nào khác với kỳ vọng ban đầu?

Năm điểm.

Thứ nhất, tôi dự đoán ở bản nộp trước rằng `retrieval_hit_rate` sẽ **giảm** khi corrupt. Thực tế nó **tăng lên 1.0**. Dự đoán đó dựa trên kịch bản corruption dạng *xoá record*; corruption thực tế được cài đặt là blank/stale/noise/duplicate, không xoá record nào — và duplicate lại đẩy hit_rate lên. Đây là chỗ tôi sai và số liệu sửa lại.

Thứ hai, `missing_ground_truth_docs` = **0 ở cả ba trạng thái**. Ở mục 9 tôi đề xuất thêm check này vào `quality.py`; lần chạy này nó sẽ không phát hiện được gì, vì không có record nào bị xoá. Chỉ số đó chỉ nhạy với kịch bản xoá record — cần ghi rõ giới hạn đó khi đề xuất, nếu không nó tạo cảm giác an toàn giả.

Thứ ba, `categories_joined` và `primary_category` **rỗng 24/24 row** — Crossref không trả field `subject` cho batch này. Tôi kỳ vọng đây là một trong bốn loại câu hỏi, nhưng nó không sinh được sample nào, và nhánh `"what categories"` trong `qa.py` trở thành code chết. Đã kiểm tra bằng cách đếm số row có `categories_joined` khác rỗng.

Thứ tư, 8/24 `summary` còn dính prefix `"Abstract "` / `"Summary "` từ JATS của Crossref. Điều đáng chú ý là nó **không** làm sai metrics, vì evaluator đọc cùng field `summary` nên `ground_truth` và câu trả lời khớp nhau. Nhưng nó làm report khó đọc. Kết luận: phải sửa ở `cleaning.py` chứ không phải sửa ở `ground_truth` — sửa một bên sẽ làm `token_f1` tụt oan.

Thứ năm, `git pull` làm mất artifact và revert code đã implement về stub. Tôi kỳ vọng conflict chỉ xảy ra ở file mình đang sửa; thực tế merge xoá `data/clean/*` **im lặng, không báo conflict**, vì phía tôi không sửa hai file đó kể từ merge base nên git coi việc phía kia xoá là quyết định sạch.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Lưu raw response trước khi parse không phải thủ tục hình thức, nó là điều kiện để repair khả thi. Số liệu chứng minh: `papers_clean_repaired.json` **bằng đúng** `papers_clean.json` trên toàn bộ DataFrame (so sánh 24 row × 16 cột sau khi sort theo `paper_id`, kết quả `True`), nên mọi metric của repaired trùng baseline tới từng chữ số. Đó là vì repair dựng lại từ `data/raw/`, không cố sửa chữa bản đã hỏng. Kết luận này không thể có nếu chỉ lưu bản đã clean. Cũng ở đây: artifact trong `data/` phải được commit và được bảo vệ như code, vì một merge resolve sai xoá chúng dễ hơn xoá code.

2. **Về data quality/observability:** Check phải kiểm tra **giá trị**, không chỉ kiểm tra sự tồn tại của cột. `float("nan")` là truthy nên qua được mọi phép kiểm tra dạng `if row[col]`, và sinh ra chuỗi `"nan"` trong artifact mà không hề crash. Loại lỗi im lặng này chính là thứ observability tồn tại để bắt. Thêm nữa, quality và freshness bắt hai lớp lỗi khác nhau và không thay thế được nhau — dataset sạch hoàn hảo vẫn có thể cũ mèm.

3. **Về ảnh hưởng của data đến RAG agent:** Coverage của test set quyết định corruption có đo được hay không. Test set phủ 25% corpus nghĩa là 75% dữ liệu có thể hỏng hoàn toàn mà mọi metric vẫn không đổi. Số liệu ở mục 8 xác nhận điều này ngay cả khi corruption đã nhắm trúng đích: 15/24 câu **không nhúc nhích**, và trong 9 câu còn lại thì 6 câu về thẳng 0 còn 3 câu chỉ lệch 0.02. Metrics không tự biết mình đang mù ở đâu — nên báo cáo phải nói rõ signal nào **không** đổi, và mức trung bình nào đang che mất phân bố nhị phân bên dưới.

### Nếu có thêm thời gian

Thêm một check *ground-truth coverage* vào `quality.py`: đếm bao nhiêu `ground_truth_doc_ids` còn tồn tại trong dataset hiện tại, ghi thành `missing_ground_truth_docs` trong quality payload của cả ba trạng thái.

Lý do: nó biến một cú tụt metrics không rõ nguyên nhân thành lời giải thích có bằng chứng — thay vì chỉ thấy `retrieval_hit_rate` giảm, ta đọc được `missing_ground_truth_docs: 3` và biết ngay nguyên nhân là dữ liệu bị xoá, không phải embedding kém. Đây là bằng chứng ở **tầng dữ liệu**, độc lập hoàn toàn với độ nhiễu của LLM judge.

Nhưng phải nói rõ giới hạn, vì tôi đã đo: với cấu hình corruption hiện tại chỉ số này là **0 ở cả ba trạng thái** và không phát hiện được gì. Nó chỉ nhạy với kịch bản *xoá record*, trong khi corruption thực tế của nhóm là blank/stale/noise/duplicate — không xoá dòng nào. Muốn nó có ích thì phải đi kèm một check thứ hai đo *chất lượng* của các doc thuộc ground truth chứ không chỉ *sự tồn tại* của chúng, ví dụ `ground_truth_docs_with_empty_summary`. Đây đúng là bài học ở điểm 2 phía trên, lặp lại ở tầng thiết kế metric: kiểm tra sự tồn tại thì rẻ nhưng bỏ lọt, kiểm tra giá trị mới bắt được lỗi im lặng.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trịnh Quang Anh 
**Ngày xác nhận:** 2026-08-06
