"""Read-only evidence capture, never opens/migrates a canonical Store."""
import urllib.request,json,pathlib,hashlib,sys
from pal.sanitize import sanitize
slot,port=sys.argv[1:3];p=pathlib.Path('evidence/functional/stable1-20261007')/slot;url='http://127.0.0.1:'+port
with urllib.request.urlopen(url+'/api/state',timeout=5) as r:s=json.load(r)
(p/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
for receipt in s['receipts']:
 with urllib.request.urlopen(url+'/api/artifact/'+receipt['artifact_id']) as r:b=r.read()
 assert hashlib.sha256(b).hexdigest()==receipt['hash'] and len(b)==receipt['size']
 a=next(x for x in s['attempts'] if x['id']==receipt['attempt_id']); m=json.loads(a['manifest']); c={'records':[x for x in s['records'] if x['id'] in m],'notes':[x for x in s['notes'] if 'note:'+x['id'] in m],'manifest':m}; rev=next(x for x in s['revisions'] if x['goal_id']==a['goal_id'] and x['revision']==a['revision'])
 prompt=sanitize('DRAFT\n'+rev['specification']+'\nReturn only the requested draft text, without tool invocations or planning transcript.\nRelevant sanitized context: '+json.dumps(tuple([(x['role'],x['content']) for x in c['records']]+[('note',x['content']) for x in c['notes']]),ensure_ascii=False))
 prefix='' if len(s['receipts'])==1 else receipt['artifact_id']+'-'
 (p/(prefix+'draft.txt')).write_bytes(b);(p/(prefix+'prompt-reconstruction.txt')).write_text(prompt)
 print(b.decode())
print(json.dumps({'goals':s['goals'],'provider_status':s['provider_status'],'runtime':s['runtime']},ensure_ascii=False))
