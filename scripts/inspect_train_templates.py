import json

train = json.load(open('data/splits/train.json', encoding='utf-8'))
arch_templates = {s['metadata']['template_id'] for s in train if s['diagram_type'] == 'architecture'}
print('Architecture templates in train:', arch_templates)
for tid in arch_templates:
    sample = next(s for s in train if s['metadata']['template_id'] == tid)
    print(f"-- {tid}: {sample.get('text', '')[:140]}...")
