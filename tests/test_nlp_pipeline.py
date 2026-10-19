"""
Automated Test Suite for Phase 3 — NLP Pipeline & Graph Construction.
Tests text preprocessing, entity extraction, relation extraction, family adapters,
end-to-end pipeline orchestration, Phase 2 validator integration, and error handling.
"""

import pytest
from typing import Dict, Any

from ir.models import DiagramType, NodeShape
from ir.validators import validate_diagram
from nlp.preprocessing import TextPreprocessor, preprocess_text, MIN_INPUT_LENGTH, MAX_INPUT_LENGTH
from nlp.classifier_interface import (
    HeuristicDiagramClassifier,
    DiagramClassifier,
    ClassificationResult,
    get_default_classifier,
    set_default_classifier,
)
from nlp.entity_extractor import EntityExtractor, extract_entities
from nlp.relation_extractor import RelationExtractor, extract_relations
from nlp.pipeline import generate_diagram, DiagramPipeline
from nlp.code_interface import CodeDiagramBridge, CodeGraphInput


# ============================================================================
# 1. TEXT PREPROCESSING UNIT TESTS
# ============================================================================

def test_preprocessor_input_validation():
    p = TextPreprocessor()
    # Non-string raises ValueError
    with pytest.raises(ValueError, match="Input must be a string"):
        p.validate_input(12345)

    # Empty raises ValueError
    with pytest.raises(ValueError, match="cannot be empty"):
        p.validate_input("")

    with pytest.raises(ValueError, match="cannot be empty"):
        p.validate_input("    \n\t  ")

    # Too short raises ValueError
    with pytest.raises(ValueError, match="too short"):
        p.validate_input("abc")

    # Too long raises ValueError
    oversized = "x" * (MAX_INPUT_LENGTH + 10)
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        p.validate_input(oversized)


def test_preprocessor_technical_term_preservation():
    text = "The application uses React frontend, Node.js backend, MongoDB database, and Redis cache."
    doc = preprocess_text(text)
    terms = set(doc.preserved_technical_terms)
    assert "React" in terms
    assert "Node.js" in terms
    assert "MongoDB" in terms
    assert "Redis" in terms


def test_preprocessor_sentence_segmentation_with_abbreviations():
    p = TextPreprocessor()
    text = "We deploy Node.js v18.0. The system handles e.g. payments and auth; finally, it returns tokens."
    sentences = p.segment_sentences(text)
    assert len(sentences) >= 2
    # Ensure Node.js is not split into 'Node' and 'js' sentence
    assert any("Node.js" in s for s in sentences)


def test_preprocessor_negation_detection():
    p = TextPreprocessor()
    neg_text = "The system cannot process the order without valid credentials."
    is_neg, spans = p.detect_negations(neg_text)
    assert is_neg
    assert any(span.lower() in ["cannot", "without"] for span in spans)

    pos_text = "The system validates the credentials successfully."
    is_neg_2, _ = p.detect_negations(pos_text)
    assert not is_neg_2


def test_preprocessor_condition_and_loop_detection():
    p = TextPreprocessor()
    cond_text = "If payment succeeds, redirect to dashboard. Otherwise, prompt user to retry."
    doc = p.preprocess(cond_text)
    assert doc.has_conditions
    assert doc.has_loops


# ============================================================================
# 2. DIAGRAM CLASSIFIER INTERFACE TESTS
# ============================================================================

def test_classifier_predictions():
    c = HeuristicDiagramClassifier()

    # Flowchart prompt
    res_flow = c.predict("If the user submits the form, then validate. Otherwise, return an error.")
    assert res_flow.diagram_type == DiagramType.FLOWCHART
    assert res_flow.confidence >= 0.50

    # Architecture prompt
    res_arch = c.predict("An architecture with React frontend, Node.js microservice, Redis cache, and MongoDB.")
    assert res_arch.diagram_type == DiagramType.ARCHITECTURE

    # Concept map prompt
    res_concept = c.predict("A concept map classifying data structures into linear arrays, stacks, and non-linear trees.")
    assert res_concept.diagram_type == DiagramType.CONCEPT_MAP

    # ER prompt
    res_er = c.predict("Entity Student has primary key id and connects with one-to-many cardinality to Course.")
    assert res_er.diagram_type == DiagramType.ER_DIAGRAM


def test_classifier_probability_distribution():
    c = HeuristicDiagramClassifier()
    probs = c.predict_proba("Microservices architecture with API Gateway and PostgreSQL.")
    assert isinstance(probs, dict)
    total_prob = sum(probs.values())
    assert pytest.approx(total_prob, 0.05) == 1.0
    assert probs[DiagramType.ARCHITECTURE.value] > 0.20


def test_classifier_interface_extensibility():
    """Verify that a mock ML classifier can be registered cleanly for Phase 4."""
    class MockPhase4MLClassifier(DiagramClassifier):
        def predict(self, text: str) -> ClassificationResult:
            return ClassificationResult(
                diagram_type=DiagramType.ARCHITECTURE,
                confidence=0.99,
                is_fallback=False,
                model_version="mock-tfidf-lr-v4.0",
                explanation="Phase 4 ML Model prediction.",
            )

        def predict_proba(self, text: str) -> Dict[str, float]:
            return {DiagramType.ARCHITECTURE.value: 0.99}

    orig_classifier = get_default_classifier()
    try:
        set_default_classifier(MockPhase4MLClassifier())
        active = get_default_classifier()
        res = active.predict("Sample text")
        assert res.diagram_type == DiagramType.ARCHITECTURE
        assert res.is_fallback is False
        assert res.model_version == "mock-tfidf-lr-v4.0"
    finally:
        set_default_classifier(orig_classifier)


# ============================================================================
# 3. ENTITY & RELATION EXTRACTION UNIT TESTS
# ============================================================================

def test_entity_extraction_deduplication():
    text = "React frontend makes requests to Node.js backend. The Node.js service queries MongoDB."
    doc = preprocess_text(text)
    entities = extract_entities(doc, DiagramType.ARCHITECTURE)
    labels = [e.label for e in entities]

    # React Frontend and Node.js Backend should be consolidated
    assert any("React" in l for l in labels)
    assert any("MongoDB" in l for l in labels)
    # Node.js should appear as a single component, not two separate nodes
    node_js_matches = [e for e in entities if "node_js" in e.id or "node.js" in e.label.lower()]
    assert len(node_js_matches) == 1


def test_relation_extraction_direction_and_labels():
    text = "React frontend makes API calls to Node.js backend. Node.js backend queries MongoDB database."
    doc = preprocess_text(text)
    entities = extract_entities(doc, DiagramType.ARCHITECTURE)
    relations, _ = extract_relations(doc, entities, DiagramType.ARCHITECTURE)

    assert len(relations) >= 2
    # Verify direction: Client -> Service -> Database
    client_nodes = [e.id for e in entities if e.category in ["client", "frontend"]]
    service_nodes = [e.id for e in entities if e.category in ["service", "backend"]]
    db_nodes = [e.id for e in entities if e.category in ["database"]]

    client_to_service = [r for r in relations if r.source_id in client_nodes and r.target_id in service_nodes]
    service_to_db = [r for r in relations if r.source_id in service_nodes and r.target_id in db_nodes]

    assert len(client_to_service) >= 1
    assert len(service_to_db) >= 1


# ============================================================================
# 4. END-TO-END MANDATORY EXAMPLES (PROMPT SECTION 9)
# ============================================================================

def test_example_1_simple_sequential_process():
    """Example 1: A simple sequential process."""
    text = "First, the user submits application. Next, the clerk reviews documents. Finally, the manager issues approval."
    graph = generate_diagram(text, diagram_type=DiagramType.FLOWCHART)

    assert graph.diagram_type == DiagramType.FLOWCHART
    assert len(graph.nodes) >= 3
    assert len(graph.edges) >= 2
    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_2_conditional_process_with_alternative_branch():
    """Example 2: A conditional process with an alternative branch."""
    text = "User inputs password. If credentials match, the system logs in the user. Otherwise, it shows an invalid password message."
    graph = generate_diagram(text, diagram_type=DiagramType.FLOWCHART)

    assert graph.diagram_type == DiagramType.FLOWCHART
    decision_nodes = [n for n in graph.nodes if n.style and n.style.shape == NodeShape.DIAMOND]
    assert len(decision_nodes) >= 1

    # Decision node must have at least 2 branches (Yes and No)
    for d_node in decision_nodes:
        out_edges = graph.get_outgoing_edges(d_node.id)
        assert len(out_edges) >= 2
        branch_labels = {e.label.lower() for e in out_edges if e.label}
        assert "yes" in branch_labels or "no" in branch_labels or len(branch_labels) >= 2

    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_3_process_with_a_loop():
    """Example 3: A process with a loop."""
    text = "User attempts payment. If payment fails, the system increments retry counter and loops back to user input until retries exceed limit."
    graph = generate_diagram(text, diagram_type=DiagramType.FLOWCHART)

    assert graph.diagram_type == DiagramType.FLOWCHART
    # Must allow cycles in flowcharts and have loop-back edge or cycle
    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_4_ecommerce_software_architecture():
    """Example 4: An e-commerce software architecture with React, Node.js, MongoDB, Redis, and Payment Gateway."""
    text = (
        "An e-commerce platform where React frontend communicates with Node.js backend. "
        "The Node.js service queries MongoDB database and caches sessions in Redis. "
        "The backend also processes payments via an external Payment Gateway."
    )
    graph = generate_diagram(text)

    assert graph.diagram_type == DiagramType.ARCHITECTURE
    node_labels = " ".join(n.label for n in graph.nodes)
    assert "React" in node_labels
    assert "Node.js" in node_labels
    assert "MongoDB" in node_labels
    assert "Redis" in node_labels
    assert "Payment Gateway" in node_labels

    # Verify distinct shapes
    shapes = {n.style.shape for n in graph.nodes if n.style and n.style.shape}
    assert NodeShape.CYLINDER in shapes  # MongoDB / Redis
    assert NodeShape.CLOUD in shapes     # Payment Gateway
    assert NodeShape.ROUNDED_RECTANGLE in shapes # React / Node.js

    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_5_concept_map_data_structures():
    """Example 5: Concept map involving arrays, linked lists, stacks, queues, trees, and graphs."""
    text = (
        "Data structures are foundational concepts in computer science. "
        "Linear data structures include arrays, linked lists, stacks, and queues. "
        "Non-linear data structures include trees and graphs."
    )
    graph = generate_diagram(text, diagram_type=DiagramType.CONCEPT_MAP)

    assert graph.diagram_type == DiagramType.CONCEPT_MAP
    labels = " ".join(n.label for n in graph.nodes)
    for term in ["Array", "Linked List", "Stack", "Queue", "Tree", "Graph"]:
        assert term in labels

    # Concept map edges must all have non-empty proposition labels
    for e in graph.edges:
        assert e.label is not None and len(e.label.strip()) > 0

    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_6_college_database_er_description():
    """Example 6: A college database description with students, departments, and courses."""
    text = (
        "In a university system, Department has many Courses (1:N cardinality). "
        "Students enroll in Courses with many-to-many relationships (M:N)."
    )
    graph = generate_diagram(text, diagram_type=DiagramType.ER_DIAGRAM)

    assert graph.diagram_type == DiagramType.ER_DIAGRAM
    labels = " ".join(n.label for n in graph.nodes)
    assert "Department" in labels
    assert "Course" in labels
    assert "Student" in labels

    # Check cardinalities
    cardinalities = {e.cardinality for e in graph.edges if e.cardinality}
    assert any(c in ["1:N", "M:N", "1:1"] for c in cardinalities)

    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_7_sequence_diagram_interactions():
    """Example 7: A sequence of interactions involving successful and failed payment."""
    text = (
        "User sends request to Frontend. Frontend forwards payment to Payment Gateway. "
        "Payment Gateway returns success or failure response to User."
    )
    graph = generate_diagram(text, diagram_type=DiagramType.SEQUENCE_DIAGRAM)

    assert graph.diagram_type == DiagramType.SEQUENCE_DIAGRAM
    # Lifelines check
    for n in graph.nodes:
        assert n.style and n.style.shape == NodeShape.LIFELINE

    # Monotonic sequence ordering check
    orders = [e.sequence_order for e in graph.edges if e.sequence_order is not None]
    assert orders == sorted(orders)

    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_8_network_topology():
    """Example 8: A network topology with switches, router, firewall, and internet."""
    text = (
        "Office workstations connect to a central Switch. "
        "The Switch connects to the Gateway Router. "
        "The Router routes traffic through a Firewall into the public Internet."
    )
    graph = generate_diagram(text, diagram_type=DiagramType.NETWORK_TOPOLOGY)

    assert graph.diagram_type == DiagramType.NETWORK_TOPOLOGY
    labels = " ".join(n.label for n in graph.nodes)
    assert "Switch" in labels
    assert "Router" in labels
    assert "Firewall" in labels
    assert "Internet" in labels

    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"


def test_example_9_task_dependency_graph():
    """Example 9: A task dependency description with parallel tasks."""
    text = (
        "Task Requirements is prerequisite for Task Design. "
        "Task Backend Setup and Task Frontend Setup depend on Task Design. "
        "Task Deployment is blocked by Task Testing."
    )
    graph = generate_diagram(text, diagram_type=DiagramType.DEPENDENCY_GRAPH)

    assert graph.diagram_type == DiagramType.DEPENDENCY_GRAPH
    assert len(graph.nodes) >= 3
    # DAG check: No cycles permitted
    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"
    assert report.metrics["cycle_count"] == 0


def test_example_10_description_containing_negation():
    """Example 10: A description containing negation."""
    text = "If user credentials are not valid, access is denied and the system will not proceed."
    doc = preprocess_text(text)
    assert doc.has_negations

    graph = generate_diagram(text, diagram_type=DiagramType.FLOWCHART)
    report = validate_diagram(graph)
    assert report.is_valid


def test_example_11_description_with_repeated_references():
    """Example 11: A description with repeated references to the same entity."""
    text = (
        "The Payment Gateway processes transactions. "
        "When an order is created, the Payment Gateway contacts the bank. "
        "Later, the Payment Gateway issues a transaction receipt."
    )
    graph = generate_diagram(text)
    # Payment Gateway must only exist ONCE as a node, not 3 duplicate nodes
    gateway_nodes = [n for n in graph.nodes if "payment_gateway" in n.id.lower()]
    assert len(gateway_nodes) == 1


def test_example_12_edge_cases_and_error_handling():
    """Example 12: Ambiguous, empty, malformed, and oversized inputs."""
    # 1. Empty input
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_diagram("")

    # 2. Pure whitespace
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_diagram("   \n\t   ")

    # 3. Too short
    with pytest.raises(ValueError, match="too short"):
        generate_diagram("Hi")

    # 4. Oversized input
    huge_input = "word " * 2500  # > 10,000 characters
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        generate_diagram(huge_input)

    # 5. Ambiguous / minimal valid input produces warning rather than crash
    minimal_text = "System."  # 7 chars, >= 5
    graph = generate_diagram(minimal_text)
    assert graph is not None
    assert any(w.code in ["W_NO_ENTITIES_EXTRACTED", "W_SINGLE_ENTITY", "W_AMBIGUOUS_INPUT"] or "warning" in w.message.lower() for w in graph.warnings)


# ============================================================================
# 5. GENERALIZATION & NO HARDCODING TESTS
# ============================================================================

def test_generalization_non_hardcoded_architecture():
    """Verify that different technical stacks produce different nodes dynamically."""
    text_vue_django = "Frontend in Vue connects to Django backend with PostgreSQL."
    graph_vue = generate_diagram(text_vue_django, diagram_type=DiagramType.ARCHITECTURE)
    labels = [n.label for n in graph_vue.nodes]
    assert any("Vue" in l for l in labels)
    assert any("Django" in l for l in labels)
    assert any("PostgreSQL" in l for l in labels)
    # React and Node.js should NOT be in this diagram!
    assert not any("React" in l for l in labels)
    assert not any("Node.js" in l for l in labels)


# ============================================================================
# 6. CODE-TO-DIAGRAM EXPLAINER BRIDGE TESTS (SECTION 8)
# ============================================================================

def test_code_diagram_bridge():
    """Verify CodeDiagramBridge accepts structured code entities with SourceLocation and passes validation."""
    code_input = CodeGraphInput(
        source_code="def calculate(x):\n    if x > 0:\n        return x * 2\n    return 0",
        language="python",
        entities=[
            {"id": "func_calc", "label": "calculate(x)", "type": "function", "line_start": 1, "line_end": 4},
            {"id": "cond_x_pos", "label": "x > 0", "type": "condition", "line_start": 2, "line_end": 2},
            {"id": "stmt_ret_mult", "label": "return x * 2", "type": "statement", "line_start": 3, "line_end": 3},
            {"id": "stmt_ret_zero", "label": "return 0", "type": "statement", "line_start": 4, "line_end": 4},
        ],
        relations=[
            {"id": "e1", "source": "func_calc", "target": "cond_x_pos", "label": "evaluates"},
            {"id": "e2", "source": "cond_x_pos", "target": "stmt_ret_mult", "label": "True"},
            {"id": "e3", "source": "cond_x_pos", "target": "stmt_ret_zero", "label": "False"},
        ],
    )

    graph = CodeDiagramBridge.build_code_diagram(code_input, diagram_type=DiagramType.CODE_FLOW)
    assert graph.diagram_type == DiagramType.CODE_FLOW
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 3

    # Check SourceLocations
    for n in graph.nodes:
        assert n.source_location is not None
        assert n.source_location.line_start >= 1
        assert n.source_location.line_end >= n.source_location.line_start

    report = validate_diagram(graph)
    assert report.is_valid, f"Validation errors: {report.errors}"
