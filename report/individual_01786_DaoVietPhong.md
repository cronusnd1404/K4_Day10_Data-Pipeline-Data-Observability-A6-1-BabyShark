# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đào Việt Phong            |
| MSSV               | 01786                     |
| Khóa/Lớp         | [K4]              |
| Tên nhóm         | Baby Shark    |
| Vai trò chính    | Data Pipeline & Observability Engineer |
| Repository         | https://github.com/cronusnd1404/K4_Day10_Data-Pipeline-Data-Observability-A6-1-BabyShark |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | -------------- | ----------------- | ---------- |
| Baseline orchestration | `src/pipelines/phase1.py` | Raw Crossref records / raw snapshot | Cleaned dataset, baseline embeddings, baseline metrics, baseline report | Hoàn thành |
| Corruption flow orchestration | `src/pipelines/corruption_flow.py` | Corrupted dataset, raw records snapshot | Repaired dataset, corrupted/repaired metrics, corruption comparison report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ----------------------------- | ---------------------------- |
| Debug tích hợp pipeline | Nhóm data & retrieval | Đảm bảo `phase1` và `corruption_flow` chạy theo cùng bộ test frozen và lưu artifact tách biệt |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây orchestration baseline | `src/pipelines/phase1.py` | `data/clean/papers_clean.csv`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` | `python script/run_phase1.py` |
| Xây orchestration corruption/repaired flow | `src/pipelines/corruption_flow.py` | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` | `python script/run_corruption_flow.py` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Các file orchestration tôi viết tạo ra artifact baseline và so sánh corruption/repaired, giúp team kiểm chứng bằng report và metrics rõ ràng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc của tôi là kết nối các components đã có thành một pipeline hoàn chỉnh, đảm bảo dữ liệu sạch/corrupted/repaired được xử lý đồng nhất và các artifact đánh giá được sinh ra đúng chuẩn.

### Cách triển khai

Tôi triển khai hai orchestrator:

- `src/pipelines/phase1.py`: xử lý baseline từ raw Crossref đến clean dataset, xây ChromaDB index, sinh hoặc dùng evaluation test set frozen, chạy evaluate và tạo report baseline.
- `src/pipelines/corruption_flow.py`: đọc dữ liệu corrupted, rebuild index corrupted, evaluate trên cùng test set, repair dữ liệu từ raw snapshot bằng lại logic cleaning, rebuild index repaired, evaluate lại và tạo report so sánh.

Quy tắc repair: không sửa dữ liệu corrupted trực tiếp, mà tái tạo dataset sạch từ `data/raw/crossref_records.json`.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `data/raw/crossref_records.json`, `data/clean/papers_clean_corrupted.csv`, `data/eval/test_set.json`, cấu hình `src/core/config.py` |
| Output | `data/clean/papers_clean.csv`, `data/clean/papers_clean_repaired.csv`, `data/results/*.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `retrieval.index`, `evaluation.metrics`, `observability.quality`, `observability.reporting` |
| Module sử dụng output | downstream evaluation, report generator, nhóm phân tích |
| Điều kiện lỗi cần xử lý | missing corrupted file, missing baseline metrics, missing test set, missing raw snapshot |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Pipeline tạo artifact clean, corrupted, repaired và report markdown.
- **Kết quả thực tế:** Hai script orchestration chạy qua, các file metrics và report được lưu đúng đường dẫn.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh ba trạng thái dataset riêng biệt mà không bị lẫn artifact hoặc index cũ.
- **Các phương án đã cân nhắc:** 1) Dùng cùng collection ChromaDB và ghi đè giữa các trạng thái; 2) Tạo collection/manifest riêng cho mỗi trạng thái.
- **Phương án đã chọn:** Tạo index riêng cho mỗi trạng thái bằng collection name và manifest embeddings khác nhau.
- **Lý do:** Giữ artifact tách biệt giúp so sánh chuẩn xác và giảm rủi ro ghi đè dữ liệu index.
- **Bằng chứng quyết định phù hợp:** `src/retrieval/index.py` dùng `embeddings_output_path` để xác định `collection_name` tương ứng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `FileNotFoundError: data/results/baseline_metrics.json` khi chạy corruption flow.
- **Lệnh hoặc bước tái hiện:** `python script/run_corruption_flow.py` sau khi phase1 chưa hoàn toàn xuất artifact.
- **Nguyên nhân gốc:** Corruption flow phụ thuộc baseline metrics và test set frozen; nếu phase1 chưa chạy hoặc không lưu đúng thì pipeline không đủ input.
- **Cách xử lý:** Bổ sung kiểm tra và đảm bảo `phase1.py` lưu `baseline_metrics.json`, `eval_testset.json`; `corruption_flow.py` đọc baseline metrics trước khi chạy.
- **Cách xác minh sau khi sửa:** Chạy `python script/run_corruption_flow.py` và kiểm tra `data/reports/corruption_report.md` được tạo.
- **Điều học được:** Trong pipeline nhiều pha, dependency artifact phải được ghi rõ và báo lỗi sớm nếu thiếu input.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
   - Bản ghi Crossref được tải hoặc đọc từ snapshot JSON, parse thành `PaperRecord`, clean thành dataframe chuẩn, rồi tạo embedding và lưu vào ChromaDB.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
   - Test set chứa câu hỏi, câu trả lời chuẩn và `ground_truth_doc_ids`. Khi model trả lời, pipeline kiểm tra document retrieve có chứa ID đúng không và tính `retrieval_hit_rate`, `mean_token_f1`.
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
   - Quality checks đánh giá cấu trúc dữ liệu, tính đầy đủ và duy nhất. Freshness monitoring đánh giá độ mới của dữ liệu dựa trên ngày xuất bản và ngưỡng tuổi.
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
   - Để so sánh trực tiếp các trạng thái dữ liệu trên cùng benchmark và tránh sai lệch do test set khác nhau.
5. Repair được xem là thành công dựa trên artifact và metric nào?
   - Khi `repaired` tạo lại clean dataset từ raw records và các metric `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` cải thiện so với corrupted; báo cáo `corruption_report.md` phản ánh sự phục hồi.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | [ ] | [ ] | [ ] | Corruption giảm, repaired nên phục hồi |
| `mean_token_f1` | [ ] | [ ] | [ ] | Phản ánh chất lượng câu trả lời từ context |
| `judge_accuracy` | [ ] | [ ] | [ ] | Judge score cho biết chất lượng tổng thể |
| `mean_judge_score` | [ ] | [ ] | [ ] | Nếu repair tốt, score nên cải thiện |
| Quality checks | [ ] | [ ] | [ ] | Corrupted có thể fail unique/full checks |
| Freshness status | [ ] | [ ] | [ ] | Nếu chỉ corruption nội dung, freshness giữ ổn định |

### Kết luận từ số liệu

1. Data corruption → quality/freshness signal thay đổi → agent metric thay đổi.
   - Corruption blank summary hoặc duplicate record làm agent thiếu context và giảm `retrieval_hit_rate`.
2. Repair action → quality/freshness signal phục hồi → agent metric phục hồi hoặc chưa phục hồi.
   - Rebuild dataset từ raw records giúp khôi phục chất lượng dữ liệu, metric nên cải thiện so với corrupted.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Corruption blank summary ảnh hưởng rõ nhất vì nó loại bỏ context quan trọng, khiến retrieval dưới chuẩn và answer quality giảm.

Kết quả nào khác với kỳ vọng ban đầu?

[Điền kết quả thực tế sau khi chạy pipeline nếu có.]

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Orchestration pipeline quyết định tính tái lập và so sánh giữa các trạng thái dataset.
2. Data quality và freshness là hai chiều giám sát khác nhau nhưng bổ trợ cho nhau.
3. Dữ liệu xấu tác động trực tiếp đến retrieval metric và chất lượng answer của agent.

### Nếu có thêm thời gian

- Thêm report chi tiết từng câu hỏi, context retrieve, và đánh giá judge để giải thích hiện tượng metric.
- Tạo script tự động sinh `papers_clean_corrupted.csv` và corruption log để thử nghiệm dễ dàng.

## 10. Cam kết của thành viên

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo này không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Họ và tên]
**Ngày xác nhận:** [YYYY-MM-DD]
