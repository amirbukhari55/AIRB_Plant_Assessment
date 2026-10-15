"""Editable contractor information pack, scoped evidence and offline issue export."""
import copy,hashlib,html,io,json,zipfile
from pathlib import Path
import pandas as pd
import streamlit as st
A=Path(__file__).parent/'assets'

def initial(data):
    return {'title':'AIRB Plant SCADA and HQ Monitoring Information Pack','reference':'','revision':'0','issue_date':'','contact':'','background':'AIRB operates facilities with different SCADA brands, interfaces and monitoring capabilities. Existing data access depends on plant-local PCs. AIRB seeks a contractor proposal for minimum rectification using existing systems where practicable.',
    'objectives':'Assess existing SCADA, PLC and supporting systems across the selected sites.\nIdentify gaps against HQ remote monitoring and automatic data logging.\nPropose minimum rectification and distinguish reuse, configuration, targeted upgrades and migration or replacement.\nProvide comparable itemised proposals with assumptions, exclusions and recurring costs clearly stated.',
    'outcomes':'HQ can remotely view agreed plant data.\nData is logged automatically and available for historical review.\nEngineers can compare multiple parameter trends at a common time for troubleshooting and diagnosis.\nSelected critical alarms reach designated personnel away from the plant and can be viewed at HQ.\nManagement can review daily production versus target, plant upsets, unplanned downtime, and maintenance frequency and cost where the required source records exist.\nRelevant data can support future finance, procurement and HR use through agreed integration.',
    'concerns':'Different SCADA systems offer different features and present different issues.\nSome equipment lacks the automation and ancillaries needed for PLC control.\nCritical alarms are mainly known inside the plant; one selective SMS system is reported but its site is not identified.\nProduction shortfall has revenue implications; billing rules and operating records must be agreed before calculating financial impact.\nAvoid incompatible quotation scopes, overlooked dependencies and future variation exposure.',
    'contractor_instructions':'Review the current information and identify the minimum work needed for each selected site. Do not assume that missing information means equipment is absent. Separate verified facts, reported information and assumptions.\nProvide proposed architecture, supported extraction route, site-specific rectification, quantities, licence coverage, deliverables, testing, training, support and programme.\nExplicitly itemise edge computers or gateways, SCADA/PLC interface upgrades and licences, network/security equipment, power/UPS, instruments and installation where required. Identify anything AIRB must supply. Price common HQ works once and site works separately. Separate one-off, annual, optional and provisional costs. Identify owner permissions, existing vendor work and other prerequisites.\nState proposed logging intervals, history retention, buffering, tag/user capacity and alarm delivery arrangements; these numerical requirements are not yet confirmed by AIRB.\nDistinguish remote monitoring from remote equipment control. Describe control and ancillary upgrades separately; do not assume authorisation for remote control.\nReturn the accompanying AIRB contractor form and a formal technical/commercial proposal. AIRB may issue a common clarification before final price comparison.',
    'limitations':'This is a preliminary desk assessment using available records. Conditions, quantities, licences and access permissions are not fully verified. Assessment groups may not map one-to-one to physical plants. Existing conflicting records are not silently resolved. Detailed evidence is available for some sites only and does not imply priority.\nPhotos show visible components, not tested performance. Construction I/O lists are design records, not confirmation of current installation or software tag counts.',
    'sites':[{'ID':s['id'],'Include':True,'Site / group':s['Site'],'Current system reported':s['Current system'],'Known gap / limitation':s['Current gap'],'Minimum change to investigate':s['Candidate route'],'Evidence basis':'Compiled inventory and extraction questionnaire where supplied; supporting records available in app. Current site verification pending.','Contractor clarification required':'Confirm actual installed components, supported interfaces, access rights, licences, condition and scope boundaries.'} for s in data['sites']],
    'extra_sections':[],'include_source_tables':True,'include_site_files':True}

def validate(pack):
    if not isinstance(pack,dict) or not isinstance(pack.get('sites'),list):raise ValueError('Invalid information pack')
    for k in ['title','reference','revision','issue_date','contact','background','objectives','outcomes','concerns','contractor_instructions','limitations']:
        if not isinstance(pack.get(k),str):raise ValueError('Invalid pack text field '+k)
    ids=[r.get('ID') for r in pack['sites']]
    if not all(ids) or len(ids)!=len(set(ids)):raise ValueError('Pack site IDs must be unique')
    if not any(r.get('Include') for r in pack['sites']):raise ValueError('Select at least one site or group')
    if not isinstance(pack.get('extra_sections'),list):raise ValueError('Invalid additional sections')
    return pack

def payload(pack,data,source):
    sites=[s for s in pack['sites'] if s['Include']];names={s['Site / group'] for s in sites}
    out=copy.deepcopy(pack);out['sites']=sites
    out['component_records']=[r for r in data.get('components',[]) if r.get('Site') in names]
    # Original submitted tables retain source wording and row IDs, not internal contractor scores.
    if pack['include_source_tables']:out['source_tables']=source
    out['evidence_files']=[]
    if pack['include_site_files']:
        if 'Ansell' in names:out['evidence_files'] += [f'ansell-{i}.jpg' for i in range(1,7)]
        if 'Top Glove Phase 2' in names:out['evidence_files'].append('TG_Phase2_IO_List_2021.pdf')
    return out

def token(out):return hashlib.sha256(json.dumps(out,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
def document(out):
    e=html.escape
    chunks=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AIRB Information Pack</title><style>body{font:15px Arial;color:#18334b;max-width:1100px;margin:30px auto;padding:20px}h1{font-size:28px}h2{margin-top:30px}h3{margin-top:22px}p,li{line-height:1.5}pre{font:inherit;white-space:pre-wrap;line-height:1.5}table{border-collapse:collapse;width:100%;margin:15px 0;font-size:13px}td,th{border:1px solid #ccd4df;padding:9px;text-align:left;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}th{background:#edf3f7}button{padding:12px;background:#183b56;color:white;border:0}.scroll{overflow-x:auto}@media print{button{display:none}body{margin:0;padding:0}.scroll{overflow:visible}h2,h3{break-after:avoid}tr{break-inside:avoid}}</style><h1>'+e(out['title'])+'</h1>']
    chunks.append('<p><b>Reference:</b> '+e(out['reference'] or 'Not assigned')+' | <b>Revision:</b> '+e(out['revision'])+' | <b>Issue date:</b> '+e(out['issue_date'] or 'Not entered')+'<br><b>Information pack version:</b> '+token(out)+'<br><b>AIRB contact:</b> '+e(out['contact'] or 'Not entered')+'</p>')
    for title,key in [('Background and current problem','background'),('Objectives','objectives'),('Expected outcomes','outcomes'),('Concerns and dependencies','concerns'),('Instructions to contractor','contractor_instructions'),('Information limitations','limitations')]:chunks.append('<h2>'+title+'</h2><pre>'+e(out[key])+'</pre>')
    chunks.append('<h2>Selected sites and existing systems</h2><p>Proposed rectification routes are preliminary. The contractor shall confirm and justify required works.</p>')
    for r in out['sites']:
        chunks.append('<h3>'+e(r['Site / group'])+'</h3>')
        for k in ['Current system reported','Known gap / limitation','Minimum change to investigate','Evidence basis','Contractor clarification required']:chunks.append('<p><b>'+e(k)+'</b></p><pre>'+e(str(r.get(k,'')))+'</pre>')
    if out.get('component_records'):chunks.append('<h2>Available component records</h2>'+pd.DataFrame(out['component_records']).to_html(index=False,escape=True))
    for r in out['extra_sections']:chunks.append('<h2>'+e(r['Heading'])+'</h2><pre>'+e(r['Content'])+'</pre>')
    chunks.append('<h2>Supporting files</h2><p>'+('<br>'.join(e('evidence/'+x) for x in out['evidence_files']) or 'No site files selected.')+'</p><p>Evidence is supplied only where available. The named site files do not define the overall programme scope. Refer to source dates and revision status.</p>')
    if out.get('source_tables'):
        chunks.append('<h2>Submitted reference tables</h2><p>These are compiled source returns, including records outside the selected quotation scope. Only the selected sites above define the requested scope. Conflicting statements remain for clarification. Source row and questionnaire references are retained where available.</p>')
        for name,rows in out['source_tables'].items():
            chunks.append('<h3>'+e(name)+'</h3>')
            if isinstance(rows,dict):
                for sub,items in rows.items():chunks.append('<h4>'+e(sub)+'</h4><div class="scroll">'+pd.DataFrame(items).to_html(index=False,escape=True)+'</div>')
            else:chunks.append('<div class="scroll">'+pd.DataFrame(rows).to_html(index=False,escape=True)+'</div>')
    chunks.append('<button onclick="window.print()">Print or save PDF</button></html>')
    return ''.join(chunks)

def bundle(out,rfq):
    from procurement import blank_html,fingerprint
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('AIRB_Information_Pack.html',document(out))
        z.writestr('AIRB_Information_Pack.json',json.dumps(out,indent=2,ensure_ascii=False))
        z.writestr('AIRB_Blank_Contractor_Form.html',blank_html(rfq))
        z.writestr('READ_ME.txt','Open AIRB_Information_Pack.html for the brief and site records. Open AIRB_Blank_Contractor_Form.html to fill answers and download response JSON for AIRB. HTML files work offline. Print them to PDF if preferred. Evidence files are under evidence/.\nInformation pack version: '+token(out)+'\nContractor response form version: '+fingerprint(rfq)+'\nSend the same issue package to every contractor. Internal contractor scores and competing proposals are not included.\n')
        for name in out['evidence_files']:
            f=A/name
            if not f.is_file():raise ValueError('Missing supporting file '+name)
            z.write(f,'evidence/'+name)
    return b.getvalue()

def render(data,source,save):
    pack=copy.deepcopy(data.get('contractor_information_pack',initial(data)))
    def commit(value):
        validate(value);u=copy.deepcopy(data);u['contractor_information_pack']=value;save(u)
    st.write('Prepare a common brief for every contractor: objectives, expected outcomes, available site systems, gaps and supporting evidence. All sites are selectable; additional evidence does not imply priority.')
    tabs=st.tabs(['Objectives and instructions','Site system details','Additional sections','Preview and download'])
    with tabs[0]:
        with st.form('pack_brief'):
            title=st.text_input('Information pack title',pack['title']);ref=st.text_input('Pack / RFQ reference',pack['reference']);revision=st.text_input('Revision',pack['revision']);issued=st.text_input('Issue date',pack['issue_date'],placeholder='YYYY-MM-DD');contact=st.text_input('AIRB contact for contractor enquiries',pack['contact'])
            values={}
            for label,key in [('Background / problem statement','background'),('Objectives','objectives'),('Expected outcomes','outcomes'),('Concerns and dependencies','concerns'),('Contractor instructions and quotation boundary','contractor_instructions'),('Evidence limitations and unknowns','limitations')]:values[key]=st.text_area(label,pack[key],height=160)
            if st.form_submit_button('Save objectives and instructions'):pack.update(title=title,reference=ref,revision=revision,issue_date=issued,contact=contact,**values);commit(pack)
    with tabs[1]:
        st.caption('Prepopulated from the current assessment when this pack is first created. Later changes in Site assessment are not silently substituted into your edited brief. Use Refresh below for a selected site. Supporting component records follow the current component register.')
        with st.form('pack_sites'):
            rows=st.data_editor(pd.DataFrame(pack['sites']),hide_index=True,width='stretch',disabled=['ID','Site / group'],column_config={'Include':st.column_config.CheckboxColumn('Include in contractor scope')})
            if st.form_submit_button('Save site information'):
                pack['sites']=rows.to_dict('records')
                try:commit(pack)
                except ValueError as e:st.error(str(e))
        selected=st.selectbox('Refresh one site from latest assessment',[s['Site / group'] for s in pack['sites']])
        st.caption('Refresh replaces the selected site’s system, gap and proposed route text. Other edited fields remain.')
        if st.button('Refresh selected site details'):
            old=next(s for s in pack['sites'] if s['Site / group']==selected);latest=next(s for s in data['sites'] if s['id']==old['ID']);old.update({'Current system reported':latest['Current system'],'Known gap / limitation':latest['Current gap'],'Minimum change to investigate':latest['Candidate route']});commit(pack)
    with tabs[2]:
        with st.form('pack_add_section'):
            heading=st.text_input('New section heading');content=st.text_area('New section content')
            if st.form_submit_button('Add section'):
                if heading.strip():pack['extra_sections'].append({'Heading':heading,'Content':content});commit(pack)
                else:st.error('Enter a heading')
        if pack['extra_sections']:
            with st.form('edit_extra_pack'):
                edited=st.data_editor(pd.DataFrame(pack['extra_sections']),num_rows='dynamic',hide_index=True,width='stretch')
                if st.form_submit_button('Save additional sections'):
                    pack['extra_sections']=[r for r in edited.to_dict('records') if str(r.get('Heading','')).strip()];commit(pack)
        with st.form('pack_files'):
            files=st.checkbox('Include supplied site photos and I/O files where available',pack['include_site_files']);tables=st.checkbox('Include compiled reference tables and questionnaires',pack['include_source_tables'])
            if st.form_submit_button('Save supporting evidence options'):pack.update(include_site_files=files,include_source_tables=tables);commit(pack)
    with tabs[3]:
        try:validate(pack);out=payload(pack,data,source)
        except ValueError as e:st.error(str(e));return
        version=token(out);st.write('**Current information pack version:** '+version)
        st.write('**Selected sites / groups:** '+', '.join(r['Site / group'] for r in out['sites']))
        st.dataframe(pd.DataFrame(out['sites']),hide_index=True,width='stretch')
        st.write('**Supporting files:** '+str(len(out['evidence_files']))+' files; component records: '+str(len(out.get('component_records',[]))))
        st.download_button('Download information pack HTML',document(out),file_name='AIRB_Information_Pack.html',mime='text/html')
        st.write('**To issue one aligned package:** save the pack, then link this version to the procurement form. Changing the information pack changes the quotation basis; older responses remain stored but are excluded from the new version’s comparison.')
        from procurement import seed,fingerprint
        rfq=copy.deepcopy(data.get('procurement',seed()));linked=rfq.get('information_pack_version')==version
        if st.button('Link saved information pack to contractor form'):
            u=copy.deepcopy(data);u['contractor_information_pack']=pack;rfq['information_pack_version']=version;rfq['information_pack_title']=pack['title'];u['procurement']=rfq;u.setdefault('information_pack_issues',[]).append({'version':version,'payload':out,'response_version':fingerprint(rfq)});save(u)
        if linked:
            st.success('This pack is linked to the contractor response form.')
            try:st.download_button('Download complete contractor issue ZIP',bundle(out,rfq),file_name='AIRB_Contractor_Information_Pack_'+version+'.zip',mime='application/zip')
            except ValueError as e:st.error(str(e))
        else:st.info('Link the current version above to enable the combined ZIP download.')
        st.caption('The ZIP contains the brief, site details, source references, selected evidence and a blank response form. Internal contractor scores and competing proposals are excluded. Open the HTML brief in a browser to print or save as PDF. Save form edits before downloading.')
