# Phase 1 Research Report: NLP, Graph Generation, Program Analysis, and Dataset Engineering

**Author**: Senior ML Engineer & Software Architect  
**Project**: AI Diagram Generator from Text & Live Code Explainer  
**Date**: October 2026  
**Status**: Completed  

---

## 1. Executive Summary

This report establishes the theoretical, empirical, and architectural foundations for:
1. Transforming natural language descriptions into 7 distinct diagram families using a modular NLP/ML pipeline.
2. Analyzing source code to generate interactive control flow, call graphs, and sandboxed step-by-step execution traces.
3. Establishing a reproducible, leak-free dataset generation and validation protocol.

Rather than relying on closed-source LLMs or brittle regex patterns, we adopt a hybrid architecture:
- **Linguistic Semantic Parsing & Machine Learning**: Supervised text classification (TF-IDF + Logistic Regression) paired with spaCy dependency tree parsing and domain-specific technical gazetteers.
- **Formal Graph Intermediate Representation (IR)**: A polymorphic, strongly validated schema representing nodes, edges, attributes, and layout metadata.
- **Static & Dynamic Program Analysis**: Python Abstract Syntax Tree (AST) decomposition, Control Flow Graph (CFG) basic-block synthesis, call graph hierarchy generation, and sandboxed `sys.settrace()` execution monitoring.

---

## 2. Literature Review: Natural Language to Diagram & Graph Generation

### 2.1 Text-to-Graph & Semantic Parsing
Transforming unstructured text into graph representations is a foundational challenge in NLP:
- **Abstract Meaning Representation (AMR)** (Banarescu et al., 2013): Represents sentence semantics as rooted, directed, edge-labeled graphs. While powerful for linguistic semantics, AMR graphs lack domain-specific diagram structures (e.g., distinguishing a cloud microservice from a cache, or a database primary key from a foreign key).
- **Subject-Verb-Object (SVO) Extraction & Dependency Parsing** (de Marneffe et al., 2006, 2014): Dependency grammar maps syntactic relations between words (e.g. `nsubj`, `dobj`, `prep`, `pobj`). For technical descriptions such as *"The frontend calls the Node.js API which reads from PostgreSQL"*, the dependency parse directly yields the semantic chain:
  `[frontend] --(calls)--> [Node.js API] --(reads from)--> [PostgreSQL]`.
- **Domain Terminology Recognition**: Technical diagrams feature composite names (e.g. `API Gateway`, `Payment Service`, `Redis Cache`, `Load Balancer`). We utilize phrase matching and technical gazetteers to ensure multi-token entities are preserved as single discrete nodes rather than being fragmented.

### 2.2 Diagram-Type Classification
Users input prompts without necessarily specifying whether they need a flowchart, software architecture diagram, or ER diagram.
- **Baseline**: A dummy majority-class classifier provides the empirical baseline.
- **Supervised Model**: A TF-IDF vectorizer (extracting word unigrams and bigrams with sublinear term-frequency scaling) paired with Multinomial Logistic Regression.
- **Feature Evidence**: Distinct vocabulary separates diagram families:
  - Flowcharts: *"if"*, *"then"*, *"otherwise"*, *"starts"*, *"ends"*, *"step"*, *"decision"*, *"loops back"*.
  - Software Architecture: *"microservice"*, *"API"*, *"database"*, *"cache"*, *"frontend"*, *"backend"*, *"gateway"*, *"Kubernetes"*.
  - Concept Maps: *"is a"*, *"type of"*, *"consists of"*, *"classified as"*, *"hierarchical"*, *"relates to"*.
  - ER Diagrams: *"entity"*, *"attribute"*, *"primary key"*, *"one-to-many"*, *"foreign key"*, *"cardinality"*.
  - Sequence Diagrams: *"sends request"*, *"responds"*, *"acknowledges"*, *"calls"*, *"returns token"*, *"lifeline"*.
  - Network Topology: *"switch"*, *"router"*, *"firewall"*, *"subnet"*, *"VLAN"*, *"workstation"*, *"LAN"*.
  - Dependency Graphs: *"depends on"*, *"prerequisite"*, *"blocked by"*, *"build step"*, *"milestone"*, *"parallel tasks"*.

### 2.3 Graph Layout Algorithms
A diagram is unreadable without appropriate geometric placement. Graph layout algorithms must reflect domain semantics:
- **Sugiyama Hierarchical DAG Layout** (Sugiyama et al., 1981): Optimal for **Flowcharts**, **Software Architectures**, and **Dependency Graphs**. Vertices are partitioned into discrete horizontal or vertical ranks based on topological ordering, minimizing edge crossings.
- **Force-Directed (Fruchterman-Reingold)** (Fruchterman & Reingold, 1991): Optimal for **Concept Maps** and **Network Topologies**. Simulates mechanical spring tension between connected nodes and electrostatic repulsion between all pairs, clustering tightly coupled concepts.
- **Lifeline Timeline Layout**: Specialized layout for **Sequence Diagrams**. Participants occupy distinct X-axis columns; chronological messages flow downwards along monotonically increasing Y offsets.

---

## 3. Literature Review: Code Analysis & Live Explainer

### 3.1 Static Program Analysis via Abstract Syntax Trees
- Python's standard `ast` module compiles source strings into an AST tree conforming to Python grammar specifications.
- **Control Flow Graph (CFG) Construction**:
  - Statements are grouped into **Basic Blocks** (linear sequences of instructions with single entry and exit points).
  - Branching constructs (`If`, `While`, `For`, `Try`) introduce conditional edges (`TrueBranch`, `FalseBranch`, `LoopBack`).
- **Call Graph Extraction**:
  - Traverses `FunctionDef`, `AsyncFunctionDef`, and `Call` nodes.
  - Resolves callers and callees, enabling interactive call-stack inspection.
- **Bidirectional Source Mapping**:
  - Python AST nodes store `lineno`, `col_offset`, `end_lineno`, and `end_col_offset`.
  - Storing these coordinates in our `DiagramNode.source_location` enables instantaneous bidirectional synchronization between the code editor and diagram canvas.

### 3.2 Dynamic Execution Tracing & Sandboxing
- **Tracing Engine**: Using `sys.settrace()`, we intercept execution hooks (`call`, `line`, `return`, `exception`). At each line event, a snapshot of local variable bindings (`frame.f_locals`) and the active call stack is captured.
- **Security Sandboxing**:
  Executing arbitrary code can lead to remote code execution (RCE) or denial of service (DoS). We enforce three layers of protection:
  1. **Static AST Pre-Filter**: Scans AST before execution. Blocks dangerous imports (`os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `threading`, `multiprocessing`) and banned functions (`exec`, `eval`, `compile`, `open`, `__import__`).
  2. **Execution Timeout**: Enforces a strict 2.0-second timeout via worker process termination, preventing infinite loops (`while True: pass`).
  3. **Step & Memory Bounds**: Caps total execution trace to 500 steps and truncates large data structures to prevent memory exhaustion.

---

## 4. Evaluation of Dataset Candidates

| Candidate Dataset | Source & License | Primary Format | Coverage | Usability Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **DiagramGenBenchmark** (`OpenRaiser/DiagramGen`) | arXiv 2024 / Hugging Face; CC-BY-4.0 | Natural text -> LaTeX/TikZ code & raster images | Flowcharts, model architectures, statistical charts | Incompatible target format (monolithic TikZ strings, not an IR); 30%+ statistical charts; requires heavy TeX distribution. |
| **FlowGen** | ICLR 2024/2025 (`nju-websoft/FlowGen`); MIT | Procedural graph synthesizer | Flowcharts only | Confirms the superiority of programmatic graph synthesis, but strictly limited to flowcharts. |
| **WebNLG** | ACL / CC-BY-4.0 | Text -> RDF Triples | General knowledge entities and relations | Valuable reference for concept maps, but lacks diagram layout coordinates, decision branches, and architecture tiers. |
| **CoNLL-04** | Academic / Public | Sentence -> SVO relations | General news entities | Informative for relation extraction metrics, but lacks technical/software domain vocabulary. |
| **Curated Multi-Family Dataset (Proposed)** | Custom Open Dataset; MIT License | Natural text -> Pydantic `DiagramGraph` IR | All 7 target diagram families | **Selected primary data strategy**: Exactly matches project IR, eliminates external parser errors, provides leak-free template-grouped splits. |

---

## 5. Dataset Engineering & Leak-Free Splitting Strategy

### 5.1 Dataset Schema Design
The schema is formalized in `data/schema/diagram_schema.json`:
- **Diagram Sample**:
  - `id`: Unique stable identifier (e.g. `ARCH_0001`, `FLOW_0012`).
  - `text`: Natural language description.
  - `diagram_type`: One of 7 supported families.
  - `nodes`: Array of `DiagramNode` (`id`, `label`, `type`, `attributes`, `source_location`).
  - `edges`: Array of `DiagramEdge` (`id`, `source`, `target`, `label`, `edge_type`, `directed`, `metadata`).
  - `metadata`: `domain`, `template_id`, `complexity`, `provenance`.

### 5.2 Leak-Free Splitting Protocol
When generating parameterized data, sharing templates or structural graphs across splits causes **data leakage**, resulting in artificially inflated test accuracy.
To guarantee rigorous generalization:
1. Every example belongs to an explicit `template_id` (e.g., `arch_ecommerce_microservices`, `flow_user_login_retry`).
2. Splitting is performed at the **template level**:
   - **70% of templates -> Train Split**
   - **15% of templates -> Validation Split**
   - **15% of templates -> Held-out Test Split**
3. No template present in the Test split appears in the Train or Validation splits. The model must generalize to unseen phrasing, distinct entity names, and novel structural graphs.

---

## 6. Next Steps for Phase 2

With Phase 1 research completed, dataset schemas validated, generation scripts implemented, and benchmark code samples curated:
- **Phase 2** will implement the Generalized Intermediate Representation in Python with Pydantic v2 schemas and diagram-specific semantic validators.
