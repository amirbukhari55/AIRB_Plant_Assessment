"""Configurable RFQ forms, offline contractor returns and transparent assessment."""
import copy,hashlib,html,json,math,uuid
from datetime import date
import pandas as pd
import streamlit as st

def uid(prefix):return prefix+uuid.uuid4().hex[:10]
def seed():
    return {'title':'Plant SCADA and HQ monitoring','reference':'','scope':'Assess existing systems, propose minimum rectification for HQ remote monitoring, automatic logging, diagnostic trends and selected off-site alarms. Quote site work and recurring costs separately.','fields':[{'id':f'Q{i:02}','section':sec,'question':q,'type':'Long text','required':True} for i,(sec,q) in enumerate([
    ('Technical','Describe existing systems to retain and minimum rectification required by site. Separate confirmed facts from assumptions.'),
    ('Technical','Describe the proposed HQ data connection, supported interfaces and existing vendor or licence dependencies.'),
    ('Technical','Describe automatic logging, timestamps, retention, data quality, communication failure and backfill.'),
    ('Technical','Describe multiple-parameter trends and troubleshooting functions, against AIRB troubleshooting requirements.'),
    ('Technical','Describe selective off-site alarms, recipient rules and HQ alarm visibility.'),
    ('Delivery','State implementation stages, outage needs, testing, training, handover and warranty/support coverage.'),
    ('Commercial','List exclusions, assumptions, provisional allowances and potential variation triggers. State licence and hosting limits.')],1)],
    'pricing':[{'id':f'P{i:02}','item':x} for i,x in enumerate(['Common HQ platform and integration','Site integration and rectification separately itemised for every quoted site','Recurring software and hosting per year','Recurring connectivity and alarm services per year','Maintenance and support per year'],1)],
    'criteria':[{'id':f'K{i:02}','criterion':x,'weight':0.0,'mandatory':False} for i,x in enumerate(['Reuse and minimum rectification','HQ connectivity and data access','Logging and diagnostic trending','Off-site alarms and operational visibility','Delivery testing and support','Commercial clarity and variation exposure'],1)],'contractors':[],'issues':[]}

def fingerprint(p):
    # Scoring weights remain internal; changes to published requirements change the token.
    payload={k:p[k] for k in ['title','reference','scope','fields','pricing']}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]

def validate(p):
    if not isinstance(p,dict):raise ValueError('Invalid procurement workspace')
    for key in ['fields','pricing','criteria','contractors','issues']:
        if not isinstance(p.get(key),list):raise ValueError('Invalid '+key)
    for key in ['fields','pricing','criteria','contractors']:
        ids=[r.get('id') for r in p[key]]
        if not all(ids) or len(set(ids))!=len(ids):raise ValueError('Duplicate or missing record IDs')
    for c in p['criteria']:
        w=c.get('weight')
        if isinstance(w,bool) or not isinstance(w,(int,float)) or not math.isfinite(w) or w<0:raise ValueError('Weights must be nonnegative finite numbers')
        if not str(c.get('criterion','')).strip():raise ValueError('Each criterion needs a name')
    for f in p['fields']:
        if not f.get('question') or f.get('type') not in ['Long text','Short text','Number','Yes or No']:raise ValueError('Invalid question')
    for c in p['contractors']:
        for row in c.get('prices',{}).values():
            a=row.get('amount')
            if a is not None and (isinstance(a,bool) or not isinstance(a,(int,float)) or not math.isfinite(a) or a<0):raise ValueError('Prices must be nonnegative finite numbers or blank')
        if not str(c.get('name','')).strip():raise ValueError('Contractor name is required')
        for v in c.get('assessments',{}).values():
            score=v.get('score')
            if score is not None and (isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or score<0 or score>5):raise ValueError('Scores must be 0 to 5 or blank')
            if (score is not None or v.get('mandatory result') in ['Pass','Fail']) and not all(str(v.get(k,'')).strip() for k in ['reason','assessor','date']):raise ValueError('Scores and mandatory decisions need reasons, assessor and date')
            if score is not None or v.get('mandatory result') in ['Pass','Fail']:
                try:date.fromisoformat(v['date'])
                except ValueError:raise ValueError('Assessment date must use YYYY-MM-DD')
    return p

def totals(p,c):
    active=[k for k in p['criteria'] if k['weight']>0];den=sum(k['weight'] for k in active)
    entries=c.get('assessments',{});scored=[k for k in active if entries.get(k['id'],{}).get('score') is not None]
    earned=sum(entries[k['id']]['score']/5*k['weight'] for k in scored)
    mandatory=[k for k in p['criteria'] if k.get('mandatory')]
    gates=[entries.get(k['id'],{}).get('mandatory result','Pending') for k in mandatory]
    eligible='Not met' if 'Fail' in gates else 'Pending' if any(x!='Pass' for x in gates) else 'Pass'
    return {'total':earned/den*100 if den and len(scored)==len(active) else None,'partial':earned/den*100 if den else None,'coverage':len(scored),'count':len(active),'mandatory':eligible}

def blank_html(p):
    token=fingerprint(p);esc=html.escape
    controls=[]
    for f in p['fields']:
        ident=esc(f['id']);kind=f['type'];required=' required' if f['required'] else ''
        control=(f'<textarea id="{ident}" rows="4"{required}></textarea>' if kind=='Long text' else f'<select id="{ident}"{required}><option value="">Select</option><option>Yes</option><option>No</option></select>' if kind=='Yes or No' else f'<input id="{ident}" type="'+('number' if kind=='Number' else 'text')+'"'+required+'>')
        controls.append(f'<div class="field"><small>{esc(f["section"])} / {ident}</small><label for="{ident}">{esc(f["question"])}'+(' *' if f['required'] else '')+'</label>'+control+'</div>')
    prices=''.join(f'<tr><td>{esc(r["id"])}</td><td>{esc(r["item"])}</td><td><input id="{esc(r["id"])}-amount" type="number" min="0" step="0.01"></td><td><input id="{esc(r["id"])}-basis" placeholder="one-off / annual / allowance / excluded"></td></tr>' for r in p['pricing'])
    spec=json.dumps({'token':token,'fields':p['fields'],'pricing':p['pricing']}).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AIRB Contractor Response</title><style>body{font:16px Arial;color:#18334b;max-width:1000px;margin:35px auto;padding:20px}h1{font-size:27px}label{display:block;font-weight:bold;margin:10px 0}input,textarea,select{box-sizing:border-box;width:100%;padding:10px;border:1px solid #b7c6d3;border-radius:4px;font:inherit;color:#111}small{color:#526779}.field{margin:25px 0}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd5dd;padding:10px;text-align:left}button{padding:12px;background:#183b56;color:white;border:0;margin:18px 8px 0 0;cursor:pointer}pre{white-space:pre-wrap;font:inherit}.notice{background:#edf4f8;padding:15px}@media print{button{display:none}body{margin:0}textarea{height:120px}.field,tr{break-inside:avoid}}</style><h1>ALIRAN IHSAN RESOURCES BERHAD</h1><h2>'''+esc(p['title'])+'''</h2><p>RFQ reference: '''+esc(p['reference'] or 'Not assigned')+''' | Form version: '''+token+'''</p><pre>'''+esc(p['scope'])+'''</pre><p class="notice">Complete this form in your browser, then download the response JSON and send it to AIRB with your formal proposal. Use Print to save a readable PDF. Entries are not sent automatically and are lost if this page is closed before downloading. Do not edit question IDs. Blank prices mean unquoted, not zero. All prices in RM excluding tax; explain tax and currency assumptions below.</p><form id="response"><label>Contractor name *</label><input id="name" required><label>Contact person and email</label><input id="contact"><label>Proposal reference</label><input id="proposal"><label>Submission date</label><input id="submitted" type="date">'''+''.join(controls)+'''<h2>Pricing schedule</h2><table><tr><th>ID</th><th>Item</th><th>RM excluding tax</th><th>Basis and inclusions</th></tr>'''+prices+'''</table><label>Taxes exclusions assumptions and validity</label><textarea id="declarations" rows="5"></textarea><button type="submit">Download completed response JSON</button><button type="button" onclick="window.print()">Print or save PDF</button></form><script>const spec='''+spec+''';document.getElementById('response').onsubmit=e=>{e.preventDefault();const val=id=>document.getElementById(id).value;const result={format:'AIRB_CONTRACTOR_RESPONSE_V1',token:spec.token,name:val('name'),contact:val('contact'),proposal:val('proposal'),submitted:val('submitted'),declarations:val('declarations'),answers:Object.fromEntries(spec.fields.map(f=>[f.id,val(f.id)])),prices:Object.fromEntries(spec.pricing.map(p=>[p.id,{amount:val(p.id+'-amount')===''?null:Number(val(p.id+'-amount')),basis:val(p.id+'-basis')}]))};const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='AIRB_contractor_response.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};</script></html>'''

def import_return(p,r):
    if r.get('format')!='AIRB_CONTRACTOR_RESPONSE_V1':raise ValueError('Use a response exported from the AIRB contractor form')
    if r.get('token')!=fingerprint(p):raise ValueError('Form version differs. Use the matching saved template or reissue the latest form; do not mix scopes.')
    if not str(r.get('name','')).strip():raise ValueError('Contractor name is required')
    if set(r.get('answers',{}))!={f['id'] for f in p['fields']} or set(r.get('prices',{}))!={f['id'] for f in p['pricing']}:raise ValueError('Response question or price IDs do not match')
    for f in p['fields']:
        value=r['answers'][f['id']]
        if not isinstance(value,str):raise ValueError('Answers must be text')
        if len(value)>30000:raise ValueError('Answer too long')
        if f['required'] and not value.strip():raise ValueError('Required answer missing: '+f['id'])
        if value.strip() and f['type']=='Yes or No' and value not in ['Yes','No']:raise ValueError('Invalid Yes or No answer')
        if value.strip() and f['type']=='Number':
            try:n=float(value)
            except ValueError:raise ValueError('Invalid number answer')
            if not math.isfinite(n):raise ValueError('Invalid number answer')
    for pr in r['prices'].values():
        a=pr.get('amount')
        if a is not None and (isinstance(a,bool) or not isinstance(a,(int,float)) or not math.isfinite(a) or a<0):raise ValueError('Prices must be nonnegative or blank')
        if not isinstance(pr.get('basis',''),str):raise ValueError('Invalid price basis')
    c={k:r.get(k,'') for k in ['name','contact','proposal','submitted','declarations']}
    c.update(id=uid('V'),token=r['token'],answers=r['answers'],prices=r['prices'],assessments={})
    return c

def render(data,save):
    p=copy.deepcopy(data.get('procurement',seed()))
    def commit(new):
        validate(new);u=copy.deepcopy(data);u['procurement']=new;save(u)
    st.write('Build a shared questionnaire, issue the blank form, record contractor proposals and assess them against the same criteria.')
    tabs=st.tabs(['Build form','Issue blank form','Contractor responses','Scoring criteria','Compare contractors'])
    with tabs[0]:
        st.caption('Starter questions reflect the discussed objectives. Edit them before issue. No contractor answers or scores are prefilled.')
        with st.form('rfq_header'):
            title=st.text_input('Form title',p['title']);reference=st.text_input('RFQ reference',p['reference']);scope=st.text_area('Scope / instructions to contractors',p['scope'])
            if st.form_submit_button('Save form details'):p.update(title=title,reference=reference,scope=scope);commit(p)
        with st.expander('Add question or field',expanded=True):
            with st.form('add_question'):
                section=st.text_input('Section','Technical');question=st.text_area('Question / information requested');kind=st.selectbox('Answer type',['Long text','Short text','Number','Yes or No']);required=st.checkbox('Required answer',True)
                if st.form_submit_button('Add field'):
                    if question.strip():p['fields'].append({'id':uid('Q'),'section':section,'question':question,'type':kind,'required':required});commit(p)
                    else:st.error('Enter a question')
        with st.form('edit_questions'):
            fields=st.data_editor(pd.DataFrame(p['fields']),hide_index=True,width='stretch',disabled=['id'],column_config={'type':st.column_config.SelectboxColumn(options=['Long text','Short text','Number','Yes or No'])})
            remove=st.multiselect('Remove question IDs',[r['id'] for r in p['fields']])
            if st.form_submit_button('Save question edits'):p['fields']=[r for r in fields.to_dict('records') if r['id'] not in remove];commit(p)
        with st.form('price_fields'):
            price=st.data_editor(pd.DataFrame(p['pricing']),hide_index=True,width='stretch',disabled=['id'])
            item=st.text_input('Additional price item');remove=st.multiselect('Remove price IDs',[r['id'] for r in p['pricing']])
            if st.form_submit_button('Save pricing fields'):
                p['pricing']=[r for r in price.to_dict('records') if r['id'] not in remove]
                if item.strip():p['pricing'].append({'id':uid('P'),'item':item})
                commit(p)
    with tabs[1]:
        token=fingerprint(p);st.write('**Current form version:** '+token)
        st.write('Download the blank HTML form and send it with the same source attachments to every contractor. They can open it in a browser, fill it offline, print/save PDF and download their answers as JSON for AIRB to import. No login or external service is needed.')
        st.warning('Save all form edits first. Changes to questions, scope or price items create a different version. Keep the original template when issuing revisions; responses from different versions are not scored together.')
        st.download_button('Export blank contractor form',blank_html(p),file_name='AIRB_Blank_Contractor_Form.html',mime='text/html')
        st.download_button('Export editable template backup',json.dumps(p,indent=2),file_name='AIRB_RFQ_Template_'+token+'.json',mime='application/json')
        if st.button('Record this version as issued'):
            p['issues'].append({'version':token,'date':date.today().isoformat(),'template':{k:copy.deepcopy(p[k]) for k in ['title','reference','scope','fields','pricing','criteria']}});commit(p)
        if p['issues']:st.dataframe(pd.DataFrame([{k:r[k] for k in ['version','date']} for r in p['issues']]),hide_index=True)
        with st.expander('Restore an issued template or template backup'):
            st.caption('Restores template fields and scoring criteria; contractor records remain. Scores are cleared to require reassessment.')
            if p['issues']:
                options={f"{i+1}: {x['version']} ({x['date']})":x for i,x in enumerate(p['issues'])};which=st.selectbox('Issued version',list(options))
                if st.button('Restore selected issued template'):
                    p.update(copy.deepcopy(options[which]['template']))
                    for c in p['contractors']:c['assessments']={}
                    commit(p)
            upload=st.file_uploader('Template backup JSON',type=['json'],key='template_restore')
            if upload and st.button('Restore uploaded template'):
                try:
                    r=json.loads(upload.getvalue());validate(r)
                    for k in ['title','reference','scope','fields','pricing','criteria']:p[k]=r[k]
                    for c in p['contractors']:c['assessments']={}
                    commit(p)
                except (ValueError,KeyError,TypeError):st.error('Invalid template backup')
    with tabs[2]:
        upload=st.file_uploader('Import completed contractor response JSON',type=['json'],key='bid_return')
        if upload and st.button('Import contractor response'):
            try:
                r=json.loads(upload.getvalue());c=import_return(p,r)
                if any(x['name'].strip().lower()==c['name'].strip().lower() and x['token']==c['token'] for x in p['contractors']):st.error('This contractor already has a response for this version. Edit the existing record, or rename a revised proposal explicitly.')
                else:p['contractors'].append(c);commit(p)
            except (ValueError,TypeError,KeyError) as e:st.error(str(e))
        with st.form('add_contractor'):
            name=st.text_input('Contractor name for manual entry');contact=st.text_input('Contact / email');ref=st.text_input('Proposal reference')
            if st.form_submit_button('Add contractor'):
                if not name.strip():st.error('Enter a contractor name')
                elif any(c['name'].lower().strip()==name.lower().strip() and c['token']==fingerprint(p) for c in p['contractors']):st.error('Contractor already exists for this version')
                else:p['contractors'].append({'id':uid('V'),'name':name,'contact':contact,'proposal':ref,'submitted':'','declarations':'','token':fingerprint(p),'answers':{},'prices':{},'assessments':{}});commit(p)
        available=[c for c in p['contractors'] if c['token']==fingerprint(p)]
        if available:
            opts={c['id']+' | '+c['name']:c for c in available};label=st.selectbox('Edit contractor',list(opts));c=opts[label]
            with st.form('edit_return_'+c['id']):
                ref=st.text_input('Recorded proposal reference',c.get('proposal',''));note=st.text_area('Declarations / exclusions',c.get('declarations',''))
                answers=st.data_editor(pd.DataFrame([{'ID':f['id'],'Question':f['question'],'Answer':str(c.get('answers',{}).get(f['id'],''))} for f in p['fields']]),disabled=['ID','Question'],hide_index=True,width='stretch')
                prices=st.data_editor(pd.DataFrame([{'ID':r['id'],'Item':r['item'],'RM excluding tax':c.get('prices',{}).get(r['id'],{}).get('amount'),'Basis / exclusions':c.get('prices',{}).get(r['id'],{}).get('basis','')} for r in p['pricing']]),disabled=['ID','Item'],hide_index=True,width='stretch',column_config={'RM excluding tax':st.column_config.NumberColumn(min_value=0.0)})
                if st.form_submit_button('Save contractor response'):
                    c['proposal']=ref;c['declarations']=note;c['answers']={r['ID']:r['Answer'] for r in answers.to_dict('records')}
                    c['prices']={r['ID']:{'amount':r['RM excluding tax'] if pd.notna(r['RM excluding tax']) else None,'basis':r['Basis / exclusions']} for r in prices.to_dict('records')}
                    c['assessments']={};st.session_state.pop('comparison_export',None);commit(p)
            st.caption('Saving revised answers clears that contractor’s scores so the revised offer is reassessed.')
        else:st.info('Add or import a contractor for the current version.')
    with tabs[3]:
        st.write('**Weights start at zero.** Set AIRB’s own criteria and weights before assessing. Positive weights are normalised to 100%; mandatory pass/fail checks are separate.')
        with st.form('criteria'):
            criteria=st.data_editor(pd.DataFrame(p['criteria']),disabled=['id'],hide_index=True,width='stretch',column_config={'weight':st.column_config.NumberColumn(min_value=0.0),'mandatory':st.column_config.CheckboxColumn()})
            new=st.text_input('Additional assessment criterion');remove=st.multiselect('Remove criterion IDs',[k['id'] for k in p['criteria']])
            if st.form_submit_button('Save scoring criteria'):
                p['criteria']=[r for r in criteria.to_dict('records') if r['id'] not in remove]
                if new.strip():p['criteria'].append({'id':uid('K'),'criterion':new,'weight':0.0,'mandatory':False})
                # Require a fresh assessment if the evaluation basis changes.
                for c in p['contractors']:c['assessments']={}
                commit(p)
        den=sum(k['weight'] for k in p['criteria'])
        st.dataframe(pd.DataFrame([{'Criterion':k['criterion'],'Weight entered':k['weight'],'Effective weight %':k['weight']/den*100 if den else None,'Mandatory':k['mandatory']} for k in p['criteria']]),hide_index=True,width='stretch')
        st.caption('Score scale: 0 = does not meet; 1 = major gaps; 2 = partial; 3 = meets requirement; 4 = exceeds with evidence; 5 = materially exceeds with evidence. Blank means not assessed. AIRB can edit criteria and provide criterion-specific scoring guidance in the criterion text.')
    with tabs[4]:
        contractors=[c for c in p['contractors'] if c['token']==fingerprint(p)]
        if not contractors:st.info('Record contractor responses first.');return
        st.write('**Weighted contribution = score ÷ 5 × effective weight %.** The total appears only when every positively weighted criterion is scored. Mandatory failures/pending checks remain visible and prevent a recommendation.')
        names={c['name']+' | '+c['id']:c for c in contractors};label=st.selectbox('Contractor to assess',list(names));c=names[label]
        with st.form('score_'+c['id']):
            rows=[]
            for k in p['criteria']:
                v=c.get('assessments',{}).get(k['id'],{})
                rows.append({'ID':k['id'],'Criterion':k['criterion'],'Score':v.get('score'),'Mandatory result':v.get('mandatory result','Pending'),'Reason / evidence':v.get('reason',''),'Assessor':v.get('assessor',''),'Assessment date':v.get('date','')})
            scores=st.data_editor(pd.DataFrame(rows),disabled=['ID','Criterion'],hide_index=True,width='stretch',column_config={'Score':st.column_config.NumberColumn(min_value=0,max_value=5,step=1),'Mandatory result':st.column_config.SelectboxColumn(options=['Pending','Pass','Fail'])})
            if st.form_submit_button('Save assessment'):
                c['assessments']={r['ID']:{'score':r['Score'] if pd.notna(r['Score']) else None,'mandatory result':r['Mandatory result'],'reason':r['Reason / evidence'],'assessor':r['Assessor'],'date':r['Assessment date']} for r in scores.to_dict('records')}
                try:commit(p)
                except ValueError as e:st.error(str(e))
        comparison=[];den=sum(k['weight'] for k in p['criteria'])
        for k in p['criteria']:
            row={'Criterion':k['criterion'],'Weight %':round(k['weight']/den*100,2) if den else None}
            for name,v in names.items():
                score=v.get('assessments',{}).get(k['id'],{}).get('score');row[v['name']]=f'{score:g}/5 → {score/5*k["weight"]/den*100:.2f}%' if score is not None and den else 'Not assessed' if score is None else f'{score:g}/5'
            comparison.append(row)
        st.subheader('Side by side scoring matrix');st.dataframe(pd.DataFrame(comparison),hide_index=True,width='stretch')
        summary=[]
        for c in contractors:
            t=totals(p,c);missing=sum(not str(c.get('answers',{}).get(f['id'],'')).strip() for f in p['fields'] if f['required'])
            summary.append({'Contractor':c['name'],'Total %':round(t['total'],2) if t['total'] is not None else None,'Scored criteria':f"{t['coverage']} / {t['count']}",'Mandatory checks':t['mandatory'],'Required answers missing':missing,'Assessment status':'Complete for review' if t['total'] is not None and t['mandatory']=='Pass' and not missing else 'Incomplete / clarification required'})
        st.dataframe(pd.DataFrame(summary),hide_index=True,width='stretch')
        st.subheader('Responses side by side')
        st.dataframe(pd.DataFrame([{'Question':f['question'],**{c['name']:c.get('answers',{}).get(f['id'],'') for c in contractors}} for f in p['fields']]),hide_index=True,width='stretch')
        st.subheader('Prices side by side')
        st.caption('Blank = unquoted. Zero is a quoted zero. No automatic sum combines one-off, annual, optional or provisional charges. Compare the same price basis before judging cost.')
        price_rows=[{'Item':r['item'],**{c['name']:(f"RM {c['prices'][r['id']]['amount']:,.2f} | {c['prices'][r['id']].get('basis','')}" if c.get('prices',{}).get(r['id'],{}).get('amount') is not None else 'Unquoted') for c in contractors}} for r in p['pricing']]
        st.dataframe(pd.DataFrame(price_rows),hide_index=True,width='stretch')
        report='<html><meta charset="utf-8"><title>AIRB Contractor Comparison</title><style>body{font:14px Arial;margin:30px;color:#18334b}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{border:1px solid #ccc;padding:8px;text-align:left;white-space:pre-wrap}th{background:#edf3f7}button{padding:10px}@media print{button{display:none}}</style><h1>AIRB Contractor Comparison</h1><h2>'+html.escape(p['title'])+'</h2><p>Form version '+fingerprint(p)+'</p><p>Weighted contribution = score / 5 x effective weight %. Blank = not assessed. Mandatory checks and missing required answers are shown separately. No automatic award recommendation.</p>'
        for heading,rows in [('Assessment summary',summary),('Scoring matrix',comparison),('Responses',[{'Question':f['question'],**{c['name']:c.get('answers',{}).get(f['id'],'') for c in contractors}} for f in p['fields']]),('Prices and bases',price_rows)]:
            report+='<h2>'+heading+'</h2>'+pd.DataFrame(rows).fillna('Not assessed').to_html(index=False,escape=True)
        report+='<h2>Assessment reasons</h2>'+pd.DataFrame([{'Contractor':c['name'],'Criterion':k['criterion'],**c.get('assessments',{}).get(k['id'],{})} for c in contractors for k in p['criteria']]).fillna('').to_html(index=False,escape=True)+'<button onclick="window.print()">Print or save PDF</button></html>'
        st.download_button('Export printable comparison',report,file_name='AIRB_Contractor_Comparison.html',mime='text/html')
        st.download_button('Export comparison and assessments JSON',json.dumps({'version':fingerprint(p),'criteria':p['criteria'],'summary':summary,'contractors':contractors},indent=2),file_name='AIRB_Contractor_Comparison.json',mime='application/json')

