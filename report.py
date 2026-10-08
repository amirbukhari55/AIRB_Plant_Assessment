"""Populate and paginate the native PPTX template. No office installation needed."""
import copy, io, json, re, zipfile
from pathlib import Path
from collections import Counter
from xml.etree import ElementTree as ET
from model import GATES, CAPABILITIES, validate_state

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
for k,v in NS.items():ET.register_namespace(k,v)

def short(value,limit):
    text=' '.join(str(value if value is not None else 'Not quoted').split())
    return text if len(text)<=limit else text[:limit-3].rsplit(' ',1)[0]+'...'

def replace_xml(raw,mapping):
    tree=ET.fromstring(raw)
    for node in tree.iter('{'+NS['a']+'}t'):
        text=node.text or ''
        for key,value in mapping.items():text=text.replace('{{'+key+'}}',str(value))
        node.text=text
    return ET.tostring(tree,encoding='utf-8',xml_declaration=True)

def metrics(sites,actions):
    return {'verified':sum(g['Status']=='Verified' for s in sites for g in s['gates'].values()),
      'applicable':sum(g['Status']!='Not applicable' for s in sites for g in s['gates'].values()),
      'closed':sum(a['Status']=='Closed' for a in actions),'open':sum(a['Status']!='Closed' for a in actions)}

def build_report(state,report_date,prepared_by='',scope='All sites',baseline=None,include_closed=False,include_registers=True,summary='',next_steps='',revision=0):
    state=validate_state(copy.deepcopy(state))
    if baseline is not None:baseline=validate_state(copy.deepcopy(baseline))
    sites=[s for s in state['sites'] if scope=='All sites' or s['Site']==scope]
    if not sites:raise ValueError('No sites selected')
    names={s['Site'] for s in sites};ids={s['id'] for s in sites}
    actions=[a for a in state['actions'] if a['Site'] in names or a['Site']=='All sites']
    m=metrics(sites,actions);pages=[]
    footer=f'{report_date} · {scope} · Saved revision {revision}'
    pages.append((1,{'TITLE':'Plant assessment\nprogress report','SUBTITLE':short(scope,85)+'\n'+short(prepared_by or 'AIRB',85),'FOOTER':footer,'NOTES':'Scope is Stage 1 assessment, not live monitoring. Source workbooks and latest saved register. Generated report date is user selected.'}))
    def section(title,headers,rows,takeaway='',notes=''):
        rows=rows or [['No records','No records entered for this scope','Not assessed']]
        for start in range(0,len(rows),5):
            page_rows=rows[start:start+5];mapping={'TITLE':title+(f' ({start//5+1})' if len(rows)>5 else ''),'SUBTITLE':f'{scope} · {report_date}','FOOTER':footer,'TAKEAWAY':short(takeaway,180),'NOTES':notes+'\n\nFull records:\n'+json.dumps(page_rows,ensure_ascii=False,indent=2),'PAGE':str(len(pages)+1)}
            limits=[42,90,48]
            for r in range(6):
                row=headers if r==0 else page_rows[r-1] if r<=len(page_rows) else ['','','']
                for c in range(3):mapping[f'CELL_{r}_{c}']=short(row[c],limits[c])
            pages.append((2,mapping))
    progress=[['Assessment groups',str(len(sites)),'Not a unique-plant count'],['Verified criteria',f"{m['verified']} / {m['applicable']} applicable criteria",'No weighted percentage'],['Action status',f"{m['closed']} closed / {m['open']} open",'Closed means register status'],['Engineering / alarms',f"{sum(r['Site'] in names or r['Site']=='All sites' for r in state['engineering'])} asset rows / {sum(r['Site'] in names or r['Site']=='All sites' for r in state['alarms'])} alarm rows",'Submitted survey records']]
    if baseline:
        old_sites=[s for s in baseline['sites'] if s['id'] in ids];old_actions=[a for a in baseline['actions'] if a['Site'] in names or a['Site']=='All sites'];old=metrics(old_sites,old_actions)
        progress.append(['Change from baseline',f"Verified criteria: {m['verified']-old['verified']:+d}; closed actions: {m['closed']-old['closed']:+d}",'Compared with uploaded backup'])
    else:progress.append(['Change from baseline','No previous snapshot supplied','Current status only'])
    section('Assessment progress',['Measure','Current position','Interpretation'],progress,summary or 'Local-PC dependence remains the key reported gap. Verify current status plant by plant.',summary)
    section('Site gaps and proposed changes',['Site','Current gap','Proposed decision'],[[s['Site'],s['Current gap'],s['Decision']] for s in sites],'Recommendations remain subject to site evidence and engineering review.')
    rows=[]
    for g in CAPABILITIES:
        counts=Counter(s['gates'][g]['Status'] for s in sites)
        rows.append([g,', '.join(f'{k}: {v}' for k,v in counts.items()),'Reported and verified are separate'])
    section('Capability assessment',['Capability','Status across selected groups','Assessment basis'],rows,'TG Phase 2 is the user-reported diagnostic benchmark. Remote access is a separate criterion.')
    selected=[a for a in actions if include_closed or a['Status']!='Closed']
    selected.sort(key=lambda a:({'High':0,'Medium':1,'Low':2}.get(a['Priority'],3),a['ID']))
    section('Actions and responsibilities',['Action / site','Proposed action','Owner / status / due'],[[a['ID']+' / '+a['Site'],a['Proposed action'],f"{a.get('Owner') or 'Unassigned'} / {a['Status']} / {a.get('Due date') or 'No due date'}"] for a in selected],'Long entries continue in slide notes. Update the register before issuing the report.')
    budget=[]
    for key in ['One-time RM','Annual RM']:
        quoted=[a[key] for a in actions if a.get(key) is not None]
        budget.append([key,f'RM {sum(quoted):,.2f}' if quoted else 'Not quoted',f'{len(quoted)} quoted / {len(actions)-len(quoted)} unquoted'])
    budget += [['Production / revenue','Actual production and contract billing data not supplied','No revenue loss calculated'],['Maintenance / downtime','Actual event and maintenance costs not supplied','No operating KPIs calculated']]
    section('Cost and management information',['Area','Current information','Coverage'],budget,'Cost totals cover quoted action estimates only, not an approved complete project budget.')
    if include_registers:
        engineering=[r for r in state['engineering'] if r['Site'] in names or r['Site']=='All sites']
        section('Engineering and automation',['Site / asset','Gap / proposed change','Operating capability'],[[r['Site']+' / '+r['Asset'],str(r.get('Gap') or '')+' / '+str(r.get('Proposed change') or ''),str(r.get('Local operation') or 'Unknown')+' / HQ: '+str(r.get('HQ remote command') or 'Unknown')] for r in engineering],'PLC operation, remote commands and safe physical isolation require separate assessment.',json.dumps(engineering,ensure_ascii=False,indent=2))
        alarms=[r for r in state['alarms'] if r['Site'] in names or r['Site']=='All sites']
        section('Alarm notification',['Site / alarm','Gap and required action','Channel / HQ visibility'],[[r['Site']+' / '+r['Alarm'],r.get('Gap / action') or 'To assess',str(r.get('Off-site channel') or 'Unknown')+' / HQ: '+str(r.get('HQ visibility') or 'Unknown')] for r in alarms],'Existing selective SMS system site remains to identify unless documented in the register.',json.dumps(alarms,ensure_ascii=False,indent=2))
    section('Next steps and decisions',['Workstream','Required result','Decision'],[['Site verification','Access, tags, history, ownership and support','Assign PICs'],['Engineering survey','Missing automation ancillaries and alarm routing','Confirm scope'],['Costed pilot','Proven read-only extraction and acceptance criteria','Approve after scoping'],['Department reporting','Validated production, billing, maintenance and HR joins','Agree data owners']],next_steps or 'Assess current gaps before committing to upgrades or migration.',next_steps)
    return assemble(pages)

def assemble(pages):
    with zipfile.ZipFile(Path(__file__).with_name('report_template.pptx')) as z:original={n:z.read(n) for n in z.namelist()}
    parts={n:b for n,b in original.items() if not re.match(r'ppt/(slides|notesSlides)/(slide|notesSlide|_rels/slide|_rels/notesSlide)\d+\.xml(?:\.rels)?$',n)}
    presentation=ET.fromstring(original['ppt/presentation.xml']);lst=presentation.find('p:sldIdLst',NS)
    for child in list(lst):lst.remove(child)
    rels=ET.fromstring(original['ppt/_rels/presentation.xml.rels'])
    for r in list(rels):
        if r.get('Type','').endswith('/slide'):rels.remove(r)
    types=ET.fromstring(original['[Content_Types].xml'])
    for t in list(types):
        if re.match(r'/ppt/(slides/slide|notesSlides/notesSlide)\d+\.xml$',t.get('PartName','')):types.remove(t)
    for number,(template,mapping) in enumerate(pages,1):
        parts[f'ppt/slides/slide{number}.xml']=replace_xml(original[f'ppt/slides/slide{template}.xml'],mapping)
        slide_rels=ET.fromstring(original[f'ppt/slides/_rels/slide{template}.xml.rels'])
        for r in slide_rels:
            if r.get('Type','').endswith('/notesSlide'):r.set('Target',f'../notesSlides/notesSlide{number}.xml')
        parts[f'ppt/slides/_rels/slide{number}.xml.rels']=ET.tostring(slide_rels,encoding='utf-8',xml_declaration=True)
        parts[f'ppt/notesSlides/notesSlide{number}.xml']=replace_xml(original[f'ppt/notesSlides/notesSlide{template}.xml'],mapping)
        notes_rels=ET.fromstring(original[f'ppt/notesSlides/_rels/notesSlide{template}.xml.rels'])
        for r in notes_rels:
            if r.get('Type','').endswith('/slide'):r.set('Target',f'../slides/slide{number}.xml')
        parts[f'ppt/notesSlides/_rels/notesSlide{number}.xml.rels']=ET.tostring(notes_rels,encoding='utf-8',xml_declaration=True)
        rid=f'rIdReport{number}';ET.SubElement(lst,'{'+NS['p']+'}sldId',{'id':str(255+number),'{'+NS['r']+'}id':rid})
        ET.SubElement(rels,'{'+REL+'}Relationship',{'Id':rid,'Type':NS['r']+'/slide','Target':f'slides/slide{number}.xml'})
        for path,kind in [(f'/ppt/slides/slide{number}.xml','slide'),(f'/ppt/notesSlides/notesSlide{number}.xml','notesSlide')]:ET.SubElement(types,'{'+CT+'}Override',{'PartName':path,'ContentType':f'application/vnd.openxmlformats-officedocument.presentationml.{kind}+xml'})
    parts['ppt/presentation.xml']=ET.tostring(presentation,encoding='utf-8',xml_declaration=True)
    parts['ppt/_rels/presentation.xml.rels']=ET.tostring(rels,encoding='utf-8',xml_declaration=True)
    ET.register_namespace('',CT)
    parts['[Content_Types].xml']=ET.tostring(types,encoding='utf-8',xml_declaration=True)
    if 'docProps/app.xml' in parts:
        root=ET.fromstring(parts['docProps/app.xml'])
        for e in root.iter():
            if e.tag.endswith('}Slides'):e.text=str(len(pages))
        parts['docProps/app.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in parts.items():z.writestr(name,raw)
    return output.getvalue()
