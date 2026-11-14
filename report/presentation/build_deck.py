"""Builds the final-review deck on the department template.

Needs python-pptx (pip install python-pptx). Run from anywhere:
    python report/presentation/build_deck.py report/presentation/CodePath_Final_Review.pptx
"""
import copy
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from pathlib import Path as _P
HERE = _P(__file__).resolve().parent
TEMPLATE = str(HERE.parents[2] / "S7_Project_ReportTemplate" / "final review PPT Template.pptx")
ASSETS = str(HERE / "assets")
SCREENS = str(HERE.parent / "figures" / "screens")
OUT = sys.argv[1]

FONT = "Arial"              # body text: on every Mac and Windows PC, with standard numerals; titles keep the template's Georgia
CRIMSON = "A4123F"          # the template's title colour
DARK = "222222"
GREY = "5B5B5B"
LIGHT = "F3F3F5"
TINT = "FBEFF3"
LINE = "D9D9DE"
GREEN = "1E7B34"
GREEN_T = "E6F3EA"
AMBER = "A15C00"
AMBER_T = "FCF1E1"
WHITE = "FFFFFF"
SDG_RED = "C5192D"
FOOTER_TEXT = "Adaptive Multi-Agent AI Tutoring System for Personalized Programming Education"


def rgb(h):
    return RGBColor.from_string(h)


# ---------------------------------------------------------------- text helpers

def add_bullet(p, color=CRIMSON, indent=0.26):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent))))
    pPr.set("indent", str(-int(Inches(indent - 0.04))))
    clr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", color)
    etree.SubElement(pPr, qn("a:buSzPct")).set("val", "100000")
    bf = etree.SubElement(pPr, qn("a:buFont"))
    bf.set("typeface", "Arial")
    etree.SubElement(pPr, qn("a:buChar")).set("char", "•")


def fill(tf, paras, size=16, color=DARK, bold=False, align=PP_ALIGN.LEFT, space_after=4, line_spacing=None, font=FONT):
    tf.clear()
    for i, spec in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if isinstance(spec, str):
            spec = {"text": spec}
        runs = spec.get("runs") or [(spec.get("text", ""), {})]
        p.alignment = spec.get("align", align)
        sa = spec.get("space_after", space_after)
        if sa is not None:
            p.space_after = Pt(sa)
        ls = spec.get("line_spacing", line_spacing)
        if ls:
            p.line_spacing = ls
        for text, opt in runs:
            r = p.add_run()
            r.text = text
            f = r.font
            f.name = opt.get("font", spec.get("font", font))
            f.size = Pt(opt.get("size", spec.get("size", size)))
            f.bold = opt.get("bold", spec.get("bold", bold))
            f.italic = opt.get("italic", spec.get("italic", False))
            f.color.rgb = rgb(opt.get("color", spec.get("color", color)))
        if spec.get("bullet"):
            add_bullet(p, spec.get("bullet_color", CRIMSON))


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.04, **kw):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    fill(tf, paras, **kw)
    return box


def shape(slide, x, y, w, h, fill_color=None, line_color=None, radius=0.1, kind=MSO_SHAPE.ROUNDED_RECTANGLE, line_width=1.0, dash=False):
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = radius
    if fill_color:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill_color)
    else:
        shp.fill.background()
    if line_color:
        shp.line.color.rgb = rgb(line_color)
        shp.line.width = Pt(line_width)
        if dash:
            from pptx.enum.dml import MSO_LINE
            shp.line.dash_style = MSO_LINE.DASH
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def label(shp, paras, anchor=MSO_ANCHOR.MIDDLE, margin=0.08, **kw):
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    tf.vertical_anchor = anchor
    kw.setdefault("align", PP_ALIGN.CENTER)
    fill(tf, paras, **kw)
    return shp


def arrow(slide, x1, y1, x2, y2, color=GREY, width=1.75, dash=False, head=True):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if dash:
        from pptx.enum.dml import MSO_LINE
        c.line.dash_style = MSO_LINE.DASH
    if head:
        ln = c.line._get_or_add_ln()
        t = etree.SubElement(ln, qn("a:tailEnd"))
        t.set("type", "triangle")
        t.set("w", "med")
        t.set("len", "med")
    return c


def table(slide, x, y, col_w, rows, row_h=0.42, header_h=None, size=12, header_size=13, header_fill=CRIMSON, zebra=LIGHT,
          first_col_bold=True, highlight_rows=(), center_cols=(), aligns=None):
    nrows, ncols = len(rows), len(rows[0])
    total_w = sum(col_w)
    gf = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(total_w), Inches(row_h * nrows))
    tbl = gf.table
    tbl.first_row = True
    tbl.horz_banding = False
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(header_h if (i == 0 and header_h) else row_h)
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.07)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if i == 0:
                cell.fill.fore_color.rgb = rgb(header_fill)
            elif i in highlight_rows:
                cell.fill.fore_color.rgb = rgb(TINT)
            else:
                cell.fill.fore_color.rgb = rgb(zebra if i % 2 == 0 else WHITE)
            al = PP_ALIGN.CENTER if j in center_cols else (aligns[j] if aligns else PP_ALIGN.LEFT)
            if i == 0:
                spec = [{"text": val, "bold": True, "color": WHITE, "size": header_size, "align": al}]
            elif isinstance(val, dict):
                spec = [dict({"size": size, "align": al}, **val)]
            else:
                spec = [{"text": val, "size": size, "align": al,
                         "bold": (first_col_bold and j == 0) or i in highlight_rows,
                         "color": CRIMSON if i in highlight_rows else DARK}]
            fill(cell.text_frame, spec, space_after=0)
    return gf


def picture(slide, path, x, y, w=None, h=None, border=True):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    pic = slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)
    if border:
        pic.line.color.rgb = rgb(LINE)
        pic.line.width = Pt(1)
    return pic


def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body


def circle_number(slide, x, y, d, txt, fill_color=CRIMSON, size=14, color=WHITE):
    c = shape(slide, x, y, d, d, fill_color, kind=MSO_SHAPE.OVAL)
    label(c, [{"text": txt, "bold": True, "size": size, "color": color}], margin=0.0)
    return c


# ---------------------------------------------------------------- deck setup

prs = Presentation(TEMPLATE)
title_slide, outline_slide = prs.slides[0], prs.slides[1]
content_layout = prs.slides[2].slide_layout
title_layout = title_slide.slide_layout
sldnum_el = copy.deepcopy([s for s in prs.slides[2].shapes if s.name.startswith("Slide Number")][0]._element)
footer_el = copy.deepcopy([s for s in outline_slide.shapes if s.name == "TextBox 5"][0]._element)
logo_shape = [s for s in title_slide.shapes if s.shape_type == 13][0]
with open(f"{ASSETS}/amrita_logo_white.png", "wb") as fh:
    fh.write(logo_shape.image.blob)

# Remove the template's placeholder content slides 3-19; slides 1 and 2 are filled in place.
sld_ids = prs.slides._sldIdLst
for sld_id in list(sld_ids)[2:]:
    prs.part.drop_rel(sld_id.rId)
    sld_ids.remove(sld_id)


def set_footer(slide, el):
    for t in el.iter(qn("a:t")):
        t.text = ""
    first = next(el.iter(qn("a:t")))
    first.text = FOOTER_TEXT
    for r in el.iter(qn("a:rPr")):
        r.set("sz", "1200")


def content_slide(title):
    s = prs.slides.add_slide(content_layout)
    s.shapes.title.text = title
    for ph in list(s.placeholders):
        if ph.placeholder_format.idx == 1:
            ph._element.getparent().remove(ph._element)
    s.shapes._spTree.append(copy.deepcopy(sldnum_el))
    el = copy.deepcopy(footer_el)
    set_footer(s, el)
    s.shapes._spTree.append(el)
    return s


# ---------------------------------------------------------------- 1. Title

shapes = {s.name: s for s in title_slide.shapes}
t = shapes["TextBox 1"]
t.left, t.top, t.width, t.height = Inches(5.45), Inches(2.5), Inches(7.6), Inches(1.4)
run = t.text_frame.paragraphs[0].runs[0]
run.text = "Adaptive Multi-Agent AI Tutoring System for Personalized Programming Education"
run.font.size = Pt(24)
text(title_slide, 5.5, 4.0, 7.5, 0.45, [{"text": "CodePath: a tutor that helps beginners think, not copy", "italic": True, "color": WHITE, "size": 16, "font": "Times New Roman"}])
g = shapes["TextBox 9"]
g.left, g.top, g.width = Inches(5.5), Inches(4.6), Inches(4.5)
paras = g.text_frame.paragraphs
paras[0].runs[0].text = "Guided by"
paras[1].runs[0].text = "Ms. Anju Sukumar"
for p in paras:
    for r in p.runs:
        r.font.size = Pt(16)
paras[1].runs[0].font.bold = True
nm = shapes["TextBox 3"]
nm.left, nm.top, nm.width, nm.height = Inches(5.5), Inches(5.38), Inches(6.5), Inches(1.35)
team = [("Kataru Reddy Eswar", "AM.SC.U4CSE23126"), ("Bharath Bommineni", "AM.SC.U4CSE23112"),
        ("Chimmili Lokesh", "AM.SC.U4CSE23114"), ("Ramisetti Gowtham Tej", "AM.SC.U4CSE23144")]
for p, (n, r) in zip(nm.text_frame.paragraphs, team):
    p.runs[0].text = f"{n}   {r}"
    p.runs[0].font.size = Pt(15)
notes(title_slide, "Opening (presenter 1). Good morning. We are presenting our final-year project, an adaptive multi-agent AI tutor for beginner programmers, called CodePath. Our guide is Ms. Anju Sukumar. In one line: when a beginner is stuck, our tutor gives only the help they need at that moment, like a teacher sitting beside them, and never the full answer.")

# ---------------------------------------------------------------- 2. Outline

body = [s for s in outline_slide.placeholders if s.placeholder_format.idx == 1][0]
body._element.getparent().remove(body._element)
items = ["Introduction", "Problem Definition", "Objectives", "Literature Review", "Research Gap",
         "Datasets, Platforms, and Implementation Tools", "Proposed Methodology", "Evaluation Setup and Criteria",
         "Results and Analysis", "Discussion and Limitations", "Conclusion", "Future Work", "Project Time Line",
         "Team Contribution", "Reference", "Appendix A: Code and Demo"]
for i, item in enumerate(items):
    c_, r_ = divmod(i, 8)
    x = 0.62 + c_ * 6.24
    y = 1.22 + r_ * 0.68
    shape(outline_slide, x, y, 5.85, 0.56, LIGHT, radius=0.5)
    circle_number(outline_slide, x + 0.08, y + 0.06, 0.44, f"{i + 1:02d}", size=13)
    text(outline_slide, x + 0.68, y, 5.1, 0.56, [{"text": item, "size": 17, "color": DARK}], anchor=MSO_ANCHOR.MIDDLE)
footer_box = [s for s in outline_slide.shapes if s.name == "TextBox 5"][0]
set_footer(outline_slide, footer_box._element)
notes(outline_slide, "This is the flow of our talk. We start with why the problem matters, then the literature and the gap, then our six-agent method, how we evaluated it, the results, and what comes next. The demo details are in the appendix.")

# ---------------------------------------------------------------- 3. Introduction

s = content_slide("Introduction: Background and Motivation")
left = shape(s, 0.62, 1.25, 5.75, 3.45, LIGHT)
text(s, 0.85, 1.42, 5.3, 0.45, [{"text": "Today: AI tools give the answer", "bold": True, "size": 20, "color": DARK}])
text(s, 0.85, 1.98, 5.35, 2.6, [
    {"text": "Write a full solution in seconds", "bullet": True},
    {"text": "Same help for every learner, with no memory of how they are doing", "bullet": True},
    {"text": "Beginners copy instead of thinking: a 2024 study of a ChatGPT tutor reported over-reliance", "bullet": True},
], size=18, space_after=10)
right = shape(s, 6.96, 1.25, 5.75, 3.45, TINT)
text(s, 7.19, 1.42, 5.3, 0.45, [{"text": "A good teacher does more", "bold": True, "size": 20, "color": CRIMSON}])
text(s, 7.19, 1.98, 5.35, 2.6, [
    {"text": "Notices where the student is stuck", "bullet": True},
    {"text": "Gives only the next step, not the answer", "bullet": True},
    {"text": "Asks the student to explain their thinking", "bullet": True},
    {"text": "Chooses what to practise next", "bullet": True},
], size=18, space_after=10)
circle_number(s, 6.42, 2.68, 0.5, "vs", fill_color=DARK, size=14)
aim = shape(s, 0.62, 4.92, 12.09, 0.8, CRIMSON)
label(aim, [{"text": "Our aim: an AI tutor that behaves like a teacher sitting beside the student", "bold": True, "size": 20, "color": WHITE}])
sdg = shape(s, 0.62, 5.95, 0.72, 0.72, SDG_RED, radius=0.08)
label(sdg, [{"text": "SDG", "bold": True, "size": 11, "color": WHITE, "space_after": 0}, {"text": "4", "bold": True, "size": 20, "color": WHITE}], margin=0.0, space_after=0)
text(s, 1.5, 5.95, 11.2, 0.72, [
    {"runs": [("UN SDG 4: Quality Education.  ", {"bold": True}), ("Target 4.4: more youth and adults with relevant skills for employment. Programming is one of those skills; our tutor helps beginners build it themselves.", {})]},
], size=15, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "AI assistants like ChatGPT can write a beginner's whole program in seconds. That is convenient, but it gives everyone the same help and the learner does not build their own reasoning. A 2024 classroom study of a ChatGPT-based tutor, PyTutor, found exactly this risk of over-reliance. A good human teacher behaves differently: they notice where you are stuck, give just the next step, ask you to explain, and choose your next exercise. Our aim is a tutor that does what that teacher does. This links to UN Sustainable Development Goal 4, Quality Education, target 4.4: building skills for employment.")

# ---------------------------------------------------------------- 4. Problem Definition

s = content_slide("Problem Definition")
ps = shape(s, 0.62, 1.22, 12.09, 1.15, TINT)
label(ps, [{"runs": [("Problem statement: ", {"bold": True, "color": CRIMSON}),
                     ("after every learner action, decide what went wrong, how much the learner knows, and whether and how much to help, without ever giving the full solution.", {})]}],
      size=19, align=PP_ALIGN.LEFT, margin=0.2)
inp = shape(s, 0.62, 2.7, 3.7, 3.1, LIGHT)
text(s, 0.82, 2.82, 3.3, 0.4, [{"text": "Input", "bold": True, "size": 18, "color": CRIMSON}])
text(s, 0.82, 3.3, 3.35, 2.4, [
    {"text": "Learner action: Run, Submit, Ask for a hint, or a question", "bullet": True},
    {"text": "The exact version of the code", "bullet": True},
    {"text": "Learner history: attempts, hints, answers", "bullet": True},
], size=15, space_after=6)
core = shape(s, 4.85, 3.2, 3.2, 2.1, CRIMSON, radius=0.18)
label(core, [{"text": "CodePath", "bold": True, "size": 24, "color": WHITE, "space_after": 2},
             {"text": "6 cooperating AI agents", "size": 15, "color": WHITE}])
arrow(s, 4.35, 4.25, 4.82, 4.25, CRIMSON, 2.5)
arrow(s, 8.08, 4.25, 8.55, 4.25, CRIMSON, 2.5)
out = shape(s, 8.58, 2.7, 4.13, 3.1, LIGHT)
text(s, 8.78, 2.82, 3.7, 0.4, [{"text": "Output", "bold": True, "size": 18, "color": CRIMSON}])
text(s, 8.78, 3.3, 3.85, 2.45, [
    {"text": "Diagnosis with evidence", "bullet": True},
    {"text": "Estimate of the learner's state", "bullet": True},
    {"text": "Help decision: wait, offer or show, and how much", "bullet": True},
    {"text": "One checked hint, never a solution", "bullet": True},
    {"text": "Reflection question, and the next problem", "bullet": True},
], size=15, space_after=4)
for i, (who, why) in enumerate([("Learners", "help that keeps them thinking"), ("Teachers", "see who needs support"), ("Institution", "untrusted code runs safely")]):
    pill = shape(s, 0.62 + i * 4.08, 6.05, 3.93, 0.58, WHITE, LINE, radius=0.5)
    label(pill, [{"runs": [(who + ": ", {"bold": True, "color": CRIMSON}), (why, {})]}], size=14)
notes(s, "Our problem in one sentence: after every action the learner takes, the tutor must decide what went wrong, how much the learner already knows, and whether and how much to help, and it must never hand over the full solution. The input is the learner's action, the exact code, and their history. The output is a diagnosis, a learner-state estimate, a help decision, at most one checked hint, a reflection question and the next problem. Three groups benefit: learners, teachers, and the institution, which needs untrusted student code to run safely.")

# ---------------------------------------------------------------- 5. Objectives

s = content_slide("Objectives")
objs = [("O1", "Multi-agent tutor", "Six collaborating agents in one learning cycle, not a single chatbot"),
        ("O2", "Learner state", "Estimate knowledge, confidence, confusion, overload and progress"),
        ("O3", "Similar learners", "Find what helped in similar situations, using cosine similarity"),
        ("O4", "Scaffolding algorithm", "DSDA chooses how much help from state, hint history and time"),
        ("O5", "Evaluation", "Verify on programming problems and real tutoring scenarios")]
cw, gap = 2.29, 0.16
for i, (code, head, desc) in enumerate(objs):
    x = 0.62 + i * (cw + gap)
    shape(s, x, 1.35, cw, 3.85, LIGHT)
    circle_number(s, x + cw / 2 - 0.42, 1.6, 0.84, code, size=18)
    text(s, x + 0.12, 2.65, cw - 0.24, 0.75, [{"text": head, "bold": True, "size": 17, "align": PP_ALIGN.CENTER, "color": DARK}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.14, 3.45, cw - 0.28, 1.6, [{"text": desc, "size": 15, "align": PP_ALIGN.CENTER, "color": GREY}])
rule = shape(s, 0.62, 5.5, 12.09, 0.95, TINT)
label(rule, [{"runs": [("Guiding rule  ", {"bold": True, "color": CRIMSON}), ("Help like a teacher: never the full solution, and more help only when the learner asks for it", {})]}], size=18)
notes(s, "We set five objectives in our proposal. O1, build the tutor as six collaborating agents instead of one chatbot. O2, keep a live estimate of each learner's knowledge, confidence, confusion, overload and progress. O3, find what helped similar learners using cosine similarity. O4, design the scoring algorithm, DSDA, that decides how much help to give. O5, evaluate it. Above all of these sits one rule: help like a teacher, never the full solution, and more help only when the learner asks.")

# ---------------------------------------------------------------- 6-7. Literature

lit_head = ["Paper (Year)", "Key contribution", "Demerit / gap", "Dataset", "Evaluation metrics"]
lit = [lit_head,
       ["Corbett & Anderson (1995) Knowledge tracing", "Probability each skill is learned; drives mastery learning", "Hand-built rule model for every domain", "ACT Programming Tutor students", "Prediction of test performance"],
       ["Piech et al. (2015) Deep Knowledge Tracing", "LSTM predicts the next answer", "Only predicts; does not choose help; hard to interpret", "ASSISTments, Khan Academy, simulated", "AUC, 5-fold cross-validation"],
       ["Liffiton et al. (2023) CodeHelp", "LLM help with guardrails: no solutions", "No per-learner model of how much to help", "52 students, 12 weeks", "Usage patterns, perceptions"],
       ["Kazemitabaar et al. (2024) CodeAid", "LLM assistant that avoids code solutions", "No learner model or similar-learner retrieval", "700 students, about 8,000 uses", "Logs, surveys, interviews"],
       ["Yang et al. (2024) PyTutor", "ChatGPT tutor with structured hints for beginners", "Over-reliance risk; hints include coding solutions", "35 vs 36 students, 11 weeks", "Engagement, completion, success"],
       ["Ma et al. (2024) RAGMan", "Course-specific RAG tutors for an intro course", "Retrieves course content only; self-reported", "455 students, intro course", "Usage, accuracy, perceptions"],
       ["Schmucker et al. (2024) Ruffle&Riley", "Two LLM agents (student and professor) teach a lesson", "No significant learning gain vs reading; not code", "200 participants, biology", "Engagement, learning gain"],
       ["Wang et al. (2025) TRAVER", "Knowledge tracing + turn-by-turn verifier for coding tutors", "Simulated students; no decision on how much help", "Simulated coding tasks (DICT)", "Task success rate"]]
s = content_slide("Literature Review")
table(s, 0.62, 1.2, [2.55, 2.95, 2.75, 2.0, 1.84], lit, row_h=0.63, header_h=0.45, size=12, header_size=13)
notes(s, "Our report reviews thirteen works; this table shows the eight closest to our project, the same systems we compare in the research gap. Knowledge tracing and Deep Knowledge Tracing model what a learner knows, but they only predict; they do not decide how to help. CodeHelp and CodeAid stop the AI from giving solutions, but they have no learner model that decides how much help each student needs. PyTutor helped weak students, but its authors saw over-reliance, and its hints include coding solutions. RAGMan retrieves course material, not what helped similar learners. Ruffle&Riley uses two LLM agents, but learning was not better than reading, which reminds us that engagement is not learning. TRAVER combines knowledge tracing with a verifier, but was tested only with simulated students.")

# ---------------------------------------------------------------- 8. Research gap

s = content_slide("Research Gap")
Y, N, U = "✓", "✗", "–"
gap_rows = [["System", "Learner model", "Decides how much help", "Withholds solutions", "Learns from similar learners", "Multiple agents", "Programming practice"],
            ["Knowledge tracing", Y, Y, U, U, U, Y],
            ["CodeHelp", U, U, Y, U, U, Y],
            ["CodeAid", U, U, Y, U, U, Y],
            ["PyTutor", U, U, N, U, U, Y],
            ["RAGMan", U, U, U, "Course content", U, Y],
            ["Ruffle&Riley", U, U, U, U, Y, N],
            ["TRAVER", Y, U, U, U, U, "Simulated"],
            ["CodePath (ours)", Y, Y, Y, Y, Y, Y]]
table(s, 0.62, 1.2, [2.55, 1.55, 1.65, 1.55, 1.75, 1.45, 1.59], gap_rows, row_h=0.42, header_h=0.62, size=15, header_size=12,
      highlight_rows=(8,), center_cols=(1, 2, 3, 4, 5, 6))
text(s, 0.62, 5.15, 12.09, 0.35, [{"runs": [(Y + " reported    ", {"bold": True}), (N + " not provided    ", {"bold": True}), (U + " not reported in the paper", {"bold": True})]}], size=12, color=GREY)
g = shape(s, 0.62, 5.6, 12.09, 1.05, TINT)
label(g, [{"runs": [("Gap: ", {"bold": True, "color": CRIMSON}), ("no reviewed system combines a learner-state model, a decision on how much help to give, learning from similar learners, and reflection with planning, for live programming practice.", {})]}], size=17, align=PP_ALIGN.LEFT, margin=0.2)
notes(s, "This matrix is the gap in one picture. Each row is a related system, each column a capability. Tick means the paper reports it, cross means it does not provide it, dash means the paper does not mention it. Guardrail tools like CodeHelp and CodeAid withhold solutions but have no learner model; knowledge tracing and TRAVER model the learner but do not decide how much help to give in a live programming session. No reviewed system combines all of these; CodePath is designed to fill exactly that gap.")

# ---------------------------------------------------------------- 9. Datasets, platforms, tools

s = content_slide("Datasets, Platforms, and Implementation Tools")
cal = shape(s, 0.62, 1.15, 12.09, 0.55, TINT)
label(cal, [{"runs": [("No model is trained, so no training dataset is needed. ", {"bold": True, "color": CRIMSON}), ("The agents work from our problem set and each learner's activity.", {})]}], size=15)
text(s, 0.62, 1.88, 5.9, 0.42, [{"text": "Dataset", "bold": True, "size": 18, "color": CRIMSON}])
for y, h, n_, head, pts in [(2.35, 2.5, "1", "Python problem set", ["496 practice problems in 17 topics", "Easy, medium and hard problems",
                                                                      "Test cases check every answer: a few are shown, the rest are hidden",
                                                                      "A short lesson for every technique"]),
                             (5.0, 1.65, "2", "Learner activity", ["Recorded as each student uses the tutor", "Code attempts, test results, hints and answers"])]:
    shape(s, 0.62, y, 5.9, h, LIGHT)
    circle_number(s, 0.8, y + 0.17, 0.42, n_, size=13)
    text(s, 1.35, y + 0.15, 5.0, 0.45, [{"text": head, "bold": True, "size": 17, "color": DARK}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 0.85, y + 0.7, 5.5, h - 0.75, [{"text": p_, "bullet": True} for p_ in pts], size=15, space_after=5)
text(s, 6.81, 1.88, 5.9, 0.42, [{"text": "Platforms and Tools", "bold": True, "size": 18, "color": CRIMSON}])
tools = [["Part", "What we used"],
         ["Platform", "Web app for learners and teachers"],
         ["Frontend", "React, TypeScript, code editor"],
         ["Backend", "Python, FastAPI"],
         ["AI agents", "LangGraph (six rule-based agents)"],
         ["Database", "PostgreSQL"],
         ["Similar-learner search", "ChromaDB"],
         ["Running student code", "Docker sandbox"],
         ["Testing", "pytest, Vitest, Playwright"],
         ["Hardware", "Laptop (Apple M2, 8 GB), no GPU"]]
table(s, 6.81, 2.35, [2.5, 3.4], tools, row_h=0.426, header_h=0.45, size=14, header_size=14)
notes(s, "An important point for the panel: we do not train any model, so we need no training dataset. Our agents follow explicit rules. The data they work from is, first, our Python problem set: 496 practice problems in 17 topics, easy, medium and hard, each checked by test cases. A few test cases are shown to the learner; the rest stay hidden for grading. Second, the learner's own activity, recorded as they use the tutor: their code attempts, test results, hints and answers. On the right are the tools: a web app built with React and TypeScript, a Python FastAPI backend, LangGraph to run the six agents, PostgreSQL as the database, ChromaDB to find similar learners, and a Docker sandbox so student code runs safely. Everything ran on one laptop with no GPU. If asked: there are 15,717 test cases in all, 1,000 visible and 14,717 hidden. An importer for the IBM CodeNet dataset is built and tested, but the full archive was not imported in this phase.")

# ---------------------------------------------------------------- 10. Architecture

s = content_slide("Proposed Methodology: System Architecture")
web = shape(s, 0.62, 1.55, 2.75, 3.1, "EAF4EC", "9CC5A4")
label(web, [{"text": "Web application", "bold": True, "size": 16, "space_after": 4},
            {"text": "React, TypeScript", "size": 13, "color": GREY, "space_after": 8},
            {"text": "Code editor", "size": 13}, {"text": "Tutor pane", "size": 13}, {"text": "Lessons, practice", "size": 13}, {"text": "Progress, profile", "size": 13}, {"text": "Teacher dashboard", "size": 13}], space_after=2)
text(s, 0.62, 1.18, 2.75, 0.35, [{"text": "Learner or teacher", "size": 13, "color": GREY, "align": PP_ALIGN.CENTER}])
api = shape(s, 4.35, 1.3, 4.1, 0.95, "EEF2FB", "AEBFE3")
label(api, [{"text": "FastAPI backend", "bold": True, "size": 16, "space_after": 1}, {"text": "logins and requests", "size": 13, "color": GREY}], space_after=0)
svc = shape(s, 4.35, 2.6, 4.1, 0.95, "EEF2FB", "AEBFE3")
label(svc, [{"text": "Tutoring service", "bold": True, "size": 16, "space_after": 1}, {"text": "one learner action at a time", "size": 13, "color": GREY}], space_after=0)
lg = shape(s, 4.35, 3.9, 4.1, 1.15, CRIMSON)
label(lg, [{"text": "LangGraph learning cycle", "bold": True, "size": 16, "color": WHITE, "space_after": 1}, {"text": "six AI agents (next slide)", "size": 13, "color": WHITE}], space_after=0)
llm = shape(s, 4.35, 5.55, 4.1, 0.9, WHITE, "9A9A9A", dash=True)
label(llm, [{"text": "Language model (optional)", "bold": True, "size": 14, "space_after": 1}, {"text": "only rewords hints; off by default", "size": 12, "color": GREY}], space_after=0)
pg = shape(s, 9.45, 1.3, 3.26, 1.1, LIGHT, "B5B5BD", kind=MSO_SHAPE.CAN)
label(pg, [{"text": "PostgreSQL", "bold": True, "size": 15, "space_after": 1}, {"text": "learner history and progress", "size": 12, "color": GREY}], space_after=0)
cdb = shape(s, 9.45, 3.85, 3.26, 1.1, LIGHT, "B5B5BD", kind=MSO_SHAPE.CAN)
label(cdb, [{"text": "ChromaDB", "bold": True, "size": 15, "space_after": 1}, {"text": "finds similar past situations", "size": 12, "color": GREY}], space_after=0)
ex = shape(s, 0.62, 5.15, 2.75, 1.3, "FDF1E6", "E3B98F")
label(ex, [{"text": "Code runner", "bold": True, "size": 15, "space_after": 1}, {"text": "runs student code safely in a Docker sandbox", "size": 12, "color": GREY}], space_after=0)
arrow(s, 3.4, 1.78, 4.32, 1.78, GREY, 2)
arrow(s, 4.32, 1.95, 3.4, 1.95, GREY, 2)
arrow(s, 6.4, 2.27, 6.4, 2.57, GREY, 2)
arrow(s, 6.4, 3.57, 6.4, 3.87, GREY, 2)
arrow(s, 6.4, 5.07, 6.4, 5.52, "9A9A9A", 1.5, dash=True)
arrow(s, 8.48, 1.8, 9.42, 1.8, GREY, 2)
arrow(s, 8.48, 4.35, 9.42, 2.25, GREY, 2)
arrow(s, 8.48, 4.47, 9.42, 4.47, GREY, 2)
arrow(s, 4.32, 3.08, 3.6, 3.08, GREY, 2, head=False)
arrow(s, 3.6, 3.08, 3.6, 5.6, GREY, 2, head=False)
arrow(s, 3.6, 5.6, 3.4, 5.6, GREY, 2)
text(s, 1.95, 4.72, 1.6, 0.35, [{"text": "student code", "size": 11, "color": GREY, "align": PP_ALIGN.RIGHT}])
cap = shape(s, 9.45, 5.3, 3.26, 1.15, TINT)
label(cap, [{"text": "Student code never runs inside the server", "bold": True, "size": 13, "color": CRIMSON}])
notes(s, "This is the architecture. The learner or teacher uses our web application, built with React. It talks to our FastAPI backend, which handles logins and requests. Each learner's actions are handled one at a time, in order, and every submission or hint request starts the LangGraph learning cycle with our six agents. The agents keep the learner's history and progress in PostgreSQL, and ChromaDB finds similar past situations. Student code never runs inside the server: it goes to a separate code runner that starts a locked-down Docker sandbox for every run. A language model is optional and can only reword hints; it is off by default, so the tutor works fully without any paid AI model.")

# ---------------------------------------------------------------- 11. Six agents + novelty

s = content_slide("Proposed Methodology: The Six-Agent Learning Cycle")
la = shape(s, 0.62, 1.2, 3.0, 0.6, WHITE, CRIMSON, radius=0.5, line_width=1.5)
label(la, [{"text": "Learner: Submit or Hint", "bold": True, "size": 13, "color": CRIMSON}])
resp = shape(s, 9.71, 1.2, 3.0, 0.6, WHITE, CRIMSON, radius=0.5, line_width=1.5)
label(resp, [{"text": "Tutor responds, then waits", "bold": True, "size": 13, "color": CRIMSON}])
arrow(s, 9.68, 1.5, 3.65, 1.5, CRIMSON, 1.5, dash=True, head=True)
text(s, 3.9, 1.12, 5.5, 0.35, [{"text": "waits for the learner's next action, then the cycle runs again", "size": 12, "italic": True, "color": GREY, "align": PP_ALIGN.CENTER}])
agents = [("Diagnostic", "What went wrong, with evidence"), ("Learner State", "How much the learner knows now"),
          ("Similar-Learner Retrieval", "What helped similar learners"), ("Adaptive Scaffolding (DSDA)", "Whether and how much to help"),
          ("Reflection", "Asks the learner to explain"), ("Learning Planner", "What to practise next")]
aw, ag = 1.86, 0.186
for i, (nm_, does) in enumerate(agents):
    x = 0.62 + i * (aw + ag)
    b = shape(s, x, 2.25, aw, 1.25, CRIMSON, radius=0.14)
    label(b, [{"text": nm_, "bold": True, "size": 14, "color": WHITE}])
    circle_number(s, x + aw / 2 - 0.2, 2.03, 0.4, str(i + 1), fill_color=DARK, size=12)
    text(s, x, 3.58, aw, 0.62, [{"text": does, "size": 13, "color": GREY, "align": PP_ALIGN.CENTER}])
    if i < 5:
        arrow(s, x + aw + 0.01, 2.87, x + aw + ag - 0.01, 2.87, DARK, 1.75)
arrow(s, 2.12, 1.82, 1.55, 2.0, CRIMSON, 1.5)
arrow(s, 11.5, 2.2, 11.5, 1.83, CRIMSON, 1.5)
text(s, 0.62, 4.32, 12.09, 0.42, [{"text": "Novelty: what is new in our approach", "bold": True, "size": 18, "color": CRIMSON}])
novel = [("Dynamic Scaffolding Decision Algorithm", "Decides how much help to give, one step at a time; never the full solution"),
         ("Hybrid experience retrieval", "Uses what helped learners in similar situations; stays quiet when evidence is weak"),
         ("Adaptive difficulty progression", "Technique by technique, easy to medium to hard, then the next topic"),
         ("Cyclic graph orchestration", "The agents run as a cycle that waits for the learner; every hint is checked first")]
nw = 2.93
for i, (head, desc) in enumerate(novel):
    x = 0.62 + i * (nw + 0.12)
    shape(s, x, 4.8, nw, 1.85, TINT)
    text(s, x + 0.12, 4.88, nw - 0.24, 0.62, [{"text": head, "bold": True, "size": 14, "color": DARK}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.12, 5.5, nw - 0.24, 1.1, [{"text": desc, "size": 13, "color": GREY}])
notes(s, "This is the heart of the project. Every time the learner submits code or asks for a hint, six agents run in order. Pressing Run only executes the code on the visible examples; it does not start the agents. One, the Diagnostic agent finds what went wrong, with evidence. Two, the Learner State agent updates how much the learner knows. Three, Retrieval looks at what helped similar learners. Four, DSDA decides whether to help and how much, then writes and checks the hint. Five, Reflection asks the learner to explain. Six, the Planner picks what to practise next. Then the cycle pauses until the learner acts again; nothing runs on its own. Our four novel contributions are at the bottom: the DSDA algorithm, which decides how much help to give; hybrid experience retrieval, which uses what helped similar learners and stays quiet when the evidence is weak; adaptive difficulty progression; and the cyclic agent workflow, which waits for the learner and checks every hint before it is shown.")

# ---------------------------------------------------------------- 12. How each agent works

s = content_slide("Proposed Approach: How Each Agent Works")
agent_rows = [["Agent", "Input", "How it decides (rules)", "Output"],
              ["1  Diagnostic", "Test results and the code", "Reads the code's structure and the error message; matches known beginner mistakes", "What went wrong and where, e.g. the loop stops one value early on line 3"],
              ["2  Learner State", "This attempt and past attempts", "Knowledge tracing: each attempt updates how well the topic is known; also looks for signs of confusion", "How well the topic is known, confused or not, or “unknown”"],
              ["3  Retrieval", "The learner's current situation", "Compares it with past situations; answers only when there are enough close matches", "The kind of help that worked before, or “no reliable match”"],
              ["4  DSDA", "All of the above + hints already given", "Need for help → help level → a new kind of hint → timing; then checks the hint", "Wait, offer or show one hint (L0 to L4); never a solution"],
              ["5  Reflection", "The issue + the learner's answer", "Builds a question from the learner's own code; reads the answer for key ideas", "A question, and a kind reply to the answer"],
              ["6  Planner", "What the learner knows, techniques, difficulty", "Each technique easy, then medium, then hard; then the next topic", "The next problem with its reason, and the route ahead"]]
table(s, 0.62, 1.2, [2.25, 2.7, 4.0, 3.14], agent_rows, row_h=0.83, header_h=0.45, size=14, header_size=14)
notes(s, "Here is how each agent works: input, rule, output. The Diagnostic agent reads the test results, the code's structure and the error message, and matches them to known beginner mistakes; for example, it finds that the loop stops one value early on line 3. The Learner State agent uses knowledge tracing, a standard method from our literature review: every attempt updates how well the learner knows the topic. It also looks for signs of confusion, and says unknown when there is no evidence. Retrieval compares the situation with past ones and answers only when there are enough close matches. DSDA decides how much help is needed, picks a help level and a new kind of hint, decides the timing, and checks the hint before it is shown. Reflection builds its question from the learner's own code and replies to their answer. The Planner moves technique by technique, from easy to hard, then to the next topic.")

# ---------------------------------------------------------------- 13. DSDA

s = content_slide("Proposed Approach: Dynamic Scaffolding Decision Algorithm")
steps = [("1", "Support score", "Combines what we know: how well the topic is known, confusion, repeated mistakes, hints that did not help, time. Unknown values are left out, not guessed."),
         ("2", "Help level", "Higher score, more help: L0 to L4. A new mistake starts at L2 or lower, and help rises one level at a time."),
         ("3", "Strategy", "The next unused kind of hint for this mistake, so a hint never repeats"),
         ("4", "Timing", "Asked: show the hint. Not asked: a first nudge on a new mistake can come by itself; after that, help is only offered.")]
for i, (n_, head, desc) in enumerate(steps):
    y = 1.25 + i * 1.36
    shape(s, 0.62, y, 6.3, 1.22, LIGHT)
    circle_number(s, 0.75, y + 0.36, 0.5, n_, size=14)
    text(s, 1.38, y + 0.08, 5.45, 0.38, [{"text": head, "bold": True, "size": 16, "color": CRIMSON}])
    text(s, 1.38, y + 0.46, 5.45, 0.74, [{"text": desc, "size": 14, "color": DARK}], space_after=0)
text(s, 7.25, 1.2, 5.46, 0.4, [{"text": "The help ladder", "bold": True, "size": 16, "color": DARK}])
ladder = [("L0", "Try yourself (offer only)"), ("L1", "Guiding question"), ("L2", "Targeted hint"), ("L3", "Step-by-step outline"), ("L4", "Example on a different task")]
for i, (lv, nm_) in enumerate(ladder):
    hgt = 0.55 + i * 0.42
    x = 7.25 + i * 1.1
    shade = ["F6D6DF", "EDB2C1", "DE7F98", "C6466A", CRIMSON][i]
    b = shape(s, x, 4.15 - hgt + 0.55, 1.0, hgt, shade, radius=0.06)
    label(b, [{"text": lv, "bold": True, "size": 15, "color": WHITE if i >= 2 else DARK}], anchor=MSO_ANCHOR.TOP)
    text(s, x - 0.05, 4.75, 1.1, 0.75, [{"text": nm_, "size": 12, "color": DARK, "align": PP_ALIGN.CENTER}])
ex = shape(s, 7.25, 5.55, 5.46, 1.1, TINT)
label(ex, [{"runs": [("Worked example: ", {"bold": True, "color": CRIMSON}), ("second wrong submission with the same bug → medium score → L2 targeted hint → offered, not pushed, because a hint was already shown", {})]}], size=13, align=PP_ALIGN.LEFT, margin=0.15)
notes(s, "DSDA is our main algorithm. Step 1: a support score that combines everything we know about the learner: how well they know the topic, how confused they are, repeated mistakes, hints that did not help, and time. Anything unknown is left out instead of guessed. Step 2: the score maps to a help level from L0 to L4. A higher score means more help, but a new mistake starts at L2 or lower, and help rises only one level at a time. Step 3: the next unused kind of hint for that mistake, so hints never repeat. Step 4: timing. If the learner asked, we show the hint. If not, the first nudge on a new mistake can come by itself, but after that more help is only offered. Worked example from our tests: on the second wrong submission with the same bug, the score is in the middle band, so level 2, a targeted hint, and it is offered, not pushed. If asked for the exact figures: the score was 0.472, and the bands are below 0.2, 0.4, 0.6 and 0.8 for levels 0 to 3.")

# ---------------------------------------------------------------- 14. Rules instead of training

s = content_slide("Proposed Approach: Rules Instead of Training")
cal = shape(s, 0.62, 1.15, 12.09, 0.6, TINT)
label(cal, [{"runs": [("We do not train a model. ", {"bold": True, "color": CRIMSON}), ("Each agent follows clear rules that we designed, so every decision can be explained.", {})]}], size=16)
cmp_rows = [["", "A trained AI model", "Our rule-based agents"],
            ["Needs a large training dataset", "Yes", {"text": "No", "bold": True, "color": GREEN}],
            ["Needs training time and a GPU", "Yes", {"text": "No", "bold": True, "color": GREEN}],
            ["Explains why it chose a hint", "Often hard", {"text": "Yes: a reason is shown with each hint", "bold": True, "color": GREEN}],
            ["Changing how it behaves", "Retrain the model", {"text": "Edit one settings file", "bold": True, "color": GREEN}],
            ["Learns from data by itself", "Yes", {"text": "Not yet: planned future work", "bold": True, "color": AMBER}]]
table(s, 0.62, 2.0, [4.2, 3.6, 4.29], cmp_rows, row_h=0.62, header_h=0.5, size=16, header_size=16)
fin = shape(s, 0.62, 5.75, 12.09, 0.85, CRIMSON)
label(fin, [{"text": "Because nothing is trained, the tutor works from the very first learner", "bold": True, "size": 18, "color": WHITE}])
notes(s, "A key point for the panel: we do not train a model. Each agent follows clear rules that we designed. Compared with a trained model, we need no large dataset, no training time and no GPU, and every hint comes with a reason the learner can see. To change the tutor's behaviour we edit one settings file instead of retraining. The trade-off is that the rules do not yet learn from data by themselves; fitting them to real learner data is in our future work. Because nothing is trained, the tutor works from the very first learner. If asked: all rule values are in one versioned settings file, policy.yaml, and they are starting values chosen by design, not tuned on data.")

# ---------------------------------------------------------------- 15. Evaluation setup

s = content_slide("Evaluation Setup and Criteria")
shape(s, 0.62, 1.22, 4.3, 5.43, LIGHT)
text(s, 0.82, 1.32, 3.9, 0.42, [{"text": "How we tested", "bold": True, "size": 17, "color": CRIMSON}])
how = [("Automated tests", "Backend, browser, unit and sandbox tests"),
       ("Agent audit", "9 realistic tutoring scenarios run through all six agents"),
       ("Problem check", "Every problem run against its own tests"),
       ("Real system", "Real database and sandbox; no paid AI model")]
for i, (head, desc) in enumerate(how):
    y = 1.85 + i * 0.9
    circle_number(s, 0.8, y + 0.05, 0.42, str(i + 1), size=13)
    text(s, 1.35, y, 3.45, 0.36, [{"text": head, "bold": True, "size": 15, "color": DARK}])
    text(s, 1.35, y + 0.34, 3.45, 0.58, [{"text": desc, "size": 13, "color": GREY}])
text(s, 0.82, 5.68, 3.95, 0.36, [{"text": "Compared with", "bold": True, "size": 15, "color": CRIMSON}])
text(s, 0.82, 6.02, 3.95, 0.6, [{"text": "Our earlier version, and the reviewed systems", "size": 13, "color": DARK}])
criteria = [["Criterion", "What we check", "Pass when"],
            ["Correct software", "All automated tests", "Every test passes"],
            ["No repeated hints", "Asking again on the same code", "A new hint each time"],
            ["Help grows slowly", "Help level after each hint", "One level at a time"],
            ["Not pushed", "More help when not asked", "Only offered"],
            ["Specific hints", "Each hint and the learner's code", "Names their code"],
            ["No full solution", "Every hint level, and asking for it", "Never shown"],
            ["Valid problems", "Model answer and starter code", "Answer passes, starter fails"],
            ["Accessible", "Automatic accessibility scan", "No violations"],
            ["Learning gain", "Test before and after, real learners", {"text": "Planned next phase", "bold": True, "color": AMBER}]]
table(s, 5.2, 1.22, [2.2, 3.15, 2.16], criteria, row_h=0.53, header_h=0.45, size=13, header_size=14)
notes(s, "How we evaluated. On the left: we ran four automated test suites, backend, browser, unit and sandbox; an agent audit that drives nine realistic tutoring scenarios through all six agents; and a check that runs every practice problem against its own tests. Everything ran on the real system, with the real database and sandbox and no paid AI model, so every hint used the built-in wording. We compare against our own earlier version and the reviewed systems. On the right are our criteria in plain words: every test passes; asking again gives a new hint; help grows one level at a time; more help is only offered when the learner has not asked; every hint names the learner's own code; the full solution is never shown; every problem's model answer passes and its starter code fails; and the automatic accessibility scan finds no violations. Learning gain needs a test before and after with real learners, so it is planned for the next phase.")

# ---------------------------------------------------------------- 16. Results numbers

s = content_slide("Results and Analysis: Key Results")
results = [("All tests passed", "Every backend, browser, unit and sandbox test passed on the final system."),
           ("Every problem verified", "Each problem's model answer passes its tests, and the starter code fails them."),
           ("Hints never repeat", "Asking again on the same code gave a different hint every time."),
           ("Help grows step by step", "Help rose one level at a time. After the first hint, more help was offered, not pushed."),
           ("Hints fit the learner", "Every hint named something from the learner's own code. None was generic advice."),
           ("Solution stays hidden", "No hint level gives the full solution, even when the learner asks for it.")]
for i, (head, desc) in enumerate(results):
    r_, c_ = divmod(i, 3)
    x = 0.62 + c_ * 4.08
    y = 1.22 + r_ * 2.27
    shape(s, x, y, 3.93, 2.1, GREEN_T)
    circle_number(s, x + 0.2, y + 0.2, 0.55, "✓", fill_color=GREEN, size=18)
    text(s, x + 0.9, y + 0.2, 2.9, 0.55, [{"text": head, "bold": True, "size": 17, "color": DARK}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.22, y + 0.92, 3.5, 1.1, [{"text": desc, "size": 16, "color": DARK}])
nm_box = shape(s, 0.62, 5.8, 12.09, 0.85, AMBER_T)
label(nm_box, [{"runs": [("Not measured yet: ", {"bold": True, "color": AMBER}), ("whether students learn more with CodePath. This needs a study with real learners, our next phase.", {})]}], size=16, align=PP_ALIGN.LEFT, margin=0.25)
notes(s, "Our results in plain words. All automated tests passed on the final system. Every practice problem was verified: its model answer passes and its starter code fails. In the agent audit, asking again on the same code gave a different hint every time; help rose one level at a time, and after the first hint more help was only offered; every hint named something from the learner's own code; and no hint level ever gives the full solution, even when the learner asks for it. What we have not measured yet is learning gain: that needs a study with real students, which is our next phase. If asked for the figures: 551 backend, 59 browser, 21 unit and 39 sandbox tests passed; all 37 audit checks passed; all 496 problems were verified; four hint requests on unchanged code gave four different hints; and all 17 hints in the audit named the learner's code.")

# ---------------------------------------------------------------- 17-18. Visual outputs

s = content_slide("Results and Analysis: Visual Outputs (1/2)")
text(s, 0.62, 1.15, 12.09, 0.42, [{"runs": [("Problem: ", {"bold": True, "color": CRIMSON}), ("Sum from 1 to N. The learner's loop uses range(1, n), so it misses the last value.", {})]}], size=15)
picture(s, f"{ASSETS}/workspace_first_hint_pane.png", 0.62, 1.7, w=5.9)
picture(s, f"{ASSETS}/offer_not_pushed_pane.png", 6.81, 1.7, w=5.9)
circle_number(s, 0.42, 1.5, 0.45, "1", size=14)
circle_number(s, 6.61, 1.5, 0.45, "2", size=14)
text(s, 0.62, 5.15, 5.9, 1.4, [{"runs": [("First wrong submission: ", {"bold": True}), ("one targeted hint, built from the learner's own call, values and loop variable. It names the concept and links to the lesson.", {})]}], size=14)
text(s, 6.81, 4.15, 5.9, 1.4, [{"runs": [("Second wrong submission: ", {"bold": True}), ("the next hint is offered, not shown. The learner tries their own idea first; one click shows it.", {})]}], size=14)
notes(s, "Here is the tutor in action on the problem Sum from 1 to N; the student's loop misses the last value. Screen one: after the first wrong submission the tutor gives one targeted hint. Notice it quotes the student's own call, sum_to_n(3), the values 3 and 6, and the loop variable i. It does not give the fix. Screen two: the student submits again without asking for help. Instead of pushing a bigger hint, the tutor only offers it, so the student tries their own idea first. That is the teacher-like behaviour we wanted.")
s = content_slide("Results and Analysis: Visual Outputs (2/2)")
picture(s, f"{ASSETS}/reflection_reply_pane.png", 0.62, 1.3, w=5.9)
picture(s, f"{ASSETS}/solved_plan_route_pane.png", 6.81, 1.3, w=5.9)
circle_number(s, 0.42, 1.1, 0.45, "3", size=14)
circle_number(s, 6.61, 1.1, 0.45, "4", size=14)
text(s, 0.62, 4.75, 5.9, 1.6, [{"runs": [("Reflection: ", {"bold": True}), ("a question about the learner's own loop. The learner wrote “no idea”; the tutor replied kindly with one small thing to try.", {})]}], size=14)
text(s, 6.81, 3.95, 5.9, 1.6, [{"runs": [("After solving: ", {"bold": True}), ("a hint was used, so the planner suggests one more problem of the same technique, on their own, and shows the route ahead.", {})]}], size=14)
notes(s, "Screen three: after three failed attempts the Reflection agent asks the student to trace their own loop by hand. The student answered no idea; the tutor did not judge, it replied with one small concrete step. Screen four: after solving with a hint, the Planner suggests one more problem of the same technique without hints, and shows the route ahead: Loops, then Functions, Strings, and Lists and dictionaries.")

# ---------------------------------------------------------------- 19. Comparison

s = content_slide("Results and Analysis: Comparison")
ba = [["Behaviour", "Before (our earlier version)", "After (final system)"],
      ["Repeated hint requests", "The same hint again", "A different hint every time"],
      ["Wrong answers without asking", "Help climbed automatically", "Help offered; shown only when asked"],
      ["Reflection", "Fixed questions; answers ignored", "About the learner's code; replies; changes the plan"],
      ["Planning", "By difficulty only", "Technique by technique, with a route"],
      ["Specific hints", "Half were generic advice", "Every hint names the learner's code"]]
table(s, 0.62, 1.22, [2.55, 2.75, 2.95], ba, row_h=0.98, header_h=0.5, size=15, header_size=15)
shape(s, 9.15, 1.22, 3.56, 5.4, TINT)
text(s, 9.35, 1.35, 3.2, 0.75, [{"text": "Compared with the state of the art", "bold": True, "size": 16, "color": CRIMSON}])
text(s, 9.35, 2.15, 3.25, 0.5, [{"text": "Among the reviewed works, only CodePath combines:", "size": 13}])
text(s, 9.35, 2.75, 3.25, 3.7, [{"text": "✓  Learner-state model"}, {"text": "✓  Decision on how much help"}, {"text": "✓  Solutions withheld, hints checked"},
                                  {"text": "✓  Learning from similar learners"}, {"text": "✓  Reflection and planning"}, {"text": "✓  Live programming practice"}],
     size=14, color=DARK, space_after=8)
notes(s, "We compare in two ways. Left, against our own earlier version: before the agent fixes, asking again gave the same hint; now each request gives a different one. Help no longer climbs automatically; reflection answers now get a reply and change the plan; planning follows techniques; and every hint now names the learner's own code, where before half were generic. If asked: before, five hint requests gave one distinct hint and 8 of 16 hints named the learner's code; after, four requests gave four different hints and all 17 named it. Right, against the state of the art: among the works we reviewed, CodePath is the only system that combines all six capabilities.")

# ---------------------------------------------------------------- 20. Discussion and limitations

s = content_slide("Discussion and Limitations")
discussion = ["CodePath coordinates multiple agents to provide guidance without directly giving complete solutions.",
              "Diagnosis uses learner code, execution results, tests and previous attempts as evidence.",
              "Learner-state tracking and retrieval help adapt the hint level to current understanding.",
              "Scaffolding and reflection encourage retries, reasoning and independent problem-solving.",
              "The workflow links diagnosis, hints and next-step planning in a continuous feedback loop."]
limitations = ["Learning gains have not yet been established through controlled studies with real learners.",
               "Learner-state estimates can be uncertain when attempt history or evidence is limited.",
               "Hint correctness, clarity, usefulness and solution-leakage prevention need broader expert evaluation.",
               "Retrieval quality depends on knowledge-base coverage, relevance and freshness.",
               "Sandbox runs and multi-agent orchestration can increase latency and compute cost.",
               "Current validation is mainly technical testing; learning outcomes and long-term retention remain unevaluated."]
for x, fill_c, head, pts in [(0.62, "FBEFF3", "Discussion", discussion), (6.81, "F6DCE4", "Limitations", limitations)]:
    shape(s, x, 1.22, 5.9, 5.43, fill_c, radius=0.06)
    text(s, x + 0.25, 1.38, 5.4, 0.5, [{"text": head, "bold": True, "size": 21, "color": CRIMSON}])
    text(s, x + 0.25, 2.0, 5.45, 4.55, [{"text": p_, "bullet": True} for p_ in pts], size=16, space_after=11)
notes(s, "Discussion. CodePath coordinates several agents to guide the learner without handing over complete solutions. The diagnosis is based on evidence: the learner's code, the run results, the tests and previous attempts. Tracking the learner's state, together with retrieval, lets the tutor adapt the hint level to what the learner understands now. Scaffolding and reflection encourage the learner to retry, reason and solve problems independently, and the workflow links diagnosis, hints and next-step planning in one continuous feedback loop. Limitations, stated honestly. We have not yet shown learning gains in a controlled study with real learners. Learner-state estimates are uncertain when there is little history. Hint quality and leak prevention need broader expert evaluation. Retrieval is only as good as its knowledge base. Running code in a sandbox and coordinating several agents adds time and compute cost. And our validation so far is mainly technical testing; learning outcomes and long-term retention are not yet evaluated.")

# ---------------------------------------------------------------- 21. Conclusion

s = content_slide("Conclusion")
text(s, 0.62, 1.22, 5.0, 4.9, [
    {"text": "We built CodePath, a tutor for beginner Python programmers on the CSMASF framework", "bullet": True},
    {"text": "Six rule-based agents decide when and how much to help, and never give the full answer", "bullet": True},
    {"text": "Verified by automated tests, an agent audit of realistic tutoring scenarios, and a check of every practice problem", "bullet": True},
], size=17, space_after=14)
status = [["Objective", "Status", "Evidence"],
          ["O1 Multi-agent tutor", {"text": "Achieved", "bold": True, "color": GREEN}, "Six agents in order; pipeline tests"],
          ["O2 Learner state", {"text": "Achieved", "bold": True, "color": GREEN}, "Estimates with evidence; audit"],
          ["O3 Similar learners", {"text": "Achieved*", "bold": True, "color": GREEN}, "*mechanism works; needs real data"],
          ["O4 DSDA algorithm", {"text": "Achieved", "bold": True, "color": GREEN}, "Worked example reproduced; tests"],
          ["O5 Evaluation", {"text": "Partly", "bold": True, "color": AMBER}, "Software verified; learner study next"]]
table(s, 5.95, 1.22, [2.45, 1.3, 3.01], status, row_h=0.68, header_h=0.45, size=13, header_size=14)
close = shape(s, 0.62, 5.55, 12.09, 1.0, CRIMSON)
label(close, [{"text": "CodePath gives a beginner only the help they need: one step at a time, never the answer", "bold": True, "size": 19, "color": WHITE}])
notes(s, "To conclude: we built CodePath on the CSMASF framework. Six rule-based agents decide when and how much to help, and never give the answer. It is verified by automated tests across four suites, an agent audit of realistic tutoring scenarios, and a check of every practice problem; if asked, that is 670 tests, 37 audit checks and 496 problems. Objective-wise: O1, O2 and O4 are achieved; O3 is achieved as a mechanism but needs real learner data to be useful; O5 is partly achieved, because the software is verified but the learning study is the next phase.")

# ---------------------------------------------------------------- 22. Future work

s = content_slide("Future Work")
fw = [("Learner study", "Pilot with 30+ students: pre and post test, learning gain, effect size"),
      ("Real LLM evaluation", "Measure leak rate, rejected hints and response time with a real model"),
      ("Learn the rule values", "Fit knowledge tracing and DSDA weights to real data; compare Deep Knowledge Tracing"),
      ("CodeNet offline study", "Import attempt sequences and replay them through the agents"),
      ("Deployment", "Linux server, independent security review, scale to many users"),
      ("More languages", "JavaScript next, then Java or C++")]
for i, (head, desc) in enumerate(fw):
    r_, c_ = divmod(i, 3)
    x = 0.62 + c_ * 4.08
    y = 1.3 + r_ * 2.65
    shape(s, x, y, 3.93, 2.4, LIGHT)
    circle_number(s, x + 0.2, y + 0.22, 0.55, str(i + 1), size=15)
    text(s, x + 0.9, y + 0.22, 2.9, 0.6, [{"text": head, "bold": True, "size": 16, "color": DARK}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.22, y + 0.98, 3.5, 1.3, [{"text": desc, "size": 14, "color": GREY}])
notes(s, "Next steps. First and most important, a study with at least 30 students, with a pre-test and post-test to measure learning gain. Second, evaluate with a real LLM for leak rate and response time. Third, learn the rule values from real data and compare with Deep Knowledge Tracing. Fourth, an offline study on CodeNet. Fifth, deployment hardening on a Linux server with a security review. Sixth, more programming languages.")

# ---------------------------------------------------------------- 23. Time line

s = content_slide("Project Time Line")
mil = [("Phase I", "Idea, objectives and literature survey"),
       ("17 Sep 2026", "Repository and interface started"),
       ("25–26 Oct 2026", "Agents, DSDA v2.1, sandbox, curriculum"),
       ("4 Nov 2026", "LangGraph anti-leak verifier, assessments"),
       ("9 Nov 2026", "Full CSMASF implementation"),
       ("10 Nov 2026", "Agent audit, final tests, report"),
       ("Nov 2026", "Final review")]
yl = 3.95
shape(s, 0.9, yl - 0.04, 11.55, 0.08, LINE, radius=0.5)
step = 11.55 / (len(mil) - 1)
for i, (date, what) in enumerate(mil):
    cx = 0.9 + i * step
    last = i == len(mil) - 1
    circle_number(s, cx - 0.22, yl - 0.22, 0.44, str(i + 1), fill_color=CRIMSON if not last else DARK, size=12)
    up = i % 2 == 0
    bx = max(0.62, min(cx - 0.95, 12.71 - 1.9))
    text(s, bx, (yl - 1.55) if up else (yl + 0.38), 1.9, 0.42, [{"text": date, "bold": True, "size": 14, "color": CRIMSON, "align": PP_ALIGN.CENTER}])
    text(s, bx, (yl - 1.12) if up else (yl + 0.8), 1.9, 0.85, [{"text": what, "size": 13, "color": DARK, "align": PP_ALIGN.CENTER}])
text(s, 0.62, 6.05, 12.09, 0.5, [{"text": "Dates from the project's commit history", "size": 12, "italic": True, "color": GREY}])
notes(s, "Our timeline, taken from our commit history. Phase one was the proposal with the problem, objectives and a nine-paper survey. Development began on 17 September. On 25 and 26 October we built the agent baseline, DSDA version 2.1, the sandbox hardening and the curriculum. On 4 November we added the LangGraph anti-leak verifier and assessments. On 9 November the full CSMASF implementation, and on 10 November the agent audit, final testing and the report.")

# ---------------------------------------------------------------- 24. Team contribution

s = content_slide("Team Contribution")
contrib = [("Bommineni Bharath", "AM.SC.U4CSE23112", ["System architecture and agent workflow design",
                                                     "FastAPI API integration and backend coordination",
                                                     "End-to-end integration, debugging and final review"]),
           ("Chimmili Lokesh", "AM.SC.U4CSE23114", ["Adaptive hint/scaffolding and reflection workflow",
                                                   "Sandbox execution and safety checks",
                                                   "Test automation, documentation and demo preparation"]),
           ("Kataru Reddy Eswar", "AM.SC.U4CSE23126", ["Retrieval pipeline and learner-context handling",
                                                      "Database / knowledge-store integration",
                                                      "Backend tests, validation and reliability checks"]),
           ("Ramisetti Gowtham Tej", "AM.SC.U4CSE23144", ["Frontend development: React, TypeScript and code editor",
                                                         "UI–backend interaction and learner workflow screens",
                                                         "Browser testing and interface refinements"])]
cw4, gap4 = 2.88, 0.19
for i, (n_, r_, pts) in enumerate(contrib):
    x = 0.62 + i * (cw4 + gap4)
    shape(s, x, 1.3, cw4, 5.15, "FBEFF3", radius=0.08)
    shape(s, x, 6.25, cw4, 0.2, CRIMSON, kind=MSO_SHAPE.RECTANGLE)
    text(s, x + 0.02, 1.55, cw4 - 0.04, 0.6, [{"text": n_, "bold": True, "size": 17, "color": CRIMSON, "align": PP_ALIGN.CENTER}], anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.1, 2.15, cw4 - 0.2, 0.36, [{"text": r_, "size": 14, "color": GREY, "align": PP_ALIGN.CENTER}])
    shape(s, x + 0.9, 2.7, cw4 - 1.8, 0.04, CRIMSON, kind=MSO_SHAPE.RECTANGLE)
    text(s, x + 0.15, 3.05, cw4 - 0.3, 3.1, [{"text": "• " + p_, "align": PP_ALIGN.CENTER} for p_ in pts], size=16, space_after=16)
notes(s, "Each of us introduces our own part. Bharath: system architecture and agent workflow design, FastAPI integration and backend coordination, and end-to-end integration, debugging and final review. Lokesh: the adaptive hint, scaffolding and reflection workflow, sandbox execution and safety checks, and test automation, documentation and demo preparation. Eswar: the retrieval pipeline and learner-context handling, database and knowledge-store integration, and backend tests, validation and reliability checks. Gowtham Tej: frontend development in React and TypeScript with the code editor, the screens that connect the learner to the backend, and browser testing and interface refinements.")

# ---------------------------------------------------------------- 25. References

s = content_slide("Reference")
refs = ["[1] A. T. Corbett and J. R. Anderson, “Knowledge tracing,” User Model. User-Adapt. Interact., vol. 4, no. 4, 1995.",
        "[2] C. Piech et al., “Deep knowledge tracing,” NIPS 28, 2015.",
        "[3] V. Rus, N. B. Niraula, R. Banjade, “DeepTutor,” Proc. AAAI, vol. 29, 2015.",
        "[4] V. Aleven et al., “Help helps, but only so much,” Int. J. Artif. Intell. Educ., vol. 26, 2016.",
        "[5] R. Puri et al., “Project CodeNet,” arXiv:2105.12655, 2021.",
        "[6] M. Liffiton et al., “CodeHelp,” arXiv:2308.06921, 2023.",
        "[7] M. Kazemitabaar et al., “CodeAid,” Proc. CHI ’24, 2024.",
        "[8] A. C. M. Yang et al., “Enhancing Python learning with PyTutor,” Comput. Educ. Artif. Intell., vol. 7, 2024.",
        "[9] I. Ma, A. Krone Martins, C. V. Lopes, “Integrating AI tutors in a programming course,” arXiv:2407.15718, 2024.",
        "[10] R. Schmucker et al., “Ruffle&Riley,” arXiv:2404.17460, 2024.",
        "[11] Y. Zhan et al., “CoderAgent,” Proc. IJCAI-25, 2025.",
        "[12] J. Wang et al., “Training turn-by-turn verifiers for dialogue tutoring agents,” Findings of ACL 2025.",
        "[13] G. Pitts, A. P. Hridi, A. B. Lekshmi Narayanan, “A survey of LLM-based applications in programming education,” HCI+NLP 2025."]
text(s, 0.62, 1.2, 5.95, 5.45, [{"text": r} for r in refs[:7]], size=14, space_after=9)
text(s, 6.76, 1.2, 5.95, 5.45, [{"text": r} for r in refs[7:]], size=14, space_after=9)
notes(s, "These are the thirteen works we reviewed. Full citations with DOIs are in our project report.")

# ---------------------------------------------------------------- 26. Appendix

s = content_slide("Appendix A: Code and Demo")
text(s, 0.62, 1.22, 5.4, 0.42, [{"text": "Repository", "bold": True, "size": 17, "color": CRIMSON}])
text(s, 0.62, 1.68, 5.4, 0.8, [{"text": "github.com/lokesh12125/AdaptiveAITutor", "size": 15, "bold": True}, {"text": "Branch: Trellis    Commit: [after final commit]", "size": 13, "color": GREY}], space_after=2)
text(s, 0.62, 2.75, 5.4, 0.42, [{"text": "Run the demo", "bold": True, "size": 17, "color": CRIMSON}])
text(s, 0.62, 3.2, 5.4, 1.45, [
    {"text": "./scripts/setup.sh", "size": 13, "font": "Courier New"},
    {"text": "./scripts/dev.sh", "size": 13, "font": "Courier New"},
    {"text": "Open 127.0.0.1:5173", "size": 13},
    {"text": "“Try as a learner” or “Try as a teacher”", "size": 13},
], space_after=5)
text(s, 0.62, 4.75, 5.4, 0.42, [{"text": "Demo flow", "bold": True, "size": 17, "color": CRIMSON}])
text(s, 0.62, 5.2, 5.4, 1.45, [
    {"text": "Wrong code → one hint → submit again → help offered", "bullet": True},
    {"text": "Reflection reply → solve → next step and route", "bullet": True},
    {"text": "Teacher dashboard", "bullet": True},
], size=14, space_after=4)
picture(s, f"{SCREENS}/home_route.png", 6.3, 1.25, w=6.41)
text(s, 6.3, 5.33, 6.41, 0.4, [{"text": "Learner home: next step and route through the course", "size": 12, "italic": True, "color": GREY, "align": PP_ALIGN.CENTER}])
notes(s, "Our code is on GitHub at the address shown. Two commands start everything, then open the browser and press Try as a learner. For the live demo: submit the off-by-one code, show the single hint, submit again to show the offer, answer the reflection, solve, and show the plan and route, then the teacher dashboard.")

# ---------------------------------------------------------------- 27. Thank you

s = prs.slides.add_slide(title_layout)
for ph in list(s.placeholders):
    ph._element.getparent().remove(ph._element)
bg = shape(s, 0, 0, 13.333, 7.5, CRIMSON, kind=MSO_SHAPE.RECTANGLE)
s.shapes.add_picture(f"{ASSETS}/amrita_logo_white.png", Inches(1.09), Inches(2.82), width=Inches(3.77))
ln = arrow(s, 4.74, 2.53, 4.74, 4.32, "F2C14E", 1.5, head=False)
text(s, 5.45, 2.55, 7.4, 1.1, [{"text": "Thank You", "bold": True, "size": 48, "color": WHITE, "font": "Segoe UI"}])
text(s, 5.5, 3.7, 7.4, 0.6, [{"text": "Questions are welcome", "italic": True, "size": 22, "color": WHITE, "font": "Times New Roman"}])
text(s, 5.5, 4.5, 7.4, 0.5, [{"text": "CodePath: a tutor that helps beginners think, not copy", "size": 16, "color": WHITE, "font": "Times New Roman"}])
notes(s, "Thank you. We are happy to take questions, and we can show the live demo.")

prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
