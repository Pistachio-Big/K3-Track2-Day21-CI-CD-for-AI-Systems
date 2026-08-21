"""
Tien ich chay nhieu thi nghiem cho Buoc 1 (khong bat buoc, nhung tao san bang
chung cho tieu chi cham diem):

  - B1 (12d): MLflow UI hien thi >= 3 lan chay voi sieu tham so khac nhau.
  - B2 (8d) : Moi lan chay ghi ca accuracy va f1_score.
  - B3 (4d) : So sanh de chon bo sieu tham so tot nhat.
  - Bonus 2 (4d): Thi nghiem voi nhieu thuat toan (random_forest,
                  gradient_boosting, logistic_regression).

Cach chay:
    # (tuy chon) tro MLflow vao SQLite cuc bo:
    #   Windows PowerShell:  $env:MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"
    #   Linux/macOS:         export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
    python run_experiments.py

Sau do mo MLflow UI de xem va so sanh:
    mlflow ui --backend-store-uri sqlite:///mlflow.db
"""

from src.train import train

# Cac cau hinh thi nghiem: doi ca sieu tham so lan thuat toan.
EXPERIMENTS = [
    {"model_type": "random_forest", "n_estimators": 50, "max_depth": 3, "min_samples_split": 2},
    {"model_type": "random_forest", "n_estimators": 100, "max_depth": 5, "min_samples_split": 2},
    {"model_type": "random_forest", "n_estimators": 200, "max_depth": 10, "min_samples_split": 5},
    {"model_type": "random_forest", "n_estimators": 300, "max_depth": None, "min_samples_split": 2},
    {"model_type": "gradient_boosting", "n_estimators": 300, "max_depth": 5, "min_samples_split": 2},
    {"model_type": "logistic_regression"},
]


def main():
    results = []
    for i, params in enumerate(EXPERIMENTS, 1):
        print(f"\n===== Thi nghiem {i}/{len(EXPERIMENTS)}: {params} =====")
        acc = train(params)
        results.append((params, acc))

    print("\n\n================ TONG KET ================")
    results.sort(key=lambda r: r[1], reverse=True)
    for params, acc in results:
        print(f"  acc={acc:.4f}  <-  {params}")
    best_params, best_acc = results[0]
    print(f"\nBo sieu tham so TOT NHAT (accuracy={best_acc:.4f}):\n  {best_params}")
    print("Hay cap nhat params.yaml voi bo nay truoc khi sang Buoc 2.")


if __name__ == "__main__":
    main()
