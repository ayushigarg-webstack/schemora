"""
Supervised Diagram-Type Classifier Training Pipeline.
Trains and evaluates Majority-Class baseline and TF-IDF + Multinomial Logistic Regression.
Performs hyperparameter optimization on train/val data and reports metrics on held-out test data.
Serializes model artifact to models/diagram_classifier.joblib.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix,
)

# Add ml-engine to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ir.models import DiagramType
from nlp.classifier_interface import HeuristicDiagramClassifier


def load_split_data(split_path: Path) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    """Loads text prompts, diagram_type labels, and full sample records from a split JSON file."""
    if not split_path.exists():
        raise FileNotFoundError(f"Split file not found: {split_path}")

    with open(split_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    texts = [s["text"].strip() for s in samples]
    labels = [s["diagram_type"] for s in samples]
    return texts, labels, samples


def train_and_evaluate(
    data_dir: Path,
    models_dir: Path,
    seed: int = 42,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Executes the end-to-end training and evaluation protocol:
    1. Loads train, val, and test splits.
    2. Trains Baseline 1 (Majority Class).
    3. Performs GridSearchCV for Baseline 2 (TF-IDF + Logistic Regression).
    4. Explores LinearSVC as an additional linear model comparison on validation data.
    5. Evaluates models on held-out test set.
    6. Benchmarks inference latency.
    7. Evaluates Heuristic classifier on the same test set for comparison.
    8. Serializes the winning model artifact and metadata.
    """
    train_path = data_dir / "train.json"
    val_path = data_dir / "val.json"
    test_path = data_dir / "test.json"

    X_train, y_train, train_samples = load_split_data(train_path)
    X_val, y_val, val_samples = load_split_data(val_path)
    X_test, y_test, test_samples = load_split_data(test_path)

    classes = sorted(list(set(y_train)))
    target_names = classes

    if verbose:
        print("=" * 80)
        print("AI DIAGRAM GENERATOR — SUPERVISED CLASSIFIER TRAINING PIPELINE")
        print("=" * 80)
        print(f"[*] Random Seed: {seed}")
        print(f"[*] Target Classes ({len(classes)}): {classes}")
        print(f"[*] Train set size: {len(X_train)} samples")
        print(f"[*] Val set size:   {len(X_val)} samples")
        print(f"[*] Test set size:  {len(X_test)} samples")
        print("-" * 80)

    # -----------------------------------------------------------------------
    # 1. BASELINE 1: Majority Class Classifier
    # -----------------------------------------------------------------------
    if verbose:
        print("[*] Training Baseline 1: Majority-Class Classifier...")
    dummy = DummyClassifier(strategy="most_frequent", random_state=seed)
    dummy.fit(X_train, y_train)

    dummy_val_preds = dummy.predict(X_val)
    dummy_test_preds = dummy.predict(X_test)

    dummy_test_acc = accuracy_score(y_test, dummy_test_preds)
    dummy_test_f1 = f1_score(y_test, dummy_test_preds, average="macro", zero_division=0)

    if verbose:
        print(f"    - Baseline 1 Test Accuracy: {dummy_test_acc:.4f} ({dummy_test_acc*100:.2f}%)")
        print(f"    - Baseline 1 Test Macro-F1: {dummy_test_f1:.4f}")
        print("-" * 80)

    # -----------------------------------------------------------------------
    # 2. BASELINE 2: TF-IDF + Logistic Regression Hyperparameter Search
    # -----------------------------------------------------------------------
    if verbose:
        print("[*] Optimizing Baseline 2: TF-IDF + Multinomial Logistic Regression...")

    base_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=r"(?u)\b\w[\w\.\-]+\b")),
        ("clf", LogisticRegression(random_state=seed, max_iter=1000, class_weight="balanced"))
    ])

    param_grid = {
        "tfidf__ngram_range": [(1, 1), (1, 2)],
        "tfidf__sublinear_tf": [True, False],
        "tfidf__min_df": [1, 2],
        "clf__C": [0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    grid_search = GridSearchCV(
        base_pipe,
        param_grid=param_grid,
        cv=cv,
        scoring="f1_macro",
        n_jobs=1,
        verbose=0
    )

    grid_search.fit(X_train, y_train)
    best_pipe = grid_search.best_estimator_

    val_preds_lr = best_pipe.predict(X_val)
    val_acc_lr = accuracy_score(y_val, val_preds_lr)
    val_f1_lr = f1_score(y_val, val_preds_lr, average="macro")

    if verbose:
        print(f"    - Best CV Macro-F1: {grid_search.best_score_:.4f}")
        print(f"    - Best Hyperparameters: {grid_search.best_params_}")
        print(f"    - Validation Accuracy: {val_acc_lr:.4f} ({val_acc_lr*100:.2f}%)")
        print(f"    - Validation Macro-F1: {val_f1_lr:.4f}")
        print("-" * 80)

    # -----------------------------------------------------------------------
    # 3. Model Comparison: LinearSVC
    # -----------------------------------------------------------------------
    if verbose:
        print("[*] Comparing with LinearSVC (Linear Support Vector Classifier)...")
    svc_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w[\w\.\-]+\b")),
        ("clf", LinearSVC(random_state=seed, max_iter=2000, class_weight="balanced"))
    ])
    svc_pipe.fit(X_train, y_train)
    val_preds_svc = svc_pipe.predict(X_val)
    val_acc_svc = accuracy_score(y_val, val_preds_svc)
    val_f1_svc = f1_score(y_val, val_preds_svc, average="macro")

    if verbose:
        print(f"    - LinearSVC Validation Accuracy: {val_acc_svc:.4f}")
        print(f"    - LinearSVC Validation Macro-F1: {val_f1_svc:.4f}")
        print("-" * 80)

    # -----------------------------------------------------------------------
    # 4. Final Held-Out Test Evaluation
    # -----------------------------------------------------------------------
    # Selected Model: Logistic Regression (provides calibrated predict_proba confidence scores)
    final_model = best_pipe
    test_preds = final_model.predict(X_test)
    test_probs = final_model.predict_proba(X_test)

    test_acc = accuracy_score(y_test, test_preds)
    test_macro_f1 = f1_score(y_test, test_preds, average="macro")
    test_weighted_f1 = f1_score(y_test, test_preds, average="weighted")
    test_prec = precision_score(y_test, test_preds, average="macro")
    test_rec = recall_score(y_test, test_preds, average="macro")

    cls_report_dict = classification_report(y_test, test_preds, target_names=target_names, output_dict=True)
    cls_report_text = classification_report(y_test, test_preds, target_names=target_names)
    conf_mat = confusion_matrix(y_test, test_preds, labels=target_names).tolist()

    # -----------------------------------------------------------------------
    # 5. Deduplicated Test Set Evaluation (Honest Reporting)
    # -----------------------------------------------------------------------
    # Evaluating on unique texts only to control for synthetic template repetition
    unique_test_map = {}
    for x, y in zip(X_test, y_test):
        if x not in unique_test_map:
            unique_test_map[x] = y

    X_test_dedup = list(unique_test_map.keys())
    y_test_dedup = list(unique_test_map.values())
    test_preds_dedup = final_model.predict(X_test_dedup)

    test_acc_dedup = accuracy_score(y_test_dedup, test_preds_dedup)
    test_f1_dedup = f1_score(y_test_dedup, test_preds_dedup, average="macro")

    # -----------------------------------------------------------------------
    # 6. Benchmark Heuristic Classifier on the same Test Set
    # -----------------------------------------------------------------------
    heuristic = HeuristicDiagramClassifier()
    heuristic_preds = [heuristic.predict(t).diagram_type.value for t in X_test]
    heuristic_acc = accuracy_score(y_test, heuristic_preds)
    heuristic_f1 = f1_score(y_test, heuristic_preds, average="macro", zero_division=0)

    # -----------------------------------------------------------------------
    # 7. Inference Latency Benchmark
    # -----------------------------------------------------------------------
    sample_text = X_test[0]
    # Warmup
    for _ in range(50):
        final_model.predict([sample_text])

    n_trials = 1000
    t0 = time.perf_counter()
    for _ in range(n_trials):
        final_model.predict([sample_text])
    t_elapsed = time.perf_counter() - t0
    avg_latency_ms = (t_elapsed / n_trials) * 1000.0

    if verbose:
        print("[+] FINAL TEST EVALUATION (HELD-OUT TEST SET):")
        print(f"    - Test Samples:         {len(X_test)} (Deduplicated: {len(X_test_dedup)})")
        print(f"    - Test Accuracy:        {test_acc:.4f} ({test_acc*100:.2f}%)")
        print(f"    - Test Macro-F1:        {test_macro_f1:.4f}")
        print(f"    - Test Weighted-F1:     {test_weighted_f1:.4f}")
        print(f"    - Test Macro Precision: {test_prec:.4f}")
        print(f"    - Test Macro Recall:    {test_rec:.4f}")
        print(f"    - Dedup Test Accuracy:  {test_acc_dedup:.4f} ({test_acc_dedup*100:.2f}%)")
        print(f"    - Dedup Test Macro-F1:  {test_f1_dedup:.4f}")
        print(f"    - Heuristic Test Acc:   {heuristic_acc:.4f} ({heuristic_acc*100:.2f}%)")
        print(f"    - Heuristic Test F1:    {heuristic_f1:.4f}")
        print(f"    - Inference Latency:    {avg_latency_ms:.3f} ms / sample")
        print("-" * 80)
        print("[+] CLASSIFICATION REPORT (HELD-OUT TEST SET):")
        print(cls_report_text)
        print("-" * 80)
        print("[+] CONFUSION MATRIX (Rows: True, Columns: Predicted):")
        print(f"Classes: {classes}")
        for row, cls_name in zip(conf_mat, classes):
            print(f"  {cls_name:<20}: {row}")
        print("=" * 80)

    # -----------------------------------------------------------------------
    # 8. Model Artifact Persistence
    # -----------------------------------------------------------------------
    models_dir.mkdir(parents=True, exist_ok=True)
    model_artifact_path = models_dir / "diagram_classifier.joblib"
    joblib.dump(final_model, model_artifact_path)

    metadata = {
        "model_version": "tfidf-logreg-v1.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "random_seed": seed,
        "classes": classes,
        "best_hyperparameters": grid_search.best_params_,
        "dataset": {
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "test_samples": len(X_test),
            "test_unique_samples": len(X_test_dedup),
        },
        "metrics": {
            "dummy_baseline": {
                "test_accuracy": round(float(dummy_test_acc), 4),
                "test_macro_f1": round(float(dummy_test_f1), 4),
            },
            "heuristic_baseline": {
                "test_accuracy": round(float(heuristic_acc), 4),
                "test_macro_f1": round(float(heuristic_f1), 4),
            },
            "linear_svc_val": {
                "val_accuracy": round(float(val_acc_svc), 4),
                "val_macro_f1": round(float(val_f1_svc), 4),
            },
            "logistic_regression": {
                "val_accuracy": round(float(val_acc_lr), 4),
                "val_macro_f1": round(float(val_f1_lr), 4),
                "test_accuracy": round(float(test_acc), 4),
                "test_macro_f1": round(float(test_macro_f1), 4),
                "test_weighted_f1": round(float(test_weighted_f1), 4),
                "test_precision": round(float(test_prec), 4),
                "test_recall": round(float(test_rec), 4),
                "dedup_test_accuracy": round(float(test_acc_dedup), 4),
                "dedup_test_macro_f1": round(float(test_f1_dedup), 4),
                "avg_latency_ms": round(float(avg_latency_ms), 3),
            },
            "classification_report": cls_report_dict,
            "confusion_matrix": conf_mat,
        }
    }

    metadata_path = models_dir / "classifier_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    if verbose:
        print(f"[+] Model artifact successfully saved to: {model_artifact_path}")
        print(f"[+] Metadata and evaluation metrics saved to: {metadata_path}")

    return metadata


def main():
    parser = argparse.ArgumentParser(description="Train Supervised Diagram Classifier.")
    parser.add_argument("--data-dir", type=str, default="data/splits", help="Path to splits directory.")
    parser.add_argument("--models-dir", type=str, default="models", help="Directory to save trained model artifacts.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    models_dir = Path(args.models_dir)

    train_and_evaluate(data_dir=data_dir, models_dir=models_dir, seed=args.seed, verbose=True)


if __name__ == "__main__":
    main()
