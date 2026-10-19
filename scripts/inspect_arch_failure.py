#!/usr/bin/env python3
import json
from pathlib import Path
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "ml-engine")
from nlp.pipeline import generate_diagram

with open("data/splits/test.json", "r", encoding="utf-8") as f:
    test_samples = json.load(f)

for s in test_samples:
    if s["metadata"]["template_id"] == "arch_realtime_iot_telemetry":
        print("SAMPLE ID:", s["id"])
        print("TEXT:", s["text"])
        print("GT NODES:", [n["label"] for n in s["nodes"]])
        print("GT EDGES:", [(e["source"], e["target"], e.get("label"), e.get("edge_type")) for e in s["edges"]])
        pred = generate_diagram(s["text"], diagram_type=s["diagram_type"])
        print("PRED NODES:", [n.label for n in pred.nodes])
        print("PRED EDGES:", [(e.source, e.target, e.label, e.type) for e in pred.edges])
        break
