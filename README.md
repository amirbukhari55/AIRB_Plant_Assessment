# AIRB Plant Assessment — Stage 1

An initial Streamlit assessment app seeded from the two supplied compiled workbooks. It inventories current systems, separates reported capability from verified capability, tracks gaps and proposed upgrades/migration, and summarises management actions. No plant connectivity or telemetry is enabled.

## Run locally

Extract the ZIP into one folder. With Python 3.11 or newer, run:

```
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local address printed by Streamlit. Local changes save in `assessment.sqlite`; keep this file and download assessment backups. Do not commit the database or secrets to GitHub.

## Durable shared storage

For hosted use, run `schema.sql` in a dedicated Supabase project. Configure Streamlit secrets:

```toml
app_password = "choose-a-private-access-password"
[supabase]
url = "https://YOUR-PROJECT.supabase.co"
service_role_key = "YOUR-SERVER-ONLY-SERVICE-ROLE-KEY"
```

Never put the service role key in source code. With these secrets the app uses Supabase and checks concurrent revisions before saving. Without them, it uses local SQLite, which is not durable on Streamlit Community Cloud. Use a private repository and private app access for company information. Shared-password access is an initial prototype arrangement; it does not provide individual accounts or user-level permissions. Agree authenticated roles and change approval before wider staff rollout.

## Hosted deployment in one batch

1. Create a private GitHub repository and upload the contents of this folder directly at the repository root: app.py, model.py, storage.py, source_data.json, requirements.txt, schema.sql and .gitignore.
2. Create a Supabase project, open SQL Editor, paste the full schema.sql and run once. An existing dedicated project can also be used.
3. In Streamlit Community Cloud choose Create app, select that repository and branch, and set the main file to app.py.
4. In Advanced settings / Secrets, paste the TOML block above, fill in the Supabase URL, server-only service-role key and your chosen app password. Deploy with Python 3.11.
5. Open the app, sign in, and review all eight pages. Keep app sharing limited to authorised colleagues. Supabase provides durable shared changes. No plant gateway or SCADA connection is required for this assessment stage.

Do not upload a local assessment.sqlite or secrets.toml to GitHub. If deploying an already reviewed local assessment, download its JSON backup and restore it into the shared app after setup.

## Review sequence

1. Review Overview and Source evidence. Groups differ from the count of source systems/zones.
2. Open each Site assessment and reconcile system scope with the site PIC.
3. Add evidence, reviewer and date before marking a criterion Verified.
4. Update the Gap and upgrade register with actions, owners and quotations.
5. Use the Roadmap to discuss a costed pilot and required upgrade/migration.
6. Export complete JSON backups and CSV actions as needed.

Sixteen criteria cover capabilities and technical readiness. Not applicable criteria are excluded from the verified-count denominator. No weighted readiness percentage is implied. Blank costs mean unquoted. An initial proposed extraction route is not a confirmed interface. No site starts with tested verification.

## Sources and assumptions

Inventory: `AIRB PLC SCADA Inventory Template (compiled 150726).xlsx`. Questionnaire: `PLC Data Extraction Questionnaire (compiled).xlsx`. Source returns mainly date from June–July 2026; current verification is needed. Source JSON preserves inventory row numbers and questionnaire question numbers. Contact details are removed. Top Glove questionnaire scope does not reliably split phases. PAMER mapping is provisional. LAP-owned systems need owner approval. NRW capture cadence differs from platform delivery cadence.

Streamlit interface API reference: https://docs.streamlit.io/develop/api-reference . Streamlit 1.50.0 and Pandas 2.3.3 are the packaged dependency versions. The app is not connected to plant equipment.

## Included pages

Management overview; Site assessment; Engineering and automation; Alarm notification; Gap and upgrade register; Source evidence; Roadmap; Backup and restore.

TG Phase 2 is a user-reported diagnostic benchmark. The selective SMS system site is not identified. Engineering and alarm registers start empty because asset-specific details were not supplied. Populate them through site surveys. No alarm sending, live SCADA monitoring, production totals or automatic purchasing is enabled. Production/revenue and maintenance KPIs are shown as evidence requirements until actual records are supplied.

## Validation

All eight pages ran without exceptions in Streamlit AppTest. Site form persistence, empty engineering/alarm form saves, action form saves, evidence validation and concurrent-save checks passed. The Supabase connection and browser appearance must be confirmed after your deployment; no live plant connection is configured.

## PowerPoint progress report

Open Progress report (PPT), choose all sites or a site, set the date and prepared-by name, and optionally add executive/next-step notes. Upload a previous JSON backup to compare verified criteria and closed actions. Click Generate PowerPoint report, then Download PowerPoint. Save assessment edits first: report generation fetches the latest saved revision. The report uses editable native slides/tables and automatic pagination. Long records are preserved in speaker notes. Include/exclude closed actions and engineering/alarm registers. There are no fabricated live operating figures.

Upload both new files report.py and report_template.pptx along with the updated app.py. No new Python dependencies or database changes are needed. Existing assessment data is retained. Export generation and generated PPTX structure/import/render were checked.


UPDATE 15 OCTOBER 2026
Upload ALL package contents, including presentation_ui.py and the entire assets folder, into the existing GitHub repository root. Keep assets as a folder. Keep existing Streamlit secrets; do not rerun SQL or reset the database. Download an assessment JSON backup before updating.
New: AIRB branding, management progress overview, editable component register, six Ansell photos, searchable TG Phase 2 construction I/O list, vendor clarification reference and additional PPT report evidence. Existing saved site/action data is retained; component defaults are added when old records load. No password is required unless app_password is configured in Secrets.
Evidence is preliminary: photos do not prove performance; the 2021 TG list is not as-built verification. Existing source reports and proposed changes remain separate.

PROCUREMENT WORKSPACE UPDATE
All sites have equal standing; photographs and I/O documents are supporting evidence only.
1. Open Procurement workspace > Build form. Edit scope and questions, click Add field for more, and add price items as needed. Save each form.
2. Issue blank form: record the version, download the HTML form and template backup. Send the same form and attachments to all contractors. The contractor opens HTML in a browser, fills it, downloads completed response JSON and can print to PDF. No entries are sent automatically or saved on closing the page.
3. Import completed response JSON, or manually add each contractor and record its answers and prices. A changed offer clears its scores. Different form versions are excluded from the same comparison.
4. Set scoring criteria and weights. Weights start at zero, pending AIRB choice. Positive weights are normalised to 100 percent. Saving criteria clears all assessment scores.
5. Assess each contractor using 0 to 5 and evidence, assessor and YYYY-MM-DD date. Blank means not assessed. Mandatory pass/fail checks are separate. Final totals remain blank until all weighted criteria are scored; missing required answers and mandatory issues remain visible.
6. Compare responses and prices side by side, and export a printable comparison HTML or detailed JSON. One-off and annual prices are not automatically mixed or summed.
No SQL or Secrets change. Upload all files including procurement.py and assets. Existing site/action/component data stays in the same assessment record. This prototype has shared access; no per-user approval or automatic award workflow is claimed.

CONTRACTOR INFORMATION PACK
Open Contractor information pack in the sidebar. Edit objectives, expected outcomes, concerns, instructions and site details; select Include for the sites in this issue. Add extra sections and choose supporting reference tables and available site evidence. Save each form. Preview and download HTML for browser printing/PDF. Click Link saved information pack to contractor form, then download the complete issue ZIP containing the information brief, selected evidence and aligned blank response form. Send the same ZIP to all bidders.
Changes in pack content or included component records create a different information-pack version; relink before issuing. Relinking changes the contractor form version, retaining but excluding earlier-version returns from current comparisons. Internal bidder scores and other bidders’ responses are never bundled in the issue ZIP.
No SQL or Secrets changes. New file information_pack.py must be uploaded alongside the other files.
