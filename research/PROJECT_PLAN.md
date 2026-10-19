# AI Diagram Generator from Text & Live Code Explainer — Project Plan

## 1. Project Overview & Objectives

### 1.1 Executive Summary
The **AI Diagram Generator from Text & Live Code Explainer** is an end-to-end, multi-modal software engineering and machine learning platform that converts:
1. **Unstructured Natural-Language Descriptions** into structured, semantically validated, and interactively editable visual diagrams (Software Architecture, Flowcharts, Concept Maps, Entity-Relationship, Sequence, Network Topology, and Dependency Graphs).
2. **Raw Source Code** (Python, JavaScript/TypeScript) into interactive control-flow graphs, call hierarchies, data-flow diagrams, and object/class relationships, paired with step-by-step runtime execution visualization and beginner-friendly pedagogical explanations.

The system is designed for computer science students, software engineers, and system architects. It strictly avoids superficial wrappers around LLMs or static flowchart generators. Instead, it couples a measurable, reproducible Machine Learning pipeline with deterministic semantic parsers, abstract syntax tree (AST) analyzers, graph layout algorithms, and a professional, Lucidchart-inspired React canvas.

---

## 2. System Architecture & Key Components

The system consists of three decoupled layers:

```
+----------------------------------------------------------------------------------------------------+
|                                    PRESENTATION LAYER (React 19 + Vite)                            |
|  +---------------------------+  +--------------------------------+  +---------------------------+  |
|  | Natural Language Mode     |  | Central Interactive Canvas     |  | Live Code Explainer Mode  |  |
|  | - Prompt input & presets  |  | - React Flow DAG & layout      |  | - Monaco/Prism editor     |  |
|  | - Category prediction &   |  | - Specialized SVG renderers    |  | - Ast/CFG/Call-Graph view |  |
|  |   user override           |  | - Custom nodes (Decision, etc) |  | - Execution Step Controller|  |
|  | - Confidence display      |  | - Node/Edge property editors   |  | - Variable state table    |  |
|  +---------------------------+  +--------------------------------+  +---------------------------+  |
|  +-----------------------------------------------------------------------------------------------+  |
|  | Lucidchart-Inspired Docking Panels: Toolbar | Validation Warnings | JSON/SVG/PNG Export/Import |  |
+----------------------------------------------------------------------------------------------------+
                                             |  REST API / JSON
                                             v
+----------------------------------------------------------------------------------------------------+
|                                    BACKEND API LAYER (FastAPI + Pydantic)                          |
|  - POST /api/diagram/generate   : End-to-end NLP-to-Diagram pipeline                               |
|  - POST /api/diagram/validate   : Generalized IR schema and cycle/semantic validation             |
|  - GET  /api/diagram/types      : Supported diagram families, metadata & confidence thresholds     |
|  - POST /api/code/analyze       : Multi-language AST parsing, CFG, call graph & data flow          |
|  - POST /api/code/trace         : Isolated, sandboxed execution tracing with state snapshots       |
|  - POST /api/code/explain       : Pedagogical plain-English node/line explanations                 |
|  - GET  /api/code/languages     : Supported parsers, limitations & security profiles               |
+----------------------------------------------------------------------------------------------------+
                                             |
             +-------------------------------+-------------------------------+
             v                                                               v
+--------------------------------------------+  +--------------------------------------------+
|             NLP & ML ENGINE                |  |            CODE ANALYSIS ENGINE            |
| - Text Preprocessing & Sentence Splitting  |  | - Multi-Language AST Parsers (Python `ast` |
| - Supervised Diagram Type Classifier       |  |   and JS/TS regex/token parser)            |
|   (TF-IDF + Multinomial Logistic Regres.)  |  | - Control Flow Graph (CFG) Generator       |
| - spaCy Dependency & Linguistic Extractor  |  | - Call Graph & Function Hierarchy Builder  |
| - Rule & Pattern Relation Extractor        |  | - Data Flow & Variable Scoping Analyzer    |
| - Domain Terminology Gazetteer             |  | - Secure Instrumented Sandboxed Tracer     |
| - Generalized Intermediate Rep (IR)        |  |   (Resource-capped, restricted builtins)   |
| - NetworkX Graph Layout Engine             |  | - Bi-directional Line-to-Node Source Mapper|
|   (Sugiyama layered, Spring, Timeline)     |  | - Pedagogical Natural-Language Explainer   |
+--------------------------------------------+  +--------------------------------------------+
```

---

## 3. Supported Diagram Families & Semantic Profiles

| Diagram Family | Target Semantics | Specific Node Types | Specific Edge Types | Layout Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Flowchart / Activity** | Sequence, decisions, loops, start/end terminals | `terminal`, `process`, `decision`, `io` | `flow`, `branch_yes`, `branch_no`, `loop_back` | Sugiyama Layered (Hierarchical DAG) |
| **Software Architecture** | Components, services, tiers, databases, gateways | `service`, `client`, `database`, `cache`, `external_api` | `api_call`, `data_read_write`, `pub_sub`, `dependency` | Layered Tier-based / Orthogonal layout |
| **Concept Map / KG** | Concepts, categories, relationships, domain knowledge | `concept`, `category`, `instance` | `is_a`, `part_of`, `relates_to`, `leads_to` | Force-Directed (Fruchterman-Reingold / Spring) |
| **Entity-Relationship (ER)** | Database entities, attributes, primary/foreign keys | `entity`, `weak_entity`, `attribute` | `one_to_one`, `one_to_many`, `many_to_many` | Orthogonal bipartite layout |
| **Sequence Diagram** | Participants, lifelines, ordered time-series messages | `participant`, `actor`, `lifeline` | `synchronous_call`, `async_call`, `return_signal` | Ordered Lifeline Timeline (X: actors, Y: step) |
| **Network Topology** | Devices, subnets, routers, firewalls, cloud boundaries | `host`, `switch`, `router`, `firewall`, `cloud` | `ethernet`, `wireless`, `wan`, `tunnel` | Cluster/Hub-and-spoke layout |
| **Dependency Graph** | Tasks, milestones, build steps, parallel execution | `task`, `milestone`, `deliverable` | `blocks`, `depends_on`, `triggers` | Topological DAG Layered layout |

---

## 4. Phase-by-Phase Roadmap & Acceptance Criteria

### Phase 0: Workspace Inspection & Project Planning *(Current)*
- **Tasks**: Inspect host environment, Python versions (3.14/3.13), Node.js (v24), npm, pip packages, hardware capabilities. Establish project repository structure, design project plans, progress records, decision records, and dataset plans.
- **Acceptance Criteria**: All 4 documentation files created under `research/`. No disruption of workspace. Clear plan approved.

### Phase 1: Research & Dataset Investigation
- **Tasks**: Evaluate public datasets (DiagramGenBenchmark, FlowGen, Text-to-Graph, CoNLL04). Design a comprehensive, reproducible multi-family dataset generator with deterministic templates, natural variations, strict split isolation (train/val/test), and JSON schema validation.
- **Acceptance Criteria**: Dataset generation script producing >= 700 verified multi-class diagram examples across 7 diagram families, split 70/15/15 with zero data leakage.

### Phase 2: Generalized Intermediate Representation (IR) & Validation
- **Tasks**: Implement Pydantic v2 schemas for Generalized Diagram IR (`DiagramGraph`, `DiagramNode`, `DiagramEdge`, `DiagramType`, `LayoutCoordinate`, `ValidationWarning`). Implement diagram-family validators checking connectivity, cycle validity, cardinality, and required attributes.
- **Acceptance Criteria**: 100% test coverage on schema serialization/deserialization and validation edge cases (cycles, dangling edges, duplicate IDs).

### Phase 3: NLP Pipeline & Graph Construction
- **Tasks**: Build `ml-engine/src/`:
  - `preprocessing.py`: text normalization, clause splitting, negation detection, conditional extraction.
  - `entity_extractor.py`: spaCy linguistic parsing, technical noun-chunk extraction, domain gazetteer.
  - `relation_extractor.py`: dependency parse rules, grammatical subject-verb-object (SVO) extraction, connective mapping.
  - `graph_builder.py`: construct IR from entities and relations.
  - `diagram_adapters.py`: adapters transforming raw graph into family-specific semantics (Architecture, Flowchart, Concept Map).
- **Acceptance Criteria**: Automated test suite verifying text-to-JSON extraction across standard examples (E-commerce architecture, Student assignment flowchart, Data structures concept map).

### Phase 4: Real Machine Learning Component Training & Evaluation
- **Tasks**: Implement supervised Diagram-Type Classifier:
  - Baseline: Majority-class predictor.
  - Model: TF-IDF vectorization (unigrams + bigrams) + Multinomial Logistic Regression / LinearSVC.
  - Reproducible training pipeline `ml-engine/train_classifier.py` saving metrics, confusion matrices, and serialized model artifact `models/diagram_classifier.joblib`.
  - Evaluate accuracy, macro-F1, per-class precision and recall on held-out test split.
- **Acceptance Criteria**: Model achieves >85% Macro-F1 on held-out test set, significantly outperforming baseline. Metrics logged in `research/ML_EVALUATION.md`.

### Phase 5: Graph Layout Engine & Graph Algorithms
- **Tasks**: Implement pure-Python / NetworkX layout algorithms:
  - Layered Sugiyama DAG layout for flowcharts and architectures.
  - Force-directed spring layout for concept maps.
  - Lifeline step layout for sequence diagrams.
  - Cycle detection, reachability analysis, and disconnected component grouping.
- **Acceptance Criteria**: Layout coordinates generated for all nodes and edges without overlapping coordinates; graceful fallback when external tools are absent.

### Phase 6: Code Analysis Engine (Live Code-to-Diagram Explainer)
- **Tasks**: Implement `ml-engine/src/code_analysis/`:
  - `code_parser.py`: Python AST parser and JavaScript AST/lexical analyzer.
  - `control_flow.py`: Control Flow Graph (CFG) extractor with basic blocks, condition edges, loop edges.
  - `call_graph.py`: Function call hierarchy and caller-callee mapping.
  - `data_flow.py`: Variable mutation, assignment, and usage tracking.
  - `execution_tracer.py`: Sandboxed, resource-limited Python execution tracer recording step-by-step line executions, call stack frames, and variable state snapshots.
  - `explainer.py`: Pedagogical plain-English natural language explainer for selected code regions and nodes.
- **Acceptance Criteria**: Correct CFG, call graph, and execution trace generated for recursion, loops, conditionals, sorting algorithms, and OOP classes. Security timeouts and banned imports (`os`, `subprocess`, socket) tested.

### Phase 7: FastAPI Backend API
- **Tasks**: Implement `backend/`:
  - Endpoints: `/health`, `/api/diagram/generate`, `/api/diagram/validate`, `/api/diagram/types`, `/api/code/analyze`, `/api/code/trace`, `/api/code/explain`, `/api/code/languages`.
  - CORS middleware, input sanitization, max-payload limits, error handling.
  - Comprehensive unit and integration tests with `pytest` and `httpx`.
- **Acceptance Criteria**: All endpoints tested, documented with OpenAPI schema, passing 100% of integration test cases.

### Phase 8: Lucidchart-Inspired React Frontend & Interactive Canvas
- **Tasks**: Implement `frontend/` using Vite + React 19 + Tailwind CSS:
  - Lucidchart-inspired visual aesthetic: professional toolbars, crisp grid canvas, collapsible docking panels, polished typography.
  - Dual Mode Switcher: "Text to Diagram" vs "Live Code Explainer".
  - React Flow canvas with custom nodes (Process, Decision, Service, Database, Concept, Lifeline).
  - Code Editor panel (Monaco/CodeMirror or Prism) with synchronized line highlighting.
  - Execution Step Player: Play, Pause, Step Next, Step Prev, Speed slider, Variable watch table, Call stack inspector.
  - Canvas editing: Drag nodes, edit labels, add/delete nodes and edges, automatic layout trigger, JSON/SVG/PNG export.
- **Acceptance Criteria**: Fully interactive canvas, real backend integration, no mock generation data in production mode, smooth step-through playback.

### Phase 9: End-to-End Integration & Robustness Testing
- **Tasks**: Test all 20 specified edge cases (sequential process, conditional loop, e-commerce architecture, concept map, ER database, sequence flow, ambiguous prompt, syntax errors, malicious code execution attempts, export/import roundtrip).
- **Acceptance Criteria**: Zero unhandled exceptions. All edge cases produce appropriate diagrams or clear, actionable error messages.

### Phase 10: ML Evaluation, Error Analysis & Pedagogical Documentation
- **Tasks**:
  - Run full benchmark evaluation script over held-out datasets.
  - Compute precision, recall, F1 for classification and entity/relation extraction.
  - Document error analysis in `research/ERROR_ANALYSIS.md`.
  - Compile comprehensive, academic-grade `README.md` explaining theory, architecture, execution, and interview defense questions.
- **Acceptance Criteria**: All metrics real and verified. Comprehensive documentation ready for second-year BTech academic evaluation and technical interviews.

### Phase 11: Final Polish, Build Verification & Quality Sign-Off
- **Tasks**: Verify full frontend production build (`npm run build`), backend cold-start, end-to-end user workflows, clean Git state.
- **Acceptance Criteria**: Production build succeeds with 0 errors. All integration tests pass.

---

## 5. Technology Stack & Dependencies

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language Runtime** | Python 3.14 / 3.13 | High-performance NLP, AST parsing, and ML inference |
| **NLP & ML** | `scikit-learn`, `spacy`, `joblib`, `numpy` | Supervised classification, POS tagging, dependency parsing |
| **Graph Processing** | `networkx` | Graph algorithms, topological sorting, layout generation |
| **Backend Framework** | `fastapi`, `uvicorn`, `pydantic v2` | High-performance async API with strict schema validation |
| **Frontend Framework** | `React 19`, `Vite`, `Tailwind CSS` | Modern responsive reactive UI |
| **Canvas & Diagramming**| `@xyflow/react` (React Flow) | Node-and-edge interactive canvas, custom nodes/edges |
| **Code Editor** | `@monaco-editor/react` / custom editor | Code syntax highlighting and bidirectional line mapping |
| **Icons & UI** | `lucide-react` | Clean, Lucidchart-style professional iconography |
| **Testing** | `pytest`, `httpx` (Backend), `vitest` (Frontend) | Automated unit, regression, and integration testing |

---

## 6. Risk Management & Fallback Strategies

| Identified Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **External Graphviz binary missing on host** | Layout failure | Implement native pure-Python Sugiyama and Spring layouts in NetworkX as zero-dependency primary engine. |
| **Ambiguous or underspecified user text** | Poor diagram generation | Return confidence metrics, semantic warnings, and recommended diagram types; allow 1-click user override. |
| **Arbitrary code execution security risk** | Host vulnerability | Sandbox Python code execution: run in isolated subprocess with strict timeouts (2s), memory caps, and restricted AST visitors blocking imports of `os`, `sys`, `subprocess`, `socket`, `shutil`. |
| **Complex nested syntax in JS/Python** | AST parse failure | Implement safe AST recovery: provide partial CFG or high-level function dependency graph with clear warning banner. |
| **LLM rate limit / offline environment** | System unavailability | The entire core ML/NLP pipeline is 100% local (scikit-learn + spaCy + AST parser). Generative AI assistance is strictly optional. |
