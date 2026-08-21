# Báo Cáo Lab MLOps — CI/CD cho AI Systems (Day 21)

**Học viên:** Dai Nguyen · **Khóa:** K3 — Track 2 · **Repo:** https://github.com/Pistachio-Big/K3-Track2-Day21-CI-CD-for-AI-Systems
**Cloud:** Oracle Cloud Infrastructure (OCI) — Object Storage (S3-compatible) + Compute VM (Ubuntu, IP 146.235.20.239)

---

## 1. Bộ siêu tham số đã chọn và lý do (Bước 1)

Chạy 6 thí nghiệm trên MLflow với các thuật toán và siêu tham số khác nhau (dữ liệu 2998 mẫu, eval 500 mẫu):

| model_type | n_estimators | max_depth | accuracy | f1_score |
|---|---|---|---|---|
| **random_forest** | **300** | **None** | **0.682** | **0.681** |
| gradient_boosting | 300 | 5 | 0.680 | 0.679 |
| random_forest | 200 | 10 | 0.644 | 0.642 |
| random_forest | 100 | 5 | 0.564 | 0.553 |
| random_forest | 50 | 3 | 0.558 | 0.519 |
| logistic_regression | — | — | 0.528 | 0.512 |

**Chọn: RandomForest, `n_estimators=300`, `max_depth=None`, `min_samples_split=2`.**
**Lý do:** cho accuracy cao nhất (0.682). Tăng số cây (`n_estimators`) và bỏ giới hạn độ sâu (`max_depth=None`) giúp mô hình học được các quan hệ phi tuyến phức tạp giữa 12 đặc trưng hóa học; các cấu hình nông (max_depth 3–5) underfit rõ rệt (0.55–0.56). GradientBoosting tương đương nhưng chậm hơn; LogisticRegression yếu nhất do bài toán phi tuyến.

## 2. So sánh Bước 2 và Bước 3

| Chỉ số | Bước 2 (2998 mẫu) | Bước 3 (5996 mẫu) |
|---|---|---|
| accuracy | 0.682 | **0.746** |
| f1_score | 0.681 | **0.745** |

Thêm 2998 mẫu (train_phase2) làm accuracy tăng **+0.064**, minh chứng "thêm dữ liệu → mô hình tốt hơn". Eval gate 0.70 nằm ngay giữa hai mức: Bước 2 (0.682) **bị chặn** — đúng vai trò bảo vệ production; Bước 3 (0.746) **vượt ngưỡng → deploy tự động**.

## 3. Khó khăn gặp phải và cách giải quyết

| Khó khăn | Cách giải quyết |
|---|---|
| **Trần accuracy Bước 2 ~0.68 < ngưỡng 0.70** (thử RF/GB/ExtraTrees/stacking đều ~0.68–0.70) | Giữ nguyên ngưỡng 0.70 đúng rubric: Bước 2 bị gate chặn (bằng chứng B6), Bước 3 (nhiều dữ liệu) vượt ngưỡng và deploy (B5/B7/B8). Đây chính là hành vi đúng của eval gate. |
| **OCI dùng S3-compatible, không phải GCP** | Chuyển `dvc[gs]`→`dvc[s3]`, `google-cloud-storage`→`boto3`; xác thực bằng Customer Secret Key. |
| **`dvc push` lỗi `SignatureDoesNotMatch`** | OCI chỉ hỗ trợ path-style (virtual-hosted lỗi SSL vì cert không phủ subdomain bucket) và cần region cho SigV4. Thêm `.dvc/aws-config` (`addressing_style=path` + `region`) và `dvc remote modify myremote configpath .dvc/aws-config`. |
| **Push không kích hoạt GitHub Actions** | Repo là *fork* → GitHub chặn auto-trigger tới khi bấm "I understand my workflows, go ahead and enable them" trong tab Actions. |
| **`curl` từ ngoài không vào được port 8000** | Mở 2 lớp: Ingress rule TCP 8000 trong VCN Security List **và** iptables trên VM — quan trọng: chèn rule ACCEPT **trước** rule REJECT (`iptables -I INPUT 5 ...`). |
| **Unpickle model trên VM** | Ghim `scikit-learn==1.4.2` trên VM khớp bản train trên CI; chạy service bằng venv riêng để tránh lỗi PEP-668 của Ubuntu. |

## 4. Kết quả (bonus đã hoàn thành)

- **Bonus 2** — 3 thuật toán (RF/GB/LR) so sánh trên MLflow.
- **Bonus 3** — báo cáo tự động: confusion matrix + precision/recall/F1 từng lớp (`outputs/report.txt`, upload artifact).
- **Bonus 4** — rollback guard: so sánh accuracy cũ/mới trước deploy (`0.6820 → 0.7460 PASSED`).
- **Bonus 5** — cảnh báo data drift: ghi phân phối nhãn vào `metrics.json`, cảnh báo nếu lớp < 10%.
