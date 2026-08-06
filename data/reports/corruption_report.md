# Data Corruption & Repair Comparison Report

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| **Retrieval Hit Rate** | 95.83% | 100.00% | 95.83% |
| **Mean Token F1** | 96.36% | 71.13% | 96.36% |
| **Judge Accuracy** | 87.50% | 58.33% | 87.50% |
| **Mean Judge Score** | 4.54 | 3.50 | 4.54 |

## 2. Data Observability & Quality Impact

| Check | Corrupted | Repaired |
|---|---|---|
| **Quality Status** | FAILED | PASSED |
| **Stale Rows** | 6 | 0 |
| **Short Summaries** | 6 | 0 |
| **Is Fresh** | NO | YES |
