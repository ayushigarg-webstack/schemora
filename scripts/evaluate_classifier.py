#!/usr/bin/env python3
"""
AI Diagram Generator — Diagram-Type Classifier Evaluation.
Evaluates the trained model, majority-class baseline, and heuristic classifier
on the held-out test split (both full 136 and deduplicated 68 samples),
as well as the validation split, measuring accuracy, macro-F1, per-class metrics,
confusion matrices, and inference latency.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix,
)

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "ml-engine"))

from nlp.classifier_interface import HeuristicDiagramClassifier


def run_evaluation():
    models_dir = Path("models")
    data_dir = Path("data/splits")
    
    model_path = models_dir / "diagram_classifier.joblib"
    assert model_path.exists(), f"Model not found at {model_path}"
    model = joblib.load(model_path)
    
    with open(data_dir / "train.json", "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(data_dir / "val.json", "r", encoding="utf-8") as f:
        val_data = json.load(f)
    with open(data_dir / "test.json", "r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    X_train = [s["text"].strip() for s in train_data]
    y_train = [s["diagram_type"] for s in train_data]
    
    X_val = [s["text"].strip() for s in val_data]
    y_val = [s["diagram_type"] for s in val_data]
    
    X_test = [s["text"].strip() for s in test_data]
    y_test = [s["diagram_type"] for s in test_data]
    
    # Deduplicated test set
    test_dedup_map = {}
    for x, y in zip(X_test, y_test):
        if x not in test_dedup_map:
            test_dedup_map[x] = y
    X_test_dedup = list(test_dedup_map.keys())
    y_test_dedup = list(test_dedup_map.values())
    
    classes = sorted(list(set(y_train)))
    
    # 1. Majority-Class Baseline
    dummy = DummyClassifier(strategy="most_frequent", random_state=42)
    dummy.fit(X_train, y_train)
    
    dummy_test_preds = dummy.predict(X_test)
    dummy_test_acc = accuracy_score(y_test, dummy_test_preds)
    dummy_test_macro_f1 = f1_score(y_test, dummy_test_preds, average="macro", zero_division=0)
    
    # 2. Heuristic Baseline
    heuristic = HeuristicDiagramClassifier()
    heuristic_test_preds = [heuristic.predict(x).diagram_type.value for x in X_test]
    heuristic_test_acc = accuracy_score(y_test, heuristic_test_preds)
    heuristic_test_macro_f1 = f1_score(y_test, heuristic_test_preds, average="macro", zero_division=0)
    
    heuristic_val_preds = [heuristic.predict(x).diagram_type.value for x in X_val]
    heuristic_val_acc = accuracy_score(y_val, heuristic_val_preds)
    heuristic_val_macro_f1 = f1_score(y_val, heuristic_val_preds, average="macro", zero_division=0)
    
    # 3. Trained Model on Validation Set
    val_preds = model.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    val_macro_f1 = f1_score(y_val, val_preds, average="macro")
    val_weighted_f1 = f1_score(y_val, val_preds, average="weighted")
    val_cm = confusion_matrix(y_val, val_preds, labels=classes).tolist()
    val_report = classification_report(y_val, val_preds, target_names=classes, output_dict=True)
    
    # 4. Trained Model on Held-out Test Set (Full 136)
    test_preds = model.predict(X_test)
    test_probs = model.predict_proba(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    test_macro_f1 = f1_score(y_test, test_preds, average="macro")
    test_weighted_f1 = f1_score(y_test, test_preds, average="weighted")
    test_macro_prec = precision_score(y_test, test_preds, average="macro")
    test_macro_rec = recall_score(y_test, test_preds, average="macro")
    test_cm = confusion_matrix(y_test, test_preds, labels=classes).tolist()
    test_report = classification_report(y_test, test_preds, target_names=classes, output_dict=True)
    test_report_text = classification_report(y_test, test_preds, target_names=classes)
    
    # 5. Trained Model on Deduplicated Test Set (68 unique)
    test_dedup_preds = model.predict(X_test_dedup)
    test_dedup_acc = accuracy_score(y_test_dedup, test_dedup_preds)
    test_dedup_macro_f1 = f1_score(y_test_dedup, test_dedup_preds, average="macro")
    
    # 6. Latency Benchmark
    sample_text = X_test[0]
    for _ in range(50):
        model.predict([sample_text])
    n_trials = 1000
    t0 = time.perf_counter()
    for _ in range(n_trials):
        model.predict([sample_text])
    elapsed = time.perf_counter() - t0
    latency_ms = (elapsed / n_trials) * 1000.0
    
    results = {
        "classes": classes,
        "sample_counts": {
            "train": len(X_train),
            "val": len(X_val),
            "test_full": len(X_test),
            "test_dedup": len(X_test_dedup),
        },
        "majority_baseline": {
            "test_accuracy": round(float(dummy_test_acc), 4),
            "test_macro_f1": round(float(dummy_test_macro_f1), 4),
        },
        "heuristic_baseline": {
            "val_accuracy": round(float(heuristic_val_acc), 4),
            "val_macro_f1": round(float(heuristic_val_macro_f1), 4),
            "test_accuracy": round(float(heuristic_test_acc), 4),
            "test_macro_f1": round(float(heuristic_test_macro_f1), 4),
        },
        "validation_set": {
            "accuracy": round(float(val_acc), 4),
            "macro_f1": round(float(val_macro_f1), 4),
            "weighted_f1": round(float(val_weighted_f1), 4),
            "confusion_matrix": val_cm,
            "classification_report": val_report,
        },
        "test_set_full": {
            "accuracy": round(float(test_acc), 4),
            "macro_f1": round(float(test_macro_f1), 4),
            "weighted_f1": round(float(test_weighted_f1), 4),
            "macro_precision": round(float(test_macro_prec), 4),
            "macro_recall": round(float(test_macro_rec), 4),
            "confusion_matrix": test_cm,
            "classification_report": test_report,
        },
        "test_set_dedup": {
            "accuracy": round(float(test_dedup_acc), 4),
            "macro_f1": round(float(test_dedup_macro_f1), 4),
        },
        "latency_ms": round(float(latency_ms), 3),
    }
    
    print("=" * 80)
    print("DIAGRAM-TYPE CLASSIFIER EVALUATION RESULTS")
    print("=" * 80)
    print(f"Latency: {latency_ms:.3f} ms / query (1,000 iterations)")
    print("\nBenchmark Summary:")
    print(f"{'Model':<30} | {'Val Acc':<10} | {'Val Macro-F1':<12} | {'Test Acc':<10} | {'Test Macro-F1':<12} | {'Dedup Acc':<10}")
    print("-" * 92)
    print(f"{'Majority Class Baseline':<30} | {'-':<10} | {'-':<12} | {dummy_test_acc*100:6.2f}%    | {dummy_test_macro_f1:12.4f} | {dummy_test_acc*100:6.2f}%")
    print(f"{'Heuristic Rule Classifier':<30} | {heuristic_val_acc*100:6.2f}%    | {heuristic_val_macro_f1:12.4f} | {heuristic_test_acc*100:6.2f}%    | {heuristic_test_macro_f1:12.4f} | {heuristic_test_acc*100:6.2f}%")
    print(f"{'Trained Logistic Regression':<30} | {val_acc*100:6.2f}%    | {val_macro_f1:12.4f} | {test_acc*100:6.2f}%    | {test_macro_f1:12.4f} | {test_dedup_acc*100:6.2f}%")
    print()
    print("Per-Class Report on Held-Out Test Set (N=136):")
    print(test_report_text)
    print("Test Confusion Matrix (Rows: True, Cols: Pred):")
    for cls_name, row in zip(classes, test_cm):
        print(f"  {cls_name:<20}: {row}")
        
    print("\nValidation Confusion Matrix (Rows: True, Cols: Pred):")
    for cls_name, row in zip(classes, val_cm):
        print(f"  {cls_name:<20}: {row}")
        
    out_path = Path("research/classifier_eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Saved detailed results to {out_path}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_evaluation()
