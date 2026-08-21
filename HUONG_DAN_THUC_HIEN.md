# Hướng Dẫn Thực Hiện — Phần Còn Lại Bạn Phải Làm Tay (Oracle Cloud / OCI)

> Toàn bộ **code** đã được hoàn thiện và kiểm thử, và đã chuyển sang dùng
> **Oracle Cloud Infrastructure (OCI)** — Object Storage qua **S3-compatible API**
> (DVC remote `s3` + `boto3`). Tài liệu này liệt kê những việc **bạn phải tự thao tác**
> (tài khoản OCI, VM, secrets). Làm tuần tự từ trên xuống.

---

## 0. Trạng thái code (đã xong, không cần sửa)

| File | Nội dung đã hoàn thiện |
|---|---|
| `src/train.py` | Đọc data, train RF/GB/LR, log MLflow, `metrics.json`, `model.pkl`, báo cáo hiệu suất (Bonus 3), phân phối nhãn (Bonus 5) |
| `src/serve.py` | Tải model từ OCI Object Storage (S3-compat, boto3), `/health`, `/predict` (map nhãn thấp/trung_bình/cao) |
| `tests/test_train.py` | 3 unit test — **đã PASS cục bộ** |
| `.github/workflows/mlops.yml` | 4 job Test→Train→Eval→Deploy + Bonus 1/3/4, auth OCI qua S3 |
| `params.yaml` | Bộ tham số tốt nhất (RandomForest, acc ~0.68) |
| `run_experiments.py` | Tự động chạy 6 thí nghiệm cho Bước 1 + Bonus 2 |
| `requirements.txt` | `dvc[s3]` + `boto3` (thay cho `dvc[gs]` + `google-cloud-storage`) |

**Lưu ý quan trọng về eval gate (đã thống nhất — giữ ngưỡng 0.70):**
- Bước 2 (2998 mẫu): accuracy ~0.68 → **eval gate CHẶN deploy** → bằng chứng **B6**.
- Bước 3 (5996 mẫu): accuracy ~0.75 → **vượt ngưỡng → deploy xanh** → bằng chứng **B5 / B7 / B8**.
- ⟹ Screenshot "4 job xanh" lấy từ **lần chạy Bước 3**. Log Eval bị chặn ở Bước 2 là bằng chứng B6.

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

Mở MLflow UI → **chụp màn hình ≥3 runs** (B1/B2) + so sánh thuật toán (Bonus 2):

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
→ http://localhost:5000 → sort theo `accuracy` → chụp màn hình.

> **Bộ tham số tốt nhất (điền vào báo cáo — B3):** RandomForest, `n_estimators=300`,
> `max_depth=None`, `min_samples_split=2` → accuracy **0.682**. Đã đặt sẵn trong `params.yaml`.

---

## 2. Hạ tầng Oracle Cloud (OCI) — BẠN PHẢI LÀM TAY

> Cần đăng nhập tài khoản OCI của bạn nên tôi không làm được. OCI Object Storage
> được truy cập qua **S3-compatible API**, vì vậy DVC dùng remote kiểu `s3`.

### 2.0 Thông tin cần lấy trước

Ghi ra 4 giá trị sau (dùng xuyên suốt):

| Biến | Cách lấy |
|---|---|
| `REGION` | Region key, ví dụ `ap-singapore-1`, `us-ashburn-1` (góc trên Console) |
| `NAMESPACE` | Console → Object Storage, hoặc CLI: `oci os ns get --query data --raw-output` |
| `COMPARTMENT_OCID` | Console → Identity → Compartments → copy OCID |
| `BUCKET` | Tên bucket bạn tự đặt (duy nhất trong namespace) |

**S3 endpoint của bạn** sẽ là:
```
https://<NAMESPACE>.compat.objectstorage.<REGION>.oraclecloud.com
```

Cài OCI CLI (tùy chọn, có thể thay bằng thao tác Console):
```bash
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
oci setup config     # nhập tenancy OCID, user OCID, region, tạo API key
```

### 2.1 Tạo bucket + Customer Secret Key (khóa S3)

Tạo bucket (Console: Object Storage → Create Bucket, hoặc CLI):
```bash
oci os bucket create --name <BUCKET> --compartment-id <COMPARTMENT_OCID>
```

Tạo **Customer Secret Key** (đây chính là Access Key / Secret Key kiểu S3):
- Console → góc phải trên (avatar) → **My profile** → **Customer secret keys** → **Generate secret key**.
- Copy **Access Key** (hiện trong danh sách) và **Secret Key** (chỉ hiện **một lần**).

⚠️ Không commit hai khóa này. DVC sẽ lưu chúng vào `.dvc/config.local` (đã được DVC tự gitignore).

### 2.2 Khởi tạo DVC + push dữ liệu (bằng chứng B4)

```bash
export NAMESPACE=<NAMESPACE>
export REGION=<REGION>
export BUCKET=<BUCKET>
export ENDPOINT=https://$NAMESPACE.compat.objectstorage.$REGION.oraclecloud.com

dvc init
dvc remote add -d myremote s3://$BUCKET/dvc
dvc remote modify myremote endpointurl $ENDPOINT
dvc remote modify myremote region $REGION
# BAT BUOC cho OCI: ep path-style + region qua file cau hinh (xem muc 7).
# File .dvc/aws-config da co san trong repo; chi can tro configpath:
dvc remote modify myremote configpath .dvc/aws-config
# Khoa bi mat -> ghi vao config.local (KHONG commit):
dvc remote modify --local myremote access_key_id <ACCESS_KEY>
dvc remote modify --local myremote secret_access_key <SECRET_KEY>

dvc add data/train_phase1.csv data/eval.csv data/train_phase2.csv
git add data/*.dvc .gitignore .dvc/config
git commit -m "feat: track datasets with DVC (OCI Object Storage)"
dvc push
```
→ Console → Object Storage → bucket → xác nhận có prefix `dvc/`. **Chụp màn hình** (B4).

> `endpointurl` nằm trong `.dvc/config` (commit — không bí mật). Access/secret nằm trong
> `.dvc/config.local` (không commit). Trên CI, hai khóa được cấp qua GitHub Secrets (mục 3).

### 2.3 Tạo VM (OCI Compute) + mở port 8000 (phục vụ B7)

Tạo instance (Console → Compute → Instances → Create):
- Image: **Ubuntu 22.04** (user mặc định `ubuntu`; nếu chọn Oracle Linux thì user là `opc`).
- Shape: `VM.Standard.E2.1.Micro` (Always Free) là đủ.
- Thêm **SSH public key** của bạn khi tạo. **Lưu Public IP** sau khi tạo.

Mở port 8000 — **OCI cần 2 lớp**:

**(a) Security List / NSG của VCN:** Console → Networking → VCN → Subnet → Security List →
Add Ingress Rule: Source `0.0.0.0/0`, IP Protocol TCP, Destination Port `8000`.

**(b) Firewall trên chính VM** (ảnh Ubuntu của OCI chặn sẵn port ≠ 22):
```bash
# SSH vào VM roi chay:
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save     # luu de reboot van con
```

### 2.4 Cấu hình VM (một lần)

```bash
# SSH vao VM (thay IP + user):
ssh ubuntu@<VM_PUBLIC_IP>
# --- ben trong VM ---
sudo apt update && sudo apt install -y python3-pip
pip3 install fastapi uvicorn scikit-learn joblib boto3
mkdir -p ~/models ~/src
exit
# --- thoat VM ---

# Copy file serve.py len VM (khong can copy key file - dung boto3 voi env):
scp src/serve.py ubuntu@<VM_PUBLIC_IP>:~/src/serve.py
```

Tạo systemd service (SSH lại vào VM, **thay các giá trị trong `<...>`**):

```bash
ssh ubuntu@<VM_PUBLIC_IP>
# --- ben trong VM ---
sudo tee /etc/systemd/system/mlops-serve.service > /dev/null <<EOF
[Unit]
Description=MLOps Model Inference Server
After=network.target
[Service]
User=$USER
WorkingDirectory=/home/$USER
Environment="CLOUD_BUCKET=<BUCKET>"
Environment="S3_ENDPOINT_URL=https://<NAMESPACE>.compat.objectstorage.<REGION>.oraclecloud.com"
Environment="AWS_DEFAULT_REGION=<REGION>"
Environment="AWS_ACCESS_KEY_ID=<ACCESS_KEY>"
Environment="AWS_SECRET_ACCESS_KEY=<SECRET_KEY>"
ExecStart=/usr/bin/python3 /home/$USER/src/serve.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable mlops-serve
echo $USER   # <- LUU ten user nay cho secret VM_USER (thuong la 'ubuntu')
exit
```
> Chưa `systemctl start` lúc này — model chưa có trên Object Storage. Service sẽ chạy
> sau khi pipeline Bước 3 deploy thành công (Bước 2 bị gate chặn nên chưa deploy).

### 2.5 SSH key cho GitHub Actions deploy

```bash
ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N "" -C "github-actions-deploy"
# Them public key vao VM:
ssh ubuntu@<VM_PUBLIC_IP> "echo '$(cat ~/.ssh/mlops_deploy.pub)' >> ~/.ssh/authorized_keys"
```

---

## 3. GitHub Secrets — BẠN PHẢI LÀM TAY

Repo GitHub → **Settings → Secrets and variables → Actions → New repository secret**.
Thêm 8 secrets sau (không có khoảng trắng thừa):

| Secret | Giá trị |
|---|---|
| `OCI_ACCESS_KEY_ID` | Access Key của Customer Secret Key (mục 2.1) |
| `OCI_SECRET_ACCESS_KEY` | Secret Key của Customer Secret Key |
| `OCI_REGION` | Region key, vd `ap-singapore-1` |
| `OCI_S3_ENDPOINT` | `https://<NAMESPACE>.compat.objectstorage.<REGION>.oraclecloud.com` |
| `CLOUD_BUCKET` | Tên bucket |
| `VM_HOST` | Public IP của VM (mục 2.3) |
| `VM_USER` | User trên VM (`ubuntu` hoặc `opc`) |
| `VM_SSH_KEY` | Toàn bộ nội dung `~/.ssh/mlops_deploy` (private key) |

---

## 4. Chạy pipeline (Bước 2 → Bước 3)

> ⚠️ **Repo là FORK**: GitHub chặn auto-trigger (push) trên fork cho tới khi bạn vào
> tab **Actions** bấm **"I understand my workflows, go ahead and enable them"**. Chưa bấm
> thì chỉ chạy tay được (workflow_dispatch). Đã bấm rồi thì push tự chạy bình thường.

### Bước 2 — push code (bằng chứng B6)

```bash
git add .
git commit -m "feat: add CI/CD pipeline, tests, and serving API"
git push origin main
```
→ Tab **Actions**: Test ✓, Train ✓, **Eval ✗ (acc ~0.68 < 0.70)**, Deploy skipped.
→ **Chụp log job Eval** → bằng chứng **B6**.

### Bước 3 — thêm dữ liệu, kích hoạt tự động (bằng chứng B5, B7, B8)

```bash
python add_new_data.py            # 2998 -> 5996 mẫu
dvc add data/train_phase1.csv
git add data/train_phase1.csv.dvc
git commit -m "data: bổ sung 2998 mẫu dữ liệu mới (train_phase2)"
dvc push                          # QUAN TRỌNG: dvc push TRƯỚC git push
git push origin main
```
→ Tab **Actions**: cả **4 job xanh** (acc ~0.75 ≥ 0.70 → deploy). **Chụp màn hình** → B5 + B8.

Thử service (B7):

```bash
VM_IP=<VM_PUBLIC_IP>
curl http://$VM_IP:8000/health
curl -X POST http://$VM_IP:8000/predict -H "Content-Type: application/json" \
  -d '{"features": [7.4, 0.70, 0.00, 1.9, 0.076, 11.0, 34.0, 0.9978, 3.51, 0.56, 9.4, 0]}'
```
→ **Chụp màn hình** 2 lệnh curl → B7. Chụp Object Storage có `models/latest/model.pkl`.

---

## 5. Bonus (điểm cộng, tối đa 20)

| Bonus | Trạng thái | Việc bạn cần làm |
|---|---|---|
| **2. Đa thuật toán** | ✅ Code xong | Chạy `run_experiments.py`, chụp MLflow so sánh RF/GB/LR |
| **3. Báo cáo tự động** | ✅ Code xong | `outputs/report.txt` tự tạo + upload artifact. Tải artifact `report` từ Actions |
| **4. Rollback** | ✅ Code xong | Bước "Rollback guard" trong job Train tự so sánh accuracy cũ/mới. Xem log để chụp |
| **5. Data drift** | ✅ Code xong | Phân phối nhãn ghi trong `metrics.json`, cảnh báo nếu lớp <10%. Không cần làm thêm |
| **1. DagsHub** | ⚙️ Cần bạn setup | Xem mục 5.1 |

### 5.1 Bonus 1 — DagsHub (cần bạn làm tay)

Workflow đã sẵn sàng: job Train đọc 3 biến từ secrets. Chỉ cần:

1. Tạo tài khoản https://dagshub.com, kết nối repo GitHub, mở tab **Remote → MLflow** lấy
   Tracking URI + token (username/password).
2. Thêm 3 GitHub Secrets: `MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_USERNAME`, `MLFLOW_TRACKING_PASSWORD`.
3. Push lại → mỗi lần train trong Actions ghi lên DagsHub. Chụp màn hình DagsHub MLflow.

> Không có 3 secrets này pipeline vẫn chạy bình thường (MLflow ghi cục bộ trong runner).

---

## 6. Checklist nộp bài (bám rubric 100đ)

- [ ] URL repo GitHub public
- [ ] Screenshot MLflow UI ≥ 3 runs (B1, B2) + so sánh thuật toán (Bonus 2)
- [ ] Screenshot log Eval bị chặn ở Bước 2 (B6)
- [ ] Screenshot Actions 4 job xanh ở Bước 3 (B5, B8)
- [ ] Screenshot 2 lệnh curl `/health` + `/predict` (B7)
- [ ] Screenshot Object Storage: `dvc/` (B4) + `models/latest/model.pkl`
- [ ] Artifact `report` tải từ Actions (Bonus 3)
- [ ] Screenshot DagsHub MLflow (Bonus 1)
- [ ] Báo cáo ≤1 trang A4: bộ tham số tốt nhất (RF n=300, max_depth=None, acc 0.682) + khó khăn (trần accuracy Bước 2 ~0.68 → gate chặn; Bước 3 thêm data lên ~0.75) + bảng so sánh:
```
| Chỉ số   | Bước 2 (2998) | Bước 3 (5996) |
|----------|---------------|---------------|
| accuracy | ~0.68         | ~0.75         |
| f1_score | ~0.68         | ~0.75         |
```

---

## 7. Ghi chú riêng cho OCI (khác GCP)

- OCI Object Storage = **S3-compatible**; xác thực bằng **Customer Secret Key**, không phải service account JSON.
- Mở port 8000 cần **cả** Security List/NSG của VCN **và** iptables trên VM (ảnh Ubuntu OCI chặn sẵn).
- **DVC bắt buộc path-style + region** (virtual-hosted lỗi SSL vì cert OCI không phủ subdomain bucket;
  thiếu region → `SignatureDoesNotMatch`). Đã xử lý bằng file `.dvc/aws-config`:
  ```
  [default]
  region = ap-singapore-1
  s3 =
      addressing_style = path
  ```
  và `dvc remote modify myremote configpath .dvc/aws-config` (file này đã commit → CI tự dùng).
- Trên CI: creds lấy từ env `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (secrets); region+addressing từ `.dvc/aws-config`.
- `boto3` (serve.py, workflow upload) dùng `endpoint_url` + `Config(s3={"addressing_style":"path"}, signature_version="s3v4")`.
- User SSH mặc định: `ubuntu` (Ubuntu image) hoặc `opc` (Oracle Linux).
