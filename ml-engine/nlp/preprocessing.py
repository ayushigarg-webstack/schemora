"""
Text Preprocessing Module for Diagram Generation.
Provides input validation, normalization, sentence and clause segmentation,
technical term preservation, negation detection, conditional extraction,
and temporal sequence tracking.
"""

import re
import unicodedata
from typing import List, Dict, Set, Tuple, Optional, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Limits & Standards
# ---------------------------------------------------------------------------
MIN_INPUT_LENGTH = 5
MAX_INPUT_LENGTH = 10000

# Canonical technical terms and frameworks to protect from lowercasing or splitting
PRESERVED_TECHNICAL_TERMS: Set[str] = {
    # Web & Frontend
    "React", "Vue", "Angular", "Next.js", "Nuxt", "Svelte", "HTML", "CSS", "TypeScript", "JavaScript",
    # Backend & Frameworks
    "Node.js", "Express", "FastAPI", "Django", "Flask", "Spring Boot", "ASP.NET", "GraphQL", "REST API",
    # Databases & Caches
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "DynamoDB", "Cassandra", "ElasticSearch", "Memcached",
    # Message Queues & Event Streaming
    "Kafka", "RabbitMQ", "ActiveMQ", "SQS", "SNS", "Pub/Sub",
    # Cloud & Infra
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Lambda", "Nginx", "Apache",
    # Protocols & Formats
    "HTTP", "HTTPS", "gRPC", "WebSocket", "TCP/IP", "UDP", "JSON", "XML", "YAML",
    # Networking
    "VLAN", "LAN", "WAN", "IP", "DNS", "DHCP", "VPN", "BGP", "OSPF",
    # Hardware & Devices
    "Switch", "Router", "Firewall", "Gateway", "Load Balancer",
    # Database concepts
    "Primary Key", "Foreign Key", "Unique Key", "Index", "Entity", "Attribute", "Relation",
    # Data Structures & CS
    "Array", "Linked List", "Doubly Linked List", "Stack", "Queue", "Binary Tree", "Binary Search Tree",
    "Balanced Tree", "AVL Tree", "Red-Black Tree", "Graph", "Directed Graph", "DAG", "Heap", "Hash Table",
    "Trie", "Priority Queue", "B-Tree",
}

# Negation patterns
NEGATION_PATTERNS = [
    r"\bnot\b",
    r"\bnever\b",
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bwithout\b",
    r"\bfails?\b",
    r"\bfailure\b",
    r"\binvalid\b",
    r"\bno longer\b",
    r"\bdoes not\b",
    r"\bdo not\b",
    r"\bdid not\b",
    r"\bwon't\b",
    r"\brejects?\b",
]

# Conditional markers
CONDITION_PATTERNS = [
    (r"\bif\b\s+(.+?)(?:,\s*then|\s+then|,|\s+the system|\s+it)", "if"),
    (r"\botherwise\b\s*,?\s*(.+)", "otherwise"),
    (r"\bunless\b\s+(.+?)(?:,|\s+then)", "unless"),
    (r"\bin case of\b\s+(.+?)(?:,|\s+then)", "in_case_of"),
    (r"\bwhen\b\s+(.+?)(?:,\s*then|\s+then|,|\s+the system|\s+it)", "when"),
    (r"\belse\b\s*,?\s*(.+)", "else"),
]

# Temporal ordering markers
TEMPORAL_MARKERS = [
    ("first", 1),
    ("initially", 1),
    ("start by", 1),
    ("then", 2),
    ("next", 2),
    ("subsequently", 2),
    ("after that", 2),
    ("following this", 2),
    ("before", 0),  # Prior step
    ("after", 2),
    ("finally", 99),
    ("at the end", 99),
]


class PreprocessedClause(BaseModel):
    """Segmented clause with semantic and logical qualifiers."""
    text: str
    clause_index: int
    is_conditional: bool = False
    condition_type: Optional[str] = None  # "if", "otherwise", "unless", "when", etc.
    condition_expr: Optional[str] = None
    is_negated: bool = False
    negation_spans: List[str] = Field(default_factory=list)
    temporal_order: Optional[int] = None
    temporal_marker: Optional[str] = None


class PreprocessedSentence(BaseModel):
    """Sentence breakdown with structural boundaries and detected tokens."""
    sentence_index: int
    raw_text: str
    clean_text: str
    clauses: List[PreprocessedClause] = Field(default_factory=list)
    is_conditional: bool = False
    is_negated: bool = False
    temporal_order: Optional[int] = None


class PreprocessedDocument(BaseModel):
    """Complete preprocessed document container."""
    raw_text: str
    normalized_text: str
    sentences: List[PreprocessedSentence] = Field(default_factory=list)
    preserved_technical_terms: List[str] = Field(default_factory=list)
    word_count: int = 0
    char_count: int = 0
    has_conditions: bool = False
    has_negations: bool = False
    has_loops: bool = False
    warnings: List[str] = Field(default_factory=list)


class TextPreprocessor:
    """Deterministic, production-grade text preprocessor and linguistic segmenter."""

    def __init__(self, technical_terms: Optional[Set[str]] = None):
        self.technical_terms = set(PRESERVED_TECHNICAL_TERMS)
        if technical_terms:
            self.technical_terms.update(technical_terms)
        
        # Build regex for matching technical terms preserving boundaries
        # Sort by descending length so multi-word tokens match before single tokens
        sorted_terms = sorted(self.technical_terms, key=len, reverse=True)
        escaped_terms = [re.escape(t) for t in sorted_terms]
        self._term_pattern = re.compile(r"\b(" + "|".join(escaped_terms) + r")\b", re.IGNORECASE)

    def validate_input(self, text: Any) -> str:
        """
        Validates raw input against length limits, whitespace, and type.
        Raises ValueError for invalid inputs.
        """
        if not isinstance(text, str):
            raise ValueError(f"Input must be a string, got {type(text).__name__}")

        trimmed = text.strip()
        if not trimmed:
            raise ValueError("Input text cannot be empty or pure whitespace.")

        if len(trimmed) < MIN_INPUT_LENGTH:
            raise ValueError(
                f"Input text is too short ({len(trimmed)} chars). Minimum length is {MIN_INPUT_LENGTH} characters."
            )

        if len(trimmed) > MAX_INPUT_LENGTH:
            raise ValueError(
                f"Input text exceeds maximum allowed length ({len(trimmed)} > {MAX_INPUT_LENGTH} chars)."
            )

        return trimmed

    def normalize(self, text: str) -> str:
        """
        Normalizes unicode characters, whitespace, newlines, and smart punctuation
        while preserving technical tokens and identifier structure.
        """
        # Unicode normalization (NFKC decomposes compatibility chars while preserving standard chars)
        norm = unicodedata.normalize("NFKC", text)

        # Smart quotes and dashes normalization
        norm = norm.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        norm = norm.replace("—", " - ").replace("–", " - ").replace("…", "...")

        # Normalize multiple spaces, tabs, and carriage returns
        norm = re.sub(r"[ \t]+", " ", norm)
        norm = re.sub(r"\r\n|\r", "\n", norm)
        norm = re.sub(r"\n+", " ", norm)

        # Fix spacing around punctuation without breaking version numbers like '2.0.0' or 'Node.js'
        norm = re.sub(r"\s+([,;:])", r"\1", norm)
        norm = norm.strip()

        return norm

    def segment_sentences(self, text: str) -> List[str]:
        """
        Segments text into sentences while respecting common technical abbreviations
        (e.g., 'e.g.', 'i.e.', 'etc.', 'vs.', 'v1.0', 'Node.js').
        """
        # Protect common abbreviations and technical terms containing dots
        protected = text
        dots_map = {
            "Node.js": "Node__DOT__js",
            "Next.js": "Next__DOT__js",
            "Nuxt.js": "Nuxt__DOT__js",
            "Vue.js": "Vue__DOT__js",
            "e.g.": "e__DOT__g__DOT__",
            "i.e.": "i__DOT__e__DOT__",
            "etc.": "etc__DOT__",
            "vs.": "vs__DOT__",
            "approx.": "approx__DOT__",
            "dept.": "dept__DOT__",
            "fig.": "fig__DOT__",
        }
        for orig, safe in dots_map.items():
            protected = re.sub(re.escape(orig), safe, protected, flags=re.IGNORECASE)

        # Protect decimal numbers e.g. 3.14 or 1.0
        protected = re.sub(r"(\d+)\.(\d+)", r"\1__DECIMAL__\2", protected)

        # Split on sentence boundaries: period, question mark, exclamation, or semicolon
        raw_sentences = re.split(r"(?<=[.?!;])\s+(?=[A-Z0-9\"'])", protected)

        sentences = []
        for s in raw_sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            # Restore dots
            for orig, safe in dots_map.items():
                s_clean = re.sub(re.escape(safe), orig, s_clean, flags=re.IGNORECASE)
            s_clean = re.sub(r"__DECIMAL__", ".", s_clean)
            sentences.append(s_clean)

        return sentences

    def detect_negations(self, text: str) -> Tuple[bool, List[str]]:
        """Identifies negation patterns and returns whether text is negated and matching spans."""
        spans = []
        for pat in NEGATION_PATTERNS:
            matches = re.findall(pat, text, flags=re.IGNORECASE)
            if matches:
                spans.extend(matches)
        return len(spans) > 0, spans

    def detect_conditions(self, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Detects if text contains conditional structure ('if', 'otherwise', 'unless', etc.).
        Returns (is_conditional, condition_type, condition_expression).
        """
        text_lower = text.lower()
        for pat, cond_type in CONDITION_PATTERNS:
            match = re.search(pat, text, flags=re.IGNORECASE)
            if match:
                expr = match.group(1).strip() if match.groups() else ""
                return True, cond_type, expr

        # Direct keyword checks
        if text_lower.startswith("if ") or " if " in text_lower:
            return True, "if", text
        if text_lower.startswith("otherwise") or "otherwise" in text_lower:
            return True, "otherwise", text
        if text_lower.startswith("unless") or "unless" in text_lower:
            return True, "unless", text

        return False, None, None

    def detect_temporal_order(self, text: str) -> Tuple[Optional[int], Optional[str]]:
        """Detects temporal ordering markers ('first', 'then', 'finally', etc.)."""
        text_lower = text.lower()
        for marker, order in TEMPORAL_MARKERS:
            # Match whole word
            if re.search(r"\b" + re.escape(marker) + r"\b", text_lower):
                return order, marker
        return None, None

    def detect_loop_indicators(self, text: str) -> bool:
        """Detects iterative loop / retry indicators ('loop', 'repeat', 'retry', 'cycles back')."""
        loop_patterns = [
            r"\bloops?\s+(?:back|again)\b",
            r"\brepeats?\b",
            r"\bretry\b",
            r"\bretrie?s\b",
            r"\bcycles?\s+back\b",
            r"\buntil\b",
            r"\bwhile\b",
            r"\bprompts\s+(?:the\s+)?user\s+to\s+re-enter\b",
        ]
        return any(re.search(pat, text, flags=re.IGNORECASE) for pat in loop_patterns)

    def segment_clauses(self, sentence: str) -> List[PreprocessedClause]:
        """
        Splits a compound or complex sentence into coherent grammatical clauses
        based on conditional, coordinating, and causal connectors.
        """
        # Clause delimiters: semicolons, 'if ..., then ...', 'otherwise', 'and then', etc.
        # We split while preserving conditional markers
        clauses = []
        raw_parts = re.split(r";|\botherwise\b|\belse\b|,\s*then\b|,\s*if\b|\band then\b", sentence, flags=re.IGNORECASE)

        idx = 0
        for part in raw_parts:
            part_str = part.strip()
            if not part_str:
                continue

            is_neg, neg_spans = self.detect_negations(part_str)
            is_cond, cond_type, cond_expr = self.detect_conditions(part_str)
            temp_order, temp_marker = self.detect_temporal_order(part_str)

            clause = PreprocessedClause(
                text=part_str,
                clause_index=idx,
                is_conditional=is_cond,
                condition_type=cond_type,
                condition_expr=cond_expr,
                is_negated=is_neg,
                negation_spans=neg_spans,
                temporal_order=temp_order,
                temporal_marker=temp_marker,
            )
            clauses.append(clause)
            idx += 1

        if not clauses:
            is_neg, neg_spans = self.detect_negations(sentence)
            is_cond, cond_type, cond_expr = self.detect_conditions(sentence)
            temp_order, temp_marker = self.detect_temporal_order(sentence)
            clauses.append(
                PreprocessedClause(
                    text=sentence,
                    clause_index=0,
                    is_conditional=is_cond,
                    condition_type=cond_type,
                    condition_expr=cond_expr,
                    is_negated=is_neg,
                    negation_spans=neg_spans,
                    temporal_order=temp_order,
                    temporal_marker=temp_marker,
                )
            )

        return clauses

    def find_technical_terms(self, text: str) -> List[str]:
        """Extracts all recognized technical entities and frameworks from the text."""
        matches = self._term_pattern.findall(text)
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for m in matches:
            canonical = m.strip()
            # Normalize casing to canonical form
            for known in self.technical_terms:
                if known.lower() == canonical.lower():
                    canonical = known
                    break
            if canonical.lower() not in seen:
                seen.add(canonical.lower())
                deduped.append(canonical)
        return deduped

    def preprocess(self, text: str) -> PreprocessedDocument:
        """
        Main entry point for full text preprocessing pipeline.
        """
        validated = self.validate_input(text)
        normalized = self.normalize(validated)
        raw_sentences = self.segment_sentences(normalized)

        processed_sentences = []
        has_conditions = False
        has_negations = False
        has_loops = self.detect_loop_indicators(normalized)
        warnings = []

        global_order = 1
        for s_idx, s_text in enumerate(raw_sentences):
            clauses = self.segment_clauses(s_text)
            s_is_cond = any(c.is_conditional for c in clauses)
            s_is_neg = any(c.is_negated for c in clauses)

            if s_is_cond:
                has_conditions = True
            if s_is_neg:
                has_negations = True

            sent = PreprocessedSentence(
                sentence_index=s_idx,
                raw_text=s_text,
                clean_text=s_text,
                clauses=clauses,
                is_conditional=s_is_cond,
                is_negated=s_is_neg,
                temporal_order=global_order,
            )
            processed_sentences.append(sent)
            global_order += 1

        technical_terms = self.find_technical_terms(normalized)

        words = normalized.split()
        word_count = len(words)
        char_count = len(normalized)

        # Ambiguity heuristics
        if word_count < 4:
            warnings.append("Very short description; input may lack sufficient relationships to produce a complete diagram.")

        return PreprocessedDocument(
            raw_text=text,
            normalized_text=normalized,
            sentences=processed_sentences,
            preserved_technical_terms=technical_terms,
            word_count=word_count,
            char_count=char_count,
            has_conditions=has_conditions,
            has_negations=has_negations,
            has_loops=has_loops,
            warnings=warnings,
        )


def preprocess_text(text: str) -> PreprocessedDocument:
    """Convenience helper function for text preprocessing."""
    preprocessor = TextPreprocessor()
    return preprocessor.preprocess(text)
