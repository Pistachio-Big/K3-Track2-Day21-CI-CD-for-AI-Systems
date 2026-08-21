import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

EVAL_THRESHOLD = 0.70


def build_model(model_type: str, params: dict):
    """
    Khoi tao mo hinh theo model_type (Bonus 2: Thi nghiem voi nhieu thuat toan).

    Ho tro: random_forest (mac dinh), gradient_boosting, logistic_regression.
    Cac tham so cay (n_estimators, max_depth, min_samples_split) chi ap dung cho
    thuat toan phu hop; logistic_regression bo qua chung.
    """
    n_estimators = int(params.get("n_estimators", 100))
    max_depth = params.get("max_depth", None)
    max_depth = int(max_depth) if max_depth is not None else None
    min_samples_split = int(params.get("min_samples_split", 2))

    if model_type == "gradient_boosting":
        return GradientBoostingClassifier(
            n_estimators=n_estimators,
            max_depth=(max_depth if max_depth is not None else 3),
            min_samples_split=min_samples_split,
            random_state=42,
        )
    elif model_type == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=42)
    else:  # random_forest (mac dinh)
        return RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42,
        )


def compute_label_distribution(y) -> dict:
    """
    Bonus 5: Tinh ty le phan phoi nhan cua tap huan luyen.
    Tra ve dict {label: ty_le}. In canh bao neu bat ky lop nao chiem < 10%.
    """
    counts = pd.Series(y).value_counts(normalize=True).sort_index()
    dist = {str(int(k)): round(float(v), 4) for k, v in counts.items()}
    for label, ratio in dist.items():
        if ratio < 0.10:
            print(
                f"[CANH BAO - DATA DRIFT] Lop {label} chi chiem {ratio:.2%} "
                f"(< 10%) trong tap huan luyen. Du lieu co the mat can bang."
            )
    return dist


def write_report(y_true, y_pred, out_path: str = "outputs/report.txt") -> None:
    """
    Bonus 3: Ghi confusion matrix + precision/recall cho tung lop ra file van ban.
    """
    labels = sorted(set(list(y_true) + list(y_pred)))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    precision, recall, f1_per, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )

    lines = []
    lines.append("=== BAO CAO HIEU SUAT MO HINH ===\n")
    lines.append("Confusion Matrix (hang = thuc te, cot = du doan):")
    header = "        " + "  ".join(f"pred_{l}" for l in labels)
    lines.append(header)
    for i, l in enumerate(labels):
        row = "  ".join(f"{v:6d}" for v in cm[i])
        lines.append(f"true_{l}  {row}")
    lines.append("")
    lines.append("Precision / Recall / F1 cho tung lop:")
    for i, l in enumerate(labels):
        lines.append(
            f"  Lop {l}: precision={precision[i]:.4f} "
            f"recall={recall[i]:.4f} f1={f1_per[i]:.4f} support={int(support[i])}"
        )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def train(
    params: dict,
    data_path: str = "data/train_phase1.csv",
    eval_path: str = "data/eval.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so (co the co model_type).
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia.

    Tra ve:
        accuracy (float): do chinh xac tren tap danh gia.
    """

    # 1. Doc du lieu huan luyen va danh gia
    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    # 2. Tach dac trung (X) va nhan (y)
    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    model_type = params.get("model_type", "random_forest")

    with mlflow.start_run():

        # Bonus 5: phan phoi nhan
        label_distribution = compute_label_distribution(y_train)

        # 3. Ghi nhan cac sieu tham so
        mlflow.log_params(params)
        mlflow.log_param("model_type", model_type)

        # 4. Khoi tao va huan luyen mo hinh (Bonus 2: nhieu thuat toan)
        model = build_model(model_type, params)
        model.fit(X_train, y_train)

        # 5. Du doan tren tap danh gia va tinh chi so
        preds = model.predict(X_eval)
        acc = float(accuracy_score(y_eval, preds))
        f1 = float(f1_score(y_eval, preds, average="weighted"))

        # 6. Ghi nhan chi so vao MLflow
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        mlflow.sklearn.log_model(model, "model")

        # 7. In ket qua ra man hinh
        print(f"Model: {model_type} | Accuracy: {acc:.4f} | F1: {f1:.4f}")

        # Bonus 3: bao cao hieu suat (confusion matrix + precision/recall)
        write_report(list(y_eval), list(preds))

        # 8. Luu metrics ra file outputs/metrics.json (co ca phan phoi nhan - Bonus 5)
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/metrics.json", "w") as f:
            json.dump(
                {
                    "accuracy": acc,
                    "f1_score": f1,
                    "model_type": model_type,
                    "label_distribution": label_distribution,
                },
                f,
            )

        # 9. Luu mo hinh ra file models/model.pkl
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.pkl")

    # 10. Tra ve acc
    return acc


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
