from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
from botocore.client import Config
import joblib
import os

app = FastAPI()

# OCI Object Storage duoc truy cap qua S3-compatible API.
CLOUD_BUCKET = os.environ["CLOUD_BUCKET"]
S3_ENDPOINT_URL = os.environ["S3_ENDPOINT_URL"]
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-ashburn-1")
MODEL_KEY = "models/latest/model.pkl"
MODEL_PATH = os.path.expanduser("~/models/model.pkl")

LABELS = {0: "thap", 1: "trung_binh", 2: "cao"}


def _s3_client():
    """Tao S3 client tro toi endpoint S3-compatible cua OCI Object Storage."""
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        region_name=AWS_REGION,
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


def download_model():
    """
    Tai file model.pkl tu OCI Object Storage ve may khi server khoi dong.

    Ham nay duoc goi mot lan khi module duoc import. Xac thuc bang
    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (dat trong systemd service,
    lay tu Customer Secret Key cua OCI).
    """
    # 1-4: tao client, tai model tu bucket ve may
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    _s3_client().download_file(CLOUD_BUCKET, MODEL_KEY, MODEL_PATH)
    print(f"Model da duoc tai xuong tu s3://{CLOUD_BUCKET}/{MODEL_KEY} (OCI)")


download_model()
model = joblib.load(MODEL_PATH)


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    """
    Endpoint kiem tra suc khoe server.
    GitHub Actions goi endpoint nay sau khi deploy de xac nhan server dang chay.

    Tra ve: {"status": "ok"}
    """
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    """
    Endpoint suy luan chinh.

    Dau vao : JSON {"features": [f1, f2, ..., f12]}
    Dau ra  : JSON {"prediction": <0|1|2>, "label": <"thap"|"trung_binh"|"cao">}

    Thu tu 12 dac trung (khop voi thu tu trong FEATURE_NAMES cua test):
        fixed_acidity, volatile_acidity, citric_acid, residual_sugar,
        chlorides, free_sulfur_dioxide, total_sulfur_dioxide, density,
        pH, sulphates, alcohol, wine_type
    """
    # 6. Kiem tra so luong dac trung.
    if len(req.features) != 12:
        raise HTTPException(
            status_code=400, detail="Expected 12 features (wine quality)"
        )

    # 7. Du doan.
    pred = int(model.predict([req.features])[0])

    # 8. Tra ve nhan tuong ung.
    return {"prediction": pred, "label": LABELS.get(pred, "unknown")}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
