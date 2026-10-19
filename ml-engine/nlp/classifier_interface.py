"""
Diagram-Type Classification Interface & Provisional Heuristic Engine.
Defines the abstract interface for diagram family classification, allowing
seamless drop-in integration of Phase 4's trained TF-IDF + Logistic Regression model
while providing an explainable, deterministic heuristic classifier for Phase 3.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import re
from pydantic import BaseModel, Field

from ir.models import DiagramType


class ClassificationResult(BaseModel):
    """Encapsulates the classification outcome with confidence and explainability metadata."""
    diagram_type: DiagramType
    confidence: float = Field(ge=0.0, le=1.0)
    is_fallback: bool = True  # True for provisional Phase 3 rule classifier, False once Phase 4 ML model is plugged in
    model_version: str = "heuristic-v1.0"
    explanation: str
    probabilities: Dict[str, float] = Field(default_factory=dict)
    matched_indicators: List[str] = Field(default_factory=list)


class DiagramClassifier(ABC):
    """
    Abstract Base Class for Diagram-Type Classifiers.
    All classification models (both Phase 3 heuristic and Phase 4 supervised ML)
    must adhere to this contract.
    """

    @abstractmethod
    def predict(self, text: str) -> ClassificationResult:
        """Predicts the most probable DiagramType for the given text description."""
        pass

    @abstractmethod
    def predict_proba(self, text: str) -> Dict[str, float]:
        """Returns normalized probability distribution across all supported DiagramTypes."""
        pass


class HeuristicDiagramClassifier(DiagramClassifier):
    """
    Explainable, deterministic heuristic classifier for Phase 3.
    Uses vocabulary indicators and grammatical structures discovered in Phase 1
    (PHASE1_RESEARCH_REPORT.md) across all 7 diagram families.
    
    NOTE: This is the Phase 3 provisional engine. Phase 4 will introduce
    the fully trained scikit-learn TF-IDF + Logistic Regression pipeline.
    """

    # Domain-specific indicative keywords and phrases
    INDICATOR_LEXICON: Dict[DiagramType, List[Tuple[str, float]]] = {
        DiagramType.FLOWCHART: [
            ("if", 1.5), ("otherwise", 2.0), ("then", 1.2), ("decision", 2.5),
            ("start", 1.5), ("finish", 1.5), ("ends", 1.5), ("process", 1.2),
            ("loop", 2.0), ("retry", 2.0), ("repeat", 2.0), ("prompts user", 2.0),
            ("step", 1.2), ("redirects to", 1.5), ("workflow", 2.0), ("branch", 2.0),
            ("credentials valid", 2.5), ("lock account", 2.0), ("evaluate", 1.5),
        ],
        DiagramType.ARCHITECTURE: [
            ("architecture", 3.0), ("microservice", 3.0), ("frontend", 2.5),
            ("backend", 2.5), ("api gateway", 3.0), ("rest api", 2.5),
            ("database", 2.0), ("cache", 2.5), ("redis", 3.0), ("mongodb", 3.0),
            ("postgresql", 3.0), ("mysql", 2.5), ("kafka", 3.0), ("server", 1.5),
            ("client", 1.8), ("cloud", 2.0), ("docker", 2.5), ("kubernetes", 3.0),
            ("load balancer", 3.0), ("service", 1.5), ("payment gateway", 2.5),
            ("component", 1.5), ("tier", 2.0), ("http", 1.5), ("grpc", 2.5),
        ],
        DiagramType.CONCEPT_MAP: [
            ("concept", 3.0), ("concept map", 3.5), ("is a", 2.5), ("type of", 2.5),
            ("consists of", 2.5), ("classified as", 3.0), ("subdivided", 2.5),
            ("category", 2.0), ("data structure", 2.5), ("array", 2.0),
            ("linked list", 2.5), ("stack", 2.0), ("queue", 2.0), ("tree", 2.0),
            ("binary search tree", 3.0), ("graph", 1.8), ("linear", 2.0),
            ("non-linear", 2.0), ("hierarchical", 2.5), ("relates to", 2.0),
            ("properties", 1.5), ("stores elements", 2.0),
        ],
        DiagramType.ER_DIAGRAM: [
            ("entity", 3.0), ("er diagram", 3.5), ("entity-relationship", 3.5),
            ("primary key", 3.5), ("foreign key", 3.5), ("attribute", 2.5),
            ("one-to-many", 3.5), ("many-to-many", 3.5), ("one-to-one", 3.5),
            ("1:n", 3.5), ("m:n", 3.5), ("1:1", 3.5), ("cardinality", 3.0),
            ("table", 2.0), ("schema", 2.5), ("relation", 2.0),
            ("student", 1.8), ("course", 1.8), ("department", 1.8), ("enrolls", 2.0),
        ],
        DiagramType.SEQUENCE_DIAGRAM: [
            ("sequence", 3.0), ("sequence diagram", 3.5), ("participant", 3.0),
            ("lifeline", 3.5), ("sends request", 3.0), ("responds with", 3.0),
            ("acknowledges", 2.5), ("returns response", 3.0), ("synchronous", 2.5),
            ("interaction", 2.0), ("calls method", 2.0), ("callback", 2.5),
            ("user submits", 2.0), ("gateway validates", 2.5),
        ],
        DiagramType.NETWORK_TOPOLOGY: [
            ("network", 2.5), ("topology", 3.0), ("switch", 3.0), ("router", 3.0),
            ("firewall", 3.0), ("subnet", 3.0), ("lan", 3.0), ("wan", 3.0),
            ("vlan", 3.0), ("workstation", 3.0), ("ip address", 3.0),
            ("internet", 2.5), ("ethernet", 3.0), ("access point", 3.0),
            ("devices", 2.0), ("connected via", 1.8),
        ],
        DiagramType.DEPENDENCY_GRAPH: [
            ("dependency", 3.0), ("depends on", 3.5), ("prerequisite", 3.5),
            ("blocked by", 3.5), ("task", 2.5), ("milestone", 3.0),
            ("build step", 3.0), ("parallel tasks", 3.5), ("pipeline", 2.0),
            ("precedes", 2.5), ("dag", 3.0), ("compilation", 2.5),
        ],
    }

    def __init__(self):
        # Precompile regex patterns for fast matching
        self._compiled_patterns: Dict[DiagramType, List[Tuple[re.Pattern, float, str]]] = {}
        for dtype, indicators in self.INDICATOR_LEXICON.items():
            patterns = []
            for phrase, weight in indicators:
                pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
                patterns.append((pat, weight, phrase))
            self._compiled_patterns[dtype] = patterns

    def predict_proba(self, text: str) -> Dict[str, float]:
        """Calculates normalized score distribution across all diagram types."""
        scores: Dict[DiagramType, float] = {dtype: 0.1 for dtype in DiagramType}

        for dtype, patterns in self._compiled_patterns.items():
            for pat, weight, _ in patterns:
                matches = pat.findall(text)
                if matches:
                    scores[dtype] += weight * len(matches)

        # Normalize to probability distribution
        total = sum(scores.values())
        if total == 0:
            equal_prob = 1.0 / len(DiagramType)
            return {dtype.value: equal_prob for dtype in DiagramType}

        return {dtype.value: round(score / total, 4) for dtype, score in scores.items()}

    def predict(self, text: str) -> ClassificationResult:
        """Determines best diagram type with matched indicators and confidence."""
        scores: Dict[DiagramType, float] = {dtype: 0.1 for dtype in DiagramType}
        matched: Dict[DiagramType, List[str]] = {dtype: [] for dtype in DiagramType}

        for dtype, patterns in self._compiled_patterns.items():
            for pat, weight, phrase in patterns:
                matches = pat.findall(text)
                if matches:
                    scores[dtype] += weight * len(matches)
                    matched[dtype].append(phrase)

        # Find maximum scoring diagram family
        sorted_types = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_type, top_score = sorted_types[0]
        second_type, second_score = sorted_types[1] if len(sorted_types) > 1 else (None, 0.0)

        total = sum(scores.values())
        probs = {dtype.value: round(s / total, 4) for dtype, s in scores.items()}

        # Compute calibrated confidence
        # If top_score dominates second_score, confidence is higher
        if total <= 1.0:
            # Almost no strong keywords matched -> default to flowchart or architecture with low confidence
            confidence = 0.50
            explanation = "Low keyword density detected; provisional assignment based on general structure."
        else:
            margin = (top_score - second_score) / (top_score + 1e-6)
            confidence = min(0.95, max(0.55, round(probs[top_type.value] * 1.5 + margin * 0.2, 2)))
            explanation = (
                f"Selected '{top_type.value}' based on {len(matched[top_type])} indicator terms: "
                f"{', '.join(matched[top_type][:5])}."
            )

        return ClassificationResult(
            diagram_type=top_type,
            confidence=confidence,
            is_fallback=True,
            model_version="heuristic-v1.0-provisional",
            explanation=explanation,
            probabilities=probs,
            matched_indicators=matched[top_type][:10],
        )


class TfidfLogisticRegressionClassifier(DiagramClassifier):
    """
    Supervised Machine Learning Diagram Classifier.
    Uses sublinear TF-IDF word unigrams/bigrams with Multinomial Logistic Regression.
    Trained on template-isolated splits with zero data leakage.
    Provides calibrated probability distributions and confidence scores.
    """

    def __init__(self, model_path: Optional[Any] = None):
        if model_path is None:
            base_dir = Path(__file__).parent.parent.parent
            model_path = base_dir / "models" / "diagram_classifier.joblib"

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Trained model artifact not found at '{self.model_path}'. "
                "Run 'python ml-engine/training/train_classifier.py' to produce the artifact."
            )

        try:
            import joblib
            self.model = joblib.load(self.model_path)
        except Exception as e:
            raise RuntimeError(f"Corrupted or invalid model artifact at '{self.model_path}': {e}")

        self.classes_ = list(self.model.classes_)
        self.model_version = "tfidf-logreg-v1.0"

    def predict_proba(self, text: str) -> Dict[str, float]:
        """Returns class probabilities using the trained model pipeline."""
        if not text or not text.strip():
            equal = round(1.0 / len(self.classes_), 4)
            return {c: equal for c in self.classes_}

        clean = text.strip()
        probs = self.model.predict_proba([clean])[0]
        return {c: round(float(p), 4) for c, p in zip(self.classes_, probs)}

    def predict(self, text: str) -> ClassificationResult:
        """Predicts the diagram family with calibrated confidence score."""
        probs = self.predict_proba(text)
        sorted_probs = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        top_class_str, top_prob = sorted_probs[0]

        try:
            diagram_type = DiagramType(top_class_str)
        except ValueError:
            diagram_type = DiagramType.FLOWCHART

        explanation = (
            f"Supervised ML model ({self.model_version}) predicted '{diagram_type.value}' "
            f"with {top_prob*100:.1f}% confidence."
        )

        return ClassificationResult(
            diagram_type=diagram_type,
            confidence=top_prob,
            is_fallback=False,
            model_version=self.model_version,
            explanation=explanation,
            probabilities=probs,
            matched_indicators=[],
        )


def load_trained_classifier(
    model_path: Optional[Any] = None,
    fallback_to_heuristic: bool = True
) -> DiagramClassifier:
    """
    Loads the trained ML classifier from disk.
    If the artifact is missing/corrupted and fallback_to_heuristic is True,
    falls back cleanly to HeuristicDiagramClassifier.
    """
    try:
        return TfidfLogisticRegressionClassifier(model_path=model_path)
    except (FileNotFoundError, RuntimeError):
        if fallback_to_heuristic:
            return HeuristicDiagramClassifier()
        raise


def _init_default_classifier() -> DiagramClassifier:
    """Initializes default classifier: trained ML model if artifact exists, else heuristic."""
    base_dir = Path(__file__).parent.parent.parent
    default_artifact = base_dir / "models" / "diagram_classifier.joblib"
    if default_artifact.exists():
        try:
            return TfidfLogisticRegressionClassifier(model_path=default_artifact)
        except Exception:
            return HeuristicDiagramClassifier()
    return HeuristicDiagramClassifier()


# Global singleton instance registry for clean Phase 4 ML integration
_CURRENT_CLASSIFIER: DiagramClassifier = _init_default_classifier()


def get_default_classifier() -> DiagramClassifier:
    """Returns the currently active diagram classifier."""
    global _CURRENT_CLASSIFIER
    return _CURRENT_CLASSIFIER


def set_default_classifier(classifier: DiagramClassifier) -> None:
    """
    Registers a new classifier.
    Allows dynamic substitution of classifier backends.
    """
    global _CURRENT_CLASSIFIER
    if not isinstance(classifier, DiagramClassifier):
        raise TypeError("Classifier must implement DiagramClassifier interface")
    _CURRENT_CLASSIFIER = classifier

