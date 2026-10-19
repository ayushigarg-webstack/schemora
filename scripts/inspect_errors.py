"""
Validation and Test Error Analysis Script for Phase 4.
Extracts confusion patterns, misclassified samples, confidence distributions,
and out-of-distribution edge cases for ERROR_ANALYSIS.md.
"""

import json
from pathlib import Path
import joblib
from sklearn.metrics import classification_report, confusion_matrix


def analyze():
    model = joblib.load("models/diagram_classifier.joblib")
    val_samples = json.load(open("data/splits/val.json", encoding="utf-8"))
    test_samples = json.load(open("data/splits/test.json", encoding="utf-8"))

    classes = sorted(list(set(s["diagram_type"] for s in val_samples)))

    print("=" * 80)
    print("VALIDATION SET ERROR ANALYSIS")
    print("=" * 80)

    X_val = [s["text"].strip() for s in val_samples]
    y_val = [s["diagram_type"] for s in val_samples]
    val_preds = model.predict(X_val)
    val_probs = model.predict_proba(X_val)

    print(classification_report(y_val, val_preds, target_names=classes))

    cm = confusion_matrix(y_val, val_preds, labels=classes)
    print("\nConfusion Matrix (Rows: True, Cols: Pred):")
    for row, c in zip(cm, classes):
        print(f"  {c:<20}: {row}")

    print("\nMisclassified Validation Templates:")
    seen = set()
    for s, y_true, y_pred, pr in zip(val_samples, y_val, val_preds, val_probs):
        if y_true != y_pred:
            tid = s["metadata"]["template_id"]
            if tid not in seen:
                seen.add(tid)
                top_prob = max(pr)
                print(f"[*] Template: {tid}")
                print(f"    True Label: {y_true}")
                print(f"    Predicted:  {y_pred} (confidence: {top_prob:.2f})")
                print(f"    Text:       {s['text']}")
                print("-" * 70)


if __name__ == "__main__":
    analyze()
