"""
Diagram generation, validation, and capability endpoints.
"""

import time
from typing import List
from fastapi import APIRouter, HTTPException, status

from ir.validators import validate_diagram
from graph.processor import GraphProcessor
from layout.engine import DiagramLayoutEngine
from layout.models import LayoutOptions
from nlp.pipeline import generate_diagram

from ..schemas.diagram import (
    DiagramTypeInfo,
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramValidateRequest,
    DiagramValidateResponse,
)

router = APIRouter(prefix="/api/diagram", tags=["Diagram Services"])

SUPPORTED_TYPES: List[DiagramTypeInfo] = [
    DiagramTypeInfo(
        type="flowchart",
        label="Flowchart",
        description="Procedural sequences, decision branches, loops, and terminal states.",
        layout_strategy="layered_sugiyama",
        example_prompt="User submits login form. If credentials valid, issue JWT and redirect to dashboard; otherwise show error.",
    ),
    DiagramTypeInfo(
        type="architecture",
        label="Software Architecture",
        description="Tiered multi-service systems, gateways, databases, caches, and queues.",
        layout_strategy="hierarchical_tiered",
        example_prompt="React frontend calls FastAPI gateway, which queries Order Service backed by Postgres and Redis cache.",
    ),
    DiagramTypeInfo(
        type="concept_map",
        label="Concept Map",
        description="Semantic ontologies, proposition networks, and academic knowledge graphs.",
        layout_strategy="force_directed",
        example_prompt="Machine Learning encompasses Supervised Learning and Unsupervised Learning. Neural Networks form the basis of Deep Learning.",
    ),
    DiagramTypeInfo(
        type="sequence_diagram",
        label="Sequence Diagram",
        description="Chronological message interchanges and lifelines between distributed participants.",
        layout_strategy="timeline_lifeline",
        example_prompt="Client sends login request to Auth Server. Auth Server validates credentials in User DB, then returns JWT to Client.",
    ),
    DiagramTypeInfo(
        type="er_diagram",
        label="Entity-Relationship (ER)",
        description="Database entities, primary/foreign keys, attributes, and 1:1, 1:N, M:N cardinalities.",
        layout_strategy="orthogonal_grid",
        example_prompt="Customer places Order with 1:N cardinality. Order contains OrderItem with 1:N cardinality. Product belongs to OrderItem.",
    ),
    DiagramTypeInfo(
        type="network_topology",
        label="Network Topology",
        description="Routers, switches, firewalls, subnets, and workstations.",
        layout_strategy="cluster_topology",
        example_prompt="Core Switch connects to Firewall, File Server, and two Workstations on the local subnet.",
    ),
    DiagramTypeInfo(
        type="dependency_graph",
        label="Dependency Graph",
        description="Directed Acyclic Graphs (DAGs) representing package dependencies and build steps.",
        layout_strategy="strict_dag",
        example_prompt="Build Step 1 compiles backend, Step 2 compiles frontend. Step 3 packages Docker image which depends on Step 1 and Step 2.",
    ),
]


@router.get("/types", response_model=List[DiagramTypeInfo])
def list_diagram_types() -> List[DiagramTypeInfo]:
    """
    Returns the list of officially supported diagram families with layout strategies
    and example prompts.
    """
    return SUPPORTED_TYPES


@router.post("/generate", response_model=DiagramGenerateResponse)
def generate_diagram_endpoint(request: DiagramGenerateRequest) -> DiagramGenerateResponse:
    """
    Generates a structured DiagramGraph intermediate representation from natural language.
    Executes text preprocessing, supervised ML diagram-type classification, entity/relation
    extraction, semantic graph validation, and geometric canvas layout.
    """
    start_time = time.perf_counter()

    # Step 1: Run complete NLP & ML extraction pipeline
    try:
        raw_graph = generate_diagram(
            text=request.text,
            diagram_type=request.diagram_type,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagram generation pipeline error: {str(e)}",
        )

    # Step 2: Apply diagram-specific geometric layout engine
    try:
        opts = LayoutOptions(direction=request.layout_direction or "TB")
        laid_out_graph = DiagramLayoutEngine.layout(raw_graph, options=opts)
    except Exception as e:
        # Fallback to raw graph if layout encounters an unexpected error
        laid_out_graph = raw_graph

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # Extract top classifier confidence if recorded
    conf = None
    for n in laid_out_graph.nodes:
        if n.confidence is not None:
            conf = max(conf or 0.0, n.confidence)

    return DiagramGenerateResponse(
        success=True,
        diagram=laid_out_graph,
        diagram_type=laid_out_graph.diagram_type.value,
        confidence=conf,
        warnings=laid_out_graph.warnings,
        execution_time_ms=round(elapsed_ms, 2),
    )


@router.post("/validate", response_model=DiagramValidateResponse)
def validate_diagram_endpoint(request: DiagramValidateRequest) -> DiagramValidateResponse:
    """
    Validates a submitted DiagramGraph against universal structural rules and
    family-specific semantic constraints.
    Returns status, validation errors, warnings, and topological metrics.
    """
    report = validate_diagram(request.diagram)
    analysis = GraphProcessor.analyze(request.diagram)

    return DiagramValidateResponse(
        is_valid=report.is_valid,
        diagram_type=request.diagram.diagram_type.value,
        errors=report.errors,
        warnings=report.warnings,
        metrics=analysis.metrics,
    )
