import json
import os
import subprocess
from pathlib import Path

folder = Path('docs/verification/phase12')
cases = [('.env.phase12','RESTORE_IN_PLACE_NOT_ALLOWED_USE_NEW_PROJECT'),('.env.phase12-restore','RESTORE_REQUIRES_EMPTY_DESTINATION')]
checks = []
for env, code in cases:
    command = ['python3','scripts/deploy.py','--env-file',env,'--evidence-dir',str(folder/'runs'),'restore','--backup','backups/20261108T023457_05fd3337']
    result = subprocess.run(command, capture_output=True, text=True, env=os.environ|{'DEPLOY_USE_SG':'1'}, timeout=180)
    logs = sorted((folder/'runs').glob('*_image-search-phase12-restore.log')) if env.endswith('-restore') else []
    log = logs[-1] if logs else None
    detail = log.read_text() if log else ''
    assert result.returncode == 1 and code in result.stdout + detail, {'env_file':env,'exit_code':result.returncode,'output':result.stdout}
    checks.append({'command':command,'exit_code':result.returncode,'expected_error_code':code,'status':'EXPECTED_REJECTION_VERIFIED','output':result.stdout.strip(),'private_operation_log':str(log) if log else None})
(folder/'restore_guards.json').write_text(json.dumps({'status':'pass','cases':checks},indent=2)+'\n')
print(json.dumps({'status':'pass','expected_rejections':len(checks)}))
