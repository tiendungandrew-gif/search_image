import json
import os
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/home/tts/prj')
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'scripts'))
from deployment.common import read_env

secrets = {}
private_envs = sorted(p for p in Path('.').glob('.env*') if p.is_file() and not p.name.endswith(('.example','.sample')))
for path in private_envs:
    for key, value in read_env(path).items():
        if any(term in key for term in ['TOKEN', 'PASSWORD', 'SECRET', 'API_KEY', 'ACCESS_KEY', 'DATABASE_URL']) and len(value) >= 16:
            secrets[f'{path.name}:{key}'] = value.encode()
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).decode().split('\0')
selected = {Path(p) for p in paths if p and Path(p).is_file()}
selected.update(p for p in Path('frontend/dist').rglob('*') if p.is_file())
selected.update(Path('evaluation/results/phase12/_sources').glob('*.tar.gz'))
hits = []
scanned = 0
archive_members = 0
for path in sorted(selected):
    if path.suffix == '.gz' and path.name.endswith('.tar.gz'):
        with tarfile.open(path) as archive:
            for member in archive:
                if not member.isfile():
                    continue
                data = archive.extractfile(member).read()
                archive_members += 1
                for label, value in secrets.items():
                    if value in data:
                        hits.append({'path':f'{path}:{member.name}','key':label})
    else:
        data = path.read_bytes()
        scanned += 1
        for label, value in secrets.items():
            if value in data:
                hits.append({'path':str(path),'key':label})
out = {'checked_at_utc':datetime.now(UTC).isoformat(),'method':'Exact known secret-value scan of Git candidate files, frontend dist and source archive members; no secret values emitted','private_env_files_checked':[p.name for p in private_envs],'files_scanned':scanned,'archive_members_scanned':archive_members,'private_values_checked':len(secrets),'matches':hits,'status':'pass' if not hits else 'fail','limitations':['Not a full historical Git secret scan or credential pattern scanner','Private env/cache/backups intentionally excluded from Git candidate set; backups remain sensitive']}
Path('docs/verification/phase12/secret_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':out['status'],'files_scanned':scanned,'archive_members_scanned':archive_members,'matches':hits}))
raise SystemExit(bool(hits))
