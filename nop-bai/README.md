# Nộp Bài — Bằng Chứng (Screenshots)

Lưu tất cả ảnh chụp màn hình vào `nop-bai/screenshots/` theo đúng tên dưới đây.
Mỗi ảnh tương ứng một tiêu chí trong rubric.

| File | Nội dung | Tiêu chí | Trạng thái |
|---|---|---|---|
| `screenshots/01-mlflow-runs.png` | MLflow UI ≥6 runs, cột accuracy/f1_score + hyperparameter + 3 thuật toán | B1, B2, Bonus 2 | ✅ |
| `screenshots/02-eval-gate-blocked-buoc2.png` | Eval ❌ (acc 0.682 < 0.70) → Deploy skipped, exit code 1 | B6 | ✅ |
| `screenshots/03-actions-4-jobs-green-buoc3.png` | Bước 3: 4 job Test/Train/Eval/Deploy đều xanh, trigger via push (data commit) | B5, B8 | ✅ |
| `screenshots/04-curl-health.png` | `/health` → `{"status":"ok"}` | B7 | ✅ |
| `screenshots/04-curl-predict.png` | `/predict` → `prediction 0 / label thap` | B7 | ✅ |
| `screenshots/05-object-storage.png` | OCI Object Storage: `dvc/files/md5/` (3 object) | B4 | ✅ |
| `report-buoc3/report.txt` | Confusion matrix + precision/recall (model 0.746) tải từ artifact | Bonus 3 | ✅ |
| `screenshots/07-dagshub-mlflow.png` | (Tùy chọn) MLflow trên DagsHub | Bonus 1 | ⏳ |

## Kết quả then chốt
- Bộ tham số tốt nhất (Bước 1): RandomForest `n_estimators=300, max_depth=None` → accuracy **0.682**.
- So sánh Bước 2 vs Bước 3:

| Chỉ số | Bước 2 (2998 mẫu) | Bước 3 (5996 mẫu) |
|---|---|---|
| accuracy | 0.682 | 0.746 |
| f1_score | 0.681 | 0.745 |

- Rollback guard (Bonus 4): `Accuracy cu = 0.6820 | Accuracy moi = 0.7460 | PASSED`.
- Báo cáo A4 để tên `bao-cao.pdf`/`bao-cao.md` trong thư mục `nop-bai/`.
