import json
from collections import Counter

train = json.load(open('data/splits/train.json', encoding='utf-8'))
val = json.load(open('data/splits/val.json', encoding='utf-8'))
test = json.load(open('data/splits/test.json', encoding='utf-8'))

prompt_words = ['ecommerce', 'e-commerce', 'architecture', 'react', 'frontend', 'node.js', 'backend', 'mongodb', 'redis']

print("TRAIN OCCURRENCES:")
for w in prompt_words:
    matches = [s['diagram_type'] for s in train if w in s['text'].lower()]
    c = Counter(matches)
    print(f"  {w:<15}: {len(matches)} total -> {dict(c)}")

print("\nVAL OCCURRENCES:")
for w in prompt_words:
    matches = [s['diagram_type'] for s in val if w in s['text'].lower()]
    c = Counter(matches)
    print(f"  {w:<15}: {len(matches)} total -> {dict(c)}")

print("\nTEST OCCURRENCES:")
for w in prompt_words:
    matches = [s['diagram_type'] for s in test if w in s['text'].lower()]
    c = Counter(matches)
    print(f"  {w:<15}: {len(matches)} total -> {dict(c)}")
