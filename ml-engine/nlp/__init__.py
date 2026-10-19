"""
Natural Language Processing (NLP) & Graph Construction Engine.
Transforms unstructured text into validated Diagram Intermediate Representation (IR) graphs.
"""

from .pipeline import generate_diagram
from .preprocessing import (
    TextPreprocessor,
    PreprocessedDocument,
    PreprocessedSentence,
    preprocess_text,
)
from .classifier_interface import (
    DiagramClassifier,
    ClassificationResult,
    HeuristicDiagramClassifier,
    get_default_classifier,
    set_default_classifier,
)
from .entity_extractor import (
    EntityExtractor,
    ExtractedEntity,
    extract_entities,
)
from .relation_extractor import (
    RelationExtractor,
    ExtractedRelation,
    extract_relations,
)
from .graph_builder import (
    GraphBuilder,
    build_raw_graph,
)
from .adapters import (
    BaseDiagramAdapter,
    FlowchartAdapter,
    ArchitectureAdapter,
    ConceptMapAdapter,
    ERDiagramAdapter,
    SequenceDiagramAdapter,
    NetworkTopologyAdapter,
    DependencyGraphAdapter,
    get_adapter_for_type,
)
from .code_interface import (
    CodeDiagramBridge,
    CodeGraphInput,
)

__all__ = [
    "generate_diagram",
    "TextPreprocessor",
    "PreprocessedDocument",
    "PreprocessedSentence",
    "preprocess_text",
    "DiagramClassifier",
    "ClassificationResult",
    "HeuristicDiagramClassifier",
    "get_default_classifier",
    "set_default_classifier",
    "EntityExtractor",
    "ExtractedEntity",
    "extract_entities",
    "RelationExtractor",
    "ExtractedRelation",
    "extract_relations",
    "GraphBuilder",
    "build_raw_graph",
    "BaseDiagramAdapter",
    "FlowchartAdapter",
    "ArchitectureAdapter",
    "ConceptMapAdapter",
    "ERDiagramAdapter",
    "SequenceDiagramAdapter",
    "NetworkTopologyAdapter",
    "DependencyGraphAdapter",
    "get_adapter_for_type",
    "CodeDiagramBridge",
    "CodeGraphInput",
]
