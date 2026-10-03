"""Beginner MNIST / Kaggle Digit Recognizer model comparison.

Expected files:
  data/train.csv  (label + pixel0 ... pixel783)
  data/test.csv   (pixel0 ... pixel783)

Run: python mnist_digit_classifier.py --data-dir data
"""

from pathlib import Path
import argparse

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier


def main():
    parser = argparse.ArgumentParser(description="Compare classifiers on Kaggle MNIST CSV files.")
    parser.add_argument("--data-dir", default="data", help="Folder containing train.csv and test.csv")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    train_path = data_dir / "train.csv"
    test_path = data_dir / "test.csv"
    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            f"Could not find {train_path} and {test_path}. Download the Kaggle files and put them in the data folder."
        )

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    if "label" not in train_df.columns:
        raise ValueError("train.csv must contain a 'label' column.")

    # Separate answers (y) from the 784 pixel measurements (X).
    y = train_df["label"]
    X = train_df.drop(columns="label")
    # Match test columns/order to training. Pixel intensities go from 0 to 255.
    X_test = test_df.reindex(columns=X.columns)
    if X_test.isna().any().any():
        raise ValueError("test.csv is missing one or more pixel columns found in train.csv.")

    # Preprocessing: use floating point and scale pixel values into [0, 1].
    X = X.astype("float32") / 255.0
    X_test = X_test.astype("float32") / 255.0

    # Keep a held-out validation set to compare models before making submissions.
    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    models = {
        "Logistic regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, solver="lbfgs"),
        ),
        "Random forest": RandomForestClassifier(
            n_estimators=200, random_state=42, n_jobs=-1
        ),
    }

    scores = {}
    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        predictions = model.predict(X_valid)
        scores[name] = accuracy_score(y_valid, predictions)
        print(f"Validation accuracy: {scores[name]:.4f}")
        print("Confusion matrix (rows = true digit, columns = predicted digit):")
        print(confusion_matrix(y_valid, predictions))
        if name == "Logistic regression":
            print("Per-digit report:")
            print(classification_report(y_valid, predictions, zero_division=0))

    best_name = max(scores, key=scores.get)
    best_model = models[best_name]
    print(f"\nBest validation model: {best_name} ({scores[best_name]:.4f})")

    # Refit the selected model on all labeled rows, then predict Kaggle's test rows.
    best_model.fit(X, y)
    test_predictions = best_model.predict(X_test)
    submission = pd.DataFrame({"ImageId": range(1, len(test_predictions) + 1), "Label": test_predictions})
    output_path = data_dir / "submission.csv"
    submission.to_csv(output_path, index=False)
    print(f"Saved Kaggle submission file: {output_path}")
    print("Review submission.csv, then upload it on the Kaggle competition page.")


if __name__ == "__main__":
    main()
