import hashlib
import json
import shlex
import subprocess
from pathlib import Path

def docker(args):
    return subprocess.check_output(['sg','docker','-c',shlex.join(['docker',*args])],text=True,timeout=60)

probe = "import hashlib,pathlib; h=hashlib.sha256(); roots=[pathlib.Path('/srv/backend/app'),pathlib.Path('/srv/backend/alembic')]; files=sorted(p for root in roots for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts); [(h.update(str(p).encode()+b'\\0'+p.read_bytes()+b'\\0')) for p in files]; print(h.hexdigest())"
results = {}
for component in ['backend','frontend']:
    values = {}
    for release in ['phase12-verify-v4','phase12-final']:
        prefix = ['run','--rm','--network','none','--read-only']
        if component == 'backend':
            raw = docker(prefix+['--entrypoint','python',f'semantic-image-search/backend:{release}','-c',probe]).strip()
        else:
            raw = docker(prefix+['--entrypoint','find',f'semantic-image-search/frontend:{release}','/usr/share/nginx/html','-type','f','-exec','sha256sum','{}','+'])
            raw = hashlib.sha256('\n'.join(sorted(raw.splitlines())).encode()).hexdigest()
        values[release]=raw
    assert len(set(values.values())) == 1, values
    results[component] = values
Path('docs/verification/phase12/component_comparison.json').write_text(json.dumps({'status':'pass','scope':'Backend app/alembic file bytes and frontend static file bytes; excludes image labels/runtime configuration','sha256':results},indent=2)+'\n')
print(json.dumps({'status':'pass','components_with_identical_application_bytes':list(results)}))
