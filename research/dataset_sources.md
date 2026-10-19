# Dataset Sources, Literature Review, & Data Strategy

This document provides a verified, evidence-grounded review of existing academic datasets, frameworks, and benchmarks for text-to-diagram and text-to-graph tasks, followed by our data engineering strategy.

---

## 1. Investigation & Verification of Existing Datasets

We evaluated candidate datasets and literature identified in the research literature and prompt guidelines:

### 1.1 DiagramGenBenchmark (`OpenRaiser/DiagramGen` / `DiagramAgent`)
- **Verified Source & Citations**:
  - Paper: *"From Words to Structured Visuals: A Benchmark and Framework for Text-to-Diagram Generation and Editing"*, Zhang et al., September 2024 (arXiv:2409.04358).
  - Repositories: Hugging Face dataset `OpenRaiser/DiagramGen`, `DiagramAgent/DiagramGenBenchmark`.
- **Actual Format & Contents**:
  - Instruction-following dataset mapping natural language commands into compilable diagram code in **LaTeX/TikZ** and **Graphviz DOT**.
  - Contains paired high-resolution raster images (PNG/PDF) rendered from TikZ/DOT.
  - Covers 8 diagram/chart types: flowcharts, model architectures, mind maps, directed graphs, undirected graphs, line charts, bar charts, and statistical tables.
- **Licensing & Accessibility**:
  - Published on Hugging Face under Creative Commons Attribution 4.0 International (CC-BY-4.0) and Apache 2.0 license. Publicly accessible.
- **Suitability for This Project**:
  - **Strengths**: Demonstrates the real-world utility of multi-type diagram generation from text; confirms the necessity of separating diagram families.
  - **Limitations & Impediments**:
    1. The target representation is **monolithic code strings** (TikZ/DOT syntax), not an abstract, validated Intermediate Representation (IR). Parsing TikZ code back into a semantic graph requires complex LaTeX AST parsers with high error rates.
    2. Over 30% of the dataset consists of statistical charts (line charts, bar charts, data tables), which belong to chart generation libraries (e.g. Chart.js, Recharts) rather than structural relational diagrams (flowcharts, software architecture, ERDs, sequence diagrams).
    3. TikZ compilation requires an installed TeX Live / MiKTeX distribution (~4 GB), which violates our requirement for a lightweight, self-contained local installation.

---

### 1.2 FlowGen Controllable Flowchart Synthesizer
- **Verified Source & Citations**:
  - Paper: *"FlowGen: Synthesizing Diverse Flowcharts to Enhance and Benchmark MLLM Reasoning"*, Nanjing University Websoft Group, ICLR 2024 / 2025.
  - Repository: GitHub `nju-websoft/FlowGen`.
- **Actual Format & Contents**:
  - Controllable procedural synthesizer that programmatically generates flowchart graphs with varying topological parameters (number of nodes, branching factor, cycle frequency, nested subgraphs).
  - Emits flowchart graphs paired with synthesized textual descriptions and multi-engine visual renderings.
- **Licensing & Accessibility**:
  - Academic research release (MIT / Apache 2.0 open-source code).
- **Suitability for This Project**:
  - **Strengths**: Validates our core thesis that **controlled synthetic data generation with strict structural schemas is the gold standard** for training and evaluating graph-generation models where public natural human-labeled data is sparse.
  - **Limitations**: Restricted strictly to flowcharts. Does not address multi-tiered cloud architectures (services, databases, caches), entity-relationship models, sequence participant timelines, network topologies, or AST code graphs.

---

### 1.3 Semantic Triple & Relation Extraction Benchmarks (WebNLG & CoNLL-04)
- **WebNLG Challenge**:
  - Sources: Gardent et al. (ACL 2017), Castro Ferreira et al. (INLG 2020), Hugging Face `web_nlg`.
  - Format: RDF triples `(Subject, Predicate, Object)` mapped to crowdsourced English sentences.
  - License: CC-BY-4.0.
  - Evaluation: Excellent reference for entity and relationship extraction for concept maps and knowledge graphs. However, RDF triples are flat semantic associations; they lack diagram layout properties, decision branch labels ("Yes"/"No"), database key attributes, and sequence ordering.
- **CoNLL-04**:
  - Sources: Roth & Yih (2004), Carreras & Màrquez (2004).
  - Format: Token-level NER tags and sentence-level relation pairs (`Work_For`, `Kill`, `OrgBased_In`, `Live_In`, `Located_In`).
  - License: Public research benchmark.
  - Evaluation: Standard for NLP relation extraction evaluation, but the domain is general news/biographical text, not technical system architectures or software diagrams.

---

### 1.4 Code-to-Diagram & Program Analysis Literature
- **Program Dependency & Control Flow**:
  - Foundational work: Cytron et al. (1991) on Static Single Assignment (SSA) and Control Flow Graphs (CFGs); Allen & Cocke (1970) on graph-theoretic flow analysis.
  - Python Standard Library: `ast` (PEP 339) provides a deterministic, standard-compliant Abstract Syntax Tree parser across Python versions.
  - Call Graph Generation: Salis et al. (ICSE 2021) on static call graphs for Python (`PyCG`).
- **Dynamic Tracing**:
  - Python's standard `sys.settrace()` API provides deterministic step-by-step hook points for `call`, `line`, `return`, and `exception` events.
  - Execution Sandboxing: Security standards require restricting unsafe builtins and setting strict execution time limits (e.g. 2.0 seconds) to avoid CPU denial-of-service via infinite loops.

---

## 2. Dataset Strategy Selection

Based on the verified findings, relying solely on external public datasets is **insufficient and technically flawed** because:
1. No single public dataset provides structured graph annotations across flowcharts, software architecture, concept maps, ER diagrams, sequence diagrams, network topologies, and dependency graphs.
2. Available benchmarks (like `OpenRaiser/DiagramGen`) produce raw TikZ/DOT code strings rather than a validated Intermediate Representation.
3. Combining disparate datasets would introduce domain imbalance and incompatible annotation schemas.

### The Two-Pronged Data Strategy

```
+--------------------------------------------------------------------------------------------------+
|                                    PROJECT DATA ENGINE                                           |
|                                                                                                  |
|  +------------------------------------------------------+  +----------------------------------+  |
|  | Sub-Dataset A: Natural Language to Diagram           |  | Sub-Dataset B: Code-to-Diagram   |  |
|  | - 7 Supported Diagram Families                       |  | - Python & JS/TS Idiomatic Code  |  |
|  | - Ground-Truth Intermediate Representation (IR)      |  | - AST & CFG Ground Truth         |  |
|  | - Template-Isolated Splits (Train 70%, Val 15%,      |  | - Call Hierarchies & Data Flow   |  |
|  |   Test 15%) with zero structural leakage             |  | - Traced Execution Snapshots     |  |
|  | - Natural Phrasing Variations & Domain Gazetteers    |  | - Sandbox Security Test Suite    |  |
|  +------------------------------------------------------+  +----------------------------------+  |
+--------------------------------------------------------------------------------------------------+
```

1. **Sub-Dataset A (Natural Language to Diagram)**:
   - Generated via a deterministic, parameterized generator (`scripts/generate_dataset.py`) using fixed random seed (`seed=42`).
   - Grounded in realistic software engineering, database, and computer science educational scenarios.
   - Every sample produces:
     - `id`: Stable identifier (e.g., `ARCH_0023`, `FLOW_0045`).
     - `text`: Natural-language prompt with technical terminology and sentence structure variations.
     - `diagram_type`: Label from the 7 supported families.
     - `nodes`: List of typed nodes with labels and domain attributes.
     - `edges`: List of typed, directed/undirected edges with relationship labels.
     - `metadata`: Domain, template group ID, complexity (`simple`, `medium`, `complex`), provenance.
   - **Leakage Prevention**: Samples are partitioned at the **template level**. All paraphrases or instances sharing an underlying structural template are strictly assigned to either Train, Val, or Test. The Test set contains unseen phrasing patterns and entities.

2. **Sub-Dataset B (Code-to-Diagram Explainer Benchmark)**:
   - Kept in a dedicated directory `data/code_samples/`.
   - Never mixed with text-to-diagram classification data.
   - Covers 7 programming patterns:
     1. Conditionals (`if`/`elif`/`else`)
     2. Loops (`while`, `for`, nested)
     3. Recursion (factorial, fibonacci, binary search)
     4. Sorting & array manipulation
     5. Data structure pointer manipulation (linked list, stack)
     6. Object-oriented programming (classes, inheritance, polymorphism)
     7. Sandbox security tests (infinite loops, banned OS/subprocess calls)

---

## 3. Data Schema Specifications

The intermediate representation schema is formally defined as JSON Schema in `data/schema/diagram_schema.json` and validated through Pydantic models.

### Node Types by Diagram Family
- **Flowchart**: `terminal`, `process`, `decision`, `io`, `subprocess`.
- **Software Architecture**: `client`, `service`, `database`, `cache`, `message_broker`, `api_gateway`, `external_system`.
- **Concept Map**: `concept`, `category`, `subtopic`, `property`.
- **ER Diagram**: `entity`, `weak_entity`, `attribute`, `key_attribute`, `multivalued_attribute`.
- **Sequence Diagram**: `actor`, `participant`, `boundary`, `database`.
- **Network Topology**: `workstation`, `switch`, `router`, `firewall`, `server`, `internet`.
- **Dependency Graph**: `task`, `milestone`, `deliverable`, `module`.

### Edge Types by Diagram Family
- **Flowchart**: `flow`, `branch_yes`, `branch_no`, `loop_back`.
- **Software Architecture**: `http_request`, `rpc_call`, `db_read_write`, `cache_lookup`, `pub_sub`.
- **Concept Map**: `is_a`, `part_of`, `relates_to`, `leads_to`, `implements`, `requires`.
- **ER Diagram**: `one_to_one`, `one_to_many`, `many_to_many`, `has_attribute`.
- **Sequence Diagram**: `sync_call`, `async_message`, `return_value`, `create_instance`.
- **Network Topology**: `ethernet`, `fiber`, `wireless`, `vpn_tunnel`, `wan_link`.
- **Dependency Graph**: `depends_on`, `blocks`, `produces`, `triggers`.

---

## 4. Reproducibility & Integrity Standards

- **Deterministic Seeds**: All generation and splitting scripts default to `seed=42`.
- **No Hallucinated Data**: Synthetic data is explicitly labeled with `provenance: "synthetic_controlled_template"`; it is never represented as human user data.
- **Executable Validation**: All generated JSON data is strictly validated against the JSON schema before persistence. Invalid samples cause generation failure.
