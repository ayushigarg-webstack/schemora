#!/usr/bin/env python3
"""
AI Diagram Generator — NLP Pipeline, Entity/Relation Extraction & Graph Quality Evaluator.
Evaluates:
1. Entity extraction: Precision, Recall, F1 (Exact & Token-Overlap matching).
2. Relationship extraction: Precision, Recall, F1 (Exact directed & Undirected).
3. Relationship direction accuracy & Label accuracy.
4. Graph semantic validity rate (using ir.validators.validate_diagram).
5. Exact graph match rate.
6. Missing/Extra nodes and edges.
7. Layout metrics: Node bounding box overlaps and edge crossings.
8. Breakdown per diagram family.
"""

import sys
import json
import re
import string
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict

# Add project root and ml-engine to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "ml-engine"))

from ir.models import DiagramGraph, DiagramType
from ir.validators import validate_diagram
from nlp.pipeline import generate_diagram
from layout.engine import DiagramLayoutEngine


def normalize_label(label: str) -> str:
    """Normalize entity/relation label: lowercase, remove punctuation, trim whitespace."""
    if not label:
        return ""
    text = label.lower()
    text = re.sub(r"^\d+\.\s*", "", text)  # remove sequence numbers like "1. "
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = [w for w in text.split() if w not in {"the", "a", "an", "to", "in", "of", "for"}]
    return " ".join(tokens)


def token_jaccard(s1: str, s2: str) -> float:
    t1 = set(s1.split())
    t2 = set(s2.split())
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def match_entities(
    gt_nodes: List[Dict[str, Any]],
    pred_nodes: List[Any],
    match_threshold: float = 0.5
) -> Tuple[Dict[str, str], Set[str], Set[str]]:
    """
    Greedy bipartite matching between GT nodes and predicted nodes.
    Returns:
        gt_to_pred: Dict mapping GT node id -> pred node id
        matched_gt: Set of GT node ids that were matched
        matched_pred: Set of Pred node ids that were matched
    """
    gt_norm = {n["id"]: normalize_label(n.get("label", "")) for n in gt_nodes}
    pred_norm = {n.id: normalize_label(n.label) for n in pred_nodes}
    
    gt_to_pred: Dict[str, str] = {}
    pred_to_gt: Dict[str, str] = {}
    
    # 1. Exact match pass
    for gid, glabel in gt_norm.items():
        if not glabel:
            continue
        for pid, plabel in pred_norm.items():
            if pid in pred_to_gt:
                continue
            if glabel == plabel:
                gt_to_pred[gid] = pid
                pred_to_gt[pid] = gid
                break
                
    # 2. Substring / Token overlap pass for remaining
    for gid, glabel in gt_norm.items():
        if gid in gt_to_pred or not glabel:
            continue
        best_pid = None
        best_sim = 0.0
        for pid, plabel in pred_norm.items():
            if pid in pred_to_gt or not plabel:
                continue
            # Substring match
            if glabel in plabel or plabel in glabel:
                sim = 0.8
            else:
                sim = token_jaccard(glabel, plabel)
                
            if sim >= match_threshold and sim > best_sim:
                best_sim = sim
                best_pid = pid
                
        if best_pid:
            gt_to_pred[gid] = best_pid
            pred_to_gt[best_pid] = gid
            
    return gt_to_pred, set(gt_to_pred.keys()), set(pred_to_gt.keys())


def check_line_intersection(p1, p2, p3, p4) -> bool:
    """Checks if line segment p1-p2 intersects p3-p4 (excluding shared endpoints)."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    # If shared endpoint, not a crossing
    if (x1, y1) in (p3, p4) or (x2, y2) in (p3, p4):
        return False

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))


def evaluate():
    test_path = Path("data/splits/test.json")
    with open(test_path, "r", encoding="utf-8") as f:
        test_samples = json.load(f)
        
    layout_engine = DiagramLayoutEngine()
    
    print("=" * 80)
    print("PHASE 9: NLP EXTRACTION & GRAPH QUALITY EVALUATION")
    print(f"Total Test Samples: {len(test_samples)} across 7 diagram families")
    print("=" * 80)
    
    # Metrics accumulators: global & per-family
    family_metrics = defaultdict(lambda: {
        "count": 0,
        "valid_graphs": 0,
        "exact_graph_matches": 0,
        "gt_nodes_total": 0,
        "pred_nodes_total": 0,
        "matched_nodes_total": 0,
        "gt_edges_total": 0,
        "pred_edges_total": 0,
        "matched_edges_undirected": 0,
        "matched_edges_directed": 0,
        "matched_edges_label_correct": 0,
        "total_warnings": 0,
        "total_errors": 0,
        "overlapping_node_pairs": 0,
        "edge_crossings": 0,
    })
    
    for idx, sample in enumerate(test_samples):
        text = sample["text"]
        gt_type_str = sample["diagram_type"]
        gt_nodes = sample["nodes"]
        gt_edges = sample["edges"]
        
        # Run NLP Pipeline with ground-truth diagram type to isolate extraction from classifier
        pred_graph: DiagramGraph = generate_diagram(text, diagram_type=gt_type_str)
        
        # Apply layout engine to evaluate geometric properties
        laid_out_graph = DiagramLayoutEngine.layout(pred_graph)
        
        # Validate diagram semantically
        val_report = validate_diagram(laid_out_graph)
        
        fam = family_metrics[gt_type_str]
        fam["count"] += 1
        if val_report.is_valid:
            fam["valid_graphs"] += 1
        fam["total_warnings"] += len(val_report.warnings)
        fam["total_errors"] += len(val_report.errors)
        
        # --- Node Matching ---
        gt_to_pred, matched_gt_nodes, matched_pred_nodes = match_entities(gt_nodes, laid_out_graph.nodes)
        pred_to_gt = {v: k for k, v in gt_to_pred.items()}
        
        fam["gt_nodes_total"] += len(gt_nodes)
        fam["pred_nodes_total"] += len(laid_out_graph.nodes)
        fam["matched_nodes_total"] += len(matched_gt_nodes)
        
        # --- Edge Matching ---
        gt_edge_pairs = set()
        gt_edge_directed_map = {}
        for e in gt_edges:
            src = e["source"]
            tgt = e["target"]
            label_norm = normalize_label(e.get("label", ""))
            gt_edge_pairs.add(frozenset([src, tgt]))
            gt_edge_directed_map[(src, tgt)] = label_norm
            
        fam["gt_edges_total"] += len(gt_edges)
        fam["pred_edges_total"] += len(laid_out_graph.edges)
        
        matched_edges_undir = 0
        matched_edges_dir = 0
        matched_edge_labels = 0
        
        # To avoid double counting multiple predicted edges matching the same GT edge
        matched_gt_edges_undir_seen = set()
        matched_gt_edges_dir_seen = set()
        
        for pe in laid_out_graph.edges:
            psrc = pe.source
            ptgt = pe.target
            plabel_norm = normalize_label(pe.label)
            
            # Check if both endpoints were matched to GT nodes
            if psrc in pred_to_gt and ptgt in pred_to_gt:
                gsrc = pred_to_gt[psrc]
                gtgt = pred_to_gt[ptgt]
                
                # Undirected match
                edge_pair = frozenset([gsrc, gtgt])
                if edge_pair in gt_edge_pairs and edge_pair not in matched_gt_edges_undir_seen:
                    matched_gt_edges_undir_seen.add(edge_pair)
                    matched_edges_undir += 1
                    
                # Directed match
                if (gsrc, gtgt) in gt_edge_directed_map and (gsrc, gtgt) not in matched_gt_edges_dir_seen:
                    matched_gt_edges_dir_seen.add((gsrc, gtgt))
                    matched_edges_dir += 1
                    
                    # Label match check
                    gt_label = gt_edge_directed_map[(gsrc, gtgt)]
                    if gt_label and plabel_norm:
                        if gt_label in plabel_norm or plabel_norm in gt_label or token_jaccard(gt_label, plabel_norm) >= 0.3:
                            matched_edge_labels += 1
                    elif not gt_label and not plabel_norm:
                        matched_edge_labels += 1
                        
        fam["matched_edges_undirected"] += matched_edges_undir
        fam["matched_edges_directed"] += matched_edges_dir
        fam["matched_edges_label_correct"] += matched_edge_labels
        
        # Exact Graph Match check
        exact_nodes = (len(gt_nodes) == len(laid_out_graph.nodes) == len(matched_gt_nodes))
        exact_edges = (len(gt_edges) == len(laid_out_graph.edges) == matched_edges_dir)
        if exact_nodes and exact_edges:
            fam["exact_graph_matches"] += 1
            
        # --- Layout Quality Metrics ---
        # 1. Bounding box overlaps
        node_pos = {}
        for n in laid_out_graph.nodes:
            pos = n.position
            if pos:
                node_pos[n.id] = (pos.x, pos.y, pos.width or 180, pos.height or 80)
                
        overlaps = 0
        node_ids = list(node_pos.keys())
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                x1, y1, w1, h1 = node_pos[node_ids[i]]
                x2, y2, w2, h2 = node_pos[node_ids[j]]
                if abs(x1 - x2) < (w1 + w2) / 2 and abs(y1 - y2) < (h1 + h2) / 2:
                    overlaps += 1
        fam["overlapping_node_pairs"] += overlaps
        
        # 2. Edge crossings
        crossings = 0
        edge_segments = []
        for e in laid_out_graph.edges:
            if e.source in node_pos and e.target in node_pos:
                p_src = (node_pos[e.source][0], node_pos[e.source][1])
                p_tgt = (node_pos[e.target][0], node_pos[e.target][1])
                edge_segments.append((p_src, p_tgt))
                
        for i in range(len(edge_segments)):
            for j in range(i + 1, len(edge_segments)):
                if check_line_intersection(edge_segments[i][0], edge_segments[i][1], edge_segments[j][0], edge_segments[j][1]):
                    crossings += 1
        fam["edge_crossings"] += crossings
        
    # --- Aggregation and Printing ---
    print("\n" + "=" * 80)
    print("RESULTS BY DIAGRAM FAMILY")
    print("=" * 80)
    
    total_samples = 0
    tot_gt_nodes = 0
    tot_pred_nodes = 0
    tot_matched_nodes = 0
    tot_gt_edges = 0
    tot_pred_edges = 0
    tot_matched_edges_undir = 0
    tot_matched_edges_dir = 0
    tot_matched_edge_labels = 0
    tot_valid_graphs = 0
    tot_exact_matches = 0
    tot_overlaps = 0
    tot_crossings = 0
    
    report_rows = []
    
    for fam_name in sorted(family_metrics.keys()):
        m = family_metrics[fam_name]
        cnt = m["count"]
        total_samples += cnt
        
        # Entity metrics
        n_p = m["matched_nodes_total"] / m["pred_nodes_total"] if m["pred_nodes_total"] else 0
        n_r = m["matched_nodes_total"] / m["gt_nodes_total"] if m["gt_nodes_total"] else 0
        n_f1 = (2 * n_p * n_r) / (n_p + n_r) if (n_p + n_r) else 0
        
        # Edge metrics (Directed)
        e_p = m["matched_edges_directed"] / m["pred_edges_total"] if m["pred_edges_total"] else 0
        e_r = m["matched_edges_directed"] / m["gt_edges_total"] if m["gt_edges_total"] else 0
        e_f1 = (2 * e_p * e_r) / (e_p + e_r) if (e_p + e_r) else 0
        
        # Edge direction accuracy (given undirected match)
        dir_acc = m["matched_edges_directed"] / m["matched_edges_undirected"] if m["matched_edges_undirected"] else 0
        # Edge label accuracy (given directed match)
        lbl_acc = m["matched_edges_label_correct"] / m["matched_edges_directed"] if m["matched_edges_directed"] else 0
        
        valid_rate = m["valid_graphs"] / cnt
        exact_rate = m["exact_graph_matches"] / cnt
        
        tot_gt_nodes += m["gt_nodes_total"]
        tot_pred_nodes += m["pred_nodes_total"]
        tot_matched_nodes += m["matched_nodes_total"]
        tot_gt_edges += m["gt_edges_total"]
        tot_pred_edges += m["pred_edges_total"]
        tot_matched_edges_undir += m["matched_edges_undirected"]
        tot_matched_edges_dir += m["matched_edges_directed"]
        tot_matched_edge_labels += m["matched_edges_label_correct"]
        tot_valid_graphs += m["valid_graphs"]
        tot_exact_matches += m["exact_graph_matches"]
        tot_overlaps += m["overlapping_node_pairs"]
        tot_crossings += m["edge_crossings"]
        
        report_rows.append({
            "family": fam_name,
            "samples": cnt,
            "node_p": n_p, "node_r": n_r, "node_f1": n_f1,
            "edge_p": e_p, "edge_r": e_r, "edge_f1": e_f1,
            "dir_acc": dir_acc, "lbl_acc": lbl_acc,
            "valid_rate": valid_rate, "exact_rate": exact_rate,
            "overlaps": m["overlapping_node_pairs"],
            "crossings": m["edge_crossings"],
        })
        
        print(f"[{fam_name.upper()}] (N={cnt})")
        print(f"  - Entity (Node) Extr:  Prec={n_p:.3f}, Rec={n_r:.3f}, F1={n_f1:.3f} (GT={m['gt_nodes_total']}, Pred={m['pred_nodes_total']})")
        print(f"  - Relation Extr (Dir): Prec={e_p:.3f}, Rec={e_r:.3f}, F1={e_f1:.3f} (GT={m['gt_edges_total']}, Pred={m['pred_edges_total']})")
        print(f"  - Edge Direction Acc:  {dir_acc*100:.1f}% ({m['matched_edges_directed']} / {m['matched_edges_undirected']})")
        print(f"  - Edge Label Acc:      {lbl_acc*100:.1f}% ({m['matched_edges_label_correct']} / {m['matched_edges_directed']})")
        print(f"  - Semantic Validity:   {valid_rate*100:.1f}% ({m['valid_graphs']} / {cnt})")
        print(f"  - Exact Graph Match:   {exact_rate*100:.1f}% ({m['exact_graph_matches']} / {cnt})")
        print(f"  - Layout Overlaps:     {m['overlapping_node_pairs']} total")
        print(f"  - Edge Crossings:      {m['edge_crossings']} total")
        print("-" * 60)
        
    # Global metrics
    overall_n_p = tot_matched_nodes / tot_pred_nodes if tot_pred_nodes else 0
    overall_n_r = tot_matched_nodes / tot_gt_nodes if tot_gt_nodes else 0
    overall_n_f1 = (2 * overall_n_p * overall_n_r) / (overall_n_p + overall_n_r) if (overall_n_p + overall_n_r) else 0
    
    overall_e_p = tot_matched_edges_dir / tot_pred_edges if tot_pred_edges else 0
    overall_e_r = tot_matched_edges_dir / tot_gt_edges if tot_gt_edges else 0
    overall_e_f1 = (2 * overall_e_p * overall_e_r) / (overall_e_p + overall_e_r) if (overall_e_p + overall_e_r) else 0
    
    overall_dir_acc = tot_matched_edges_dir / tot_matched_edges_undir if tot_matched_edges_undir else 0
    overall_lbl_acc = tot_matched_edge_labels / tot_matched_edges_dir if tot_matched_edges_dir else 0
    overall_valid_rate = tot_valid_graphs / total_samples
    overall_exact_rate = tot_exact_matches / total_samples
    
    print("\n" + "=" * 80)
    print("OVERALL HELD-OUT TEST SUMMARY (N=136)")
    print("=" * 80)
    print(f"Entity Precision / Recall / F1:     {overall_n_p:.4f} / {overall_n_r:.4f} / {overall_n_f1:.4f}")
    print(f"Relationship Prec / Recall / F1:   {overall_e_p:.4f} / {overall_e_r:.4f} / {overall_e_f1:.4f}")
    print(f"Relationship Direction Accuracy:    {overall_dir_acc*100:.2f}% ({tot_matched_edges_dir}/{tot_matched_edges_undir})")
    print(f"Relationship Label Accuracy:        {overall_lbl_acc*100:.2f}% ({tot_matched_edge_labels}/{tot_matched_edges_dir})")
    print(f"Diagram Semantic Validity Rate:     {overall_valid_rate*100:.2f}% ({tot_valid_graphs}/{total_samples})")
    print(f"Exact Graph Match Rate:             {overall_exact_rate*100:.2f}% ({tot_exact_matches}/{total_samples})")
    print(f"Layout Node Bounding Box Overlaps:  {tot_overlaps} total ({tot_overlaps/total_samples:.2f}/diagram)")
    print(f"Layout Edge Crossings:              {tot_crossings} total ({tot_crossings/total_samples:.2f}/diagram)")
    print("=" * 80)
    
    eval_output = {
        "overall": {
            "total_samples": total_samples,
            "entity_precision": round(overall_n_p, 4),
            "entity_recall": round(overall_n_r, 4),
            "entity_f1": round(overall_n_f1, 4),
            "relation_precision": round(overall_e_p, 4),
            "relation_recall": round(overall_e_r, 4),
            "relation_f1": round(overall_e_f1, 4),
            "direction_accuracy": round(overall_dir_acc, 4),
            "label_accuracy": round(overall_lbl_acc, 4),
            "semantic_validity_rate": round(overall_valid_rate, 4),
            "exact_graph_match_rate": round(overall_exact_rate, 4),
            "total_overlaps": tot_overlaps,
            "total_crossings": tot_crossings,
        },
        "per_family": report_rows,
    }
    
    out_file = Path("research/nlp_graph_eval_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(eval_output, f, indent=2)
    print(f"[+] Saved evaluation results to {out_file}\n")


if __name__ == "__main__":
    evaluate()
