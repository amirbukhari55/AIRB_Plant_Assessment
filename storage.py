import json, sqlite3
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from model import initial_state, validate_state

class Store:
    def __init__(self, config=None, path=None):
        self.config=config
        self.path=Path(path or Path(__file__).parent/'assessment.sqlite')
    def load(self):
        if self.config:
            rows=self.remote('GET',{'id':'eq.airb-stage1','select':'revision,payload'})
            if not rows: raise RuntimeError('Run schema.sql to initialise the assessment record')
            row=rows[0];return (validate_state(row['payload']) if row['payload'] else initial_state()),row['revision']
        with sqlite3.connect(self.path) as c:
            c.execute('CREATE TABLE IF NOT EXISTS assessment(id INTEGER PRIMARY KEY, revision INTEGER, payload TEXT)')
            row=c.execute('SELECT revision,payload FROM assessment WHERE id=1').fetchone()
            if not row:
                data=initial_state();c.execute('INSERT INTO assessment VALUES(1,0,?)',(json.dumps(data),));return data,0
            return validate_state(json.loads(row[1])),row[0]
    def headers(self):
        key=self.config['service_role_key']
        return {'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json','Prefer':'return=representation'}
    def remote(self, method, params, payload=None):
        url=self.config['url'].rstrip('/')+'/rest/v1/plant_assessment?'+urlencode(params)
        req=Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers=self.headers(),method=method)
        with urlopen(req,timeout=15) as response:return json.load(response)
    def save(self,data,revision):
        validate_state(data)
        if self.config:
            rows=self.remote('PATCH',{'id':'eq.airb-stage1','revision':'eq.'+str(revision)},{'revision':revision+1,'payload':data})
            if not rows: raise RuntimeError('Another user saved changes. Reload before saving.')
        else:
            with sqlite3.connect(self.path) as c:
                cursor=c.execute('UPDATE assessment SET payload=?,revision=? WHERE id=1 AND revision=?',(json.dumps(data),revision+1,revision))
                if cursor.rowcount!=1: raise RuntimeError('Another user saved changes. Reload before saving.')
        return revision+1
