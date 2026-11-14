"""회차 하나의 DB 실행 기록(deploy_runs)과 wcp-ai 추적 로그를 모은다. 키는 SSM에서 메모리로만 읽는다.
usage: python3 collect.py <deployId> [out.json]"""
import json, subprocess, sys, re
import boto3
from live_bench import ssm

def db(did):
    ps=[p for pg in boto3.client('ssm').get_paginator('get_parameters_by_path').paginate(Path='/wcp/be',WithDecryption=True,Recursive=True) for p in pg['Parameters']]
    v={p['Name'].rsplit('/',1)[1]:p['Value'] for p in ps}
    url=v.get('SUPABASE_URL','https://dowhtvfzzzeijgqotjny.supabase.co'); key=v['SUPABASE_SECRET_KEY']
    q=f'{url}/rest/v1/deploy_runs?deploy_id=eq.{did}&select=status,stage,failure,ticket_id,created_at,updated_at,agent_result,input'
    r=subprocess.run(['curl','-sS',q,'-H',f'apikey: {key}','-H',f'authorization: Bearer {key}'],capture_output=True,text=True)
    return json.loads(r.stdout)

def trace(tickets):
    pat='|'.join(tickets)
    out=ssm(f'docker logs -t wcp-ai 2>&1 | grep -E "{pat}"')
    return [l for l in out.splitlines() if 'trace ticket=' in l or 'submitted' in l]

if __name__=='__main__':
    did=sys.argv[1]; rows=db(did)
    tickets=[r['ticket_id'] for r in rows if r.get('ticket_id')]
    rec={'deployId':did,'runs':[{k:v for k,v in r.items() if k!='input'} | {'input_port': r['input']['spec']['services'][0]['runtime']['port']} for r in rows],
         'trace': trace(tickets) if tickets else []}
    if len(sys.argv)>2:
        p=sys.argv[2]; d=json.load(open(p)); d['collected']=rec; json.dump(d,open(p,'w'),ensure_ascii=False,indent=1)
    print(json.dumps(rec,ensure_ascii=False,indent=1)[:3000])
