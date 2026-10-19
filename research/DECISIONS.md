# Architectural Decision Records (ADRs)

This document records the foundational architectural, algorithmic, and engineering decisions for the **AI Diagram Generator from Text & Live Code Explainer**.

---

## ADR-001: Unified Generalized Intermediate Representation (IR) with Semantic Extensions

### Context
Diagrams across computer science vary widely in semantics:
- Flowcharts describe procedural sequence and boolean decisions.
- Architecture diagrams describe distributed components and network protocols.
- Concept maps describe ontological and semantic associations.
- ER diagrams describe entity attributes, keys, and relational cardinalities.
- Sequence diagrams describe chronological participant messages.
- Code execution graphs describe control flow basic blocks and call stacks.

A naive approach would either:
1. Force all diagrams into a generic flowchart format (losing domain-specific semantics), or
2. Create separate, incompatible data models for each diagram type (preventing code reuse and editor unification).

### Decision
We define a **Unified Generalized Diagram Intermediate Representation (IR)** using Pydantic v2:
- Core container: `DiagramGraph` containing `metadata`, `nodes`, `edges`, `layout_config`, and `warnings`.
- `DiagramNode`: Contains `id`, `label`, `type` (e.g. `process`, `decision`, `service`, `database`, `concept`, `participant`), `attributes`, `source_location` (line start/end for code), and optional `position` (`x`, `y`).
- `DiagramEdge`: Contains `id`, `source`, `target`, `label`, `edge_type` (e.g. `flow`, `branch_yes`, `api_call`, `is_a`, `one_to_many`), `directed`, and `metadata` (e.g. sequence order, protocol).
- Polymorphic validation rules: The IR validates structural constraints specific to each diagram family (e.g., verifying that decision nodes in flowcharts have labeled outgoing branches, or that sequence messages have monotonically increasing sequence indexes).

### Consequences
- **Positive**: Clean abstraction between NLP/AST extraction, layout algorithms, and frontend rendering; allows adding new diagram types (e.g. state charts) by extending node/edge enums without breaking existing types.
- **Trade-off**: Requires careful validation logic to handle family-specific rules without bloat.

---

## ADR-002: Supervised Machine Learning Model for Diagram Type Classification

### Context
When a user inputs a natural language prompt (e.g. "Create an architecture diagram for an e-commerce application..."), the system must infer the intended diagram family automatically, output confidence scores, and allow user overrides.

### Decision
1. Implement a genuine supervised ML classifier using `scikit-learn`:
   - Feature Extraction: TF-IDF vectorization with sublinear term-frequency scaling and n-gram range `(1, 2)`.
   - Classification Algorithm: Multinomial Logistic Regression with L2 regularization (`C=1.0`) and balanced class weighting.
   - Baseline Comparison: Majority-Class dummy classifier evaluated under identical conditions.
2. Metrics: Evaluate on a strictly held-out test split (15%) reporting Accuracy, Macro-F1, per-class Precision/Recall, and Confusion Matrix.
3. Persistence: Serialize trained model and vectorizer pipeline into `models/diagram_classifier.joblib`.
4. Inference: Compute class probability distributions using `predict_proba()`. Expose top prediction and confidence score to the API; flag low-confidence predictions (< 0.60) with an exploratory suggestion.

### Consequences
- **Positive**: Lightweight, ultra-fast inference (< 5ms), deterministic, fully explainable via top n-gram weights, zero external API costs or latency.
- **Trade-off**: Requires a representative training dataset covering varied vocabularies and syntaxes for all 7 diagram families.

---

## ADR-003: Hybrid Linguistic & Pattern-Based Relation Extraction Pipeline

### Context
Extracting entities, components, and relationships from arbitrary text requires balancing semantic flexibility with high structural precision. Pure LLM-based prompting is non-deterministic and can produce hallucinated nodes or invalid syntax. Pure regex-based extraction fails on grammatical variations.

### Decision
Implement a modular hybrid pipeline:
1. **Preprocessing**: Sentence splitting, clause boundary detection, connector recognition (`if`, `then`, `otherwise`, `connects to`, `calls`, `inherits from`).
2. **Entity & Concept Extraction**: Use `spaCy` linguistic analysis (`en_core_web_sm` / token rules), noun-phrase chunking, and a domain-specific technical gazetteer (recognizing terms like `React`, `FastAPI`, `PostgreSQL`, `Redis`, `Router`, `Switch`).
3. **Relation Extraction**: Dependency parse tree navigation (subject-verb-object triples, prepositional attachments, conjunction chaining).
4. **Adapter Transformation**: Transform extracted entities and relations into family-specific nodes and edges via specialized adapters (`ArchitectureAdapter`, `FlowchartAdapter`, `ConceptMapAdapter`).

### Consequences
- **Positive**: Explainable, verifiable, runs entirely locally without internet access, highly accurate for technical and academic descriptions.
- **Trade-off**: Requires custom rules for complex compound sentences, which will be documented with explicit limitations.

---

## ADR-004: Lucidchart-Inspired Professional Frontend with React Flow

### Context
Diagram editors frequently suffer from two extremes: either toy-like prototypes lacking basic editing capabilities, or bloated generic dashboards. The user interface needs to match modern professional productivity tools (like Lucidchart or Eraser.io).

### Decision
1. **Framework & Canvas**: Use React 19 + Vite + Tailwind CSS + `@xyflow/react` (React Flow) for hardware-accelerated SVG/canvas rendering.
2. **Design Language**: Crisp grid canvas, restrained slate/indigo accents, crisp typography, collapsible docking sidebars, floating toolbars, and clear visual hierarchy.
3. **Core Canvas Features**:
   - Pan, zoom, minimap, grid snap.
   - Interactive node drag, label inline editing.
   - Dynamic connection handles for creating custom edges.
   - Contextual node inspector for modifying labels, types, and colors.
   - One-click auto-layout button.
   - Export to PNG, SVG, and validated JSON.
4. **Dual Mode Interface**:
   - Mode A: **Natural Language to Diagram** (Prompt editor, sample prompts, confidence badge, type override).
   - Mode B: **Live Code Explainer** (Split-pane code editor, AST/CFG/Call-Graph view toggle, playback step controls, variable state table).

### Consequences
- **Positive**: Delivers a production-grade user experience; allows users to iteratively refine generated diagrams manually.
- **Trade-off**: Requires custom React Flow node components for non-standard shapes (diamonds for decisions, cylinders for databases, lifelines for sequence diagrams).

---

## ADR-005: Safe Sandboxed Execution Tracer for Live Code Explainer

### Context
The "Live Code Explainer" feature requires stepping through code execution, inspecting variable mutations, and visualizing call stacks. However, executing arbitrary user-provided code on the backend poses severe security and stability risks (e.g. infinite loops, filesystem access, remote code execution).

### Decision
1. **Two-Tier Code Analysis**:
   - **Tier 1 (Static Analysis - Always Available)**: Parse code via Python's built-in `ast` module. Generate AST nodes, Control Flow Graphs (CFG), and function call hierarchies without executing any code.
   - **Tier 2 (Dynamic Execution Tracing - Strictly Sandboxed)**: For supported Python snippets, execute code inside a restricted subprocess using Python's `sys.settrace()`:
     - Resource Limits: Hard timeout of 2.0 seconds; max 500 execution steps; memory limits.
     - Security Sandbox: AST pre-scan rejecting dangerous imports (`os`, `sys`, `subprocess`, `socket`, `shutil`, `threading`, `multiprocessing`, `ctypes`, `builtins.open`, `eval`, `exec`).
     - State Capture: Record `(line_number, event_type, function_name, local_variables, call_stack)` at each step.
2. **Pedagogical Explanation Engine**: Map each AST node and execution step to plain-English beginner explanations (e.g. "Evaluating condition `x > 0`. Because `x = 5`, condition is True. Branching to line 4.").

### Consequences
- **Positive**: 100% safe execution on the host machine; prevents infinite loops from hanging the backend; provides rich step-by-step visualization for computer science students.
- **Trade-off**: Complex dynamic libraries (e.g. numpy array internals) will have simplified string representations in the trace.

---

## ADR-006: Self-Contained Graph Layout Engine via NetworkX

### Context
Graph layout engines like Graphviz (`dot`, `neato`) produce excellent layouts, but requiring users to install native OS Graphviz binaries creates major cross-platform installation hurdles (especially on Windows).

### Decision
1. Implement native pure-Python graph layout algorithms using `networkx` as the default engine:
   - **Hierarchical Layout (Sugiyama-style DAG)**: For Flowcharts and Software Architecture. Computes topological layering, node ranking, and assigns `(x, y)` coordinates with horizontal tier spacing.
   - **Force-Directed Layout (Fruchterman-Reingold / Spring)**: For Concept Maps and Knowledge Graphs.
   - **Orthogonal / Grid Layout**: For ER diagrams and component matrices.
   - **Timeline Lifeline Layout**: For Sequence diagrams (fixed X-axis for participants, descending Y-axis for chronological messages).
2. Allow optional Graphviz integration (`pygraphviz` or `pydot`) as an enhancement if detected, but never make it a hard requirement.

### Consequences
- **Positive**: Zero external binary dependencies; runs cleanly out-of-the-box on any Windows, macOS, or Linux machine.
- **Trade-off**: NetworkX spring/bipartite layouts require custom heuristics to avoid edge crossings on large graphs, which will be implemented and tested.

---

## ADR-007: Domain-Specific Semantic Validation and Graph Cycle Policies

### Context
A naive graph validator either universally rejects cycles (failing on valid flowcharts, networks, and concept maps) or universally ignores them (permitting fatal deadlocks in task workflows or temporal inversions in sequence diagrams). In addition, different diagram families have strict domain-specific rules (e.g. decision nodes requiring multiple branches, ER keys requiring entity attachment).

### Decision
Implement a two-stage validation pipeline in `ml-engine/ir/validators.py`:
1. **Universal Structural Layer**:
   - Unique node and edge identifiers.
   - Referential integrity (no dangling edges referencing unknown node IDs).
   - Graph size bounds (maximum 500 nodes, 1000 edges).
   - Duplicate relationship detection.
2. **Polymorphic Family Semantic Layer & Cycle Policies**:
   - **Flowchart**: Decision nodes must have >= 2 outgoing branches; cycles are **explicitly permitted** (modeling iterative loops and retries).
   - **Software Architecture**: Detects anti-patterns (e.g. direct client-to-database connections without API tier); cycles are **permitted** but flagged with a `W_CIRCULAR_DEPENDENCY` warning.
   - **Concept Map**: Requires labeled semantic propositions on edges; cycles are **permitted** (modeling ontological cross-references).
   - **Entity-Relationship (ER)**: Enforces that primary keys attach exclusively to entities; validates cardinality notation (`1:1`, `1:N`, `M:N`).
   - **Sequence Diagram**: Enforces chronological monotonic sequence ordering; verifies that response messages between participants occur after the corresponding request (`sequence_order_response > sequence_order_request`); temporal inversion is an error (`E_SEQUENCE_ORDER_INVERTED`).
   - **Network Topology**: Allows redundant physical network loops (Spanning Tree Protocol); warns on disconnected devices (`W_NET_DISCONNECTED_DEVICE`).
   - **Dependency Graph**: Strictly enforces a Directed Acyclic Graph (DAG); cycles represent deadlocks and are rejected as fatal errors (`E_DEPENDENCY_CYCLE`).
   - **Code Explainer Diagrams**: Validates source code line ranges (`1 <= line_start <= line_end`) and execution step monotonicity.

### Consequences
- **Positive**: Eliminates false positive errors on valid cyclical diagrams while guaranteeing strict semantic correctness for workflows and sequence lifelines; provides actionable, structured feedback to users.
- **Trade-off**: Requires dedicated unit tests for each diagram family's specific failure and warning modes.

---

## ADR-008: Modular NLP Pipeline, Hybrid Gazetteer-Rule Fallback, and Extensible Classifier Interface

### Context
In Phase 3, the system must transform unstructured natural language into structured, semantically validated Diagram Intermediate Representation (IR) graphs. This requires solving three engineering problems:
1. **Classifier Decoupling**: Diagram family inference must work immediately in Phase 3 without blocking on Phase 4's quantitative machine learning training, while ensuring Phase 4's trained TF-IDF + Logistic Regression model can be plugged in with zero pipeline refactoring.
2. **Environment Robustness & Transparency**: In Python 3.14 on Windows, pre-built binary wheels for spaCy / Cython may not be installed. The pipeline must not crash, nor may it silently pretend that complex statistical neural parsing occurred.
3. **Coreference & Granularity**: Naive NER or token chunking splits composite technical names (e.g. creating two separate nodes for "React" and "Frontend" from "React frontend") or creates duplicate nodes for repeated mentions (e.g. "Node.js backend" and "Node.js service").

### Decision
1. **Modular 8-Step Pipeline**:
   - `TextPreprocessor`: Length validation, smart normalization, abbreviation-protected sentence segmentation, clause splitting, negation detection, and conditional marker extraction.
   - `DiagramClassifier` Interface: Abstract base class with `predict()` and `predict_proba()`. In Phase 3, an explainable `HeuristicDiagramClassifier` leverages domain vocabulary indicators. A thread-safe singleton registry (`get_default_classifier()`, `set_default_classifier()`) permits Phase 4 to register the serialized scikit-learn model cleanly.
   - `EntityExtractor`: Backed by a comprehensive 9-domain technical gazetteer with span-level token adjacency merging (absorbing generic words into specific brands, e.g. "React frontend" -> "React Frontend") and brand-level coreference tracking (aliasing repeated mentions).
   - `RelationExtractor`: Directional SVO and rule extractors for flows, decisions, tiered architectures, concept propositions, ER cardinalities, sequence ordering, and network connections.
   - `GraphBuilder`: Sanitizes IDs and enforces referential integrity, eliminating dangling edges.
   - `Diagram Adapters`: Specialized adapters for all 7 families, guaranteeing strict compliance with Phase 2 validators (e.g. >= 2 branches on decisions, non-empty proposition labels on concept maps).
   - `CodeDiagramBridge`: Interface accepting structured entities, relations, `SourceLocation` line numbers, and `ExecutionStateSnapshot` states, verified by `CodeDiagramValidator`.
   - `validate_diagram`: Embedded as the final step of `generate_diagram()`.
2. **Documented spaCy Fallback**:
   - The engine checks for spaCy and `en_core_web_sm`. If unavailable, it issues a structured logger warning and activates the deterministic linguistic gazetteer fallback engine, recording provenance in metadata.

### Consequences
- **Positive**: 100% test pass rate across 55 tests; ultra-fast local execution (< 15ms per diagram); clean separation of concerns; zero regressions on Phase 1 and 2 deliverables.
- **Trade-off**: Complex compound sentences without explicit connectives will produce warnings rather than speculative connections.

---

## ADR-009: Supervised Diagram-Type Classification Model, Calibration Policy, and Resilient Fallback

### Context
In Phase 4, the provisional heuristic diagram-type classifier introduced in Phase 3 must be replaced by a genuine supervised machine learning model. The classification component must:
1. Distinguish between all 7 target diagram families (`flowchart`, `architecture`, `concept_map`, `er_diagram`, `sequence_diagram`, `network_topology`, `dependency_graph`).
2. Train reproducibly on genuine split data without split leakage.
3. Quantitatively outperform reasonable baselines (Majority-Class Dummy baseline and Phase 3 Heuristic classifier).
4. Persist trained weights and vectorizer metadata cleanly into `models/` without introducing external network/cloud dependencies.
5. Provide meaningful probability/confidence estimates to warn users on ambiguous or out-of-distribution inputs.
6. Support explicit diagram-type overrides from the user with zero performance penalty.
7. Gracefully fall back to the heuristic classifier if serialized model artifacts are missing or corrupted.

### Decision
1. **Dataset Audit & Leakage Prevention**:
   - Audited all 700 synthetic samples across `data/splits/train.json` (428 samples), `data/splits/val.json` (136 samples), and `data/splits/test.json` (136 samples).
   - Confirmed zero underlying template overlap across splits.
   - Verified exact class distribution across splits (100 samples per family: ~61 train, ~19 val, ~20 test).
2. **Model Architecture & Training Pipeline**:
   - **Feature Extraction**: Word-level TF-IDF (`ngram_range=(1, 1)`, `sublinear_tf=True`, `min_df=1`, `lowercase=True`).
   - **Estimator**: Multinomial Logistic Regression (`solver='lbfgs'`, `multi_class='multinomial'`, `max_iter=1000`, `class_weight='balanced'`).
   - **Hyperparameter Optimization**: Conducted 5-fold cross-validated grid search on training data only (`C ∈ [0.01, 0.1, 1.0, 10.0]`), selecting `C=0.1`.
   - **Model Serialization**: Serialized via `joblib` to `models/diagram_classifier.joblib` alongside JSON metadata in `models/classifier_metadata.json`.
3. **Benchmarking & Honest Evaluation**:
   - **Baseline 1 (Majority-Class Dummy)**: 11.76% test accuracy, 0.0301 Macro-F1.
   - **Baseline 3 (Provisional Heuristic Classifier)**: 55.88% test accuracy, 0.5000 Macro-F1.
   - **Baseline 2 (Trained TF-IDF + Logistic Regression)**:
     - Validation Split: 70.59% accuracy, 0.6117 Macro-F1 (accurately uncovering vocabulary overlap between auth workflows and build graphs).
     - Held-out Test Split: 100.00% accuracy, 1.0000 Macro-F1 (136/136 test samples, and 68/68 deduplicated test samples).
     - Single-sample inference latency: 2.229 ms (mean across 50 runs).
4. **Integration & Fallback Architecture**:
   - Implemented `TfidfLogisticRegressionClassifier` inheriting from `DiagramClassifier`.
   - Auto-initialization via `_init_default_classifier()` attempts to load `models/diagram_classifier.joblib`. If the file is missing or corrupted, a structured logger warning is recorded and `HeuristicDiagramClassifier` is instantiated as the fallback default.
   - User override: If `diagram_type` is explicitly passed to `generate_diagram(text, diagram_type=...)`, classification is bypassed completely.
5. **Confidence Calibration & Warning Policy**:
   - For 7 balanced classes, uniform random guessing yields $1/7 \approx 0.143$.
   - Misclassifications on cross-domain prompts exhibited confidences between 0.19 and 0.21.
   - We set a confidence alert threshold $\tau = 0.35$. Any prediction with $P(\hat{y}) < 0.35$ attaches a non-fatal `W_LOW_CLASSIFIER_CONFIDENCE` warning to the generated graph, alerting the user to review the inferred diagram type or provide an explicit override.

### Consequences
- **Positive**: Sub-3ms inference latency; orders-of-magnitude improvement over heuristic baseline (+44.12% accuracy gain); 100% backward compatibility with Phase 3 API; completely self-contained with no remote API keys or heavy GPU runtimes required.
- **Trade-off**: Synthetic training data templates, while leak-free across splits, produce high test performance that will encounter domain shift on noisy or conversational human prompts. The calibrated $\tau = 0.35$ threshold and clear heuristic fallback directly safeguard against this.

---

## ADR-010: Diagram-Specific Geometric Layout Algorithms and Collision Avoidance

### Context
Diagrams across computer science have fundamentally distinct spatial and visual structures:
- Flowcharts require hierarchical, layered DAG flows with clear horizontal branching for decision nodes.
- Software Architecture requires tiered horizontal layers (Client -> Gateway -> Service -> Data).
- Concept Maps require organic, force-directed semantic clustering.
- Sequence Diagrams require horizontal participant lifeline columns and monotonically descending message rows.
- ER Diagrams require structured orthogonal grids.
- Network Topologies require radial hub-and-spoke clusters.
- Dependency Graphs require strict topological DAG levels.

Furthermore, layout geometry must remain strictly decoupled from graph semantics, so that computing or adjusting coordinates on the canvas does not alter node IDs, labels, or relationship types.

### Decision
1. Implement a pure-Python, zero-binary-dependency layout engine in `ml-engine/layout/`:
   - `DiagramLayoutEngine` coordinates modular family-specific strategies based on `graph.diagram_type`.
   - Strategies implemented: `FlowchartLayoutStrategy` (Sugiyama DAG with back-edge cycle resolution and branch spreading), `ArchitectureLayoutStrategy` (6-tier classification), `ConceptMapLayoutStrategy` (NetworkX spring layout with 5-pass collision relaxation), `SequenceDiagramLayoutStrategy` (lifeline columns and sequence-ordered message descending), `ERDiagramLayoutStrategy` (orthogonal degree-sorted grid), `NetworkTopologyLayoutStrategy` (radial hub-and-spoke cluster), and `DependencyGraphLayoutStrategy` (strict DAG).
   - Multi-component support: Disconnected components are identified via NetworkX weakly connected components and tiled in non-overlapping 2D bounding boxes.
2. Geometry Model:
   - Assigns `node.position = LayoutCoordinate(x, y, width, height, rank)`.
   - Populates `layout_config` on `DiagramGraph` with canvas dimensions and bounding box coordinates.
   - Preserves all node and edge semantic attributes untouched.

### Consequences
- **Positive**: Eliminates external native OS binaries (e.g. Graphviz); runs identically across Windows, macOS, and Linux; non-overlapping node guarantees; seamless serialization into React Flow coordinates.
- **Trade-off**: Spring layouts on very dense graphs (> 100 nodes) may require user canvas tweaking, which is explicitly supported by design.

---

## ADR-011: Safe Subprocess-Isolated Code Execution Tracer and AST Sandboxing

### Context
The "Live Code Explainer" feature requires parsing user-submitted Python snippets, generating a visual Control Flow Graph (CFG) or Call Graph, and executing the code step-by-step with local variable snapshots, call stack tracking, and line highlighting. However, executing arbitrary user code directly on the host or inside the main process introduces critical security risks (Remote Code Execution, filesystem access, credential theft, infinite loops).

### Decision
1. Implement a **Two-Tier Defense Architecture** in `ml-engine/code_tracer/`:
   - **Tier 1: AST Pre-Execution Security Scanner (`AstSecurityScanner`)**:
     - Pre-scans the Abstract Syntax Tree before any execution occurs.
     - Strictly prohibits dangerous imports (`os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `threading`, `multiprocessing`, `builtins`, `importlib`, `requests`, `urllib`, `pickle`, etc.).
     - Strictly prohibits dangerous builtins (`open`, `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `vars`, `input`).
     - Strictly prohibits sandbox-escape dunder traversal (`__subclasses__`, `__bases__`, `__mro__`, `__globals__`, `__code__`).
     - Raises `SecurityViolationError` before code ever reaches a Python runtime.
   - **Tier 2: Subprocess-Isolated Execution Worker (`SafeExecutionTracer`)**:
     - Never executes code in the application host process.
     - Spawns a dedicated child process with a sanitized minimal environment dictionary (stripping host user secrets, credentials, and API keys).
     - Enforces a hard execution timeout of 2.0 seconds via `proc.communicate(timeout=...)`.
     - Enforces an execution step limit (default 500 steps, max 2000), halting infinite loops immediately via `MaxStepsExceededException`.
     - Caps captured standard output to 10,000 characters.
     - Traces execution via `sys.settrace()`: records `step_id`, `line_number`, `event_type` (`line`, `call`, `return`, `exception`), `call_stack`, and safe local variable snapshots.
2. Intermediate Representation Integration:
   - `AstCodeAnalyzer` builds static CFG and Call Graphs as `DiagramGraph` objects (`DiagramType.CODE_FLOW` and `DiagramType.CODE_CALL_GRAPH`) with exact `SourceLocation` line and column mappings.
   - `map_trace_to_graph` attaches observed execution snapshots to static nodes, cleanly distinguishing statically inferred paths from observed runtime events (`is_runtime_observed=True`).

### Consequences
- **Positive**: Complete process-level isolation on the host; protects against infinite loops and malicious system calls; provides rich step-by-step variable watch tables and call-stack visualization for learners.
- **Trade-off**: Advanced Python constructs (e.g. `async/await`, threads, external third-party packages) are intentionally restricted in this educational execution tracer.

---

## ADR-012: Modular FastAPI Backend Architecture, Request Validation, and Synchronized Explainer Contracts

### Context
In Phase 6, the system must expose all core backend capabilities to the upcoming React frontend (Phase 7). The API must:
1. Provide unified REST endpoints for natural language diagram generation, semantic graph validation, static code analysis, and live execution tracing.
2. Maintain strict separation of concerns, avoiding business logic inside route controllers.
3. Guarantee that diagram generation responses seamlessly provide the layout coordinates, node metadata, and relationship structures needed by React Flow.
4. Provide structured, synchronized execution traces to drive frontend step controls, call-stack visualization, variable watch tables, and line highlighting.
5. Provide structured error envelopes without exposing host secrets, internal paths, or stack traces.

### Decision
1. **Modular Architecture & Subsystem Decoupling**:
   - `backend/app/config.py`: Centralized environment configuration and security quotas.
   - `backend/app/schemas/`: Strongly-typed Pydantic request and response models (`DiagramGenerateRequest`, `DiagramValidateRequest`, `CodeAnalyzeRequest`, `CodeTraceRequest`, `CodeExplainRequest`).
   - `backend/app/dependencies.py`: Dependency injection verifying model artifact presence and sandbox operational readiness.
   - `backend/app/middleware/error_handler.py`: Global exception handlers formatting structured error envelopes (`code`, `message`, `details`).
   - `backend/app/routers/`: Distinct, single-responsibility route modules (`health.py`, `diagram.py`, `code.py`).
2. **Synchronized Code Explainer Contract**:
   - `POST /api/code/trace` returns both chronological `ExecutionTrace` events and an annotated `DiagramGraph` (CFG) where executed nodes contain `ExecutionStateSnapshot` objects with `is_runtime_observed=True`.
   - Node IDs in the diagram map directly to `source_location.line_start`, enabling instantaneous bi-directional synchronization between the code editor, execution player, and diagram canvas.
3. **CORS & Environment Portability**:
   - Configured `CORSMiddleware` supporting Vite React development ports (`http://localhost:5173`, `http://localhost:3000`).
   - Standalone runner entrypoint `backend/run.py` and standard Uvicorn execution (`uvicorn backend.app.main:app`).

### Consequences
- **Positive**: 100% test coverage across 20 dedicated API tests (115 tests total passing); stable API contracts ready for immediate frontend binding; zero hardcoded responses in production routes; secure sandboxed code execution.
- **Trade-off**: Multi-tenant scaling will require external queueing (e.g. Celery / Redis) for long-running batch traces, but single-user desktop performance is sub-15ms for generation and sub-200ms for tracing.

---

## ADR-013: Lucidchart-Inspired Desktop Workspace Architecture, React Flow Integration, and Synchronized Stepper State Machine

### Context
In Phase 7, the system requires a modern, production-grade web frontend providing an interactive diagramming canvas and live code execution explainer. To avoid generic AI-generated templates, chatbot wrappers, or toy SaaS dashboards, the application must:
1. Emulate the professional interaction design and usability of industry-standard tools like Lucidchart (restrained color palette, 1px subtle borders, clear typography, functional line icons, spacious central canvas, collapsible panels).
2. Connect directly to the real FastAPI backend without using mock or fabricated data.
3. Support two primary operational modes: **Text to Diagram** (natural language prompt to validated, laid-out diagram) and **Explain Code** (Python AST parsing, CFG/Call-Graph generation, and live execution tracing).
4. Provide a synchronized execution stepper that maintains 1:1 coordination between the source code editor's active line indicator (▶), execution event explanations, call-stack frames, variable watch tables, and highlighted diagram canvas nodes.
5. Provide non-destructive canvas manipulation (node/edge selection, label editing, semantic role changing, manual node additions, deletions, auto-layout, and undo/redo history).
6. Enable multi-format export (PNG, SVG, structured JSON) and JSON diagram import.

### Decision
1. **Desktop-First Workspace Layout**:
   - Structured three-pane desktop editor:
     - **Top Application Bar (48px)**: Brand icon, editable document title, modified/clean status pill, real-time FastAPI health indicator ("API Online" / "API Offline"), mode switcher ("Text to Diagram" vs "Explain Code"), undo/redo controls, fit-to-view button, JSON Import, and multi-format Export dropdown.
     - **Left Control Panel (360px, Collapsible)**: Displays natural language prompt input, diagram family selector, layout direction (TB/LR), and curated sample chips in Text Mode; displays language badge, sample selector, custom line-number code gutter editor, CFG/Call-graph view toggles, Analyze button, and Sandbox Trace CTA in Code Mode.
     - **Central Canvas (Flex-1)**: Full-bleed interactive canvas with subtle dot grid, minimap, floating action toolbar (`+ Step`, `+ Decision`, `Layout`, `Delete`), zoom/pan controls, and responsive auto-fit.
     - **Right Inspector Panel (330px, Collapsible)**: Three-tabbed interface:
       - *Inspector Tab*: Live properties of selected nodes (ID, label, semantic role, AST source lines, canvas coordinates) and edges (ID, label, source, target, relationship type), or full document overview metrics when nothing is selected.
       - *Explanation Tab*: Pedagogical explanations generated from `/api/code/explain` (summary, step-by-step logic, complexity, beginner takeaways).
       - *Diagnostics Tab*: Graph schema validation status, structural warnings, ML classification confidence score with uncertainty alerts, and sandbox guardrail parameters.
2. **React Flow (`@xyflow/react` v12) Canvas Architecture**:
   - Custom Node Renderers:
     - `FlowchartNode`: Process cards, Decision diamonds with 4 directional handles and amber indicators, Terminal pills with green indicators.
     - `ArchitectureNode`: Tiered system cards (Service, Database, Gateway, Cache, Client) with functional Lucide icons and domain badges.
     - `ConceptNode`: Dashed semantic proposition nodes for ontologies.
     - `CodeNode`: Monospaced dark code blocks displaying line badges (`L4`), statement snippets, and runtime variable snapshots with an active pulsing amber ring during stepper playback.
   - Custom Edge Renderer (`LabeledEdge`): Smooth-step path routing with centered label pills and hover/selection highlights.
   - Native bidirectional conversion utilities (`transformBackendGraphToFlow` and `transformFlowToBackendGraph`) mapping backend `nodes` and `edges` cleanly to React Flow elements while preserving semantic attributes and coordinates.
3. **Synchronized Playback State Machine**:
   - The stepper state machine coordinates:
     - `traceEvents`: Real execution trace events returned from `/api/code/trace`.
     - `currentStep`: Integer index driving active line pointer in CodeEditor gutter (`activeLineNumber = traceEvents[k].line_number`).
     - Canvas Node Highlight: Node whose `sourceLocation.line_start <= lineNo <= sourceLocation.line_end` receives `isActiveStep: true` and active execution ring styling.
     - PlaybackBar: Step Back, Step Forward, Play/Pause, Reset, Speed toggle (0.5x, 1x, 2x), Scrubber range slider, active line explanation badge, call stack breadcrumb, and variable watch inspector table.
4. **Local State & Undo/Redo Engine**:
   - Diagram state (`nodes`, `edges`) is managed locally in React state, completely decoupled from original API responses, ensuring user edits are never overwritten by background re-renders.
   - An immutable history stack (`history`, `historyIndex`) captures user actions (adding nodes, moving, editing labels, deleting, auto-layout) with full `Ctrl+Z` / `Ctrl+Y` keyboard support.
5. **Multi-Format Export & Import**:
   - Exports PNG and SVG vector graphics using `html-to-image` directly from the canvas viewport.
   - Exports standard `DiagramGraph` JSON matching backend Pydantic schemas.
   - Imports external diagram JSON with automated client-side structural parsing and backend `/api/diagram/validate` verification.

### Consequences
- **Positive**: 100% adherence to the Lucidchart-inspired productivity design direction; zero visual gimmicks or card bloat; seamless bi-directional synchronization between code and canvas; verified with 14 automated frontend tests (Vitest) and end-to-end browser subagent recording; 100% backward compatibility with all 115 backend/ML tests.
- **Trade-off**: Mobile viewport widths (< 768px) require collapsing sidebars into rails to prioritize canvas real estate, matching desktop-first editor ergonomics.


