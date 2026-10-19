"""
Entity and Concept Extraction Module.
Extracts processes, services, databases, concepts, participants, devices, and tasks
using linguistic patterns, technical gazetteers, and spaCy (with documented fallback).
Handles coreference resolution and alias deduplication without combining distinct entities.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional, Any
from pydantic import BaseModel, Field

from ir.models import DiagramType
from .preprocessing import PreprocessedDocument, PreprocessedSentence

logger = logging.getLogger(__name__)

# Check spaCy availability
SPACY_AVAILABLE = False
_SPACY_NLP = None

try:
    import spacy
    try:
        _SPACY_NLP = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except (OSError, IOError):
        logger.warning(
            "spaCy model 'en_core_web_sm' is not installed. "
            "Activating deterministic rule-based linguistic gazetteer fallback."
        )
except ImportError:
    logger.warning(
        "spaCy is not installed in the current environment. "
        "Activating deterministic rule-based linguistic gazetteer fallback."
    )


class ExtractedEntity(BaseModel):
    """Normalized diagram entity candidate."""
    id: str = Field(description="Unique sanitized node ID")
    canonical_name: str = Field(description="Normalized canonical display name")
    label: str = Field(description="Diagram display label")
    category: str = Field(description="Semantic category e.g. service, database, concept, decision, process")
    aliases: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.90
    first_seen_sentence: int = 0


# ============================================================================
# COMPREHENSIVE DOMAIN GAZETTEER
# ============================================================================

GAZETTEER_ENTITIES: Dict[str, Dict[str, Any]] = {
    # 1. SOFTWARE ARCHITECTURE — Frontend
    "React": {"category": "client", "label": "React", "tier": "frontend"},
    "Vue": {"category": "client", "label": "Vue", "tier": "frontend"},
    "Angular": {"category": "client", "label": "Angular", "tier": "frontend"},
    "Next.js": {"category": "client", "label": "Next.js", "tier": "frontend"},
    "Frontend": {"category": "client", "label": "Frontend", "tier": "frontend"},
    "Web App": {"category": "client", "label": "Web App", "tier": "frontend"},
    "Mobile App": {"category": "client", "label": "Mobile App", "tier": "frontend"},
    "Browser": {"category": "client", "label": "Browser", "tier": "frontend"},
    "Client": {"category": "client", "label": "Client", "tier": "frontend"},
    "User Interface": {"category": "client", "label": "User Interface", "tier": "frontend"},
    "UI": {"category": "client", "label": "UI", "tier": "frontend"},

    # 2. SOFTWARE ARCHITECTURE — Backend & Gateways
    "Node.js": {"category": "service", "label": "Node.js API", "tier": "backend"},
    "Express": {"category": "service", "label": "Express Service", "tier": "backend"},
    "FastAPI": {"category": "service", "label": "FastAPI Service", "tier": "backend"},
    "Django": {"category": "service", "label": "Django Service", "tier": "backend"},
    "Flask": {"category": "service", "label": "Flask Service", "tier": "backend"},
    "Spring Boot": {"category": "service", "label": "Spring Boot Service", "tier": "backend"},
    "Backend": {"category": "service", "label": "Backend API", "tier": "backend"},
    "API Gateway": {"category": "service", "label": "API Gateway", "tier": "gateway"},
    "Auth Service": {"category": "service", "label": "Auth Service", "tier": "backend"},
    "Payment Service": {"category": "service", "label": "Payment Service", "tier": "backend"},
    "Order Service": {"category": "service", "label": "Order Service", "tier": "backend"},
    "Inventory Service": {"category": "service", "label": "Inventory Service", "tier": "backend"},
    "User Service": {"category": "service", "label": "User Service", "tier": "backend"},
    "Notification Service": {"category": "service", "label": "Notification Service", "tier": "backend"},
    "Microservice": {"category": "service", "label": "Microservice", "tier": "backend"},
    "Load Balancer": {"category": "service", "label": "Load Balancer", "tier": "gateway"},

    # 3. SOFTWARE ARCHITECTURE — Databases & Caches
    "PostgreSQL": {"category": "database", "label": "PostgreSQL DB", "tier": "database"},
    "MySQL": {"category": "database", "label": "MySQL DB", "tier": "database"},
    "MongoDB": {"category": "database", "label": "MongoDB", "tier": "database"},
    "SQLite": {"category": "database", "label": "SQLite DB", "tier": "database"},
    "Redis": {"category": "cache", "label": "Redis Cache", "tier": "cache"},
    "Memcached": {"category": "cache", "label": "Memcached", "tier": "cache"},
    "ElasticSearch": {"category": "database", "label": "ElasticSearch", "tier": "database"},
    "Database": {"category": "database", "label": "Primary Database", "tier": "database"},
    "DB": {"category": "database", "label": "Database", "tier": "database"},
    "Cache": {"category": "cache", "label": "Cache Tier", "tier": "cache"},

    # 4. SOFTWARE ARCHITECTURE — Messaging & External
    "Kafka": {"category": "service", "label": "Kafka Broker", "tier": "messaging"},
    "RabbitMQ": {"category": "service", "label": "RabbitMQ", "tier": "messaging"},
    "Stripe": {"category": "external_api", "label": "Stripe Gateway", "tier": "external"},
    "PayPal": {"category": "external_api", "label": "PayPal API", "tier": "external"},
    "Payment Gateway": {"category": "external_api", "label": "Payment Gateway", "tier": "external"},
    "External Payment Gateway": {"category": "external_api", "label": "Payment Gateway", "tier": "external"},
    "Auth0": {"category": "external_api", "label": "Auth0 Provider", "tier": "external"},
    "Third-Party Service": {"category": "external_api", "label": "External Service", "tier": "external"},

    # 5. CONCEPT MAPS — Core Computer Science Data Structures
    "Data Structure": {"category": "concept", "label": "Data Structure", "level": "root"},
    "Data Structures": {"category": "concept", "label": "Data Structures", "level": "root"},
    "Linear Data Structure": {"category": "concept", "label": "Linear Data Structure", "level": "category"},
    "Non-Linear Data Structure": {"category": "concept", "label": "Non-Linear Data Structure", "level": "category"},
    "Array": {"category": "concept", "label": "Array", "level": "concept"},
    "Arrays": {"category": "concept", "label": "Array", "level": "concept"},
    "Linked List": {"category": "concept", "label": "Linked List", "level": "concept"},
    "Linked Lists": {"category": "concept", "label": "Linked List", "level": "concept"},
    "Doubly Linked List": {"category": "concept", "label": "Doubly Linked List", "level": "concept"},
    "Circular Linked List": {"category": "concept", "label": "Circular Linked List", "level": "concept"},
    "Stack": {"category": "concept", "label": "Stack", "level": "concept"},
    "Stacks": {"category": "concept", "label": "Stack", "level": "concept"},
    "Queue": {"category": "concept", "label": "Queue", "level": "concept"},
    "Queues": {"category": "concept", "label": "Queue", "level": "concept"},
    "Tree": {"category": "concept", "label": "Tree", "level": "concept"},
    "Trees": {"category": "concept", "label": "Tree", "level": "concept"},
    "Binary Tree": {"category": "concept", "label": "Binary Tree", "level": "concept"},
    "Binary Search Tree": {"category": "concept", "label": "Binary Search Tree", "level": "concept"},
    "Balanced Tree": {"category": "concept", "label": "Balanced Tree", "level": "concept"},
    "AVL Tree": {"category": "concept", "label": "AVL Tree", "level": "concept"},
    "Graph": {"category": "concept", "label": "Graph", "level": "concept"},
    "Graphs": {"category": "concept", "label": "Graph", "level": "concept"},
    "Directed Graph": {"category": "concept", "label": "Directed Graph", "level": "concept"},
    "Hash Table": {"category": "concept", "label": "Hash Table", "level": "concept"},
    "Hash Tables": {"category": "concept", "label": "Hash Table", "level": "concept"},
    "Heap": {"category": "concept", "label": "Heap", "level": "concept"},
    "Heaps": {"category": "concept", "label": "Heap", "level": "concept"},
    "Trie": {"category": "concept", "label": "Trie", "level": "concept"},

    # 5B. CONCEPT MAPS — AI, Machine Learning & Computer Science Domains
    "Artificial Intelligence": {"category": "concept", "label": "Artificial Intelligence", "level": "root"},
    "AI": {"category": "concept", "label": "Artificial Intelligence", "level": "root"},
    "Machine Learning": {"category": "concept", "label": "Machine Learning", "level": "category"},
    "Deep Learning": {"category": "concept", "label": "Deep Learning", "level": "category"},
    "Computer Vision": {"category": "concept", "label": "Computer Vision", "level": "concept"},
    "Neural Networks": {"category": "concept", "label": "Neural Networks", "level": "concept"},
    "Neural Network": {"category": "concept", "label": "Neural Networks", "level": "concept"},
    "Supervised Learning": {"category": "concept", "label": "Supervised Learning", "level": "concept"},
    "Unsupervised Learning": {"category": "concept", "label": "Unsupervised Learning", "level": "concept"},
    "Reinforcement Learning": {"category": "concept", "label": "Reinforcement Learning", "level": "concept"},
    "Natural Language Processing": {"category": "concept", "label": "Natural Language Processing", "level": "concept"},
    "NLP": {"category": "concept", "label": "Natural Language Processing", "level": "concept"},

    # 6. DATABASE / ER ENTITIES
    "Student": {"category": "entity", "label": "Student", "is_entity": True},
    "Students": {"category": "entity", "label": "Student", "is_entity": True},
    "Department": {"category": "entity", "label": "Department", "is_entity": True},
    "Departments": {"category": "entity", "label": "Department", "is_entity": True},
    "Course": {"category": "entity", "label": "Course", "is_entity": True},
    "Courses": {"category": "entity", "label": "Course", "is_entity": True},
    "Instructor": {"category": "entity", "label": "Instructor", "is_entity": True},
    "Instructors": {"category": "entity", "label": "Instructor", "is_entity": True},
    "Enrollment": {"category": "entity", "label": "Enrollment", "is_entity": True},
    "Order": {"category": "entity", "label": "Order", "is_entity": True},
    "Orders": {"category": "entity", "label": "Order", "is_entity": True},
    "Product": {"category": "entity", "label": "Product", "is_entity": True},
    "Products": {"category": "entity", "label": "Product", "is_entity": True},
    "Customer": {"category": "entity", "label": "Customer", "is_entity": True},
    "Customers": {"category": "entity", "label": "Customer", "is_entity": True},

    # 7. NETWORK DEVICES
    "Workstation": {"category": "host", "label": "Workstation", "device_type": "workstation"},
    "Workstations": {"category": "host", "label": "Workstations", "device_type": "workstation"},
    "PC": {"category": "host", "label": "Workstation PC", "device_type": "workstation"},
    "Switch": {"category": "switch", "label": "Network Switch", "device_type": "switch"},
    "Switches": {"category": "switch", "label": "Network Switches", "device_type": "switch"},
    "Router": {"category": "router", "label": "Gateway Router", "device_type": "router"},
    "Routers": {"category": "router", "label": "Routers", "device_type": "router"},
    "Firewall": {"category": "firewall", "label": "Security Firewall", "device_type": "firewall"},
    "Internet": {"category": "cloud", "label": "Public Internet", "device_type": "internet"},
    "Subnet": {"category": "subnet", "label": "Local Subnet", "device_type": "subnet"},
    "Server": {"category": "host", "label": "Local Server", "device_type": "server"},

    # 8. SEQUENCE PARTICIPANTS
    "User": {"category": "participant", "label": "End User", "role": "actor"},
    "Bank": {"category": "participant", "label": "Banking Network", "role": "external"},

    # 9. TASKS & WORKFLOW STEPS
    "Requirements": {"category": "task", "label": "Requirements Analysis"},
    "Design": {"category": "task", "label": "System Design"},
    "Backend Setup": {"category": "task", "label": "Backend Setup"},
    "Frontend Setup": {"category": "task", "label": "Frontend Setup"},
    "API Integration": {"category": "task", "label": "API Integration"},
    "Testing": {"category": "task", "label": "Automated Testing"},
    "Deployment": {"category": "task", "label": "Production Deployment"},
}


def sanitize_node_id(name: str) -> str:
    """Creates a deterministic, clean, valid node identifier."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower())
    clean = clean.strip("_")
    if not clean or clean[0].isdigit():
        clean = "node_" + clean
    return f"node_{clean}" if not clean.startswith("node_") else clean


class EntityExtractor:
    """
    Modular Entity & Concept Extractor.
    Extracts software components, CS concepts, flowchart actions, ER entities,
    network devices, and participants with coreference resolution and alias deduplication.
    """

    def __init__(self, custom_gazetteer: Optional[Dict[str, Dict[str, Any]]] = None):
        self.gazetteer = dict(GAZETTEER_ENTITIES)
        if custom_gazetteer:
            self.gazetteer.update(custom_gazetteer)

        # Sort gazetteer keys longest first to match compound phrases before components
        self._sorted_keys = sorted(self.gazetteer.keys(), key=len, reverse=True)
        escaped = [re.escape(k) for k in self._sorted_keys]
        self._gazetteer_regex = re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)

    def extract(
        self,
        doc: PreprocessedDocument,
        diagram_type: Optional[DiagramType] = None
    ) -> List[ExtractedEntity]:
        """
        Main extraction entry point.
        Dispatches to family-specific heuristic rules and merges gazetteer matches.
        """
        entities: List[ExtractedEntity] = []
        seen_canonical: Dict[str, ExtractedEntity] = {}

        # 1. Gazetteer exact and case-insensitive phrase matching with span tracking
        # Generic tier terms that should be absorbed into specific brands
        GENERIC_TERMS = {"frontend", "backend", "database", "db", "cache", "service", "client", "web app"}
        NON_ACTOR_PHRASES = [r"\buser\s+(?:sessions?|data|credentials?|account|inputs?)\b"]

        for s_idx, sent in enumerate(doc.sentences):
            sent_text = sent.clean_text

            # Check for non-actor user phrases
            ignore_user_spans: Set[Tuple[int, int]] = set()
            for nap in NON_ACTOR_PHRASES:
                for nm in re.finditer(nap, sent_text, re.IGNORECASE):
                    ignore_user_spans.add((nm.start(), nm.end()))

            raw_spans = []
            for match in self._gazetteer_regex.finditer(sent_text):
                m_str = match.group(0)
                start, end = match.start(), match.end()

                # Check if this match falls inside an ignored span (e.g. 'user' in 'user sessions')
                if any(is_s <= start and end <= is_e for is_s, is_e in ignore_user_spans):
                    continue

                matched_key = None
                for k in self._sorted_keys:
                    if k.lower() == m_str.lower():
                        matched_key = k
                        break
                if matched_key:
                    raw_spans.append((start, end, m_str, matched_key))

            # Filter/Merge adjacent specific + generic pairs (e.g. "React frontend", "Node.js backend", "MongoDB database")
            filtered_matches = []
            skip_indices = set()

            for i in range(len(raw_spans)):
                if i in skip_indices:
                    continue
                start_i, end_i, str_i, key_i = raw_spans[i]

                # Check if next match is adjacent
                if i + 1 < len(raw_spans):
                    start_j, end_j, str_j, key_j = raw_spans[i + 1]
                    # If within 2 characters (e.g. space)
                    if start_j - end_i <= 2:
                        key_i_lower = key_i.lower()
                        key_j_lower = key_j.lower()

                        if key_i_lower not in GENERIC_TERMS and key_j_lower in GENERIC_TERMS:
                            # Specific followed by generic e.g. "React" + "Frontend"
                            combined_label = f"{key_i} {key_j.title()}"
                            filtered_matches.append((key_i, combined_label))
                            skip_indices.add(i + 1)
                            continue
                        elif key_i_lower in GENERIC_TERMS and key_j_lower not in GENERIC_TERMS:
                            # Generic followed by specific e.g. "Database" + "PostgreSQL"
                            combined_label = f"{key_j} {key_i.title()}"
                            filtered_matches.append((key_j, combined_label))
                            skip_indices.add(i + 1)
                            continue

                filtered_matches.append((key_i, self.gazetteer[key_i].get("label", key_i)))

            seen_brand_keys: Dict[str, ExtractedEntity] = {
                e.attributes.get("brand_key", "").lower(): e
                for e in entities if "brand_key" in e.attributes
            }

            for matched_key, display_label in filtered_matches:
                info = self.gazetteer[matched_key]
                brand_k = matched_key.lower()

                # If the same brand was already registered in the diagram, treat as repeated coreference
                if brand_k in seen_brand_keys:
                    existing = seen_brand_keys[brand_k]
                    if display_label not in existing.aliases:
                        existing.aliases.append(display_label)
                    continue

                canonical = display_label
                node_id = sanitize_node_id(canonical)

                if canonical.lower() in seen_canonical:
                    existing = seen_canonical[canonical.lower()]
                    if matched_key not in existing.aliases:
                        existing.aliases.append(matched_key)
                else:
                    attrs = dict(info)
                    attrs["brand_key"] = matched_key
                    entity = ExtractedEntity(
                        id=node_id,
                        canonical_name=canonical,
                        label=canonical,
                        category=info.get("category", "component"),
                        aliases=[matched_key],
                        attributes=attrs,
                        confidence=0.95,
                        first_seen_sentence=s_idx,
                    )
                    seen_canonical[canonical.lower()] = entity
                    seen_brand_keys[brand_k] = entity
                    entities.append(entity)

        # 2. Family-specific structural entity extraction
        if diagram_type == DiagramType.FLOWCHART or (diagram_type is None and doc.has_conditions):
            flow_entities = self._extract_flowchart_entities(doc)
            for fe in flow_entities:
                if fe.canonical_name.lower() not in seen_canonical:
                    seen_canonical[fe.canonical_name.lower()] = fe
                    entities.append(fe)

        elif diagram_type == DiagramType.ER_DIAGRAM:
            er_entities = self._extract_er_entities(doc)
            for ee in er_entities:
                if ee.canonical_name.lower() not in seen_canonical:
                    seen_canonical[ee.canonical_name.lower()] = ee
                    entities.append(ee)

        elif diagram_type == DiagramType.DEPENDENCY_GRAPH:
            task_entities = self._extract_task_entities(doc)
            for te in task_entities:
                if te.canonical_name.lower() not in seen_canonical:
                    seen_canonical[te.canonical_name.lower()] = te
                    entities.append(te)

        elif diagram_type == DiagramType.CONCEPT_MAP:
            concept_entities = self._extract_concept_entities(doc)
            for ce in concept_entities:
                if ce.canonical_name.lower() not in seen_canonical:
                    seen_canonical[ce.canonical_name.lower()] = ce
                    entities.append(ce)

        # 3. Dynamic clause-based action/process extraction if entities are scarce
        if len(entities) < 2 and (diagram_type == DiagramType.FLOWCHART or diagram_type is None):
            action_entities = self._extract_action_clauses(doc)
            for ae in action_entities:
                if ae.canonical_name.lower() not in seen_canonical:
                    seen_canonical[ae.canonical_name.lower()] = ae
                    entities.append(ae)

        # 4. Ultimate fallback if still 0 entities for any diagram type
        if len(entities) == 0 and doc.sentences:
            action_entities = self._extract_action_clauses(doc)
            for ae in action_entities:
                if ae.canonical_name.lower() not in seen_canonical:
                    seen_canonical[ae.canonical_name.lower()] = ae
                    entities.append(ae)

        return entities

    def _extract_flowchart_entities(self, doc: PreprocessedDocument) -> List[ExtractedEntity]:
        """Extracts decision nodes, condition evaluations, and procedural steps."""
        entities = []
        step_counter = 1

        for s_idx, sent in enumerate(doc.sentences):
            for clause in sent.clauses:
                clause_text = clause.text.strip()
                clause_lower = clause_text.lower()

                # A. Condition / Decision detection (binary branches: if, unless, in case of, or questions)
                is_decision_cond = (
                    clause.condition_type in ["if", "unless", "in_case_of"]
                    or clause_lower.startswith("if ")
                    or " if " in clause_lower
                    or "?" in clause_text
                )
                if is_decision_cond:
                    # Formulate concise decision label
                    cond_match = re.search(r"\bif\b\s+(.+?)(?:,\s*then|\s+then|,|\s+the system|\s+it|\?|$)", clause_text, re.IGNORECASE)
                    if cond_match:
                        cond_expr = cond_match.group(1).strip()
                        # Clean condition
                        cond_label = cond_expr.capitalize()
                        if not cond_label.endswith("?"):
                            cond_label += "?"
                    else:
                        cond_label = clause_text.rstrip(".") + "?"

                    # Shorten if too verbose
                    if len(cond_label) > 40:
                        words = cond_label.split()[:5]
                        cond_label = " ".join(words) + "?"

                    node_id = f"node_decision_{step_counter}"
                    entities.append(
                        ExtractedEntity(
                            id=node_id,
                            canonical_name=cond_label,
                            label=cond_label,
                            category="decision",
                            attributes={"condition_type": clause.condition_type or "if"},
                            confidence=0.90,
                            first_seen_sentence=s_idx,
                        )
                    )
                    step_counter += 1

                # B. Explicit process steps ("validates credentials", "issues auth token", "redirects to landing page")
                elif any(clause_lower.startswith(prefix) for prefix in ["when ", "the system ", "it ", "otherwise "]):
                    clean_action = re.sub(
                        r"^(?:when\s+(?:a\s+)?user\s+[^,]+,\s*|the\s+system\s+|it\s+|otherwise,?\s*)",
                        "",
                        clause_text,
                        flags=re.IGNORECASE
                    )
                    clean_action = clean_action.strip().rstrip(".")
                    if len(clean_action) > 3:
                        # Capitalize first letter
                        label = clean_action[0].upper() + clean_action[1:]
                        if len(label) > 45:
                            label = " ".join(label.split()[:6])

                        node_id = f"node_step_{step_counter}"
                        entities.append(
                            ExtractedEntity(
                                id=node_id,
                                canonical_name=label,
                                label=label,
                                category="process",
                                attributes={"is_negated": clause.is_negated},
                                confidence=0.85,
                                first_seen_sentence=s_idx,
                            )
                        )
                        step_counter += 1

        return entities

    def _extract_er_entities(self, doc: PreprocessedDocument) -> List[ExtractedEntity]:
        """Extracts database entities and associated attribute lists."""
        entities = []
        # Pattern e.g. "Entity Student has attributes id, name, and email"
        for s_idx, sent in enumerate(doc.sentences):
            match = re.search(r"\b(?:entity\s+)?([A-Z][a-zA-Z0-9_]+)\s+(?:has|contains|with)\s+(?:attributes?\s+)?(.+)", sent.clean_text, re.IGNORECASE)
            if match:
                ent_name = match.group(1).capitalize()
                raw_attrs = match.group(2).strip()
                # Split attributes by comma / and
                attr_tokens = [a.strip().strip(".") for a in re.split(r",|\band\b", raw_attrs) if a.strip()]
                clean_attrs = [a for a in attr_tokens if len(a) > 1 and a.lower() not in ["and", "attributes", "attribute"]]

                entities.append(
                    ExtractedEntity(
                        id=sanitize_node_id(ent_name),
                        canonical_name=ent_name,
                        label=ent_name,
                        category="entity",
                        attributes={"fields": clean_attrs},
                        confidence=0.92,
                        first_seen_sentence=s_idx,
                    )
                )

        return entities

    def _extract_task_entities(self, doc: PreprocessedDocument) -> List[ExtractedEntity]:
        """Extracts task names and dependencies."""
        entities = []
        # Pattern: "Task A", "Task B", "Step 1", "Compile step", etc.
        matches = re.findall(r"\b(?:Task|Step|Phase|Milestone)\s+([A-Za-z0-9_]+)\b", doc.normalized_text, re.IGNORECASE)
        for m in set(matches):
            label = f"Task {m.upper()}"
            entities.append(
                ExtractedEntity(
                    id=sanitize_node_id(label),
                    canonical_name=label,
                    label=label,
                    category="task",
                    confidence=0.90,
                )
            )
        return entities

    def _extract_concept_entities(self, doc: PreprocessedDocument) -> List[ExtractedEntity]:
        """Extracts concepts from proposition phrases e.g. 'A encompasses B and C'."""
        entities = []
        pattern = re.compile(
            r"([A-Z][a-zA-Z\s]+?)\s+(?:encompasses|comprises|utilizes|includes|contains|consists of|is composed of)\s+([^.]+)",
            re.IGNORECASE
        )
        for s_idx, sent in enumerate(doc.sentences):
            for m in pattern.finditer(sent.clean_text):
                subj = m.group(1).strip()
                objs = m.group(2).strip()
                if subj and len(subj) > 2:
                    entities.append(
                        ExtractedEntity(
                            id=sanitize_node_id(subj),
                            canonical_name=subj,
                            label=subj,
                            category="concept",
                            attributes={"level": "root" if s_idx == 0 else "category"},
                            confidence=0.90,
                            first_seen_sentence=s_idx,
                        )
                    )
                for obj in re.split(r",|\band\b", objs):
                    clean_obj = obj.strip()
                    if clean_obj and len(clean_obj) > 2 and clean_obj.lower() not in ["and", "or", "the"]:
                        entities.append(
                            ExtractedEntity(
                                id=sanitize_node_id(clean_obj),
                                canonical_name=clean_obj,
                                label=clean_obj,
                                category="concept",
                                attributes={"level": "concept"},
                                confidence=0.88,
                                first_seen_sentence=s_idx,
                            )
                        )
        return entities

    def _extract_action_clauses(self, doc: PreprocessedDocument) -> List[ExtractedEntity]:
        """Fallback action extraction from individual sentences when no gazetteer terms matched."""
        entities = []
        idx = 1
        for s_idx, sent in enumerate(doc.sentences):
            text = sent.clean_text.strip()
            if len(text) < 5:
                continue
            words = text.split()
            short_label = " ".join(words[:6])
            if len(words) > 6:
                short_label += "..."
            entities.append(
                ExtractedEntity(
                    id=f"node_step_{idx}",
                    canonical_name=short_label,
                    label=short_label,
                    category="process",
                    confidence=0.75,
                    first_seen_sentence=s_idx,
                )
            )
            idx += 1
        return entities


def extract_entities(
    doc: PreprocessedDocument,
    diagram_type: Optional[DiagramType] = None
) -> List[ExtractedEntity]:
    """Convenience helper function for entity extraction."""
    extractor = EntityExtractor()
    return extractor.extract(doc, diagram_type)
