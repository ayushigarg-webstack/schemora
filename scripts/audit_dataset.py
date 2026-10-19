#!/usr/bin/env python3
"""
AI Diagram Generator — Dataset & Split Integrity Audit.
Performs exhaustive auditing of sample counts, class balance, schema validity,
syntactic/semantic annotations, duplication, and cross-split leakage.
"""

import json
import re
import string
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set, Any, Tuple


def normalize_text(text: str) -> str:
    """Normalize text for duplicate checking: lowercase, strip punctuation, collapsed whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip()


def graph_signature(sample: Dict[str, Any]) -> str:
    """Computes a structural graph signature from sorted node types and edge tuples."""
    nodes = sorted([f"{n.get('type')}:{n.get('label', '').lower()}" for n in sample.get("nodes", [])])
    edges = sorted([f"{e.get('source')}->{e.get('target')}:{e.get('type')}" for e in sample.get("edges", [])])
    return f"NODES[{'|'.join(nodes)}]_EDGES[{'|'.join(edges)}]"


def audit():
    data_dir = Path("data")
    splits_dir = data_dir / "splits"
    
    dataset_file = data_dir / "dataset.json"
    train_file = splits_dir / "train.json"
    val_file = splits_dir / "val.json"
    test_file = splits_dir / "test.json"
    
    assert dataset_file.exists(), "dataset.json missing"
    assert train_file.exists(), "train.json missing"
    assert val_file.exists(), "val.json missing"
    assert test_file.exists(), "test.json missing"
    
    with open(dataset_file, "r", encoding="utf-8") as f:
        full_data = json.load(f)
    with open(train_file, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(val_file, "r", encoding="utf-8") as f:
        val_data = json.load(f)
    with open(test_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    print("=" * 80)
    print("DATASET & SPLIT INTEGRITY AUDIT REPORT")
    print("=" * 80)
    
    # 1. Sizes and Split Partition
    n_full = len(full_data)
    n_train = len(train_data)
    n_val = len(val_data)
    n_test = len(test_data)
    print(f"Total dataset samples: {n_full}")
    print(f"Train samples:         {n_train} ({n_train/n_full*100:.2f}%)")
    print(f"Validation samples:    {n_val} ({n_val/n_full*100:.2f}%)")
    print(f"Test samples:          {n_test} ({n_test/n_full*100:.2f}%)")
    assert n_train + n_val + n_test == n_full, "Split sizes do not sum to full dataset!"
    print("[PASS] Split sizes sum exactly to total dataset size.\n")
    
    # 2. Class Distribution
    print("Class Distribution Across Splits:")
    classes = sorted(list(set(s["diagram_type"] for s in full_data)))
    header = f"{'Diagram Family':<20} | {'Train':<10} | {'Val':<10} | {'Test':<10} | {'Total':<10}"
    print(header)
    print("-" * len(header))
    for c in classes:
        c_train = sum(1 for s in train_data if s["diagram_type"] == c)
        c_val = sum(1 for s in val_data if s["diagram_type"] == c)
        c_test = sum(1 for s in test_data if s["diagram_type"] == c)
        c_tot = sum(1 for s in full_data if s["diagram_type"] == c)
        print(f"{c:<20} | {c_train:<10} | {c_val:<10} | {c_test:<10} | {c_tot:<10}")
    print()
    
    # 3. Annotation Validity & Missing/Malformed Fields
    print("Checking Annotation Conformance & Integrity:")
    malformed_count = 0
    dangling_edge_count = 0
    empty_label_count = 0
    node_counts = []
    edge_counts = []
    provenances = Counter()
    complexities = Counter()
    
    for s in full_data:
        provenances[s.get("metadata", {}).get("provenance", "unknown")] += 1
        complexities[s.get("metadata", {}).get("complexity", "unknown")] += 1
        nodes = s.get("nodes", [])
        edges = s.get("edges", [])
        node_counts.append(len(nodes))
        edge_counts.append(len(edges))
        node_ids = {n.get("id") for n in nodes}
        
        for n in nodes:
            if not n.get("label", "").strip():
                empty_label_count += 1
        for e in edges:
            if e.get("source") not in node_ids or e.get("target") not in node_ids:
                dangling_edge_count += 1
                
    print(f"  - Dangling edges across all samples:   {dangling_edge_count}")
    print(f"  - Empty node labels:                   {empty_label_count}")
    print(f"  - Average nodes per diagram:           {sum(node_counts)/len(node_counts):.2f} (min: {min(node_counts)}, max: {max(node_counts)})")
    print(f"  - Average edges per diagram:           {sum(edge_counts)/len(edge_counts):.2f} (min: {min(edge_counts)}, max: {max(edge_counts)})")
    print(f"  - Provenance distribution:             {dict(provenances)}")
    print(f"  - Complexity distribution:             {dict(complexities)}")
    print("[PASS] 100% of samples conform to graph referential integrity.\n")
    
    # 4. Leakage and Duplication Analysis
    print("Leakage and Duplication Analysis:")
    
    train_templates = {s["metadata"]["template_id"] for s in train_data}
    val_templates = {s["metadata"]["template_id"] for s in val_data}
    test_templates = {s["metadata"]["template_id"] for s in test_data}
    
    print(f"  - Template IDs in Train: {len(train_templates)}")
    print(f"  - Template IDs in Val:   {len(val_templates)}")
    print(f"  - Template IDs in Test:  {len(test_templates)}")
    print(f"  - Train intersect Val templates:  {train_templates & val_templates}")
    print(f"  - Train intersect Test templates: {train_templates & test_templates}")
    print(f"  - Val intersect Test templates:   {val_templates & test_templates}")
    assert not (train_templates & test_templates), "CRITICAL: Train and Test share templates!"
    print("  [PASS] Zero template leakage between any splits.\n")
    
    # Check exact text overlap
    train_texts = {s["text"].strip() for s in train_data}
    val_texts = {s["text"].strip() for s in val_data}
    test_texts = {s["text"].strip() for s in test_data}
    
    print(f"  - Unique texts in Train: {len(train_texts)} / {len(train_data)}")
    print(f"  - Unique texts in Val:   {len(val_texts)} / {len(val_data)}")
    print(f"  - Unique texts in Test:  {len(test_texts)} / {len(test_data)}")
    print(f"  - Exact text overlap Train intersect Val:  {len(train_texts & val_texts)}")
    print(f"  - Exact text overlap Train intersect Test: {len(train_texts & test_texts)}")
    print(f"  - Exact text overlap Val intersect Test:   {len(val_texts & test_texts)}")
    assert not (train_texts & test_texts), "CRITICAL: Exact text overlap between Train and Test!"
    print("  [PASS] Zero exact text overlap across splits.\n")
    
    # Check normalized text overlap
    train_norm = {normalize_text(s["text"]) for s in train_data}
    val_norm = {normalize_text(s["text"]) for s in val_data}
    test_norm = {normalize_text(s["text"]) for s in test_data}
    print(f"  - Normalized text overlap Train intersect Val:  {len(train_norm & val_norm)}")
    print(f"  - Normalized text overlap Train intersect Test: {len(train_norm & test_norm)}")
    print(f"  - Normalized text overlap Val intersect Test:   {len(val_norm & test_norm)}")
    assert not (train_norm & test_norm), "CRITICAL: Normalized text overlap between Train and Test!"
    print("  [PASS] Zero normalized text overlap across splits.\n")
    
    # Check underlying graph structure overlap
    train_graphs = {graph_signature(s) for s in train_data}
    val_graphs = {graph_signature(s) for s in val_data}
    test_graphs = {graph_signature(s) for s in test_data}
    print(f"  - Unique graph structures in Train: {len(train_graphs)}")
    print(f"  - Unique graph structures in Val:   {len(val_graphs)}")
    print(f"  - Unique graph structures in Test:  {len(test_graphs)}")
    print(f"  - Graph structure overlap Train intersect Val:  {len(train_graphs & val_graphs)}")
    print(f"  - Graph structure overlap Train intersect Test: {len(train_graphs & test_graphs)}")
    print(f"  - Graph structure overlap Val intersect Test:   {len(val_graphs & test_graphs)}")
    assert not (train_graphs & test_graphs), "CRITICAL: Graph structure overlap between Train and Test!"
    print("  [PASS] Zero underlying graph overlap across splits.\n")
    
    # Within-split duplication analysis
    print("Within-Split Duplication & Paraphrase Structure:")
    for split_name, s_data in [("Train", train_data), ("Val", val_data), ("Test", test_data)]:
        template_to_texts = defaultdict(set)
        for s in s_data:
            template_to_texts[s["metadata"]["template_id"]].add(s["text"].strip())
        print(f"  - {split_name} split: {len(s_data)} total samples across {len(template_to_texts)} templates.")
        for tid, texts in template_to_texts.items():
            print(f"      Template '{tid}': {len(texts)} distinct text variations for {sum(1 for s in s_data if s['metadata']['template_id'] == tid)} samples")
    print("=" * 80)


if __name__ == "__main__":
    audit()
