import json, math
from datetime import date
from pathlib import Path

BASE_GATES = ['Ownership and approval','Supported extraction interface','Tag mapping and units','Logging and history','Secure site connectivity','Backups and vendor support','Outage and load test','HQ data validation']
CAPABILITIES = ['HQ remote data access','Multi-parameter trending','PLC operating control','Automation ancillary completeness','Selective off-site alarm notification','Live HQ alarms','Daily production measurement','Maintenance and downtime records']
GATES = CAPABILITIES + BASE_GATES
STATES = ['Unknown','Reported','Blocked','Verified','Not applicable']
DECISIONS = ['Investigate','Integrate existing system','Upgrade selected components','Migrate software','Replace system','Owner approval required']

def initial_state():
    sites = [
      ('MAHB / KLIA','Treatment','AVEVA Edge 2020 SP2 / Siemens S7-1200','Database candidate; validate engine and read-only access','History and CSV tags reported. OPC server not included. Dedicated modem requested. Remote-access answers conflict.','Investigate','WTP - MAHB', {'Ownership and approval':'Reported','Logging and history':'Reported','Tag mapping and units':'Reported'}),
      ('PAMER group (mapping provisional)','Conveyance','WinCC / Siemens S7-1500, 10 inventory records','Validate reported OPC-UA route','No dedicated extraction questionnaire. Endpoint, licence, tag count, support and group mapping need verification.','Investigate',None,{'Supported extraction interface':'Reported','Backups and vendor support':'Unknown'}),
      ('Top Glove Phase 1','Reclamation','InduSoft / FATEK in inventory','Vendor access and SCADA stability review','Lag/hang reported. WRP questionnaire does not reliably separate phases and has inconsistent PLC descriptions.','Investigate','WRP - TG',{'Supported extraction interface':'Blocked','Backups and vendor support':'Blocked'}),
      ('Top Glove Phase 2','Reclamation','WinCC V7.5 SP2 / Siemens ET200SP in inventory','Verify phase-specific access and configuration','Expired support in inventory. WRP questionnaire is not phase-specific; avoid assuming Phase 1 restrictions apply identically.','Investigate','WRP - TG',{}),
      ('Ansell','Reclamation','Bespoke Thydaa / Siemens S7-1200','Developer-supported extraction discovery','Restricted access, unconfirmed historian and database, support to verify with Minder Control.','Investigate','WRP - AS',{'Supported extraction interface':'Blocked','Backups and vendor support':'Blocked'}),
      ('Gunung Semanggol','Treatment','Citect / GE Fanuc VersaMax','LAP-approved OPC or existing reporting route','LAP-owned assets. Reported OPC server and local logging. Windows 7 reported.','Owner approval required',None,{'Ownership and approval':'Blocked','Supported extraction interface':'Reported','Logging and history':'Reported'}),
      ('Taiping Headworks','Treatment','Citect / GE Fanuc VersaMax','LAP-approved OPC or existing reporting route','LAP-owned assets. No program backup reported. Windows 7 reported.','Owner approval required',None,{'Ownership and approval':'Blocked','Supported extraction interface':'Reported','Logging and history':'Reported','Backups and vendor support':'Blocked'}),
    ]
    for label,tab in [('PPSB','NRW - PPSB'),('NMB','NRW - NMB'),('IIUM','NRW - IIUM'),('SATS','NRW - SATS'),('JPB','NRW - JPB')]:
        sites.append((label,'NRW','PMAC / vendor platforms; verify per zone','Controlled CSV import, then approved scheduling/API','Manual CSV reported. 15-minute capture/daily upload in questionnaire. API, ownership and validation flags pending.' + (' IIUM header says George Kent; detail repeats DIEHL.' if label=='IIUM' else ''),'Investigate',tab,{'Logging and history':'Reported','Supported extraction interface':'Reported'}))
    records=[]
    for n,a in enumerate(sites,1):
        label,segment,system,route,gap,decision,tab,states=a
        records.append({'id':f'S{n:02d}','Site':label,'Segment':segment,'Current system':system,'Candidate route':route,'Current gap':gap,'Decision':decision,'questionnaire':tab,'gates':{g:{'Status':states.get(g,'Unknown'),'Evidence':'Initial desk assessment from source returns; site verification pending.','Verified by':'','Review date':''} for g in GATES}})
    actions=[]
    for site in records:
        actions.append({'ID':f'A{len(actions)+1:03d}','Site':site['Site'],'Objective':'Automatic logging','Gap':site['Current gap'],'Proposed action':site['Candidate route'],'Change type':'Verification','Priority':'High' if site['Segment']!='NRW' else 'Medium','Owner':'Unassigned','Status':'Open','Evidence':'Source return; proposal needs site/vendor validation','One-time RM':None,'Annual RM':None,'Due date':''})
    actions.append({'ID':f'A{len(actions)+1:03d}','Site':'All sites','Objective':'Shared department dashboards','Gap':'Source IDs, capacity units, formulas and tag definitions inconsistent','Proposed action':'Reconcile master register; define production, cost, procurement and HR joins','Change type':'Data preparation','Priority':'High','Owner':'Unassigned','Status':'Open','Evidence':'Compiled inventory and questionnaire review','One-time RM':None,'Annual RM':None,'Due date':''})
    value={'schema_version':1,'sites':records,'actions':actions,'engineering':[],'alarms':[],'components':json.loads((Path(__file__).parent/'assets'/'component-seed.json').read_text())}
    for s in records:
        s['gates']['HQ remote data access']['Evidence']='User reports dependence on plant-local PC for data access. Individual site access needs confirmation.'
        if s['Segment']!='NRW':s['gates']['HQ remote data access']['Status']='Blocked'
        else:
            for g in ['PLC operating control','Automation ancillary completeness']:
                s['gates'][g].update(Status='Not applicable',Evidence='This NRW platform group is assessed for monitoring. Equipment control is outside its present scope.')
        if s['Site']=='Top Glove Phase 2':
            s['gates']['Multi-parameter trending'].update(Status='Reported',Evidence='User identifies TG Phase 2 as the local diagnostic benchmark for multiple trends and troubleshooting. Exact functions need demonstration.')
    for objective,gap,action,kind in [
      ('Remote access','Data accessible only through plant-local PC','Verify approved HQ access and extraction for each site','Connectivity/security'),
      ('Diagnostic trending','Different SCADA systems offer different analysis features','Demonstrate TG Phase 2 functions and compare all sites against agreed requirements','Verification'),
      ('Automation capability','Missing automation ancillaries prevent some PLC control','Survey critical assets for instruments, actuators, feedback, controllers, pneumatics and interlocks','Hardware'),
      ('Alarm notification','One selective SMS system reported; site not identified','Identify existing system; confirm alarm filtering, recipients, escalation and future HQ visibility','Licence/interface'),
      ('Production and reliability','Daily production, downtime and maintenance costs need management visibility','Verify production meters/targets, billing basis, incident logs and maintenance records','Data preparation')]:
        actions.append({'ID':f'A{len(actions)+1:03d}','Site':'All sites','Objective':objective,'Gap':gap,'Proposed action':action,'Change type':kind,'Priority':'High','Owner':'Unassigned','Status':'Open','Evidence':'User requirements, 7 October 2026. Site verification pending.','One-time RM':None,'Annual RM':None,'Due date':''})
    return value

def readiness(site):
    statuses=[site['gates'][g]['Status'] for g in GATES]
    if 'Blocked' in statuses: return 'Blocked pending resolution'
    if all(v in ['Verified','Not applicable'] for v in statuses): return 'Verified for agreed assessment scope'
    return 'Verification required'

def validate_state(value):
    if not isinstance(value,dict) or value.get('schema_version')!=1: raise ValueError('Unsupported assessment format')
    seed=initial_state()
    # Preserve earlier Stage 1 backups while adding new assessment fields.
    seed_by_id={s['id']:s for s in seed['sites']}
    value.setdefault('engineering',[]);value.setdefault('alarms',[])
    value.setdefault('components',seed['components'])
    if not isinstance(value['components'],list):raise ValueError('Invalid component register')
    for row in value['components']:
        if row.get('Site') not in {s['Site'] for s in seed['sites']} or not str(row.get('Component','')).strip():raise ValueError('Components need a valid site and component name')
    if len({r.get('ID') for r in value['components']})!=len(value['components']):raise ValueError('Component IDs must be unique')
    for s in value.get('sites',[]):
        for g in CAPABILITIES:
            if s.get('id') in seed_by_id:s['gates'].setdefault(g,seed_by_id[s['id']]['gates'][g])
    if {s['id'] for s in value.get('sites',[])}!={s['id'] for s in seed['sites']}: raise ValueError('Site IDs do not match this assessment')
    for s in value['sites']:
        if s['Decision'] not in DECISIONS: raise ValueError('Invalid decision')
        for gate in GATES:
            item=s['gates'][gate]
            if item['Status'] not in STATES: raise ValueError('Invalid gate status')
            if item['Status']=='Not applicable' and not str(item.get('Evidence','')).strip():raise ValueError('Not applicable requires a reason')
            if item['Status']=='Verified' and not all(str(item.get(k,'')).strip() for k in ['Evidence','Verified by','Review date']): raise ValueError('Verified gates require evidence, reviewer and review date')
            if item['Status']=='Verified':
                try: date.fromisoformat(item['Review date'])
                except ValueError: raise ValueError('Verified review dates must use YYYY-MM-DD')
    if not isinstance(value.get('actions'),list): raise ValueError('Actions must be a list')
    for a in value['actions']:
        for k in ['ID','Site','Gap','Proposed action','Status','Priority']:
            if not isinstance(a.get(k),str) or not a[k].strip(): raise ValueError(f'Action requires {k}')
        for k in ['One-time RM','Annual RM']:
            if a.get(k) is not None and (isinstance(a[k],bool) or not isinstance(a[k],(int,float)) or not math.isfinite(a[k]) or a[k]<0): raise ValueError('Costs must be blank or nonnegative numbers')
    if len({a['ID'] for a in value['actions']})!=len(value['actions']):raise ValueError('Action IDs must be unique')
    allowed={s['Site'] for s in value['sites']}|{'All sites'}
    if any(a['Site'] not in allowed for a in value['actions']):raise ValueError('Select an existing site or All sites')
    for key in ['engineering','alarms']:
        if not isinstance(value[key],list):raise ValueError('Invalid register')
        for row in value[key]:
            if row.get('Site') not in allowed:raise ValueError('Select a valid site for each register row')
            if not str(row.get('Asset' if key=='engineering' else 'Alarm','')).strip():raise ValueError('Register rows need an asset or alarm name')
    return value
