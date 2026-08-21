# Hướng Dẫn Thực Hiện — Phần Còn Lại Bạn Phải Làm Tay

> Toàn bộ **code** đã được hoàn thiện và kiểm thử. Tài liệu này liệt kê những
> việc **bạn phải tự thao tác** (tài khoản cloud, VM, secrets) vì cần đăng nhập
> cá nhân của bạn. Làm tuần tự từ trên xuống.

---

## 0. Trạng thái code (đã xong, không cần sửa)

| File | Nội dung đã hoàn thiện |
|---|---|
| `src/train.py` | Đọc data, train RF/GB/LR, log MLflow, `metrics.json`, `model.pkl`, báo cáo hiệu suất (Bonus 3), phân phối nhãn (Bonus 5) |
| `src/serve.py` | Tải model từ GCS, `/health`, `/predict` (map nhãn thấp/trung_bình/cao) |
| `tests/test_train.py` | 3 unit test — **đã PASS cục bộ** |
| `.github/workflows/mlops.yml` | 4 job Test→Train→Eval→Deploy + Bonus 1/3/4 |
| `params.yaml` | Bộ tham số tốt nhất (RandomForest, acc ~0.68) |
| `run_experiments.py` | Tự động chạy 6 thí nghiệm cho Bước 1 + Bonus 2 |

**Lưu ý quan trọng về eval gate (đã thống nhất — giữ ngưỡng 0.70):**
- Bước 2 (2998 mẫu): accuracy ~0.68 → **eval gate CHẶN deploy** → đây chính là bằng chứng tiêu chí **B6** (gate hoạt động).
- Bước 3 (5996 mẫu): accuracy ~0.75 → **vượt ngưỡng → deploy xanh** → bằng chứng **B5 / B7 / B8**.
- ⟹ Screenshot "4 job xanh" để nộp lấy từ **lần chạy Bước 3**, không phải Bước 2. Log Eval bị chặn ở Bước 2 là bằng chứng B6.

---

## 1. Chạy cục bộ để lấy bằng chứng Bước 1 (máy bạn)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python generate_data.py
```

Chạy 6 thí nghiệm tự động (ghi vào MLflow) — phục vụ B1, B2, B3, Bonus 2:

```bash
# Windows PowerShell:
$env:MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"
python run_experiments.py
```
```bash
# Linux/macOS:
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
python run_experiments.py
```

Mở MLflow UI để **chụp màn hình ≥3 runs** (bằng chứng B1/B2) và so sánh thuật toán (Bonus 2):

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
→ mở http://localhost:5000 → sort theo `accuracy` → chụp màn hình.

> **Bộ tham số tốt nhất (điền vào báo cáo — B3):** RandomForest, `n_estimators=300`,
> `max_depth=None`, `min_samples_split=2` → accuracy **0.682**. Đã đặt sẵn trong `params.yaml`.

---

## 2. Hạ tầng cloud — BẠN PHẢI LÀM TAY (ví dụ GCP)

> Tôi không làm được phần này vì cần đăng nhập tài khoản cloud của bạn. Dùng GCP
> làm ví dụ; nếu dùng AWS/Azure xem bảng ánh xạ trong `tasks/buoc-2.md`.

### 2.1 Bucket + Service Account

```bash
export PROJECT=<YOUR_PROJECT>
export BUCKET=<BUCKET_NAME_DUY_NHAT>

gcloud services enable storage.googleapis.com --project $PROJECT
gsutil mb -p $PROJECT -l us-central1 gs://$BUCKET

gcloud iam service-accounts create mlops-lab-sa --display-name "MLOps Lab SA" --project $PROJECT
gsutil iam ch serviceAccount:mlops-lab-sa@$PROJECT.iam.gserviceaccount.com:roles/storage.objectAdmin gs://$BUCKET
gcloud iam service-accounts keys create sa-key.json --iam-account mlops-lab-sa@$PROJECT.iam.gserviceaccount.com
```
⚠️ **Không commit `sa-key.json`** (đã có trong `.gitignore`).

### 2.2 Khởi tạo DVC + push dữ liệu (bằng chứng B4)

```bash
dvc init
dvc remote add -d myremote gs://$BUCKET/dvc
dvc remote modify myremote credentialpath sa-key.json

dvc add data/train_phase1.csv data/eval.csv data/train_phase2.csv
git add data/*.dvc .gitignore .dvc/config
git commit -m "feat: track datasets with DVC"
dvc push
```
→ Vào Cloud Storage Console xác nhận có prefix `dvc/`. **Chụp màn hình** (B4).

### 2.3 Tạo VM + mở port 8000 (phục vụ B7)

```bash
gcloud compute instances create mlops-serve --zone=us-central1-a --machine-type=e2-small \
  --image-family=ubuntu-2204-lts --image-project=ubuntu-os-cloud --tags=mlops-serve --project $PROJECT
gcloud compute firewall-rules create allow-mlops-serve --allow=tcp:8000 --target-tags=mlops-serve --project $PROJECT
gcloud compute instances describe mlops-serve --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'   # <- LƯU IP NÀY
```

### 2.4 Cấu hình VM (một lần)

```bash
# SSH vào VM
gcloud compute ssh mlops-serve --zone=us-central1-a
# --- bên trong VM ---
sudo apt update && sudo apt install -y python3-pip
pip3 install fastapi uvicorn scikit-learn joblib google-cloud-storage
mkdir -p ~/models ~/src
exit
# --- thoát VM ---

# Copy key + file serve.py lên VM
gcloud compute scp sa-key.json  mlops-serve:~/sa-key.json  --zone=us-central1-a
gcloud compute scp src/serve.py mlops-serve:~/src/serve.py --zone=us-central1-a
```

Tạo systemd service (SSH lại vào VM, **thay `<YOUR_BUCKET_NAME>`**):

```bash
gcloud compute ssh mlops-serve --zone=us-central1-a
# --- bên trong VM ---
sudo tee /etc/systemd/system/mlops-serve.service > /dev/null <<EOF
[Unit]
Description=MLOps Model Inference Server
After=network.target
[Service]
User=$USER
WorkingDirectory=/home/$USER
Environment="GCS_BUCKET=<YOUR_BUCKET_NAME>"
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/$USER/sa-key.json"
ExecStart=/usr/bin/python3 /home/$USER/src/serve.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable mlops-serve
echo $USER   # <- LƯU tên user này cho secret VM_USER
exit
```
> Chưa `systemctl start` lúc này — model chưa có trên GCS. Service sẽ chạy sau khi
> pipeline Bước 3 deploy thành công (Bước 2 bị gate chặn nên chưa deploy).

### 2.5 SSH key cho GitHub Actions deploy

```bash
ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N "" -C "github-actions-deploy"
gcloud compute ssh mlops-serve --zone=us-central1-a \
  --command "echo '$(cat ~/.ssh/mlops_deploy.pub)' >> ~/.ssh/authorized_keys"
```

---

## 3. GitHub Secrets — BẠN PHẢI LÀM TAY

Repo GitHub → **Settings → Secrets and variables → Actions → New repository secret**.
Thêm đúng 5 secrets (không có khoảng trắng thừa):

| Secret | Giá trị |
|---|---|
| `CLOUD_CREDENTIALS` | Toàn bộ nội dung file `sa-key.json` |
| `CLOUD_BUCKET` | Tên bucket (vd `my-mlops-bucket`) |
| `VM_HOST` | IP public VM (mục 2.3) |
| `VM_USER` | Tên user trên VM (`echo $USER` ở mục 2.4) |
| `VM_SSH_KEY` | Toàn bộ nội dung `~/.ssh/mlops_deploy` (private key) |

---

## 4. Chạy pipeline (Bước 2 → Bước 3)

### Bước 2 — push code (bằng chứng B5 một phần, B6)

```bash
git add .
git commit -m "feat: add CI/CD pipeline, tests, and serving API"
git push origin main
```
→ Tab **Actions**: Test ✓, Train ✓, **Eval ✗ (bị chặn vì acc ~0.68 < 0.70)**, Deploy skipped.
→ **Chụp log job Eval** → bằng chứng **B6** (gate chặn khi < 0.70).

### Bước 3 — thêm dữ liệu, kích hoạt tự động (bằng chứng B5 đầy đủ, B7, B8)

```bash
python add_new_data.py            # 2998 -> 5996 mẫu
dvc add data/train_phase1.csv
git add data/train_phase1.csv.dvc
git commit -m "data: bổ sung 2998 mẫu dữ liệu mới (train_phase2)"
dvc push                          # QUAN TRỌNG: dvc push TRƯỚC git push
git push origin main
```
→ Tab **Actions**: cả **4 job xanh** (acc ~0.75 ≥ 0.70 → deploy). **Chụp màn hình** → B5 + B8.

Khởi động/thử service (B7):

```bash
VM_IP=<YOUR_VM_IP>
curl http://$VM_IP:8000/health
curl -X POST http://$VM_IP:8000/predict -H "Content-Type: application/json" \
  -d '{"features": [7.4, 0.70, 0.00, 1.9, 0.076, 11.0, 34.0, 0.9978, 3.51, 0.56, 9.4, 0]}'
```
→ **Chụp màn hình** kết quả 2 lệnh curl → B7. Chụp Cloud Storage có `models/latest/model.pkl`.

---

## 5. Bonus (điểm cộng, tối đa 20)

| Bonus | Trạng thái | Việc bạn cần làm |
|---|---|---|
| **2. Đa thuật toán** | ✅ Code xong | Chạy `run_experiments.py`, chụp MLflow so sánh RF/GB/LR |
| **3. Báo cáo tự động** | ✅ Code xong | Tự động tạo `outputs/report.txt` + upload artifact. Chụp/ tải artifact `report` từ Actions |
| **4. Rollback** | ✅ Code xong | Bước "Rollback guard" trong job Train tự so sánh accuracy cũ/mới. Xem log để chụp |
| **5. Data drift** | ✅ Code xong | Phân phối nhãn ghi trong `metrics.json`, cảnh báo nếu lớp <10%. Không cần làm thêm |
| **1. DagsHub** | ⚙️ Cần bạn setup | Xem mục 5.1 dưới |

### 5.1 Bonus 1 — DagsHub (cần bạn làm tay)

Workflow đã sẵn sàng: job Train đọc 3 biến từ secrets. Chỉ cần:

1. Tạo tài khoản https://dagshub.com, kết nối repo GitHub, mở tab **Remote → MLflow** lấy:
   - Tracking URI (dạng `https://dagshub.com/<user>/<repo>.mlflow`)
   - Token (username + password/token).
2. Thêm 3 GitHub Secrets:
   - `MLFLOW_TRACKING_URI`
   - `MLFLOW_TRACKING_USERNAME`
   - `MLFLOW_TRACKING_PASSWORD`
3. Push lại → mỗi lần train trong Actions sẽ ghi lên DagsHub. Chụp màn hình DagsHub MLflow.

> Không có 3 secrets này pipeline vẫn chạy bình thường (MLflow ghi cục bộ trong runner).

---

## 6. Checklist nộp bài (bám rubric 100đ)

- [ ] URL repo GitHub public
- [ ] Screenshot MLflow UI ≥ 3 runs (B1, B2) + so sánh thuật toán (Bonus 2)
- [ ] Screenshot log Eval bị chặn ở Bước 2 (B6)
- [ ] Screenshot Actions 4 job xanh ở Bước 3 (B5, B8)
- [ ] Screenshot 2 lệnh curl `/health` + `/predict` (B7)
- [ ] Screenshot Cloud Storage: `dvc/` (B4) + `models/latest/model.pkl`
- [ ] Artifact `report` tải từ Actions (Bonus 3)
- [ ] Screenshot DagsHub MLflow (Bonus 1)
- [ ] Báo cáo ≤1 trang A4: bộ tham số tốt nhất (RF n=300, max_depth=None, acc 0.682) + khó khăn (trần accuracy Bước 2 ~0.68, gate chặn; Bước 3 thêm data lên 0.75) + bảng so sánh acc Bước 2 vs Bước 3
```
| Chỉ số   | Bước 2 (2998) | Bước 3 (5996) |
|----------|---------------|---------------|
| accuracy | ~0.68         | ~0.75         |
| f1_score | ~0.68         | ~0.75         |
```
