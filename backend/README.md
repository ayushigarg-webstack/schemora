# Backend API Specification & Developer Guide

The **AI Diagram Generator & Live Code Explainer** backend is a production-grade, asynchronous REST API built with **FastAPI**, **Pydantic v2**, and **Uvicorn**. It exposes high-throughput endpoints for natural language diagram generation, semantic validation, AST program analysis, and sandboxed execution tracing.

---

## 1. Quickstart & Server Launch

### Prerequisites
- Python 3.10+ (tested on Python 3.14.3)
- Required packages: `fastapi`, `uvicorn`, `pydantic`, `networkx`, `scikit-learn`, `joblib`, `httpx`

### Launch Commands

To start the API server locally on `http://127.0.0.1:8000`:

```bash
# Direct runner entrypoint
python backend/run.py

# Or via Uvicorn CLI
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Interactive API Documentation
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 2. API Endpoint Catalog

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Subsystem diagnostics, uptime, and component statuses | `200 OK` |
| `GET` | `/api/diagram/types` | Lists supported diagram families and layout algorithms | `200 OK` |
| `POST` | `/api/diagram/generate` | Generates a laid-out `DiagramGraph` from natural language | `200 OK` / `400` / `422` |
| `POST` | `/api/diagram/validate` | Validates a diagram representation and computes graph metrics | `200 OK` / `422` |
| `GET` | `/api/code/languages` | Lists supported programming languages and sandbox status | `200 OK` |
| `POST` | `/api/code/analyze` | Generates CFG or Call Graph with exact line mappings | `200 OK` / `400` / `422` |
| `POST` | `/api/code/explain` | Returns pedagogical plain-English line/node explanation | `200 OK` / `400` |
| `POST` | `/api/code/trace` | Executes code in isolated sandbox and returns execution trace | `200 OK` / `400` |

---

## 3. Representative Request & Response Contracts

### A. Health Diagnostics (`GET /health`)
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 12.45,
  "components": {
    "nlp_pipeline": {
      "status": "available",
      "details": "8-step modular extraction pipeline operational",
      "operational": true
    },
    "classifier_model": {
      "status": "available",
      "details": "Active classifier: TfidfLogisticRegressionClassifier (artifact: diagram_classifier.joblib)",
      "operational": true
    },
    "layout_engine": {
      "status": "available",
      "details": "7 family strategies operational (NetworkX 3.7)",
      "operational": true
    },
    "code_tracer_sandbox": {
      "status": "available",
      "details": "Subprocess worker isolation & AST security scanner operational",
      "operational": true
    }
  }
}
```

### B. Natural Language to Diagram (`POST /api/diagram/generate`)
**Request:**
```json
{
  "text": "User submits login form. If credentials valid, issue JWT and redirect to dashboard; otherwise show error message.",
  "layout_direction": "TB"
}
```
**Response:**
```json
{
  "success": true,
  "diagram_type": "flowchart",
  "confidence": 0.88,
  "execution_time_ms": 14.32,
  "warnings": [],
  "diagram": {
    "id": "FLOW_0001",
    "diagram_type": "flowchart",
    "version": "2.0.0",
    "layout_config": {
      "strategy": "layered_sugiyama",
      "canvas_width": 800.0,
      "canvas_height": 620.0,
      "direction": "TB"
    },
    "nodes": [
      {
        "id": "n1",
        "label": "Start",
        "type": "terminal",
        "position": {"x": 320.0, "y": 60.0, "width": 160.0, "height": 60.0, "rank": 0}
      },
      {
        "id": "n2",
        "label": "User Submits Login Form",
        "type": "process",
        "position": {"x": 320.0, "y": 220.0, "width": 160.0, "height": 60.0, "rank": 1}
      },
      {
        "id": "n3",
        "label": "Credentials Valid?",
        "type": "decision",
        "position": {"x": 304.0, "y": 380.0, "width": 176.0, "height": 66.0, "rank": 2}
      }
    ],
    "edges": [
      {"id": "e1", "source": "n1", "target": "n2", "label": null, "edge_type": "flow", "directed": true},
      {"id": "e2", "source": "n2", "target": "n3", "label": null, "edge_type": "flow", "directed": true}
    ]
  }
}
```

### C. Live Code Static Analysis (`POST /api/code/analyze`)
**Request:**
```json
{
  "code": "x = 10\nif x > 5:\n    res = 'large'\nelse:\n    res = 'small'\n",
  "language": "python",
  "view_mode": "cfg"
}
```
**Response:**
```json
{
  "success": true,
  "language": "python",
  "view_mode": "cfg",
  "total_nodes": 6,
  "total_edges": 6,
  "warnings": [],
  "diagram": {
    "id": "cfg_1234",
    "diagram_type": "code_flow",
    "nodes": [
      {
        "id": "cfg_2",
        "label": "x = 10",
        "type": "statement",
        "source_location": {
          "line_start": 1,
          "line_end": 1,
          "col_start": 0,
          "code_snippet": "x = 10"
        },
        "position": {"x": 320.0, "y": 140.0, "width": 160.0, "height": 60.0, "rank": 1}
      }
    ]
  }
}
```

### D. Sandboxed Execution Tracing (`POST /api/code/trace`)
**Request:**
```json
{
  "code": "total = 0\nfor i in range(3):\n    total += i\n",
  "language": "python",
  "max_steps": 100,
  "timeout_seconds": 2.0
}
```
**Response:**
```json
{
  "success": true,
  "total_steps": 8,
  "terminated_normally": true,
  "termination_reason": "completed",
  "stdout": "",
  "trace": {
    "total_steps": 8,
    "terminated_normally": true,
    "events": [
      {
        "step_id": 0,
        "line_number": 1,
        "event_type": "line",
        "function_name": "main",
        "call_stack": ["main"],
        "variables": {"total": 0},
        "explanation": "Executing line 1 (active state: total=0)"
      },
      {
        "step_id": 1,
        "line_number": 2,
        "event_type": "line",
        "function_name": "main",
        "call_stack": ["main"],
        "variables": {"total": 0, "i": 0},
        "explanation": "Executing line 2 (active state: total=0, i=0)"
      }
    ]
  }
}
```

---

## 4. Security Sandboxing Architecture

1. **AST Pre-Execution Security Scanner (`AstSecurityScanner`)**:
   - Analyzes the abstract syntax tree before runtime execution.
   - Prohibits dangerous imports: `os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `threading`, `multiprocessing`, `builtins`, `importlib`, etc.
   - Prohibits restricted builtins: `open`, `eval`, `exec`, `compile`, `__import__`, `globals`, `locals`, `vars`, `input`.
   - Prohibits sandbox-escape dunder traversal: `__subclasses__`, `__bases__`, `__mro__`, `__globals__`, `__code__`, `__closure__`.
   - Returns a structured `400 Bad Request` with `SECURITY_VIOLATION` code if any violation is detected.

2. **Subprocess-Isolated Worker (`SafeExecutionTracer`)**:
   - Executes code in a dedicated child process with an isolated environment dictionary.
   - Enforces a 2.0-second execution timeout via process termination (`proc.kill()`).
   - Halts infinite loops cleanly at the step limit (default 500 steps) via `MaxStepsExceededException`.
   - Caps standard output at 10,000 characters.
