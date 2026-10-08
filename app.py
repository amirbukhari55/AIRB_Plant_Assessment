import copy, hmac, json
from pathlib import Path
import pandas as pd
import streamlit as st
from model import GATES, CAPABILITIES, STATES, DECISIONS, readiness, validate_state
from storage import Store

st.set_page_config(page_title='AIRB Plant Assessment',page_icon='🏭',layout='wide')
try: settings=dict(st.secrets)
except FileNotFoundError: settings={}
password=settings.get('app_password')
if password and not st.session_state.get('authenticated'):
    st.title('AIRB Plant Assessment')
    supplied=st.text_input('Access password',type='password')
    if st.button('Sign in'):
        if hmac.compare_digest(supplied,str(password)):
            st.session_state.authenticated=True;st.rerun()
        else:st.error('Incorrect password')
    st.stop()
config=settings.get('supabase')
store=Store(dict(config) if config else None)
if 'assessment' not in st.session_state:
    try:st.session_state.assessment,st.session_state.revision=store.load()
    except Exception:
        st.error('Could not load the assessment. Check storage configuration and database setup.');st.stop()
data=st.session_state.assessment
source=json.loads((Path(__file__).parent/'source_data.json').read_text())

def save(updated):
    try:
        revision=store.save(updated,st.session_state.revision)
        st.session_state.assessment=updated;st.session_state.revision=revision
        st.success('Assessment saved.');st.rerun()
    except (ValueError,RuntimeError) as e: st.error(str(e))
    except Exception: st.error('Save failed. Check the connection and reload before retrying.')

st.sidebar.title('AIRB • Package A')
page=st.sidebar.radio('Assessment workspace',['Management overview','Site assessment','Engineering and automation','Alarm notification','Gap and upgrade register','Source evidence','Roadmap','Progress report (PPT)','Backup and restore'])
st.sidebar.caption('Stage 1: current conditions and required change')
if st.sidebar.button('Reload saved assessment'):
    del st.session_state['assessment'];st.rerun()
st.sidebar.caption('Shared Supabase storage' if config else 'Local SQLite storage. Cloud deployment needs durable storage.')
st.title(page)
st.caption('Reported June–July 2026 information • Desk assessment dated 7 October 2026 • Verify current conditions at each site')

if page=='Management overview':
    st.info('Objective: remote HQ monitoring, automatic logging and trusted data for operations and other departments. This app tracks readiness; it does not connect to plant controls.')
    segment=st.selectbox('Filter assessment groups',['All']+sorted({s['Segment'] for s in data['sites']}))
    sites=[s for s in data['sites'] if segment=='All' or s['Segment']==segment]
    verified=sum(g['Status']=='Verified' for s in sites for g in s['gates'].values())
    c=st.columns(4)
    applicable=sum(g['Status']!='Not applicable' for s in sites for g in s['gates'].values())
    c[0].metric('Assessment groups',len(sites));c[1].metric('Verified criteria',f'{verified} / {applicable}')
    c[2].metric('Groups with blockers',sum('Blocked' in [g['Status'] for g in s['gates'].values()] for s in sites))
    c[3].metric('Open actions',sum(a['Status']!='Closed' for a in data['actions'] if segment=='All' or a['Site']=='All sites' or a['Site'] in [s['Site'] for s in sites]))
    st.caption('Groups are not a verified count of plants. Sixteen criteria per group; Not applicable is excluded from the denominator. No weighted readiness percentage.')
    st.subheader('Priority capability comparison')
    rows=[{'Site':s['Site'],**{g:s['gates'][g]['Status'] for g in CAPABILITIES}} for s in sites]
    colours={'Unknown':'#f1f5f9','Reported':'#dbeafe','Blocked':'#fee2e2','Verified':'#dcfce7','Not applicable':'#f3f4f6'}
    frame=pd.DataFrame(rows)
    st.dataframe(frame.style.map(lambda v:'background-color: '+colours.get(v,'white'),subset=CAPABILITIES),hide_index=True,width='stretch')
    st.caption('TG Phase 2 is the user-reported local diagnostic benchmark. Remote HQ access and local trending are assessed separately.')
    st.subheader('Production and reliability: evidence required')
    st.dataframe(pd.DataFrame([
      ['Daily production','Flow totaliser, resets, reporting day and production target','Not supplied'],
      ['Production shortfall','Validated daily production versus approved target','Not supplied'],
      ['Revenue exposure','Tariff, billable volume, guarantees and contract billing rules','Not supplied'],
      ['Plant upsets / downtime','Event start/end, cause and affected equipment','Not supplied'],
      ['Maintenance frequency / cost','Work orders, labour, spares and vendor costs','Not supplied']],columns=['Management priority','Evidence to obtain','Actual data']),hide_index=True,width='stretch')
    st.caption('No production/revenue values are fabricated. Shortfall × tariff is an indicative volumetric scenario, not confirmed lost revenue.')
    st.subheader('Submitted equipment inventory')
    inventory=pd.DataFrame(source['System Inventory'])
    counts=inventory['PLC Brand'].value_counts()
    st.bar_chart(counts)
    st.caption('16 system records; 29 reported PLCs. Brand chart counts system records, not PLC units. NRW has 17 populated records. Original workbook totals require corrections.')
    st.subheader('Required decisions')
    st.write('Begin with extraction discovery. Upgrade only where a specific gap requires it. Migrate software or replace hardware after supported integration options, reliability and lifecycle constraints have been evaluated.')

elif page=='Site assessment':
    name=st.selectbox('Site / group',[s['Site'] for s in data['sites']]);index=next(i for i,s in enumerate(data['sites']) if s['Site']==name);site=data['sites'][index]
    st.subheader(site['Current system']);st.write('**Candidate route:** '+site['Candidate route']);st.warning(site['Current gap'])
    st.write('**Current assessment:** '+readiness(site))
    with st.form('site_edit'):
        route=st.text_area('Proposed extraction route',site['Candidate route'])
        gap=st.text_area('Current gaps / system condition',site['Current gap'])
        decision=st.selectbox('Upgrade / migration decision',DECISIONS,index=DECISIONS.index(site['Decision']))
        rows=[{'Criterion':g,**site['gates'][g]} for g in GATES]
        gates=st.data_editor(pd.DataFrame(rows),hide_index=True,width='stretch',disabled=['Criterion'],column_config={'Status':st.column_config.SelectboxColumn(options=STATES,required=True)})
        st.caption('Reported = source/user statement. Verified = tested/documented with evidence, reviewer and date (YYYY-MM-DD). Blocked = obstacle. Unknown = insufficient evidence. Not applicable needs a reason.')
        if st.form_submit_button('Save site assessment'):
            updated=copy.deepcopy(data);target=updated['sites'][index]
            target.update({'Candidate route':route,'Current gap':gap,'Decision':decision})
            target['gates']={r['Criterion']:{k:str(r.get(k,'') or '') for k in ['Status','Evidence','Verified by','Review date']} for r in gates.to_dict('records')}
            save(updated)
    tab=site.get('questionnaire')
    if tab:
        with st.expander('Questionnaire evidence for this group'):
            st.dataframe(pd.DataFrame(source['Questionnaires'][tab]),hide_index=True,width='stretch')
    else:st.caption('No dedicated extraction questionnaire supplied for this group. Consult the system inventory and collect further evidence.')

elif page=='Engineering and automation':
    st.info('Assess each asset separately. Local PLC control, authorised remote commands and safe maintenance isolation are different capabilities. This app issues no control commands.')
    columns=['Site','Asset','Local operation','HQ remote command','Sensor / transmitter','Actuated valve / drive','Position / status feedback','Controller / PLC logic','Pneumatic supply','Interlocks','Physical isolation / LOTO','Gap','Proposed change','Evidence']
    st.caption('No asset-specific hardware information was supplied. Add critical equipment here rather than assuming components are absent.')
    with st.form('engineering'):
        edited=st.data_editor(pd.DataFrame(data['engineering'],columns=columns),num_rows='dynamic',hide_index=True,width='stretch',column_config={
          'Site':st.column_config.SelectboxColumn(options=[s['Site'] for s in data['sites']],required=True),
          'Local operation':st.column_config.SelectboxColumn(options=['Unknown','Manual','PLC / SCADA','Mixed']),
          'HQ remote command':st.column_config.SelectboxColumn(options=['Unknown','Unavailable','Reported','Tested / approved','Not required']),
          **{k:st.column_config.SelectboxColumn(options=['Unknown','Present - reported','Present - verified','Missing','Not required']) for k in columns[4:11]}})
        if st.form_submit_button('Save engineering survey'):
            updated=copy.deepcopy(data);updated['engineering']=json.loads(edited.to_json(orient='records'));save(updated)
    st.write('**Possible scope:** instrumentation, actuators, feedback, PLC logic, pneumatic capacity, power/network and protective interlocks. A site engineer must verify design and isolation requirements before remote control is considered.')

elif page=='Alarm notification':
    st.info('User reports one selective SMS system. Its site and technical details remain unidentified. This register assesses capability and routing; it does not send messages or display live alarms.')
    columns=['Site','Alarm','Severity','Trigger / threshold','Local display','Off-site channel','Recipient roles','Acknowledgement','Escalation','HQ visibility','Status','Gap / action','Evidence']
    with st.form('alarm_rules'):
        edited=st.data_editor(pd.DataFrame(data['alarms'],columns=columns),num_rows='dynamic',hide_index=True,width='stretch',column_config={
          'Site':st.column_config.SelectboxColumn(options=['All sites']+[s['Site'] for s in data['sites']],required=True),
          'Severity':st.column_config.SelectboxColumn(options=['Critical','High','Medium','Low','To define']),
          'Off-site channel':st.column_config.SelectboxColumn(options=['Unknown','None','SMS','Email','Other']),
          'HQ visibility':st.column_config.SelectboxColumn(options=['Unknown','None','Reported','Verified']),
          'Status':st.column_config.SelectboxColumn(options=['Unknown','Reported','Verified','Proposed'])})
        if st.form_submit_button('Save alarm assessment'):
            updated=copy.deepcopy(data);updated['alarms']=json.loads(edited.to_json(orient='records'));save(updated)
    st.write('**Assess:** selective alarm routing, nominated recipients, duplicate suppression, delayed delivery, acknowledgement, escalation and notification during network failure. Later HQ monitoring should show source time, received time, active/cleared state and communication health.')

elif page=='Gap and upgrade register':
    st.caption('Recommendations remain proposed until reviewed. Blank cost means unquoted; it does not mean free. Close actions only after reviewing completion evidence.')
    with st.form('actions'):
        edited=st.data_editor(pd.DataFrame(data['actions']),num_rows='dynamic',hide_index=True,width='stretch',column_config={
          'Site':st.column_config.SelectboxColumn(options=['All sites']+[s['Site'] for s in data['sites']],required=True),
          'Status':st.column_config.SelectboxColumn(options=['Open','In progress','Awaiting vendor','Awaiting owner','Closed'],required=True),
          'Priority':st.column_config.SelectboxColumn(options=['High','Medium','Low'],required=True),
          'Change type':st.column_config.SelectboxColumn(options=['Verification','Data preparation','Licence/interface','Hardware','Connectivity/security','Software migration','Training/support']),
          'One-time RM':st.column_config.NumberColumn(min_value=0.0),'Annual RM':st.column_config.NumberColumn(min_value=0.0)})
        if st.form_submit_button('Save action register'):
            updated=copy.deepcopy(data);updated['actions']=json.loads(edited.to_json(orient='records'))
            used={a['ID'] for a in updated['actions'] if a.get('ID')}
            for a in updated['actions']:
                if not a.get('ID'):
                    number=1
                    while f'A{number:03d}' in used:number+=1
                    a['ID']=f'A{number:03d}';used.add(a['ID'])
            save(updated)
    costs=pd.DataFrame(data['actions'],columns=['ID','Site','Objective','Gap','Proposed action','Change type','Priority','Owner','Status','Evidence','One-time RM','Annual RM','Due date'])
    for column in ['One-time RM','Annual RM']:
        vals=pd.to_numeric(costs[column],errors='coerce');st.write(f'**{column}:** '+(f'RM {vals.sum():,.2f} quoted across {vals.notna().sum()} actions. {vals.isna().sum()} unquoted.' if vals.notna().any() else 'Not quoted yet.'))
    st.download_button('Download action register CSV',costs.to_csv(index=False).encode(),file_name='AIRB_gap_upgrade_register.csv',mime='text/csv')

elif page=='Source evidence':
    tab=st.selectbox('Inventory / evidence table',list(source))
    if tab=='Questionnaires':
        q=st.selectbox('Questionnaire',list(source[tab]));st.dataframe(pd.DataFrame(source[tab][q]),hide_index=True,width='stretch')
    else:st.dataframe(pd.DataFrame(source[tab]),hide_index=True,width='stretch')
    st.subheader('Reconciliation findings')
    st.write('• NRW summary counts IDs rather than zone names: 2 shown versus 17 populated records.\n• Brand categories omit FATEK and do not match GE Fanuc.\n• Challenge categories use the system-type column. Severity counts use frequency.\n• IDs differ across tabs. Top Glove phases and PAMER group mapping need confirmation.\n• Capacities, system ages and numeric tag counts need verification.\n• MAHB remote access and IIUM platform descriptions conflict across returns.')
    st.caption('Original wording is retained where available. Source row identifies the inventory location. Contact details are excluded from these tables. The register contains proposals separately from source evidence.')

elif page=='Roadmap':
    st.dataframe(pd.DataFrame([
      ['Assess current condition','Reconciled register, ownership, stability, support and evidence','Stage 1'],
      ['Select change per site','Retain/integrate, targeted upgrade, software migration or replacement with rationale','Stage 1'],
      ['Approve costed pilot','Quoted equipment/licences/services and acceptance criteria','Decision gate'],
      ['Prove automatic collection','Read-only tests, correct units/time, buffering and no control impact','Future phase'],
      ['Enable HQ monitoring','Central history, freshness indicators, trends and controlled access','Future phase'],
      ['Connect departments','Production/cost reconciliation, procurement planning and HR records','Future phase']],columns=['Workstream','Required result','Phase']),hide_index=True,width='stretch')
    st.subheader('Decision rules')
    st.write('**Integrate existing:** interface and capacity proven, permissions approved.\n\n**Targeted upgrade:** a licence, gateway, network or server limitation can be resolved.\n\n**Software migration:** supported access or maintainability cannot be achieved economically with the current software.\n\n**Replacement:** hardware reliability/lifecycle or capability requires replacement after an engineering review.')
    st.subheader('Department requirements')
    st.write('Finance needs verified billing volumes, tariffs and actual costs. Procurement needs stocks and work orders. HR needs rosters, attendance and competencies. SCADA supplies operating context; business records supply the remaining information.')

elif page=='Progress report (PPT)':
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from report import build_report
    st.write('Generate an editable PowerPoint from the latest saved assessment. Save form changes before generating. Long records continue in slide notes; tables paginate automatically.')
    scope=st.selectbox('Report scope',['All sites']+[s['Site'] for s in data['sites']])
    report_date=st.date_input('Report date',datetime.now(ZoneInfo('Asia/Kuala_Lumpur')).date())
    author=st.text_input('Prepared by','Amir Bukhari')
    summary=st.text_area('Executive summary / progress update')
    next_steps=st.text_area('Next steps / management decisions')
    include_closed=st.checkbox('Include closed actions',False)
    include_registers=st.checkbox('Include engineering and alarm registers',True)
    previous=st.file_uploader('Optional previous assessment backup for progress comparison',type=['json'],key='report_baseline')
    baseline=None;valid=True
    if previous:
        try:baseline=validate_state(json.loads(previous.getvalue()))
        except (ValueError,KeyError,TypeError):st.error('Invalid previous assessment backup.');valid=False
    if st.button('Generate PowerPoint report',disabled=not valid):
        try:
            latest,revision=store.load()
            st.session_state.ppt_report=build_report(latest,report_date.isoformat(),author,scope,baseline,include_closed,include_registers,summary,next_steps,revision)
            st.session_state.ppt_filename='AIRB_Plant_Assessment_Progress_'+report_date.isoformat()+'.pptx'
            st.success('Report generated from saved revision '+str(revision))
        except Exception:st.error('Report generation failed. Check storage and confirm report_template.pptx is uploaded.')
    if st.session_state.get('ppt_report'):
        st.download_button('Download PowerPoint',st.session_state.ppt_report,file_name=st.session_state.ppt_filename,mime='application/vnd.openxmlformats-officedocument.presentationml.presentation')
        st.caption('Download is the last generated report. Regenerate after changing options or saving new assessment data.')

else:
    st.download_button('Download complete assessment backup',json.dumps(data,indent=2),file_name='AIRB_plant_assessment_backup.json',mime='application/json')
    uploaded=st.file_uploader('Restore an assessment backup',type=['json'])
    if uploaded:
        try:
            restored=validate_state(json.load(uploaded));st.write(f"Backup contains {len(restored['sites'])} groups and {len(restored['actions'])} actions.")
            if st.button('Replace saved assessment with this backup'):save(restored)
        except (ValueError,KeyError,TypeError):st.error('Invalid assessment backup. Use a backup exported from this app.')
    st.caption('Backup restores replace the complete assessment. Concurrent saves are checked. Keep backups alongside durable shared storage.')
