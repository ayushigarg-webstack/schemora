"""
NLP Pipeline & Diagram Orchestrator.
Coordinates text preprocessing, diagram-type classification, entity extraction,
relation extraction, family-specific adapter transformations, and Phase 2 IR validation.
"""

from typing import Optional, Union, Dict, Any
from datetime import datetime, timezone
import logging

from ir.models import (
    DiagramGraph,
    DiagramType,
    ValidationWarning,
    DiagramMetadata,
)
from ir.validators import validate_diagram

from .preprocessing import TextPreprocessor, PreprocessedDocument
from .classifier_interface import get_default_classifier, ClassificationResult
from .entity_extractor import EntityExtractor, SPACY_AVAILABLE
from .relation_extractor import RelationExtractor
from .graph_builder import GraphBuilder
from .adapters import get_adapter_for_type

logger = logging.getLogger(__name__)


class DiagramPipeline:
    """
    End-to-end Diagram Generation Pipeline.
    Callable locally without external servers, frontends, or internet access.
    """

    def __init__(
        self,
        preprocessor: Optional[TextPreprocessor] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        relation_extractor: Optional[RelationExtractor] = None,
        graph_builder: Optional[GraphBuilder] = None,
    ):
        self.preprocessor = preprocessor or TextPreprocessor()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.relation_extractor = relation_extractor or RelationExtractor()
        self.graph_builder = graph_builder or GraphBuilder()

    def generate(
        self,
        text: str,
        diagram_type: Optional[Union[str, DiagramType]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> DiagramGraph:
        """
        Executes the 8-step diagram generation pipeline.
        
        Args:
            text: Unstructured natural language description.
            diagram_type: Optional explicit diagram family override.
            config: Optional runtime configuration dictionary.
            
        Returns:
            DiagramGraph: Strongly validated intermediate representation.
        """
        cfg = config or {}

        # ------------------------------------------------------------------
        # Step 1 & 2: Input Validation & Text Preprocessing
        # ------------------------------------------------------------------
        doc: PreprocessedDocument = self.preprocessor.preprocess(text)

        # ------------------------------------------------------------------
        # Step 3: Determine Diagram Type
        # ------------------------------------------------------------------
        classification_res: Optional[ClassificationResult] = None
        target_type: DiagramType

        if diagram_type is not None:
            # User explicit override
            if isinstance(diagram_type, DiagramType):
                target_type = diagram_type
            elif isinstance(diagram_type, str):
                target_type = DiagramType(diagram_type.strip().lower())
            else:
                raise ValueError(f"Invalid diagram_type: {type(diagram_type)}")
            classifier_confidence = 1.0
            classifier_model = "user_override"
        else:
            # Query classifier interface (Phase 3 heuristic, Phase 4 ML)
            classifier = get_default_classifier()
            classification_res = classifier.predict(doc.normalized_text)
            target_type = classification_res.diagram_type
            classifier_confidence = classification_res.confidence
            classifier_model = classification_res.model_version

        # ------------------------------------------------------------------
        # Step 4: Extract Entities & Concepts
        # ------------------------------------------------------------------
        entities = self.entity_extractor.extract(doc, diagram_type=target_type)

        pipeline_warnings: List[ValidationWarning] = []

        if len(entities) == 0:
            pipeline_warnings.append(
                ValidationWarning(
                    code="W_NO_ENTITIES_EXTRACTED",
                    message="No domain entities or components could be extracted from the text.",
                    level="warning",
                )
            )
        elif len(entities) == 1:
            pipeline_warnings.append(
                ValidationWarning(
                    code="W_SINGLE_ENTITY",
                    message=f"Only a single entity '{entities[0].label}' was extracted. Relationships could not be established.",
                    level="info",
                    element_id=entities[0].id,
                )
            )

        # ------------------------------------------------------------------
        # Step 5: Extract Relationships
        # ------------------------------------------------------------------
        relations, rel_warnings = self.relation_extractor.extract(
            doc=doc,
            entities=entities,
            diagram_type=target_type
        )
        for rw in rel_warnings:
            pipeline_warnings.append(
                ValidationWarning(
                    code="W_RELATION_EXTRACTION",
                    message=rw,
                    level="info",
                )
            )

        # ------------------------------------------------------------------
        # Step 6: Construct Raw Elements
        # ------------------------------------------------------------------
        raw_nodes, raw_edges = self.graph_builder.build_elements(entities, relations)

        # ------------------------------------------------------------------
        # Step 7: Diagram-Specific Family Adapter Transformation
        # ------------------------------------------------------------------
        adapter = get_adapter_for_type(target_type)
        metadata = DiagramMetadata(
            title=cfg.get("title", f"{target_type.value.replace('_', ' ').title()}"),
            description=doc.normalized_text[:120] + ("..." if len(doc.normalized_text) > 120 else ""),
            domain=target_type.value,
            provenance="nlp_pipeline",
            version="2.0.0",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        adapted_graph = adapter.adapt(
            nodes=raw_nodes,
            edges=raw_edges,
            text=doc.normalized_text,
            metadata=metadata,
        )

        # Attach classification and NLP engine metadata
        adapted_graph.metadata.domain = target_type.value
        adapted_graph.warnings.extend(pipeline_warnings)

        # ------------------------------------------------------------------
        # Step 8: Phase 2 Semantic Validation
        # ------------------------------------------------------------------
        report = validate_diagram(adapted_graph)

        # Merge validation report warnings into graph
        existing_warning_codes = {w.code for w in adapted_graph.warnings}
        for vw in report.warnings:
            if vw.code not in existing_warning_codes:
                adapted_graph.warnings.append(vw)
                existing_warning_codes.add(vw.code)

        # If errors were detected, record them as warnings with 'caution' level
        for err in report.errors:
            adapted_graph.warnings.append(
                ValidationWarning(
                    code=err.code,
                    message=f"Validation Alert: {err.message}",
                    level="caution",
                    element_id=err.element_id,
                )
            )

        return adapted_graph


# Singleton pipeline instance
_DEFAULT_PIPELINE = DiagramPipeline()


def generate_diagram(
    text: str,
    diagram_type: Optional[Union[str, DiagramType]] = None,
    config: Optional[Dict[str, Any]] = None
) -> DiagramGraph:
    """
    Main public API entry point for NLP diagram generation.
    
    Usage:
        from nlp import generate_diagram
        graph = generate_diagram("When user signs in, system validates credentials...")
    """
    return _DEFAULT_PIPELINE.generate(text, diagram_type=diagram_type, config=config)
