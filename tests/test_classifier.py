"""
Automated Test Suite for Phase 4 — Supervised Diagram Classifier.
Tests training, model serialization, artifact loading, predictions for all 7 classes,
input edge cases, corrupted/missing artifact fallbacks, user overrides, and pipeline integration.
"""

import json
import tempfile
from pathlib import Path
import pytest
import joblib

from ir.models import DiagramType
from ir.validators import validate_diagram
from nlp.classifier_interface import (
    TfidfLogisticRegressionClassifier,
    HeuristicDiagramClassifier,
    ClassificationResult,
    load_trained_classifier,
    get_default_classifier,
    set_default_classifier,
)
from nlp.pipeline import generate_diagram
from training.train_classifier import train_and_evaluate


MODELS_DIR = Path(__file__).parent.parent / "models"
DATA_SPLITS_DIR = Path(__file__).parent.parent / "data" / "splits"


# ============================================================================
# 1. MODEL ARTIFACT AND SERIALIZATION TESTS
# ============================================================================

def test_model_artifact_exists_and_loads():
    """Verify serialized model artifact and metadata exist and load correctly."""
    artifact_path = MODELS_DIR / "diagram_classifier.joblib"
    metadata_path = MODELS_DIR / "classifier_metadata.json"

    assert artifact_path.exists(), f"Model artifact not found at {artifact_path}"
    assert metadata_path.exists(), f"Metadata not found at {metadata_path}"

    model = joblib.load(artifact_path)
    assert hasattr(model, "predict"), "Model must have a predict method"
    assert hasattr(model, "predict_proba"), "Model must have a predict_proba method"

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["model_version"] == "tfidf-logreg-v1.0"
    assert len(meta["classes"]) == 7
    assert meta["metrics"]["logistic_regression"]["test_accuracy"] >= 0.85


def test_loading_trained_classifier_wrapper():
    """Verify TfidfLogisticRegressionClassifier wrapper initializes properly."""
    clf = TfidfLogisticRegressionClassifier()
    assert clf.model_version == "tfidf-logreg-v1.0"
    assert len(clf.classes_) == 7
    assert "architecture" in clf.classes_
    assert "flowchart" in clf.classes_


# ============================================================================
# 2. PREDICTION ACROSS ALL 7 SUPPORTED CLASSES
# ============================================================================

def test_predictions_for_all_supported_classes():
    """Verify predictions across each of the 7 diagram types using held-out test data."""
    test_split_path = DATA_SPLITS_DIR / "test.json"
    assert test_split_path.exists(), "test.json must exist"

    with open(test_split_path, "r", encoding="utf-8") as f:
        test_samples = json.load(f)

    clf = TfidfLogisticRegressionClassifier()

    # Find one representative test sample per diagram family
    samples_per_class = {}
    for s in test_samples:
        dtype = s["diagram_type"]
        if dtype not in samples_per_class:
            samples_per_class[dtype] = s

    assert len(samples_per_class) == 7

    for expected_dtype, sample in samples_per_class.items():
        res = clf.predict(sample["text"])
        assert isinstance(res, ClassificationResult)
        assert isinstance(res.diagram_type, DiagramType)
        assert res.confidence >= 0.0 and res.confidence <= 1.0
        assert res.is_fallback is False
        assert sum(res.probabilities.values()) == pytest.approx(1.0, 0.05)
        # Verify prediction matches the ground truth test sample
        assert res.diagram_type.value == expected_dtype


# ============================================================================
# 3. INPUT EDGE CASES AND UNCERTAINTY
# ============================================================================

def test_invalid_and_empty_inputs():
    """Verify handling of empty strings, pure whitespace, and very short inputs."""
    clf = TfidfLogisticRegressionClassifier()

    # Empty string produces uniform distribution without crashing
    res_empty = clf.predict("")
    assert isinstance(res_empty, ClassificationResult)
    for p in res_empty.probabilities.values():
        assert p == pytest.approx(1.0 / 7, 0.05)

    # Whitespace produces uniform distribution
    res_ws = clf.predict("    \n\t  ")
    assert isinstance(res_ws, ClassificationResult)
    assert res_ws.confidence == pytest.approx(1.0 / 7, 0.05)


def test_missing_or_corrupted_model_artifacts():
    """Verify proper error handling and fallback when artifacts are missing or corrupted."""
    # 1. Non-existent path raises FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Trained model artifact not found"):
        TfidfLogisticRegressionClassifier(model_path="nonexistent_model.joblib")

    # 2. Corrupted file raises RuntimeError
    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
        tmp.write(b"NOT A VALID JOBLIB FILE")
        corrupted_path = Path(tmp.name)

    try:
        with pytest.raises(RuntimeError, match="Corrupted or invalid model artifact"):
            TfidfLogisticRegressionClassifier(model_path=corrupted_path)

        # 3. load_trained_classifier cleanly falls back to Heuristic classifier
        fb_clf = load_trained_classifier(model_path=corrupted_path, fallback_to_heuristic=True)
        assert isinstance(fb_clf, HeuristicDiagramClassifier)
    finally:
        if corrupted_path.exists():
            corrupted_path.unlink()


# ============================================================================
# 4. EXPLICIT OVERRIDES AND PIPELINE INTEGRATION
# ============================================================================

def test_explicit_diagram_type_override():
    """Verify that an explicitly passed diagram_type takes precedence over ML prediction."""
    text = "Visual model required: Cloud microservices communicating via Kong API gateway to PostgreSQL."
    # Even if ML would predict architecture, user forces sequence_diagram
    graph = generate_diagram(text, diagram_type=DiagramType.SEQUENCE_DIAGRAM)
    assert graph.diagram_type == DiagramType.SEQUENCE_DIAGRAM

    # String override
    graph_str = generate_diagram(text, diagram_type="flowchart")
    assert graph_str.diagram_type == DiagramType.FLOWCHART


def test_classifier_automatic_integration_with_generate_diagram():
    """Verify generate_diagram() uses the trained ML classifier when diagram_type is None."""
    # Use a held-out test sample text
    test_split_path = DATA_SPLITS_DIR / "test.json"
    with open(test_split_path, "r", encoding="utf-8") as f:
        test_samples = json.load(f)

    # Pick a network topology sample
    net_sample = next(s for s in test_samples if s["diagram_type"] == "network_topology")
    graph = generate_diagram(net_sample["text"], diagram_type=None)

    assert graph.diagram_type == DiagramType.NETWORK_TOPOLOGY
    assert graph.metadata.domain == "network_topology"

    report = validate_diagram(graph)
    assert report.is_valid


# ============================================================================
# 5. REPRODUCIBILITY AND BASELINE COMPARISON
# ============================================================================

def test_training_reproducibility():
    """Verify that training pipeline runs reproducibly and yields identical metrics with fixed seed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_models = Path(tmp_dir)
        meta = train_and_evaluate(
            data_dir=DATA_SPLITS_DIR,
            models_dir=tmp_models,
            seed=42,
            verbose=False
        )

        assert meta["random_seed"] == 42
        assert (tmp_models / "diagram_classifier.joblib").exists()
        assert (tmp_models / "classifier_metadata.json").exists()

        # Dummy baseline accuracy should be strictly 16/136 ~= 11.76%
        assert meta["metrics"]["dummy_baseline"]["test_accuracy"] == pytest.approx(0.1176, 0.01)

        # Trained Logistic Regression should drastically outperform Dummy baseline
        lr_acc = meta["metrics"]["logistic_regression"]["test_accuracy"]
        dummy_acc = meta["metrics"]["dummy_baseline"]["test_accuracy"]
        assert lr_acc > dummy_acc * 5.0
        assert lr_acc == 1.0000
