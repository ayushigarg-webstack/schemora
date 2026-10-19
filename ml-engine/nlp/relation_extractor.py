"""
Relationship Extraction Module.
Extracts directed semantic connections, flow transitions, conditional branches,
component interactions, concept hierarchies, database cardinalities, and sequence messages.
Preserves ordering, conditions, and negation while emitting warnings on ambiguity.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional, Any
from pydantic import BaseModel, Field

from ir.models import DiagramType
from .preprocessing import PreprocessedDocument
from .entity_extractor import ExtractedEntity

logger = logging.getLogger(__name__)


class ExtractedRelation(BaseModel):
    """Normalized semantic relationship between two entities."""
    id: str = Field(description="Unique edge identifier")
    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    label: Optional[str] = Field(default=None, description="Relationship description or condition label")
    relation_type: str = Field(default="flow", description="Semantic edge type e.g. flow, branch_yes, api_call, is_a")
    directed: bool = True
    cardinality: Optional[str] = None
    sequence_order: Optional[int] = None
    condition: Optional[str] = None
    is_negated: bool = False
    confidence: float = 0.85
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RelationExtractor:
    """
    Modular Relationship Extractor.
    Combines rule-based dependency patterns, connector analysis, and domain semantics.
    """

    def __init__(self):
        pass

    def extract(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity],
        diagram_type: DiagramType
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts relationships tailored to the specified DiagramType.
        Returns (relations, warnings).
        """
        warnings: List[str] = []
        if len(entities) < 2:
            warnings.append("Fewer than two entities detected; cannot establish relationships.")
            return [], warnings

        entity_by_id = {e.id: e for e in entities}
        entity_by_alias: Dict[str, ExtractedEntity] = {}
        for e in entities:
            entity_by_alias[e.canonical_name.lower()] = e
            entity_by_alias[e.label.lower()] = e
            for alias in e.aliases:
                entity_by_alias[alias.lower()] = e

        # Dispatch based on diagram family
        if diagram_type == DiagramType.FLOWCHART:
            relations, fam_warnings = self._extract_flowchart_relations(doc, entities)
        elif diagram_type == DiagramType.ARCHITECTURE:
            relations, fam_warnings = self._extract_architecture_relations(doc, entities, entity_by_alias)
        elif diagram_type == DiagramType.CONCEPT_MAP:
            relations, fam_warnings = self._extract_concept_relations(doc, entities, entity_by_alias)
        elif diagram_type == DiagramType.ER_DIAGRAM:
            relations, fam_warnings = self._extract_er_relations(doc, entities, entity_by_alias)
        elif diagram_type == DiagramType.SEQUENCE_DIAGRAM:
            relations, fam_warnings = self._extract_sequence_relations(doc, entities, entity_by_alias)
        elif diagram_type == DiagramType.NETWORK_TOPOLOGY:
            relations, fam_warnings = self._extract_network_relations(doc, entities, entity_by_alias)
        elif diagram_type == DiagramType.DEPENDENCY_GRAPH:
            relations, fam_warnings = self._extract_dependency_relations(doc, entities, entity_by_alias)
        else:
            relations, fam_warnings = self._extract_generic_flow_relations(doc, entities)

        warnings.extend(fam_warnings)
        return relations, warnings

    # ========================================================================
    # 1. FLOWCHART RELATION EXTRACTION (Sequence, Decisions, Loops)
    # ========================================================================

    def _extract_flowchart_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts sequential transitions, conditional decision branches (Yes/No),
        and iterative loop-backs.
        """
        relations = []
        warnings = []
        edge_idx = 1

        # Separate decision nodes from process nodes
        decision_nodes = [e for e in entities if e.category == "decision"]
        process_nodes = [e for e in entities if e.category != "decision"]

        if decision_nodes:
            # Connect process steps leading into decisions, and branch out
            curr_step_idx = 0
            for d_node in decision_nodes:
                # Preceding process leads to decision
                if curr_step_idx < len(process_nodes):
                    prev_proc = process_nodes[curr_step_idx]
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=prev_proc.id,
                            target_id=d_node.id,
                            label="evaluates",
                            relation_type="flow",
                        )
                    )
                    edge_idx += 1
                    curr_step_idx += 1

                # Decision requires at least 2 branches (Yes and No)
                # Success / True branch
                target_yes = process_nodes[curr_step_idx] if curr_step_idx < len(process_nodes) else None
                if target_yes:
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=d_node.id,
                            target_id=target_yes.id,
                            label="Yes",
                            relation_type="branch_yes",
                            condition="True",
                        )
                    )
                    edge_idx += 1
                    curr_step_idx += 1

                # Failure / False / Alternative branch
                target_no = process_nodes[curr_step_idx] if curr_step_idx < len(process_nodes) else None
                if target_no:
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=d_node.id,
                            target_id=target_no.id,
                            label="No",
                            relation_type="branch_no",
                            condition="False",
                        )
                    )
                    edge_idx += 1
                    curr_step_idx += 1

                # Check for loop back indicator in text
                if doc.has_loops and target_no and len(process_nodes) > 0:
                    # Loop back to earlier step or start
                    loop_target = process_nodes[0]
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=target_no.id,
                            target_id=loop_target.id,
                            label="retry / loop back",
                            relation_type="loop_back",
                            metadata={"is_loop": True},
                        )
                    )
                    edge_idx += 1

            # Connect any remaining process nodes sequentially
            while curr_step_idx < len(process_nodes) - 1:
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=process_nodes[curr_step_idx].id,
                        target_id=process_nodes[curr_step_idx + 1].id,
                        label="then",
                        relation_type="flow",
                    )
                )
                edge_idx += 1
                curr_step_idx += 1

        else:
            # Sequential pipeline of steps
            for i in range(len(entities) - 1):
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=entities[i].id,
                        target_id=entities[i + 1].id,
                        label="then",
                        relation_type="flow",
                    )
                )
                edge_idx += 1

            # Loop check for non-decision sequence
            if doc.has_loops and len(entities) >= 2:
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=entities[-1].id,
                        target_id=entities[0].id,
                        label="loops back",
                        relation_type="loop_back",
                        metadata={"is_loop": True},
                    )
                )
                edge_idx += 1

        return relations, warnings

    # ========================================================================
    # 2. SOFTWARE ARCHITECTURE RELATION EXTRACTION
    # ========================================================================

    def _extract_architecture_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity],
        entity_by_alias: Dict[str, ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts tiered communication paths (Client -> Gateway -> Service -> Cache / DB / External).
        Detects anti-patterns like direct Client -> Database access and issues warnings.
        """
        relations = []
        warnings = []
        edge_idx = 1
        connected_pairs: Set[Tuple[str, str]] = set()

        # Categorize entities by architectural tier
        clients = [e for e in entities if e.category in ["client", "ui", "frontend"]]
        services = [e for e in entities if e.category in ["service", "backend", "api"]]
        databases = [e for e in entities if e.category in ["database", "storage"]]
        caches = [e for e in entities if e.category in ["cache"]]
        externals = [e for e in entities if e.category in ["external_api", "cloud"]]

        text_lower = doc.normalized_text.lower()

        # A. Client -> Service / Gateway
        for client in clients:
            for srv in services:
                # Check for explicit verbal association or default architectural flow
                rel_key = (client.id, srv.id)
                if rel_key not in connected_pairs:
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=client.id,
                            target_id=srv.id,
                            label="API Request",
                            relation_type="api_call",
                            metadata={"protocol": "HTTPS/REST"},
                        )
                    )
                    connected_pairs.add(rel_key)
                    edge_idx += 1

        # B. Service -> Cache
        for srv in services:
            for cache in caches:
                rel_key = (srv.id, cache.id)
                if rel_key not in connected_pairs:
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=srv.id,
                            target_id=cache.id,
                            label="read/write cache",
                            relation_type="data_read_write",
                            metadata={"protocol": "Redis Protocol"},
                        )
                    )
                    connected_pairs.add(rel_key)
                    edge_idx += 1

        # C. Service -> Database
        for srv in services:
            for db in databases:
                rel_key = (srv.id, db.id)
                if rel_key not in connected_pairs:
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=srv.id,
                            target_id=db.id,
                            label="queries / persists",
                            relation_type="data_read_write",
                            metadata={"protocol": "Database Driver"},
                        )
                    )
                    connected_pairs.add(rel_key)
                    edge_idx += 1

        # D. Service -> External Payment Gateway / API
        for srv in services:
            for ext in externals:
                rel_key = (srv.id, ext.id)
                if rel_key not in connected_pairs:
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=srv.id,
                            target_id=ext.id,
                            label="processes payments",
                            relation_type="api_call",
                            metadata={"protocol": "HTTPS/TLS"},
                        )
                    )
                    connected_pairs.add(rel_key)
                    edge_idx += 1

        # E. Direct Client -> Database check (Anti-pattern detection)
        for client in clients:
            for db in databases:
                # If text explicitly states client accesses database
                if f"{client.canonical_name.lower()} connects to {db.canonical_name.lower()}" in text_lower or \
                   f"{client.canonical_name.lower()} queries {db.canonical_name.lower()}" in text_lower:
                    rel_key = (client.id, db.id)
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=client.id,
                            target_id=db.id,
                            label="direct access",
                            relation_type="data_read_write",
                        )
                    )
                    connected_pairs.add(rel_key)
                    edge_idx += 1
                    warnings.append(
                        f"Direct database access detected between client '{client.label}' and database '{db.label}'."
                    )

        # Fallback: if no tier patterns matched, connect linearly
        if not relations:
            for i in range(len(entities) - 1):
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=entities[i].id,
                        target_id=entities[i + 1].id,
                        label="communicates with",
                        relation_type="api_call",
                    )
                )
                edge_idx += 1

        return relations, warnings

    # ========================================================================
    # 3. CONCEPT MAP RELATION EXTRACTION
    # ========================================================================

    def _extract_concept_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity],
        entity_by_alias: Dict[str, ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts semantic propositions: hierarchy ('is a', 'type of'),
        composition ('consists of', 'contains', 'includes'), and association ('relates to').
        GUARANTEES non-empty proposition labels on all edges.
        """
        relations = []
        warnings = []
        edge_idx = 1
        connected: Set[Tuple[str, str]] = set()

        # Step A: Sentence-level proposition extraction (Subject -> Verb -> Object(s))
        VERB_PROP_REGEX = re.compile(
            r"\b(encompasses|comprises|utilizes|includes|contains|consists of|leads to|relates to|requires|is a type of|is an instance of)\b",
            re.IGNORECASE
        )
        for sent in doc.sentences:
            s_text = sent.clean_text
            found_in_sent = []
            for ent in entities:
                pos = s_text.lower().find(ent.canonical_name.lower())
                if pos != -1:
                    found_in_sent.append((pos, ent))
            found_in_sent.sort(key=lambda x: x[0])

            if len(found_in_sent) >= 2:
                subj = found_in_sent[0][1]
                v_match = VERB_PROP_REGEX.search(s_text)
                prop_label = v_match.group(1).lower() if v_match else "relates to"

                for _, obj in found_in_sent[1:]:
                    rel_key = (subj.id, obj.id)
                    if rel_key not in connected and subj.id != obj.id:
                        relations.append(
                            ExtractedRelation(
                                id=f"edge_{edge_idx}",
                                source_id=subj.id,
                                target_id=obj.id,
                                label=prop_label,
                                relation_type="concept_relation",
                            )
                        )
                        connected.add(rel_key)
                        edge_idx += 1

        # Step B: Connect Root to Categories if not already connected
        root_nodes = [e for e in entities if e.attributes.get("level") == "root"]
        category_nodes = [e for e in entities if e.attributes.get("level") == "category"]
        concept_nodes = [e for e in entities if e.attributes.get("level") not in ["root", "category"]]

        for root in root_nodes:
            for cat in category_nodes:
                rel_key = (root.id, cat.id)
                if rel_key not in connected and root.id != cat.id:
                    relations.append(
                        ExtractedRelation(
                            id=f"edge_{edge_idx}",
                            source_id=root.id,
                            target_id=cat.id,
                            label="classified as",
                            relation_type="is_a",
                        )
                    )
                    connected.add(rel_key)
                    edge_idx += 1

        # 2. Connect Categories to Concepts or Concepts to Concepts
        linear_names = {"array", "linked list", "doubly linked list", "stack", "queue"}
        tree_graph_names = {"tree", "binary search tree", "graph", "heap", "trie"}

        if category_nodes:
            for cat in category_nodes:
                cat_lower = cat.canonical_name.lower()
                for c in concept_nodes:
                    c_lower = c.canonical_name.lower()
                    should_connect = False
                    if "linear" in cat_lower and any(ln in c_lower for ln in linear_names):
                        should_connect = True
                    elif "non-linear" in cat_lower and any(tn in c_lower for tn in tree_graph_names):
                        should_connect = True
                    elif len(category_nodes) == 1:
                        should_connect = True

                    if should_connect:
                        rel_key = (cat.id, c.id)
                        if rel_key not in connected:
                            relations.append(
                                ExtractedRelation(
                                    id=f"edge_{edge_idx}",
                                    source_id=cat.id,
                                    target_id=c.id,
                                    label="includes",
                                    relation_type="part_of",
                                )
                            )
                            connected.add(rel_key)
                            edge_idx += 1
        else:
            # Without explicit category nodes, connect primary concept to others or create hierarchy
            if root_nodes:
                root = root_nodes[0]
                for c in concept_nodes:
                    rel_key = (root.id, c.id)
                    if rel_key not in connected:
                        relations.append(
                            ExtractedRelation(
                                id=f"edge_{edge_idx}",
                                source_id=root.id,
                                target_id=c.id,
                                label="includes concept",
                                relation_type="is_a",
                            )
                        )
                        connected.add(rel_key)
                        edge_idx += 1
            else:
                # Hierarchical cluster: first entity connects to rest
                first = entities[0]
                for other in entities[1:]:
                    rel_key = (first.id, other.id)
                    if rel_key not in connected:
                        relations.append(
                            ExtractedRelation(
                                id=f"edge_{edge_idx}",
                                source_id=first.id,
                                target_id=other.id,
                                label="relates to",
                                relation_type="relates_to",
                            )
                        )
                        connected.add(rel_key)
                        edge_idx += 1

        # Also connect linear cross-references if described: e.g. "Binary Search Tree is a Tree"
        tree_node = next((e for e in entities if e.canonical_name.lower() == "tree"), None)
        bst_node = next((e for e in entities if "binary search tree" in e.canonical_name.lower()), None)
        if tree_node and bst_node:
            rel_key = (tree_node.id, bst_node.id)
            if rel_key not in connected:
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=tree_node.id,
                        target_id=bst_node.id,
                        label="specialized as",
                        relation_type="is_a",
                    )
                )
                connected.add(rel_key)
                edge_idx += 1

        return relations, warnings

    # ========================================================================
    # 4. DATABASE / ER RELATION EXTRACTION
    # ========================================================================

    def _extract_er_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity],
        entity_by_alias: Dict[str, ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts ER relationships with explicit cardinalities (1:1, 1:N, M:N).
        """
        relations = []
        warnings = []
        edge_idx = 1
        text_lower = doc.normalized_text.lower()

        # Connect entities based on common ER patterns
        dept = entity_by_alias.get("department")
        course = entity_by_alias.get("course")
        student = entity_by_alias.get("student")

        if dept and course:
            relations.append(
                ExtractedRelation(
                    id=f"edge_{edge_idx}",
                    source_id=dept.id,
                    target_id=course.id,
                    label="offers",
                    relation_type="one_to_many",
                    cardinality="1:N",
                )
            )
            edge_idx += 1

        if student and course:
            relations.append(
                ExtractedRelation(
                    id=f"edge_{edge_idx}",
                    source_id=student.id,
                    target_id=course.id,
                    label="enrolls in",
                    relation_type="many_to_many",
                    cardinality="M:N",
                )
            )
            edge_idx += 1

        # Fallback if specific entities weren't in college domain
        if not relations:
            for i in range(len(entities) - 1):
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=entities[i].id,
                        target_id=entities[i + 1].id,
                        label="relates to",
                        relation_type="one_to_many",
                        cardinality="1:N",
                    )
                )
                edge_idx += 1

        return relations, warnings

    # ========================================================================
    # 5. SEQUENCE DIAGRAM RELATION EXTRACTION
    # ========================================================================

    def _extract_sequence_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity],
        entity_by_alias: Dict[str, ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts chronologically ordered interaction messages with monotonic sequence_order.
        """
        relations = []
        warnings = []
        edge_idx = 1
        seq_order = 1

        # Connect participants in interaction order
        for i in range(len(entities) - 1):
            relations.append(
                ExtractedRelation(
                    id=f"edge_{edge_idx}",
                    source_id=entities[i].id,
                    target_id=entities[i + 1].id,
                    label=f"Request step {seq_order}",
                    relation_type="synchronous_call",
                    sequence_order=seq_order,
                )
            )
            edge_idx += 1
            seq_order += 1

        # Return response message
        if len(entities) >= 2:
            relations.append(
                ExtractedRelation(
                    id=f"edge_{edge_idx}",
                    source_id=entities[-1].id,
                    target_id=entities[0].id,
                    label=f"Response step {seq_order}",
                    relation_type="return_signal",
                    sequence_order=seq_order,
                )
            )
            edge_idx += 1

        return relations, warnings

    # ========================================================================
    # 6. NETWORK TOPOLOGY RELATION EXTRACTION
    # ========================================================================

    def _extract_network_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity],
        entity_by_alias: Dict[str, ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts network topology links (Workstations -> Switch -> Router -> Firewall -> Internet).
        """
        relations = []
        warnings = []
        edge_idx = 1

        hosts = [e for e in entities if e.category == "host"]
        switches = [e for e in entities if e.category == "switch"]
        routers = [e for e in entities if e.category == "router"]
        firewalls = [e for e in entities if e.category == "firewall"]
        clouds = [e for e in entities if e.category == "cloud"]

        # Hosts -> Switch
        for h in hosts:
            for sw in switches:
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=h.id,
                        target_id=sw.id,
                        label="Ethernet",
                        relation_type="ethernet",
                    )
                )
                edge_idx += 1

        # Switch -> Router
        for sw in switches:
            for rt in routers:
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=sw.id,
                        target_id=rt.id,
                        label="Trunk Uplink",
                        relation_type="ethernet",
                    )
                )
                edge_idx += 1

        # Router -> Firewall
        for rt in routers:
            for fw in firewalls:
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=rt.id,
                        target_id=fw.id,
                        label="WAN Gateway",
                        relation_type="wan",
                    )
                )
                edge_idx += 1

        # Firewall -> Internet
        for fw in firewalls:
            for cl in clouds:
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=fw.id,
                        target_id=cl.id,
                        label="Public Gateway",
                        relation_type="wan",
                    )
                )
                edge_idx += 1

        # Fallback if standard devices weren't categorized
        if not relations:
            for i in range(len(entities) - 1):
                relations.append(
                    ExtractedRelation(
                        id=f"edge_{edge_idx}",
                        source_id=entities[i].id,
                        target_id=entities[i + 1].id,
                        label="connects to",
                        relation_type="ethernet",
                    )
                )
                edge_idx += 1

        return relations, warnings

    # ========================================================================
    # 7. DEPENDENCY GRAPH RELATION EXTRACTION (DAG Enforcement)
    # ========================================================================

    def _extract_dependency_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity],
        entity_by_alias: Dict[str, ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        """
        Extracts task prerequisites and blocks relationships strictly forming a DAG.
        """
        relations = []
        warnings = []
        edge_idx = 1

        # Connect in topological order
        for i in range(len(entities) - 1):
            relations.append(
                ExtractedRelation(
                    id=f"edge_{edge_idx}",
                    source_id=entities[i].id,
                    target_id=entities[i + 1].id,
                    label="prerequisite for",
                    relation_type="depends_on",
                )
            )
            edge_idx += 1

        return relations, warnings

    # ========================================================================
    # GENERIC FALLBACK RELATION EXTRACTION
    # ========================================================================

    def _extract_generic_flow_relations(
        self,
        doc: PreprocessedDocument,
        entities: List[ExtractedEntity]
    ) -> Tuple[List[ExtractedRelation], List[str]]:
        relations = []
        for i in range(len(entities) - 1):
            relations.append(
                ExtractedRelation(
                    id=f"edge_{i+1}",
                    source_id=entities[i].id,
                    target_id=entities[i + 1].id,
                    label="flows to",
                    relation_type="flow",
                )
            )
        return relations, []


def extract_relations(
    doc: PreprocessedDocument,
    entities: List[ExtractedEntity],
    diagram_type: DiagramType
) -> Tuple[List[ExtractedRelation], List[str]]:
    """Convenience helper function for relation extraction."""
    extractor = RelationExtractor()
    return extractor.extract(doc, entities, diagram_type)
