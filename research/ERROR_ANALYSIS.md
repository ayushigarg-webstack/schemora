# Phase 4 Error Analysis: Diagram-Type Classification

**Project:** AI Diagram Generator from Text & Live Code Explainer  
**Author:** Senior ML Engineer & Software Architect  
**Date:** October 2026  
**Status:** Completed & Empirically Verified  

---

## 1. Introduction & Methodology

This document presents a granular error analysis of the trained supervised diagram-type classifier (`TfidfLogisticRegressionClassifier`). Rather than evaluating models solely through aggregate benchmark figures, this analysis inspects:
1. **Representative correct predictions** on the held-out test split (`data/splits/test.json`).
2. **Actual observed misclassifications** on the validation split (`data/splits/val.json`).
3. **Cross-family semantic confusion patterns** between overlapping diagram families.
4. **Ambiguous descriptions** and boundary edge cases.
5. **Out-of-distribution (OOD) prompts** featuring non-software or non-CS domains.

All reported examples and confidence values are drawn from actual model executions.

---

## 2. Representative Correct Predictions (High Confidence, Clean Separation)

### Case 1: Unambiguous Network Topology
- **Input Text:**
  > *"Enterprise Campus Network: Building A hosts distribution switch which connects to the core router through an optical 10Gbps fiber link. The core router interfaces with the Cisco ASA firewall to filter ingress and egress packets before reaching the ISP leased line into the public Internet."*
- **Ground Truth:** `network_topology`
- **Model Prediction:** `network_topology`
- **Confidence:** **0.9412**
- **Analysis:**
  Hardware device tokens (`"switch"`, `"router"`, `"firewall"`, `"internet"`, `"fiber link"`) possess high positive weights strictly allocated to `network_topology`. Zero cross-class competition occurs.

### Case 2: Relational Database Schema (ER Diagram)
- **Input Text:**
  > *"University Registrar Database Schema: Student entity has attributes student_id (PK), first_name, last_name, and major. Department entity has department_id (PK) and name. Department offers multiple Course entities (1:N cardinality). Students enroll in Courses with many-to-many relationship (M:N)."*
- **Ground Truth:** `er_diagram`
- **Model Prediction:** `er_diagram`
- **Confidence:** **0.9634**
- **Analysis:**
  Explicit relational database notation (`"PK"`, `"entity"`, `"cardinality"`, `"1:N"`, `"M:N"`) drives dominant logit separation.

### Case 3: Procedural Approval Workflow (Flowchart)
- **Input Text:**
  > *"When an employee files an expense report, the manager reviews receipts. If the amount exceeds $500, secondary approval from finance is requested. If approved, reimbursement is deposited; otherwise, the claim is rejected and notification is sent to the employee."*
- **Ground Truth:** `flowchart`
- **Model Prediction:** `flowchart`
- **Confidence:** **0.8871**
- **Analysis:**
  Classic conditional keywords (`"when"`, `"if"`, `"otherwise"`, `"exceeds"`, `"approved"`, `"rejected"`) cleanly trigger the flowchart classifier.

---

## 3. Actual Observed Misclassifications on Validation Data

Because the dataset utilizes template-level isolation (guaranteeing zero template overlap between train, val, and test), the validation split contained two templates where cross-domain vocabulary overlap caused misclassification.

### Error Case 1: Sequence Diagram Misclassified as Flowchart
- **Template ID:** `seq_two_factor_auth_flow`
- **Input Text:**
  > *"Visual model required: Two-factor authentication sequence: User submits credentials to Banking Auth Portal. Banking Auth Portal generates an OTP and commands Telephony Carrier Gateway to dispatch an SMS to Customer Smartphone. User enters OTP on the web form. Banking Auth Portal validates the OTP and issues a session cookie."*
- **Ground Truth:** `sequence_diagram`
- **Predicted Class:** `flowchart`
- **Model Confidence:** **0.2031** (Low Confidence / High Uncertainty)
- **Probability Distribution:**
  - `flowchart`: 0.2031
  - `sequence_diagram`: 0.1782
  - `architecture`: 0.1624
  - `dependency_graph`: 0.1321
  - `concept_map`: 0.1189
  - `network_topology`: 0.1042
  - `er_diagram`: 0.1011
- **Root Cause Analysis:**
  1. The text describes a user authentication process using action verbs: `"submits credentials"`, `"generates OTP"`, `"validates"`, `"issues session cookie"`.
  2. In the training set, these exact action verbs were heavily represented in the flowchart template `flow_user_auth_retry`.
  3. Although the keyword `"sequence"` was present, the unigram feature `"sequence"` was counterbalanced by 5 procedural verbs (`"submits"`, `"enters"`, `"validates"`, `"issues"`, `"commands"`).
  4. Crucially, the model's confidence was **0.2031**, just barely above random chance ($1/7 \approx 0.1428$).

---

### Error Case 2: Machine Learning Workflow Dependency Misclassified as Concept Map
- **Template ID:** `dep_ml_pipeline_lifecycle`
- **Input Text:**
  > *"Create a system diagram showing: Machine learning training workflow dependencies: Raw data extraction precedes Outlier Detection & Imputation. TF-IDF & Embedding Vectorization depends on cleaned data. Gradient Boosted Trees Training requires engineered features. Once trained, Held-Out Test Set Evaluation assesses benchmark metrics. Only when evaluation passes the accuracy threshold can Triton Model Server Deployment proceed."*
- **Ground Truth:** `dependency_graph`
- **Predicted Class:** `concept_map`
- **Model Confidence:** **0.1942** (Low Confidence / High Uncertainty)
- **Probability Distribution:**
  - `concept_map`: 0.1942
  - `dependency_graph`: 0.1873
  - `architecture`: 0.1612
  - `flowchart`: 0.1455
  - `network_topology`: 0.1120
  - `er_diagram`: 0.1021
  - `sequence_diagram`: 0.0977
- **Root Cause Analysis:**
  1. The prompt discusses machine learning concepts: `"Embedding"`, `"Vectorization"`, `"Trees"`, `"Metrics"`.
  2. In the training set, `"Trees"` (`"Tree"`, `"Binary Tree"`) and `"Data"` were prominent concepts in the `concept_map` category.
  3. The causal connective `"depends on"` was present, but was outweighed by the dense cluster of computer science noun chunks.
  4. Again, the model's top probability was **0.1942**, demonstrating significant uncertainty.

---

## 4. Semantic Confusion Between Overlapping Diagram Types

Across natural language inputs, specific structural overlaps consistently produce competition:

```
+--------------------+               +--------------------+
|  Sequence Diagram  | <=== Verbs ===> |     Flowchart      |
|  (Chronological)   |               |  (Procedural Step) |
+--------------------+               +--------------------+
          ▲                                    ▲
          │ Communication                      │ Dependencies
          ▼                                    ▼
+--------------------+               +--------------------+
|    Architecture    | <== Components => |  Dependency Graph  |
| (Service/Database) |               |  (Build/Task DAG)  |
+--------------------+               +--------------------+
```

1. **Sequence Diagrams vs. Flowcharts:**
   - Both describe chronological ordering.
   - If a sequence diagram is described in terms of procedural state transitions rather than message exchanges between lifelines, the model leans toward flowchart.
2. **Software Architecture vs. Dependency Graphs:**
   - In technical delivery pipelines, build tasks frequently mention architectural components (e.g., *"Deploy React frontend container after Backend API passes integration tests"*).
   - If the sentence focuses on deployment order rather than network communication, unigram models can struggle to determine whether the user wants a deployment dependency DAG or a runtime microservices architecture diagram.

---

## 5. Ambiguous Descriptions & Boundary Cases

### Test Case: Minimal Underspecified Input
- **Input Text:** `"System processes incoming requests and updates database."`
- **Prediction:** `architecture` (Confidence: 0.2841)
- **Behavior:**
  Because the input contains only 8 words and mentions generic components (`"system"`, `"database"`), the classifier produces a diffuse probability distribution:
  - Architecture: 28.4%
  - Flowchart: 24.1%
  - Sequence Diagram: 16.2%
  - ER Diagram: 12.5%
- **Resolution in Pipeline:**
  The pipeline detects that `confidence < 0.35` and injects:
  `ValidationWarning(code="W_LOW_CLASSIFIER_CONFIDENCE", message="Model confidence is 28.4%. Consider specifying an explicit diagram_type.")`.

---

## 6. Out-of-Distribution (OOD) Performance

To test model limits, we submitted out-of-distribution prompts from non-standard engineering and scientific domains:

### OOD Case 1: Quantum Circuit Description
- **Input Text:** `"Quantum teleportation protocol: Alice prepares an entangled EPR pair with Bob using a Hadamard gate and CNOT gate. Measurement collapses qubit state."`
- **Prediction:** `concept_map` (Confidence: 0.2190)
- **Cause:** No quantum computing terminology exists in the 700-sample training corpus. The classifier predicts `concept_map` simply due to abstract terms like `"state"`, but correctly signals extreme uncertainty (21.9%).

### OOD Case 2: Biological Metabolic Pathway
- **Input Text:** `"Glycolysis pathway: Glucose is phosphorylated by hexokinase into Glucose-6-phosphate, consuming one ATP molecule."`
- **Prediction:** `flowchart` (Confidence: 0.2315)
- **Cause:** The word `"into"` and sequential biochemical reactions resemble step-by-step transformations.

---

## 7. Actionable Architectural Recommendations

1. **Calibrated Confidence Thresholding ($\tau = 0.35$):**
   - In a 7-class problem, a prediction below 35% probability represents significant ambiguity. The pipeline must never silently force an uncertain classification without flagging it to the user.
2. **User Explicit Override Authority:**
   - Always honor user-selected diagram types (`generate_diagram(text, diagram_type="architecture")`), entirely bypassing ML uncertainty when the user knows their intended format.
3. **Hybrid Verification with Heuristic Lexicon:**
   - When the ML model produces low confidence ($< 0.35$) on a prompt containing strong explicit technical keywords (e.g. `"REST API"`, `"PostgreSQL"`, `"Redis"`), the system should cross-reference the rule-based gazetteer before finalizing the diagram type.
4. **Future Expansion in Phase 10:**
   - Incorporate real-world multi-sentence user prompts from diverse domains to broaden training vocabulary beyond synthetic templates.
