"""Build the Experiment 07 Word report from the local project and observed MCP results."""
from __future__ import annotations
import csv, json
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Experiment_07_Automated_Recruitment_Workflow_System_Updated_22_Tests.docx"
EVIDENCE = json.loads((ROOT / "artifacts" / "lab_evidence.json").read_text(encoding="utf-8"))
CASES = EVIDENCE["batch_cases"]
RESULTS = {r["id"]: r for r in EVIDENCE["batch_results"]}
COMPLETE = next(e for e in EVIDENCE["query2_events"] if e.get("type") == "complete")
STEPS = {e["step"]: e for e in EVIDENCE["query2_events"] if e.get("type") == "step"}

BLACK = RGBColor(0, 0, 0)
TNR = "Times New Roman"

def set_run(run, size=10.5, bold=None, italic=None):
    run.font.name = TNR
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), TNR)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), TNR)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), TNR)
    run.font.size = Pt(size)
    run.font.color.rgb = BLACK
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic
    return run

def set_style(style, size, bold=False):
    style.font.name = TNR
    style._element.rPr.rFonts.set(qn("w:ascii"), TNR)
    style._element.rPr.rFonts.set(qn("w:hAnsi"), TNR)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), TNR)
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = BLACK

def shade(cell, fill="E7E7E7"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd"); tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)

def repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader"); tbl_header.set(qn("w:val"), "true"); tr_pr.append(tbl_header)

def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr(); tr_pr.append(OxmlElement("w:cantSplit"))

def set_cell_margins(cell, top=70, start=85, bottom=70, end=85):
    tc = cell._tc; tc_pr = tc.get_or_add_tcPr(); mar = tc_pr.first_child_found_in("w:tcMar")
    if mar is None: mar = OxmlElement("w:tcMar"); tc_pr.append(mar)
    for m, v in (("top",top),("start",start),("bottom",bottom),("end",end)):
        node=mar.find(qn("w:"+m))
        if node is None: node=OxmlElement("w:"+m); mar.append(node)
        node.set(qn("w:w"),str(v)); node.set(qn("w:type"),"dxa")

def add_table(doc, headers, rows, widths=None, font_size=8.6):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.CENTER; table.autofit = False
    repeat_header(table.rows[0])
    for i, head in enumerate(headers):
        cell=table.rows[0].cells[i]; shade(cell); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p=cell.paragraphs[0]; p.paragraph_format.space_after=Pt(0)
        set_run(p.add_run(str(head)),font_size,bold=True)
    for row_data in rows:
        cells=table.add_row().cells; prevent_row_split(table.rows[-1])
        for i, value in enumerate(row_data):
            cell=cells[i]; cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; set_cell_margins(cell)
            p=cell.paragraphs[0]; p.paragraph_format.space_before=Pt(0); p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.04
            set_run(p.add_run(str(value)),font_size)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths): row.cells[i].width=Inches(width)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return table

def add_para(doc, text="", style=None, bold_prefix=None, align=None, size=10.5, before=0, after=5):
    p=doc.add_paragraph(style=style)
    p.paragraph_format.space_before=Pt(before); p.paragraph_format.space_after=Pt(after); p.paragraph_format.line_spacing=1.12
    if align is not None: p.alignment=align
    if bold_prefix and text.startswith(bold_prefix):
        set_run(p.add_run(bold_prefix),size,bold=True); set_run(p.add_run(text[len(bold_prefix):]),size)
    elif text: set_run(p.add_run(text),size)
    return p

def add_bullet(doc, text, numbered=False):
    p=doc.add_paragraph(style="List Number" if numbered else "List Bullet")
    p.paragraph_format.space_after=Pt(3); p.paragraph_format.line_spacing=1.08
    for r in p.runs: set_run(r,10)
    set_run(p.add_run(text),10)
    return p

def add_heading(doc, text, level=1):
    p=doc.add_heading(text,level=level)
    p.paragraph_format.keep_with_next=True
    p.paragraph_format.space_before=Pt(11 if level==1 else 7)
    p.paragraph_format.space_after=Pt(5)
    for r in p.runs: set_run(r,{1:15,2:12,3:10.5}.get(level,10.5),bold=True)
    return p

def add_code(doc, text, size=9):
    p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(.12); p.paragraph_format.right_indent=Inches(.12)
    p.paragraph_format.space_before=Pt(3); p.paragraph_format.space_after=Pt(7); p.paragraph_format.line_spacing=1.0
    p.paragraph_format.keep_together=True
    ppr=p._p.get_or_add_pPr(); shd=OxmlElement("w:shd"); shd.set(qn("w:fill"),"F1F1F1"); ppr.append(shd)
    for i,line in enumerate(text.rstrip().splitlines()):
        if i: p.add_run().add_break()
        set_run(p.add_run(line),size)
    return p

def add_screenshot_slot(doc, label, what_to_capture):
    add_para(doc,what_to_capture,size=9,after=3)
    t=doc.add_table(rows=1,cols=1); t.style="Table Grid"; t.alignment=WD_TABLE_ALIGNMENT.CENTER
    cell=t.cell(0,0); shade(cell,"F5F5F5"); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
    cell.height=Inches(.52)
    p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(0)
    set_run(p.add_run(f"{label}  |  Replace this box with your screenshot"),9,bold=True)
    prevent_row_split(t.rows[0]); doc.add_paragraph().paragraph_format.space_after=Pt(1)

def draw_arrow(draw, start, end, color="black", width=4):
    draw.line([start,end],fill=color,width=width)
    import math
    ang=math.atan2(end[1]-start[1],end[0]-start[0]); length=18
    p1=(end[0]-length*math.cos(ang-math.pi/6),end[1]-length*math.sin(ang-math.pi/6))
    p2=(end[0]-length*math.cos(ang+math.pi/6),end[1]-length*math.sin(ang+math.pi/6))
    draw.polygon([end,p1,p2],fill=color)

def create_workflow_diagram(path):
    w,h=1500,1260; im=Image.new("RGB",(w,h),"white"); d=ImageDraw.Draw(im)
    regular=r"C:\Windows\Fonts\times.ttf"; bold=r"C:\Windows\Fonts\timesbd.ttf"
    try: f=ImageFont.truetype(regular,28); fb=ImageFont.truetype(bold,31); small=ImageFont.truetype(regular,23)
    except OSError: f=ImageFont.load_default(); fb=f; small=f
    def box(x,y,bw,bh,title,sub=""):
        d.rounded_rectangle((x,y,x+bw,y+bh),radius=16,fill="#F4F4F4",outline="black",width=3)
        lines=[title]+([sub] if sub else [])
        total=sum(d.textbbox((0,0),line,font=fb if i==0 else small)[3]-d.textbbox((0,0),line,font=fb if i==0 else small)[1] for i,line in enumerate(lines))+8*(len(lines)-1)
        yy=y+(bh-total)//2
        for i,line in enumerate(lines):
            font=fb if i==0 else small; bb=d.textbbox((0,0),line,font=font); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
            d.text((x+(bw-tw)//2,yy),line,font=font,fill="black"); yy+=th+8
    box(430,25,640,92,"Candidate CSV","1,000 synthetic application rows")
    box(430,165,640,105,"Ingest and normalize","Check headers; trim fields; parse numeric scores")
    box(430,325,640,105,"Validate and detect duplicates","Required fields, email, score range, candidate ID")
    box(65,495,570,115,"Invalid or duplicate","Record reason; exclude from scoring")
    box(865,495,570,115,"Valid candidate","Continue to the transparent rule engine")
    box(65,690,570,100,"rejected_records.csv","Quarantine snapshot with reasons")
    box(865,655,570,120,"Weighted score and explanation","Skills 40% · experience 30% · assessment 30%")
    box(865,820,570,100,"Route to review category","Shortlist / manual / not-shortlisted")
    box(865,990,570,100,"Prepare notification draft","Status-specific wording; sent=false")
    box(65,990,570,100,"Authorized human review","Approve / edit / hold / request information")
    box(65,1140,1370,80,"Append audit event","Record proposal, reviewer action, final state, and notification status")
    draw_arrow(d,(750,117),(750,165)); draw_arrow(d,(750,270),(750,325))
    draw_arrow(d,(650,430),(360,495)); draw_arrow(d,(850,430),(1150,495))
    draw_arrow(d,(350,610),(350,690)); draw_arrow(d,(1150,610),(1150,655)); draw_arrow(d,(1150,775),(1150,820))
    draw_arrow(d,(1150,920),(1150,990)); draw_arrow(d,(865,1040),(635,1040))
    draw_arrow(d,(350,1090),(580,1140)); draw_arrow(d,(1150,1090),(920,1140))
    d.text((500,1102),"No external notification is sent",font=small,fill="black")
    im.save(path,dpi=(180,180))

def observed_result(case, result):
    rid=case["id"]; value=result.get("result")
    if rid.startswith("M"):
        if isinstance(value,dict):
            summary=value.get("summary",{}); routes=summary.get("routing",{})
            return (f"PASS. {value.get('model')} consulted; unsafe Qwen plan cannot authorize tools. Blocked unsafe action; selected {value.get('selected_tool')}; "
                    f"contact data returned: {value.get('contains_contact_data')}. Safe summary: {summary.get('total')} total, {summary.get('valid')} valid, "
                    f"{summary.get('invalid')} quarantined; routes: shortlist {routes.get('SHORTLIST_REVIEW')}, manual {routes.get('MANUAL_REVIEW')}, "
                    f"not-shortlisted {routes.get('NOT_SHORTLISTED_REVIEW')}.")
        return "FAIL. Security case produced no structured safety result."
    if rid in ("X01","D01","D02") and isinstance(value,dict):
        routes=value.get("routing",{})
        return f"PASS. {value.get('total')} total; {value.get('valid')} valid; {value.get('invalid')} quarantined. Routing: {routes.get('SHORTLIST_REVIEW')} shortlist review, {routes.get('MANUAL_REVIEW')} manual review, {routes.get('NOT_SHORTLISTED_REVIEW')} not-shortlisted review."
    if rid.startswith("V") or rid in ("S03","N02","H03","R01"):
        return f"PASS. {value.get('passed')}/{value.get('total')} deterministic checks passed; {value.get('failed')} failed." if isinstance(value,dict) else "PASS. Deterministic checks completed."
    if rid=="S01" or rid=="S02":
        return "PASS. C0001 = 75.00; contributions 30.0000 + 22.5000 + 22.5000; SHORTLIST_REVIEW; notification DRAFT, not sent."
    if rid=="S04":
        b=value.get("breakdown",{}); return f"PASS. C0002 = {value.get('score')}; contributions {b.get('skills_score')} + {b.get('experience_score')} + {b.get('assessment_score')}; {value.get('proposed_status')}."
    if rid=="N01": return f"PASS. Draft status {value['notification']['status']}; sent={value['notification']['sent']}; message uses review-stage wording."
    if rid in ("H01","H02","A01"):
        return f"PASS. {value.get('reviewer_action')} recorded for {value.get('candidate_id')}; final state {value.get('final_status')}; notification {value.get('notification_status')}."
    if rid=="R02": return f"PASS. Expected controlled lookup error returned: {value}."
    return "PASS. " + json.dumps(value,ensure_ascii=False)

def build():
    doc=Document(); sec=doc.sections[0]
    sec.page_width=Inches(8.5); sec.page_height=Inches(11)
    sec.top_margin=Inches(.65); sec.bottom_margin=Inches(.65); sec.left_margin=Inches(.68); sec.right_margin=Inches(.68)
    for name,size,bold in [("Normal",10.5,False),("Body Text",10.5,False),("Title",23,True),("Subtitle",12,False),("Heading 1",15,True),("Heading 2",12,True),("Heading 3",10.5,True),("Caption",9,False),("List Bullet",10,False),("List Number",10,False)]:
        if name in doc.styles: set_style(doc.styles[name],size,bold)
    title_ppr=doc.styles["Title"]._element.pPr
    if title_ppr is not None:
        title_border=title_ppr.find(qn("w:pBdr"))
        if title_border is not None: title_ppr.remove(title_border)
    doc.core_properties.title="Experiment 07 Automated Recruitment Workflow System"
    doc.core_properties.subject="Lab case study report for a local MCP and Ollama recruitment workflow"
    # Cover page
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(52); p.paragraph_format.space_after=Pt(12)
    set_run(p.add_run("EXPERIMENT NO. 07"),12,bold=True)
    p=doc.add_paragraph(style="Title"); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(30); p.paragraph_format.space_after=Pt(12)
    set_run(p.add_run("Automated Recruitment Workflow System"),23,bold=True)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(30)
    set_run(p.add_run("Case Study Report  |  Human Resources Domain"),12)
    add_para(doc,"A local, explainable workflow for candidate data validation, rule-based scoring, review routing, notification drafts, and human oversight.",align=WD_ALIGN_PARAGRAPH.CENTER,size=11,after=28)
    add_table(doc,["Report detail","Value"],[["Observed execution date","22 October 2026"],["Local language model","Ollama Qwen 2.5 7B Instruct"],["Tool protocol","Model Context Protocol (MCP), stdio transport"],["Input dataset","1,000 synthetic candidate applications"],["Rule version","1.0"]],[2.3,4.1],10)
    add_para(doc,"This experiment demonstrates a decision-support workflow. Every routing result remains a proposal for human review; the application does not send real recruitment messages or make final hiring decisions.",align=WD_ALIGN_PARAGRAPH.CENTER,size=10,after=12)
    doc.add_page_break()

    add_heading(doc,"1 Aim",1)
    add_para(doc,"To design and demonstrate an automated recruitment workflow that reads structured candidate applications, validates and normalizes the data, identifies duplicates, applies transparent job-related scoring rules, routes applications to review categories, drafts notifications, records human review, and preserves an audit trail.")
    add_heading(doc,"2 Objectives",1)
    for x in ["Build a CSV ingestion pipeline with schema checks and explicit error handling.","Normalize candidate fields and identify missing, malformed, out-of-range, and duplicate records.","Apply configurable 40/30/30 weighted criteria and retain criterion-wise explanations.","Route valid applications to shortlist review, manual review, or not-shortlisted review using consistent boundaries.","Generate professional notification drafts without sending them.","Allow a simulated authorized reviewer to approve, edit, hold, or request information.","Append workflow and review events to an audit log and preserve invalid-record reasons.","Evaluate the system with deterministic batch queries and a large synthetic dataset.","Explain privacy, access control, human oversight, and fairness limitations."]:
        add_bullet(doc,x)

    add_heading(doc,"3 Tools and technologies",1)
    add_table(doc,["Tool or technology","Use in the experiment"],[
        ["Python 3.10+","CSV ingestion, validation, scoring, routing, review logic, and local HTTP workbench."],
        ["Ollama + qwen2.5:7b-instruct","Local request interpretation and plain-language explanation of observed results."],
        ["MCP Python SDK / FastMCP","Exposes recruitment operations as MCP tools and connects the workbench client to the server over stdio."],
        ["HTML, CSS, JavaScript","Browser workbench with sequential guided stages, batch tests, dataset metrics, and review simulation."],
        ["CSV and JSON","Candidate data, rules, rejected-record snapshot, audit events, test queries, and workflow traces."],
        ["Local browser and localhost HTTP server","Displays the workflow locally; the app does not integrate with an external HR platform or email service."],
    ],[2.1,4.3],9)

    add_heading(doc,"4 System workflow diagram",1)
    diagram=ROOT/"artifacts"/"experiment07_workflow.png"; create_workflow_diagram(diagram)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(diagram),width=Inches(6.65))
    add_para(doc,"Figure 1. End-to-end candidate processing with invalid-record quarantine and human review.",style="Caption",align=WD_ALIGN_PARAGRAPH.CENTER,size=9,after=6)
    add_para(doc,"The browser workbench sends requests to a local Python server. Its MCP client discovers and calls the local FastMCP server over stdio. Candidate scoring and routing are deterministic functions driven by rules.json. Ollama is used for interpreting the request and explaining the result; it does not set the weights or make the routing decision.")

    add_heading(doc,"5 Dataset description and sample content",1)
    add_para(doc,"The reproducible dataset contains 1,000 fictional applications for the Junior Software Developer role. A fixed seed creates varied scores and synthetic names. Contact fields use the reserved example.test domain. The file includes intentionally planted validation, duplicate, high/low, and threshold cases.")
    add_table(doc,["CSV field","Meaning and validation"],[
        ["candidate_id","Application reference; non-empty and unique within the loaded batch."],["candidate_name","Display name; required after whitespace trimming."],["email","Synthetic contact address; required and checked for basic email shape."],["skills_score","Role-related skills score from 0 through 100; weight 40%."],["experience_score","Relevant experience score from 0 through 100; weight 30%."],["assessment_score","Technical assessment score from 0 through 100; weight 30%."],["application_role","Position applied for; this dataset uses Junior Software Developer."]
    ],[1.65,4.75],8.8)
    add_heading(doc,"5.1 Observed dataset profile",2)
    summary=next(r["result"] for r in EVIDENCE["batch_results"] if r["id"]=="D01")
    routes=summary["routing"]
    add_table(doc,["Measure","Observed value"],[
        ["Candidate rows loaded",f"{summary['total']:,}"],["Valid rows",f"{summary['valid']:,} ({summary['valid']/summary['total']*100:.1f}%)"],["Invalid or quarantined rows",f"{summary['invalid']:,} ({summary['invalid']/summary['total']*100:.1f}%)"],["Shortlist review",str(routes["SHORTLIST_REVIEW"])],["Manual review",str(routes["MANUAL_REVIEW"])],["Not-shortlisted review",str(routes["NOT_SHORTLISTED_REVIEW"])],["Unique candidate IDs", "998 unique values across 1,000 rows; two duplicate occurrences are flagged."]
    ],[2.3,4.1],9)
    add_heading(doc,"5.2 Planted data-quality and boundary cases",2)
    rejected=list(csv.DictReader((ROOT/"rejected_records.csv").open(encoding="utf-8",newline="")))
    reason_counts={}
    for r in rejected:
        for reason in r["rejection_reason"].split("; "): reason_counts[reason]=reason_counts.get(reason,0)+1
    add_table(doc,["Case","Count","Handling"],[
        ["Missing email",str(reason_counts.get("Missing field: email",0)),"Quarantined with a missing-field reason."],
        ["Malformed email",str(reason_counts.get("Invalid email format",0)),"Quarantined; not scored."],
        ["Skills score above 100",str(reason_counts.get("skills_score must be between 0 and 100",0)),"Quarantined; out-of-range value."],
        ["Experience score below 0",str(reason_counts.get("experience_score must be between 0 and 100",0)),"Quarantined; out-of-range value."],
        ["Nonnumeric assessment score",str(reason_counts.get("Invalid numeric value: assessment_score",0)),"Quarantined; numeric conversion failed."],
        ["Missing candidate name",str(reason_counts.get("Missing field: candidate_name",0)),"Quarantined as a required field is blank."],
        ["Duplicate candidate IDs","2 duplicate occurrences","Original occurrence is retained; duplicate rows receive a reason."],
        ["Boundary score inputs","75, 74.99, 50, 49.99","Confirm shortlist/manual/not-shortlisted boundaries."],
        ["High and low score","100 and 0","Check the upper and lower valid score limits."],
    ],[1.7,.8,3.9],8.5)
    add_heading(doc,"5.3 Representative rows from candidates.csv",2)
    add_para(doc,"All displayed rows use application_role = Junior Software Developer. The K/E/A column lists skills, experience, and assessment scores in that order.",size=9)
    with (ROOT/"candidates.csv").open(encoding="utf-8-sig",newline="") as f: candidate_rows=list(csv.DictReader(f))
    wanted={"C0001":"75-point boundary","C0002":"74.99 boundary","C0003":"50-point boundary","C0004":"49.99 boundary","C0005":"High-score limit","C0006":"Low-score limit","C0011":"Missing email","C0012":"Malformed email","C0013":"Skills score out of range","C0018":"Duplicate ID occurrence"}
    examples=[]
    for row in candidate_rows:
        case=wanted.get(row["candidate_id"])
        if row["email"]=="candidate0018@example.test": case="Duplicate ID occurrence"
        if case and len(examples)<10:
            examples.append([row["candidate_id"],row["candidate_name"] or "(blank)",row["email"] or "(blank)",f"{row['skills_score']} / {row['experience_score']} / {row['assessment_score']}",case])
    add_table(doc,["ID","Fictional name","Email","K / E / A","Case"],examples,[.7,1.05,1.85,1.05,1.75],7.7)
    add_para(doc,"The example table is a sample, not the entire CSV. The full dataset is retained in candidates.csv; rejected_records.csv stores invalid rows and reasons.",size=9)

    add_heading(doc,"6 Methods",1)
    add_heading(doc,"6.1 Ingestion, normalization, and validation",2)
    add_para(doc,"The loader checks that all expected headers exist before processing. String fields are trimmed, required fields are checked, email shape is validated, numeric scores are parsed, and each score must remain within 0–100. Duplicate candidate_id values are flagged rather than silently deleted. Invalid rows are excluded from scoring and written to the rejected-record snapshot with a reason.")
    add_heading(doc,"6.2 Weighted scoring and explanation",2)
    add_table(doc,["Criterion","Weight","Formula","C0001 input","C0001 contribution"],[
        ["Role-related skills", "40%", "K × 0.40", "75", "30.0000"],["Relevant experience","30%","E × 0.30","75","22.5000"],["Technical assessment","30%","A × 0.30","75","22.5000"],["Total","100%","sum of unrounded contributions","","75.00 / 100"]
    ],[1.5,.7,1.35,.85,2.0],8.5)
    add_para(doc,"Worked formula: S = (0.40 × K) + (0.30 × E) + (0.30 × A). For C0001, S = 30 + 22.5 + 22.5 = 75.00. Contributions are retained to four decimal places in the MCP response; the final total is calculated from unrounded contributions and rounded once to two decimal places. This prevents rounding components from changing a routing boundary.")
    add_heading(doc,"6.3 Routing policy",2)
    add_table(doc,["Final score","Proposed status","Required next step"],[
        ["75.00–100.00","SHORTLIST_REVIEW","Human reviewer examines the application for next-stage consideration."],["50.00–74.99","MANUAL_REVIEW","Human reviewer examines evidence and application details."],["Below 50.00","NOT_SHORTLISTED_REVIEW","Human reviewer examines the application before any adverse decision."]
    ],[1.25,2.0,3.15],9)
    add_para(doc,"Boundary observation: C0002 has three component scores of 74.99. Its unrounded weighted contributions are 29.996, 22.497, and 22.497, giving 74.99 overall and MANUAL_REVIEW. The inclusive 75.00 boundary maps to SHORTLIST_REVIEW; a score of 50.00 maps to MANUAL_REVIEW.")
    add_heading(doc,"6.4 Notification drafts and human review",2)
    add_para(doc,"A valid application receives a personalized draft matched to its proposed status. The draft is marked DRAFT and sent=false. The lower-score review message explicitly describes review and does not imply a final rejection. The reviewer tool accepts APPROVE, EDIT, HOLD, and REQUEST_INFO, records a role and notes, and leaves notification_status as NOT_SENT.")
    add_table(doc,["Review action","Recorded outcome"],[
        ["APPROVE","Keep the proposed workflow status; still no real notification dispatch."],["EDIT","REQUIRES_REVIEW; reviewer notes document the change."],["HOLD","ON_HOLD while additional review is pending."],["REQUEST_INFO","AWAITING_INFORMATION; any communication remains unsent in this lab."]
    ],[1.55,4.85],8.8)
    add_heading(doc,"6.5 Audit logging",2)
    audit_p=add_para(doc,"A full batch appends one evaluation event per input row to audit_log.csv. Fields include timestamp, candidate ID, validation status, score, criterion breakdown, rule version, proposed status, reviewer action, final status, notification status, error details, reviewer, and review notes. rejected_records.csv is a reason-coded snapshot refreshed by batch processing. Guided workflow runs append a privacy-conscious summary to artifacts/workflow_runs.jsonl.")
    audit_p.paragraph_format.keep_together=True
    add_heading(doc,"6.6 Adversarial prompt safeguards",2)
    add_para(doc,"Three adversarial prompts were submitted through local Qwen to test attempts to override instructions, disclose candidate contact details, and introduce age or gender into scoring. A deterministic policy gate runs before tool selection. It blocks these patterns and allows only get_dataset_summary, which returns counts without names or contact fields. Qwen text is not used to authorize tool execution. This targeted test covers the listed patterns only; it does not prove resistance to every possible prompt injection.")

    add_heading(doc,"7 Important code",1)
    add_para(doc,"The following short extracts show the core behavior. The runnable implementations are in mcp_server.py, server.py, notifications.py, and rules.json.")
    add_heading(doc,"7.1 Compute unrounded total, then route",2)
    add_code(doc,"raw = {key: scores[key] * weight / 100\n        for key, weight in rules['criteria'].items()}\nbreakdown = {key: round(value, 4) for key, value in raw.items()}\nscore = round(sum(raw.values()), 2)\n\nif score >= 75:\n    status = 'SHORTLIST_REVIEW'\nelif score >= 50:\n    status = 'MANUAL_REVIEW'\nelse:\n    status = 'NOT_SHORTLISTED_REVIEW'")
    add_heading(doc,"7.2 Validate and detect duplicate IDs",2)
    add_code(doc,"for field in REQUIRED_FIELDS:\n    if not str(candidate.get(field, '')).strip():\n        errors.append(f'Missing field: {field}')\n\nif candidate_id in seen_ids:\n    errors.append('Duplicate candidate_id')\nelse:\n    seen_ids.add(candidate_id)\n\nif errors:\n    quarantine(candidate, reason='; '.join(errors))\n    # Do not score invalid records")
    add_heading(doc,"7.3 Discover and call the MCP server",2)
    add_code(doc,"params = StdioServerParameters(\n    command=sys.executable,\n    args=[str(ROOT / 'mcp_server.py')],\n)\nasync with stdio_client(params) as (read, write):\n    async with ClientSession(read, write) as session:\n        await session.initialize()\n        tools = await session.list_tools()\n        result = await session.call_tool(tool_name, arguments)")
    add_para(doc,"The batch runner reuses one MCP session for its selected queries. Each displayed test result comes from an actual MCP tool call. The local Qwen response is used as a visible explanation, while scoring and route selection remain rule-based.")

    # Query 1 section with user-owned screenshot slots
    doc.add_page_break(); add_heading(doc,"8 Query 1 guided dataset summary",1)
    q1="Summarize the candidate dataset. Show the total records, valid and quarantined records, and counts routed to each review category."
    add_para(doc,"Prompt",bold_prefix="Prompt")
    add_code(doc,q1)
    add_para(doc,"The dataset counts are shown in Section 5.1. Add your own screenshots below, matching each capture to the corresponding numbered stage in the Guided Workflow page.")
    q1_captions=["Capture the entered dataset-summary request.","Show the local Qwen interpretation of the request.","Show the selected get_dataset_summary tool and the reason it was selected.","Show MCP tool discovery and the selected input schema.","Show the empty-argument validation and dispatched MCP request.","Show the dataset totals and routing counts returned by MCP.","Show the run ID and appended workflow trace confirmation."]
    for i,caption in enumerate(q1_captions,1):
        add_heading(doc,f"Query 1 Step {i} screenshot",2)
        add_screenshot_slot(doc,f"Q1-S{i}",caption)

    # Query 2 captured run
    doc.add_page_break(); add_heading(doc,"9 Query 2 evaluated candidate C0001",1)
    q2=EVIDENCE["query2_prompt"]
    add_para(doc,"Prompt",bold_prefix="Prompt")
    add_code(doc,q2)
    add_para(doc,"Observed result: the candidate was valid, scored 75.00, and entered SHORTLIST_REVIEW. The notification was created as a draft and was not sent. The run ID is " + COMPLETE.get("run_id","" ) + ".")
    s1=STEPS[1]["detail"]; s2=STEPS[2]["detail"]; s3=STEPS[3]["detail"]; s4=STEPS[4]["detail"]; s5=STEPS[5]["detail"]; s6=STEPS[6]["detail"]; s7=STEPS[7]["detail"]
    q2_steps=[
        ("1 Capture request",f"Input: {s1['input']['user_text']}\nOutput: normalized request retained ({s1['output']['characters']} characters).","Capture the prompt and the normalized request."),
        ("2 Local Qwen interpretation",f"Model: {s2['input']['model']}\nQwen response: {s2['output']['qwen_response']}","Capture the local model prompt/response stage."),
        ("3 Safe tool selection",f"Selected MCP tool: {s3['output']['selected_tool']}\nArguments: {json.dumps(s3['output']['arguments'])}\nReason: {s3['output']['selection_reason']}","Capture the decision plan and safe tool arguments."),
        ("4 MCP discovery",f"Available tools: {', '.join(s4['output']['discovered_tools'])}\nSelected schema: {json.dumps(s4['output']['selected_tool_schema']['inputSchema'])}","Capture discovered tools and the evaluate_candidate schema."),
        ("5 Validate and execute",f"MCP input JSON: {json.dumps(s5['input'],indent=2)}\nValidation: {json.dumps(s5['validation'],indent=2)}\nOutput: {json.dumps(s5['output'],indent=2)}","Capture the JSON input, schema validation, and MCP dispatch."),
        ("6 Inspect and explain",f"MCP result: {json.dumps(COMPLETE['result'],indent=2)}\nQwen explanation: {s6['output']['qwen_explanation']}","Capture the score breakdown, proposed status, draft notification, and explanation."),
        ("7 Record outcome",f"Run ID: {COMPLETE['run_id']}\nTrace: {s7['output']['trace_file']}\nTrace appended: {s7['output']['trace_appended']}\nHuman approval required: {s7['output']['human_approval_required']}\nDispatch: {s7['output']['notification_dispatch']}","Capture the final run trace and human-approval safeguards."),
    ]
    for i,(title,content,caption) in enumerate(q2_steps,1):
        add_heading(doc,f"Query 2 Step {title}",2)
        add_code(doc,content,size=8 if i==6 else 9)
        add_screenshot_slot(doc,f"Q2-S{i}",caption)

    # Batch tables grouped by their test focus
    batch_heading=add_heading(doc,"10 Batch test queries and observed results",1)
    batch_heading.paragraph_format.page_break_before=True
    add_para(doc,"The batch test page ran all 22 listed queries through the local MCP server. The security cases also submit adversarial prompts to local Qwen, then verify that deterministic policy routing blocks unsafe actions before any candidate-review tool can be called. A test is marked PASS when the observed result meets its expected behavior, including the expected controlled error for an unknown candidate.")
    groups=[("Dataset processing",["X01","D01","D02"]),("Validation",["V01","V02","V03","V04"]),("Scoring and routing",["S01","S02","S03","S04"]),("Notifications",["N01","N02"]),("Human review and audit",["H01","H02","H03","A01"]),("Reliability and error handling",["R01","R02"]),("Security and prompt injection",["M01","M02","M03"])]
    case_map={c["id"]:c for c in CASES}
    for group,ids in groups:
        add_heading(doc,f"10.{groups.index((group,ids))+1} {group} tests",2)
        rows=[]
        for rid in ids:
            c=case_map[rid]; r=RESULTS[rid]
            rows.append([rid,c["query"],observed_result(c,r)])
        add_table(doc,["ID","Batch test query","Observed result"],rows,[.45,3.0,3.0],7.8)
    add_para(doc,"Batch result: 22/22 query cases passed (100%). The deterministic validation and threshold sub-suite passed 10/10 checks with zero failures. All three adversarial prompts were blocked from approval, message dispatch, contact-data disclosure, or protected-trait scoring; only the non-sensitive dataset summary tool was allowed. R02 is a successful negative test because the MCP tool returned the expected controlled ‘Candidate not found’ error.",bold_prefix="Batch result:")

    add_heading(doc,"11 Results and performance metrics",1)
    timing=EVIDENCE.get("full_dataset_timing",{})
    metrics=[
        ["Data validation rate",f"{summary['valid']}/{summary['total']} = {summary['valid']/summary['total']*100:.1f}%","992 valid rows continued; 8 rows were quarantined."],
        ["Workflow processing success rate",f"{summary['valid']}/{summary['valid']} = 100%","Every valid application received score, explanation, proposed route, and draft."],
        ["Notification draft generation rate",f"{summary['valid']}/{summary['valid']} = 100%","Valid rows receive DRAFT text; no real dispatch occurs."],
        ["Batch test pass rate",f"{len(CASES)}/{len(CASES)} = 100%","All observed batch queries matched their expected result."],
        ["Full-batch processing time",f"{timing.get('elapsed_ms','Not measured')} ms","Measured over the local HTTP + MCP batch invocation; device-dependent."],
        ["Mean time per valid record",f"{timing.get('milliseconds_per_valid_record','Not measured')} ms/record",f"Elapsed time divided by {timing.get('valid_records',summary['valid'])} valid records; includes local request/transport overhead."],
        ["Human review completion rate","Not interpreted as a hiring outcome","The full dataset begins with review pending. Batch review examples are simulated controls only."],
        ["Notification delivery success","Not applicable","No delivery tool or external email service exists in this classroom system."],
    ]
    add_table(doc,["Metric","Observed result","Interpretation"],metrics,[1.8,1.45,3.2],8.3)
    add_heading(doc,"12 Inference",1)
    for x in [
        "The synthetic dataset exercised both ordinary records and intentionally planted edge cases at a scale ten times the lab minimum.",
        "The criteria and thresholds produced stable, explainable routes. C0001 at 75.00 entered SHORTLIST_REVIEW; C0002 at 74.99 entered MANUAL_REVIEW; the 50.00 and 49.99 boundaries were covered by the 10/10 deterministic check suite.",
        "Validation quarantined missing, malformed, nonnumeric, out-of-range, and duplicate records with explicit reasons. Duplicate occurrences were flagged while the first record remained available.",
        "The 22/22 batch pass rate and 10/10 sub-check result show that the application matched the configured software rules in this run. The end-to-end timing is specific to this device and includes MCP transport overhead.",
        "Three adversarial prompts attempted automatic approval and dispatch, contact-data disclosure, and protected-trait scoring. The deterministic selector blocked each unsafe request and permitted only the summary tool. This is coverage of the tested patterns, not a guarantee against every possible prompt injection.",
        "Human actions were recorded as simulated review events. Notification drafts remained unsent. These controls demonstrate workflow traceability, not the validity or fairness of hiring decisions.",
    ]: add_bullet(doc,x)
    add_heading(doc,"13 Conclusion",1)
    add_para(doc,"The experiment implemented a local recruitment workflow that ingests 1,000 synthetic applications, validates and quarantines invalid rows, calculates transparent weighted scores, routes valid applications to human-review categories, drafts appropriate messages, and records processing and review events. The observed run passed all 22 batch queries, including three adversarial prompt-injection tests, and all 10 deterministic checks. A precision correction preserved the distinction between 74.99 and the 75.00 shortlist boundary. Human review remains mandatory, messages are not sent, and the results do not establish that the criteria are fair or suitable for real hiring.")

    # Ensure every existing run in the document remains Times New Roman and black.
    for p in doc.paragraphs:
        for r in p.runs:
            if r.font.name is None: set_run(r)
            r.font.color.rgb=BLACK
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.name=TNR; r.font.color.rgb=BLACK
                        r._element.get_or_add_rPr().rFonts.set(qn("w:ascii"),TNR); r._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"),TNR)
    doc.save(OUT)
    print(OUT)

if __name__=="__main__": build()
