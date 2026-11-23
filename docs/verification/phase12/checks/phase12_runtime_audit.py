import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path

import httpx

ROOT = Path('/home/tts/prj')
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'scripts'))
from deployment.common import read_env

def docker(args):
    result = subprocess.run(['sg', 'docker', '-c', shlex.join(['docker', *args])], text=True, capture_output=True, check=True, timeout=120)
    return result.stdout

out = {'checked_at_utc': datetime.now(UTC).isoformat(), 'production_like': {}}
release = json.loads(Path('docs/verification/phase12/release.json').read_text())
for project in ['image-search-phase12', 'image-search-phase12-restore']:
    containers = {}
    for service in ['backend', 'worker', 'frontend', 'postgres', 'qdrant', 'minio']:
        raw = json.loads(docker(['inspect', f'{project}-{service}-1']))[0]
        host = raw['HostConfig']
        health = raw['State'].get('Health', {})
        checks = []
        for row in health.get('Log', []):
            elapsed = datetime.fromisoformat(row['End'][:26]) - datetime.fromisoformat(row['Start'][:26])
            checks.append({'elapsed_ms': round(elapsed.total_seconds()*1000, 2), 'exit_code': row['ExitCode']})
        containers[service] = {'image_id': raw['Image'], 'user': raw['Config']['User'], 'state': raw['State']['Status'], 'health': health.get('Status'), 'health_checks': checks, 'read_only_rootfs': host['ReadonlyRootfs'], 'cap_drop': host['CapDrop'], 'security_opt': host['SecurityOpt'], 'memory_bytes': host['Memory'], 'nano_cpus': host['NanoCpus'], 'ports': raw['NetworkSettings']['Ports'], 'mounts': [{'type': v['Type'], 'destination': v['Destination'], 'read_write': v['RW']} for v in raw['Mounts']]}
        assert raw['State']['Status'] == 'running' and health['Status'] == 'healthy'
        if service in ['backend', 'worker', 'frontend']:
            assert host['ReadonlyRootfs'] and 'ALL' in host['CapDrop'] and raw['Config']['User'] in ['10001:10001', '101:101', '10001', '101']
            if project == 'image-search-phase12':
                component = 'backend' if service == 'worker' else service
                assert raw['Image'] == release['images'][component]
        if service != 'frontend':
            assert not any(raw['NetworkSettings']['Ports'].values())
    out['production_like'][project] = containers

probe = "import importlib.util,json,pathlib; print(json.dumps({'pytest_present':importlib.util.find_spec('pytest') is not None,'ruff_present':importlib.util.find_spec('ruff') is not None,'test_source_present':pathlib.Path('/srv/backend/tests').exists(),'private_env_present':any(p.name.startswith('.env') for p in pathlib.Path('/srv').rglob('*'))}))"
out['backend_image'] = json.loads(docker(['run', '--rm', '--network', 'none', '--read-only', '--entrypoint', 'python', 'semantic-image-search/backend:phase12-final', '-c', probe]))
assert not any(out['backend_image'].values())
docker(['run', '--rm', '--network', 'none', '--read-only', '--entrypoint', '/bin/sh', 'semantic-image-search/frontend:phase12-final', '-c', 'test ! -d /srv/frontend/src && test ! -d /usr/share/nginx/html/src && ! command -v node && test -f /usr/share/nginx/html/index.html'])
out['frontend_image'] = {'static_assets_present': True, 'node_runtime_absent': True, 'application_source_absent': True}

cfg = read_env('.env')
with httpx.Client(base_url='http://127.0.0.1:8000', headers={'Authorization':'Bearer '+cfg['API_TOKEN']}, timeout=15) as c:
    live = c.get('/api/v1/health/live'); live.raise_for_status()
    workspace = c.get('/api/v1/system/workspace'); workspace.raise_for_status()
    out['serving_preservation'] = {'live':live.json(),'workspace':workspace.json()}
    assert workspace.json()['dataset']['images'] == 513 and workspace.json()['dataset']['generation'] == 3
    assert workspace.json()['dataset']['index_id'] == 'b4597021-4b91-491d-99ae-0617a6ca389c'
sql = 'SELECT (SELECT count(*) FROM entities),(SELECT count(*) FROM entity_relationships),(SELECT count(*) FROM image_entities);'
out['serving_preservation']['knowledge_counts'] = docker(['compose', 'exec', '-T', 'postgres', 'psql', '-U', cfg['POSTGRES_USER'], '-d', cfg['POSTGRES_DB'], '-At', '-c', sql]).strip()
assert out['serving_preservation']['knowledge_counts'] == '4|3|3'
out['env_permissions'] = {p.name: oct(p.stat().st_mode & 0o777) for p in [Path('.env'), Path('.env.phase12'), Path('.env.phase12-restore')]}
assert set(out['env_permissions'].values()) == {'0o600'}
Path('docs/verification/phase12/runtime_audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'status':'pass','serving_images':513,'serving_generation':3,'production_like_projects':list(out['production_like'])}))
