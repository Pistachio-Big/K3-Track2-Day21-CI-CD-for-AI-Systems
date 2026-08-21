# Nộp Bài — Bằng Chứng (Screenshots)

Lưu tất cả ảnh chụp màn hình vào `nop-bai/screenshots/` theo đúng tên dưới đây.
Mỗi ảnh tương ứng một tiêu chí trong rubric.

| Tên file (lưu vào `screenshots/`) | Nội dung cần chụp | Tiêu chí |
|---|---|---|
| `01-mlflow-runs.png` | MLflow UI hiển thị ≥3 runs với hyperparameter khác nhau (có cột accuracy & f1_score) | B1, B2, Bonus 2 |
| `02-eval-gate-blocked-buoc2.png` | Log job **Eval** ở Bước 2 báo accuracy ~0.68 < 0.70 → deploy bị chặn | B6 |
| `03-actions-4-jobs-green-buoc3.png` | Tab Actions lần chạy Bước 3: cả 4 job Test/Train/Eval/Deploy xanh | B5, B8 |
| `04-curl-health-predict.png` | Kết quả `curl /health` và `curl /predict` từ VM | B7 |
| `05-object-storage.png` | OCI Object Storage: prefix `dvc/` + file `models/latest/model.pkl` | B4 |
| `06-report-artifact.png` | Artifact `report` (outputs/report.txt) tải từ Actions | Bonus 3 |
| `07-dagshub-mlflow.png` | (Nếu làm Bonus 1) MLflow trên DagsHub | Bonus 1 |

## Ghi chú
- `01-mlflow-runs.png`: ảnh MLflow bạn vừa chụp (12 runs) — lưu vào đây với tên này.
- Ảnh Bước 2 (`02`) và Bước 3 (`03`) chỉ có sau khi bạn cấu hình OCI + push (xem `../HUONG_DAN_THUC_HIEN.md`).
- Báo cáo A4 để tên `bao-cao.pdf` hoặc `bao-cao.md` đặt trong thư mục `nop-bai/`.
