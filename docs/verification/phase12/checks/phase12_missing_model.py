import json,sys
from pathlib import Path
import httpx
sys.path.insert(0,'scripts')
from deployment.common import Deployment
x=Deployment('.env.phase12','docs/verification/phase12/runs')
assert x.project=='image-search-phase12'
h={'Authorization':'Bearer '+x.cfg['API_TOKEN']}
with httpx.Client(base_url='http://127.0.0.1:8088',headers=h,timeout=12) as c:
 assert c.get('/api/v1/system/workspace').json()['dataset']['images']==0
 old=x.cfg['DEPLOY_MODEL_PATH'];old_search=x.cfg['SEARCH_ENABLED']
 absent=Path('.cache/deployment/phase12/absent-model').resolve();absent.mkdir(parents=True,exist_ok=True)
 try:
  x.update(DEPLOY_MODEL_PATH=str(absent),SEARCH_ENABLED='true')
  x.compose('up','-d','--no-deps','--no-build','--wait','--wait-timeout','120','backend','worker',timeout=180)
  ready=c.get('/api/v1/health/ready');reply=c.post('/api/v1/search',json={'text':'colored shapes','top_k':2});page=c.get('/')
  inventory=x.application('app.cli.operations','inventory')
  assert ready.status_code==200 and page.status_code==200
  assert reply.status_code==503 and reply.json()['error']['code']=='NOT_READY'
  assert inventory['model_artifacts']=='not_installed' and inventory['counts']['images']==0
  Path('docs/verification/phase12/missing_model.json').write_text(json.dumps({'ready':ready.json(),'search_status':reply.status_code,'search_error':reply.json()['error']['code'],'frontend_status':page.status_code,'inventory':inventory},indent=2)+'\n')
  print('Verified: missing model keeps application accessible, search NOT_READY, dataset empty.')
 finally:
  x.update(DEPLOY_MODEL_PATH=old,SEARCH_ENABLED=old_search)
  x.compose('up','-d','--no-deps','--no-build','--wait','--wait-timeout','120','backend','worker',timeout=180)
