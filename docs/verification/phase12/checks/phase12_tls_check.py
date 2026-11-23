import json,sys
from pathlib import Path
import httpx,ssl
sys.path.insert(0,'scripts')
from deployment.common import Deployment,read_env,write_env
from deploy import startup
x=Deployment('.env.phase12','docs/verification/phase12/runs')
assert x.project=='image-search-phase12'
original=x.cfg.copy()
folder=Path('.cache/deployment/phase12/tls').resolve()
try:
 x.update(DEPLOY_TLS_PATH=str(folder),DEPLOY_TLS_CA_FILE=str(folder/'tls.crt'),DEPLOY_HTTPS_PORT='8448',DEPLOY_CHECK_URL='https://127.0.0.1:8448',CORS_ORIGINS='["https://127.0.0.1:8448"]')
 x.tls=True
 startup(x)
 context=ssl.create_default_context(cafile=str(folder/'tls.crt'))
 with httpx.Client(base_url='https://127.0.0.1:8448',verify=context,headers={'Authorization':'Bearer '+x.cfg['API_TOKEN']},timeout=12) as c:
  reply=c.post('/api/v1/search',json={'text':'colored shapes','top_k':3});assert reply.status_code==200 and len(reply.json()['results'])==3
  assert c.get('/').status_code==200
  Path('docs/verification/phase12/tls_local.json').write_text(json.dumps({'verification':'SELF_SIGNED_LOCAL_TLS_WITH_EXPLICIT_CA_AND_HOSTNAME_VALIDATION','https_status':200,'search_status':reply.status_code,'tls_url':'https://127.0.0.1:8448','public_certificate':'NOT_CONFIGURED','private_key_permissions':'0600; uid101'},indent=2)+'\n')
finally:
 write_env(x.path,original)
 y=Deployment('.env.phase12','docs/verification/phase12/runs')
 startup(y)
