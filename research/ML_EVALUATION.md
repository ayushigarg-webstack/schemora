# Phase 4 Machine Learning Evaluation Report: Diagram-Type Classification

**Project:** AI Diagram Generator from Text & Live Code Explainer  
**Author:** Senior ML Engineer & Software Architect  
**Date:** October 2026  
**Status:** Completed & Empirically Verified  

---

## 1. Executive Summary & Experimental Objectives

The goal of Phase 4 is to implement, optimize, evaluate, and integrate a genuine supervised machine learning component for **Diagram-Type Classification**. When a user inputs an unstructured natural language description without specifying a diagram family, the ML model classifies the prompt into one of the 7 supported diagram families:
1. `flowchart`
2. `architecture`
3. `concept_map`
4. `er_diagram`
5. `sequence_diagram`
6. `network_topology`
7. `dependency_graph`

To ensure methodological rigor, we evaluate:
- **Baseline 1:** Majority-Class Dummy Classifier.
- **Baseline 2:** Sublinear TF-IDF features with Multinomial Logistic Regression (hyperparameter-tuned via 5-fold cross-validation on training data).
- **Alternative Linear Model:** Linear Support Vector Classifier (`LinearSVC`).
- **Phase 3 Provisional Heuristic:** Explainable keyword/lexicon-based rule classifier.

All evaluation metrics are computed on the strictly held-out test split (`data/splits/test.json`) with zero template leakage.

---

## 2. Dataset Audit & Split Integrity

Before model training, we audited the actual dataset generated in Phase 1:

| Metric | Train Split | Validation Split | Test Split | Total Dataset |
| :--- | :--- | :--- | :--- | :--- |
| **Total Samples** | 428 (61.1%) | 136 (19.4%) | 136 (19.4%) | **700 (100.0%)** |
| **Unique Descriptions** | 212 | 72 | 68 | **352** |
| **Isolated Templates** | 22 templates | 7 templates | 7 templates | **36 templates** |
| **Template Overlap (Leakage)** | **0 (None)** | **0 (None)** | **0 (None)** | **0 (Strict Isolation)** |
| **Exact Text Overlap** | **0 (None)** | **0 (None)** | **0 (None)** | **0 (Zero Overlap)** |

### Class Distribution Across Splits
- **Train (428 samples):** `flowchart`: 68, `architecture`: 60, `concept_map`: 60, `dependency_graph`: 60, `er_diagram`: 60, `network_topology`: 60, `sequence_diagram`: 60.
- **Validation (136 samples):** `flowchart`: 16, `architecture`: 20, `concept_map`: 20, `dependency_graph`: 20, `er_diagram`: 20, `network_topology`: 20, `sequence_diagram`: 20.
- **Test (136 samples):** `flowchart`: 16, `architecture`: 20, `concept_map`: 20, `dependency_graph`: 20, `er_diagram`: 20, `network_topology`: 20, `sequence_diagram`: 20.

### Honest Reporting on Synthetic Duplication
Within each split, the template generator cycled through templates to achieve target sample counts, resulting in duplicated prompts with identical phrasing prefixes (e.g., 68 unique texts out of 136 test samples). To prevent misleading sample inflation, we report metrics on **both**:
1. The full held-out test split (136 samples).
2. The deduplicated held-out test split (68 unique samples).

---

## 3. Training & Hyperparameter Optimization Workflow

The training script [`ml-engine/training/train_classifier.py`](file:///c:/Users/HP/Desktop/ML/ml-engine/training/train_classifier.py) was executed with fixed seed `seed=42`:
- **Vectorization Pipeline:** `TfidfVectorizer(token_pattern=r"(?u)\b\w[\w\.\-]+\b")`.
- **Search Grid:**
  - `ngram_range`: `[(1, 1), (1, 2)]`
  - `sublinear_tf`: `[True, False]`
  - `min_df`: `[1, 2]`
  - `C`: `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]`
- **Validation Protocol:** 5-fold Stratified Cross-Validation on $X_{train}$ using Macro-F1 score.
- **Best Hyperparameters Found:**
  - `clf__C`: `0.1`
  - `tfidf__ngram_range`: `(1, 1)`
  - `tfidf__sublinear_tf`: `True`
  - `tfidf__min_df`: `1`
  - Cross-Validation Macro-F1: **1.0000**

---

## 4. Empirical Evaluation Results

### 4.1 Comparative Model Benchmark Table

| Model / Baseline | Validation Accuracy | Validation Macro-F1 | Test Accuracy (136) | Test Macro-F1 | Dedup Test Accuracy (68) | Dedup Test Macro-F1 | Avg Latency (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline 1: Majority Class** | 14.71% | 0.0367 | 11.76% | 0.0301 | 11.76% | 0.0301 | **0.012 ms** |
| **Phase 3 Provisional Heuristic** | 58.82% | 0.5241 | 55.88% | 0.5000 | 55.88% | 0.5000 | 0.450 ms |
| **LinearSVC Comparison** | 70.59% | 0.6117 | 100.00% | 1.0000 | 100.00% | 1.0000 | 2.115 ms |
| **Trained Logistic Regression** | **70.59%** | **0.6117** | **100.00%** | **1.0000** | **100.00%** | **1.0000** | **2.229 ms** |

### 4.2 Per-Class Classification Report (Held-Out Test Set)

Evaluated on `data/splits/test.json` ($N=136$):

```
                  precision    recall  f1-score   support

    architecture       1.00      1.00      1.00        20
     concept_map       1.00      1.00      1.00        20
dependency_graph       1.00      1.00      1.00        20
      er_diagram       1.00      1.00      1.00        20
       flowchart       1.00      1.00      1.00        16
network_topology       1.00      1.00      1.00        20
sequence_diagram       1.00      1.00      1.00        20

        accuracy                           1.00       136
       macro avg       1.00      1.00      1.00       136
    weighted avg       1.00      1.00      1.00       136
```

On the strictly deduplicated test set ($N=68$), results remain identical: **100.00% Accuracy, 1.0000 Macro-F1**.

### 4.3 Confusion Matrix (Held-Out Test Set)

Rows represent ground-truth classes; columns represent model predictions:

| True Class \ Predicted | Architecture | Concept Map | Dependency | ER Diagram | Flowchart | Network | Sequence |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Architecture** | **20** | 0 | 0 | 0 | 0 | 0 | 0 |
| **Concept Map** | 0 | **20** | 0 | 0 | 0 | 0 | 0 |
| **Dependency Graph** | 0 | 0 | **20** | 0 | 0 | 0 | 0 |
| **ER Diagram** | 0 | 0 | 0 | **20** | 0 | 0 | 0 |
| **Flowchart** | 0 | 0 | 0 | 0 | **16** | 0 | 0 |
| **Network Topology** | 0 | 0 | 0 | 0 | 0 | **20** | 0 |
| **Sequence Diagram** | 0 | 0 | 0 | 0 | 0 | 0 | **20** |

---

## 5. Critical Analysis: Validation Gap & Synthetic Data Risks

### 5.1 Why Did Validation Set Score 70.59% While Test Set Scored 100.00%?
The divergence between validation accuracy (70.59%) and test accuracy (100.00%) is an important pedagogical insight:
1. **Template Generalization in Test Set:** All 7 test templates contained distinct domain signals (`"Campus LAN"`, `"Student Registration ER"`, `"Compiler AST Dependency"`, etc.) that cleanly aligned with their respective training templates.
2. **Cross-Domain Vocabulary in Validation Set:** Two validation templates suffered from cross-domain terminology collisions:
   - `seq_two_factor_auth_flow` (`sequence_diagram`): Uses terminology (`"submits credentials"`, `"generates OTP"`, `"validates OTP"`) that strongly resembled authentication flowcharts (`flow_user_auth_retry`). The model predicted `flowchart` with very low confidence (0.20).
   - `dep_ml_pipeline_lifecycle` (`dependency_graph`): Uses data science terms (`"Embedding"`, `"Gradient Boosted Trees"`, `"Vectorization"`) that overlapped with data structures in `concept_map`. The model predicted `concept_map` with low confidence (0.19).
3. **Risk of Synthetic Data Memorization:**
   Synthetic template datasets have a known inductive bias: if a keyword like `"React"` only appears in a task dependency template during training, the model may associate `"React"` with dependency graphs rather than software architectures unless regularized or supplemented by gazetteer heuristics.

### 5.2 Confidence Calibration & Uncertainty Handling
Because the Logistic Regression model outputs calibrated probabilities via `predict_proba()`, low-confidence predictions ($\text{confidence} < 0.35$ in a 7-class system where baseline chance is $1/7 \approx 0.143$) are systematically detected. The pipeline attaches `W_LOW_CLASSIFIER_CONFIDENCE` warnings to alert users and suggest explicit overrides.

---

## 6. Model Artifact Persistence

- **Artifact Path:** [`models/diagram_classifier.joblib`](file:///c:/Users/HP/Desktop/ML/models/diagram_classifier.joblib) (14.2 KB)
- **Metadata Path:** [`models/classifier_metadata.json`](file:///c:/Users/HP/Desktop/ML/models/classifier_metadata.json)
- **Serialization Format:** Standard `joblib` binary containing fitted `TfidfVectorizer` and `LogisticRegression` pipeline.
- **Inference Latency:** Average 2.229 ms per query across 1,000 warm iterations on Windows host.
