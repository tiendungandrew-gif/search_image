import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path('/home/tts/prj')
os.chdir(ROOT)
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'backend')]
from deployment.common import read_env
from app.evaluation.dataset import validate_dataset
from app.evaluation.contracts import QueryCase

cfg = read_env('.env.phase12')
base = 'http://127.0.0.1:' + cfg['DEPLOY_HTTP_PORT']
headers = {'Authorization': 'Bearer ' + cfg['API_TOKEN']}
with httpx.Client(base_url=base, headers=headers, timeout=20) as client:
    response = client.post('/api/v1/search', json={'text': 'colored shapes', 'top_k': 7})
    response.raise_for_status()
    ids = [r['image_id'] for r in response.json()['results']]
assert len(ids) == 7
report = ROOT / 'docs/verification/phase12/indexed_ids.json'
report.write_text(json.dumps({'image_ids': sorted(ids)}, indent=2) + '\n')
snapshot = validate_dataset(base, cfg['API_TOKEN'], str(report), '.cache/deployment/phase12/benchmark_images', 'phase12_synthetic_shapes_v1')
snapshot['limitations'] = ['Seven synthetic shape images; deployment smoke only', 'No human relevance labels; no quality claims', 'Local CPU single-client through Nginx; not a production capacity benchmark']
target = ROOT / 'evaluation/datasets/manifests/phase12_synthetic_v1.json'
with target.open('x') as handle:
    json.dump(snapshot, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
target = ROOT / 'evaluation/queries/phase12_synthetic_v1.jsonl'
with target.open('x') as handle:
    for n, text in enumerate(['a red circle', 'a blue rectangle', 'colored geometric shapes'], 1):
        case = QueryCase(query_id=f'phase12_text_{n}', query_type='single_intent', language='en', group_id=f'shape_{n}', split='dev', request={'mode': 'text', 'text': text, 'top_k': 7})
        handle.write(case.model_dump_json() + '\n')
target = ROOT / 'evaluation/experiments/phase12_proxy_fast.json'
with target.open('x') as handle:
    json.dump({'name': 'phase12_proxy_fast', 'seed': 42, 'profile': 'fast', 'requests': 300, 'warmup': 10, 'concurrency': 1, 'top_k': 7, 'sample_resources': True}, handle, indent=2)
    handle.write('\n')
print(json.dumps({'images': len(ids), 'dataset_sha256': snapshot['sha256'], 'classification': 'SYNTHETIC_DEPLOYMENT_SMOKE'}))
