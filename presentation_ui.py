"""Management-facing presentation of source evidence; no plant connection."""
import copy,json
from pathlib import Path
import pandas as pd
import streamlit as st
A=Path(__file__).parent/'assets'

def branding():
    st.markdown('''<style>
    .stApp {background:#f5f8fc} [data-testid="stSidebar"] {background:#eaf0f7}
    .block-container {padding-top:5rem;max-width:1450px}
    h1,h2,h3 {color:#123255} [data-testid="stMetric"] {background:white;padding:18px;border-radius:12px;border:1px solid #dee7f0}
    .airb-banner {background:linear-gradient(110deg,#102c4b,#126d79);color:white;padding:26px 30px;border-radius:16px;margin:12px 0 22px}
    .airb-banner h2 {color:white;margin:0} .airb-banner p {margin:8px 0 0;color:#d9edf3}
    </style>''',unsafe_allow_html=True)
    st.sidebar.image(str(A/'airb-logo.png'),width=170)
    st.caption('ALIRAN IHSAN RESOURCES BERHAD · PACKAGE A')
    st.markdown('**Plant systems assessment & HQ monitoring programme**')

def overview(data,source):
    st.markdown('<div class="airb-banner"><h2>From plant-local data to HQ visibility</h2><p>Current condition → initial gaps → preliminary minimum rectification</p></div>',unsafe_allow_html=True)
    st.write('**Progress:** available site returns compiled, system differences reviewed, initial barriers identified, and supporting evidence linked where available. Technical validation and contractor pricing are future steps.')
    c=st.columns(4)
    c[0].metric('Assessment groups',len(data['sites']))
    c[1].metric('Component records',len(data.get('components',[])))
    c[2].metric('Open actions',sum(a['Status']!='Closed' for a in data['actions']))
    c[3].metric('Sites with reported blockers',sum(any(g['Status']=='Blocked' for g in s['gates'].values()) for s in data['sites']))
    st.caption('Evidence coverage describes collected material, not implementation completion. Groups are not a confirmed count of physical plants. Supporting evidence varies by site; missing evidence does not mean missing equipment.')
    t=st.tabs(['Key findings','Minimum change to investigate','Management priorities'])
    with t[0]:
        st.dataframe(pd.DataFrame([
        ['HQ access','User reports dependence on plant-local PCs','Remote connectivity and authorised extraction remain the central gap'],
        ['Diagnostic capability','Interfaces and features vary; TG Phase 2 is the reported benchmark','Retain multi-parameter trending as an explicit requirement'],
        ['Existing components','Component photos and signal documents available for some sites','Assess reuse and record source limitations consistently for every site'],
        ['Alarms','Critical alarms primarily known locally; one selective SMS system reported','Identify existing routing and extend off-site visibility'],
        ['Automation','Some assets lack required ancillaries, as reported by user','Assess per asset; monitoring and remote control are separate scopes']
        ],columns=['Area','Available evidence','Assessment implication']),hide_index=True,width='stretch')
    with t[1]:
        st.dataframe(pd.DataFrame([
        ['All sites','Assess existing systems for reuse','Confirm supported extraction, secure HQ connectivity, logging and alarm interfaces','Resolve site-specific access, hardware, software and evidence gaps'],
        ['Each site / group','Use available inventory, returns, photos and documents','Record targeted rectification only where supported by a gap','No wholesale replacement decision made']
        ],columns=['Scope','Reuse approach','Minimum change to investigate','Uncertainty']),hide_index=True,width='stretch')
        st.info('These are preliminary investigation routes, not confirmed equipment requirements or a contractor-priced scope. Costs are not yet established.')
    with t[2]:
        st.write('Daily production versus target; production shortfall and billing context; upsets and unplanned downtime; maintenance frequency and cost. Actual operational datasets have not been supplied, so no live KPI values are shown.')
        st.write('**Next stage:** validate the specific unknowns, confirm minimum rectification, and prepare a common scope for comparable turnkey proposals when ready.')
    return data['sites']

def evidence_workspace(data,save):
    tabs=st.tabs(['Component register','Site photo evidence','Site signal documents','Tigernix reference'])
    with tabs[0]:
        st.caption('Components are separate from process assets and I/O signals. Photo presence does not establish health or performance. Older saved assessments gain these records without replacing existing site/action data.')
        rows=data.get('components',json.loads((A/'component-seed.json').read_text()))
        with st.form('components'):
            frame=st.data_editor(pd.DataFrame(rows),num_rows='dynamic',hide_index=True,width='stretch',column_config={'Site':st.column_config.SelectboxColumn(options=[s['Site'] for s in data['sites']],required=True),'Evidence status':st.column_config.SelectboxColumn(options=['Visible in photo','Documented design','Previously reported','Not yet confirmed'])})
            if st.form_submit_button('Save component register'):
                updated=copy.deepcopy(data);updated['components']=json.loads(frame.to_json(orient='records'))
                for i,r in enumerate(updated['components'],1):
                    if not r.get('ID'):r['ID']='NEW-'+str(i)
                save(updated)
        st.download_button('Download components CSV',pd.DataFrame(rows).to_csv(index=False),file_name='AIRB_SCADA_components.csv')
    with tabs[1]:
        selected_site=st.selectbox('Site for photographs',[s['Site'] for s in data['sites']],key='photo_site')
        if selected_site!='Ansell':
            st.info('No photographs supplied for this site yet. Existing inventory and questionnaire information remain available in Site assessment.')
        else:
            photo_gallery()
    with tabs[2]:
        selected_site=st.selectbox('Site for signal documentation',[s['Site'] for s in data['sites']],key='signal_site')
        if selected_site!='Top Glove Phase 2':st.info('No detailed I/O document supplied for this site yet. This does not imply no instrumentation is installed.')
        else:signal_document()
    with tabs[3]:
        vendor_reference()

def photo_gallery():
        st.info('User identifies all six photos as Ansell. Photo filenames and the screen show 21 August 2026. AVR is visible; UPS presence is not established. Zero screen readings are not proof of faulty instruments.')
        captions=['PLC assembly, relay bank, breakers and panel wiring','Ethernet switch and Mean Well EDR-75-24 PSU','Rear operator computer, ventilation and panel-door equipment','Operator computer ports and local wiring','Local process mimic, counters and alarm indications','Panel front, local selectors and indicators']
        cols=st.columns(2)
        for i,caption in enumerate(captions,1):cols[(i-1)%2].image(str(A/f'ansell-{i}.jpg'),caption=caption,width='stretch')

def signal_document():
        st.warning('TG Phase 2 only · Rev A · 15 April 2021 · Issued for Construction. Not an as-built or current-condition verification. REMOTE selector signals do not prove HQ access; ISOLATOR_ON does not prove safe physical isolation.')
        st.dataframe(pd.DataFrame([['DI',528,145,383],['DO',176,58,118],['AI',80,22,58],['AO',44,12,32],['Total',828,237,591]],columns=['Type','Listed total','Listed spare','Assigned (total minus spare)']),hide_index=True,width='stretch')
        st.caption('Totals transcribed from source page 26. Channels are not equipment counts, software tag counts or verified present-day capacity.')
        rows=json.loads((A/'tg-signals.json').read_text());kind=st.selectbox('Signal type',['All','DI','DO','AI','AO']);query=st.text_input('Search equipment / signal tag');spares=st.checkbox('Include listed spares',False)
        selected=[r for r in rows if (kind=='All' or r['I/O type']==kind) and (spares or not r['Spare']) and query.lower() in r['Source row'].lower()]
        st.dataframe(pd.DataFrame(selected),hide_index=True,width='stretch')
        st.caption('Searchable source transcription; repeated spare names are retained. Use the original PDF for authoritative column alignment.')
        st.download_button('Download original TG I/O list',(A/'TG_Phase2_IO_List_2021.pdf').read_bytes(),file_name='TG_Phase2_IO_List_2021.pdf')

def vendor_reference():
        st.write('**Supporting ERP reference — vendor statements, not verified delivery.** The present assessment remains focused on plant conditions and HQ monitoring.')
        st.dataframe(pd.DataFrame([
        ['Integration','REST APIs and SCADA/OPC-UA connectors stated','Does not establish compatibility or licence coverage at each plant'],
        ['HR / Admin','Configurable workflows; external payroll integration; seven-year migration stated','Validate field mapping, scope and acceptance later'],
        ['Procurement','Emergency PR, officer assignment and KPI tracking stated','Confirm AIRB workflows and full cost coverage'],
        ['NRW / Municipal','Operational workflows, budget controls and permissions stated','Requires demonstration against AIRB examples'],
        ['Commercial','SGD 80,000 implementation plus SGD 80,000/year subscription; support text also mentions 20%','Obtain an unambiguous fee schedule and support cost base'],
        ['Plant hardware boundary','Proposal Section 10 excludes edge gateway hardware and SCADA/PLC-side upgrades','Quote minimum site rectification and dependencies separately'],
        ['AIRB prerequisites','Proposal assigns power, internet/cellular and network provisions to AIRB','Record who supplies each item and its cost'],
        ['Automatic monitoring','Supported OPC-UA / Ethernet/IP interfaces assumed; manual plants remain manual until upgraded','ERP deployment alone does not complete automatic HQ monitoring']
        ],columns=['Area','Vendor response summary','Open point']),hide_index=True,width='stretch')
        st.download_button('Download vendor clarification reference',(A/'Tigernix_Clarifications.pdf').read_bytes(),file_name='Tigernix_Clarifications.pdf')
