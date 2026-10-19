"""
Compatibility module forwarding imports to nlp package.
"""

from nlp import (
    generate_diagram,
    TextPreprocessor,
    PreprocessedDocument,
    preprocess_text,
    EntityExtractor,
    extract_entities,
    RelationExtractor,
    extract_relations,
    GraphBuilder,
    build_raw_graph,
    get_adapter_for_type,
    CodeDiagramBridge,
    CodeGraphInput,
)

__all__ = [
    "generate_diagram",
    "TextPreprocessor",
    "PreprocessedDocument",
    "preprocess_text",
    "EntityExtractor",
    "extract_entities",
    "RelationExtractor",
    "extract_relations",
    "GraphBuilder",
    "build_raw_graph",
    "get_adapter_for_type",
    "CodeDiagramBridge",
    "CodeGraphInput",
]
