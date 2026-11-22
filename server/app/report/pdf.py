"""Render the client report as a PDF (ReportLab). Input is the customer-safe dictionary from data.collect plus the
optional overview. Pure formatting: it states nothing the data does not contain."""
import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas as rl_canvas

from .data import safe_text

FONT_DIR = Path(__file__).parent / "fonts"
W, H = A4
MARGIN = 20 * mm
INK, MUTED, RULE, PANEL = colors.HexColor("#101418"), colors.HexColor("#5a6472"), colors.HexColor("#d9dee5"), colors.HexColor("#f3f5f8")
NAVY, GOLD, GREEN, RED, BLUE = (colors.HexColor(c) for c in ("#12315a", "#b7791f", "#1f7a4d", "#a23b3b", "#2b5fa6"))
CONF_COLOR = {"High": GREEN, "Medium": GOLD, "Low": RED, None: MUTED}


def _fonts() -> None:
    if "Plex" in pdfmetrics.getRegisteredFontNames():
        return
    for name, file in (("Plex", "IBMPlexSans-Regular"), ("Plex-Medium", "IBMPlexSans-Medium"), ("Plex-Bold", "IBMPlexSans-Bold"),
                       ("Plex-Italic", "IBMPlexSans-Italic"), ("PlexMono", "IBMPlexMono-Regular"),
                       ("Serif", "InstrumentSerif-Regular"), ("Serif-Italic", "InstrumentSerif-Italic")):
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / f"{file}.ttf")))
    pdfmetrics.registerFontFamily("Plex", normal="Plex", bold="Plex-Bold", italic="Plex-Italic", boldItalic="Plex-Bold")
    pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif", italic="Serif-Italic", boldItalic="Serif-Italic")


def _styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="Plex", fontSize=9.5, leading=14, textColor=INK, alignment=TA_LEFT)
    s = {"body": ParagraphStyle("body", **base)}
    s["small"] = ParagraphStyle("small", parent=s["body"], fontSize=8, leading=11, textColor=MUTED)
    s["tiny"] = ParagraphStyle("tiny", parent=s["small"], fontSize=7, leading=9)
    s["h1"] = ParagraphStyle("h1", fontName="Serif", fontSize=24, leading=28, textColor=NAVY, spaceBefore=4, spaceAfter=8)
    s["h2"] = ParagraphStyle("h2", fontName="Serif", fontSize=17, leading=21, textColor=NAVY, spaceBefore=16, spaceAfter=4, keepWithNext=1)
    s["h3"] = ParagraphStyle("h3", fontName="Plex-Medium", fontSize=10, leading=13, textColor=INK, spaceBefore=9, spaceAfter=3, keepWithNext=1)
    s["stat"] = ParagraphStyle("stat", fontName="Serif", fontSize=26, leading=30, textColor=NAVY)
    s["qtext"] = ParagraphStyle("qtext", parent=s["body"], fontName="Plex-Medium", fontSize=10, leading=14.5, spaceAfter=2)
    s["eyebrow"] = ParagraphStyle("eyebrow", fontName="PlexMono", fontSize=7.5, leading=10, textColor=MUTED, spaceAfter=2)
    s["title"] = ParagraphStyle("title", fontName="Serif", fontSize=27, leading=31, textColor=NAVY, spaceAfter=8)
    s["headline"] = ParagraphStyle("headline", fontName="Serif", fontSize=16.5, leading=21, textColor=NAVY)
    s["bullet"] = ParagraphStyle("bullet", parent=s["body"], leftIndent=11, bulletIndent=0, spaceAfter=4)
    s["quote"] = ParagraphStyle("quote", parent=s["body"], fontSize=9.2, leading=13.4)
    s["cell"] = ParagraphStyle("cell", parent=s["body"], fontSize=8.3, leading=11)
    s["cellb"] = ParagraphStyle("cellb", parent=s["cell"], fontName="Plex-Medium")
    s["mono"] = ParagraphStyle("mono", parent=s["cell"], fontName="PlexMono", fontSize=7.2, leading=9.5, textColor=MUTED)
    return s


def esc(text) -> str:
    return escape(str(text if text is not None else ""))


def para_text(text: str) -> str:
    """Escape and keep line breaks of an expert's answer."""
    return esc(text).replace("\r", "").replace("\n\n", "<br/><br/>").replace("\n", "<br/>")


def cite(refs: list[str]) -> str:
    return " ".join(f'<font name="PlexMono" size="7.2" color="#2b5fa6">[{esc(r)}]</font>' for r in refs)


def pill(text: str, color) -> str:
    return f'<font name="Plex-Medium" size="7.6" color="#ffffff" backColor="{color.hexval().replace("0x", "#")}">&nbsp;{esc(text)}&nbsp;</font>'


def fmt_date(iso: str | None, with_time: bool = False) -> str:
    if not iso:
        return "not recorded"
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return d.strftime("%d %b %Y, %H:%M UTC") if with_time else d.strftime("%d %B %Y")


class Heading(Paragraph):
    def __init__(self, text, style, level):
        super().__init__(text, style)
        self.toc_level, self.toc_text = level, text


class NumberedCanvas(rl_canvas.Canvas):
    """Two passes so every footer can say "Page x of y"."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.setFont("Plex", 7.5)
                self.setFillColor(MUTED)
                self.drawRightString(W - MARGIN, 11 * mm, f"Page {self._pageNumber} of {total}")
            super().showPage()
        super().save()


class ReportDoc(BaseDocTemplate):
    def __init__(self, buf, case_id: str, **kw):
        super().__init__(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=24 * mm, bottomMargin=20 * mm,
                         title="Synex research report", author="Synex", subject=f"Case {case_id}", **kw)
        self.case_id = case_id
        cover = Frame(MARGIN, 18 * mm, W - 2 * MARGIN, H - 70 * mm, id="cover", leftPadding=0, rightPadding=0)
        body = Frame(MARGIN, 20 * mm, W - 2 * MARGIN, H - 44 * mm, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate("cover", [cover], onPage=self._cover_page), PageTemplate("body", [body], onPage=self._body_page)])

    def afterFlowable(self, flowable):
        if isinstance(flowable, Heading) and flowable.toc_level == 0:
            self.notify("TOCEntry", (flowable.toc_level, flowable.toc_text, self.page))

    def _cover_page(self, c, doc):
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, H - 46 * mm, W, 46 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Serif", 30)
        c.drawString(MARGIN, H - 26 * mm, "Synex")
        c.setFont("PlexMono", 8)
        c.drawString(MARGIN, H - 34 * mm, "EXPERT RESEARCH REPORT")
        c.setFillColor(colors.HexColor("#c9a24d"))
        c.rect(MARGIN, H - 46 * mm, 38 * mm, 1.6 * mm, stroke=0, fill=1)
        c.setFont("Plex", 7.5)
        c.setFillColor(MUTED)
        c.drawString(MARGIN, 11 * mm, "Prepared for the client who asked the question. Confidential.")
        c.restoreState()

    def _body_page(self, c, doc):
        c.saveState()
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(MARGIN, H - 17 * mm, W - MARGIN, H - 17 * mm)
        c.line(MARGIN, 16 * mm, W - MARGIN, 16 * mm)
        c.setFont("Serif", 11)
        c.setFillColor(NAVY)
        c.drawString(MARGIN, H - 14 * mm, "Synex")
        c.setFont("PlexMono", 7.5)
        c.setFillColor(MUTED)
        c.drawRightString(W - MARGIN, H - 14 * mm, f"RESEARCH REPORT  ·  CASE {self.case_id}")
        c.setFont("Plex", 7.5)
        c.drawString(MARGIN, 11 * mm, "Prepared for the client who asked the question. Confidential.")
        c.restoreState()


def _table(rows, widths, header=True, zebra=True, extra=()):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), PANEL), ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY)]
    t.setStyle(TableStyle(style + list(extra)))
    return t


def _box(flowables, bg=PANEL, bar=NAVY, pad=9):
    t = Table([[flowables]], colWidths=[W - 2 * MARGIN])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 2.2, bar), ("LEFTPADDING", (0, 0), (-1, -1), pad + 2),
                           ("RIGHTPADDING", (0, 0), (-1, -1), pad), ("TOPPADDING", (0, 0), (-1, -1), pad - 2), ("BOTTOMPADDING", (0, 0), (-1, -1), pad - 2)]))
    return t


def _short(text: str, n: int = 110) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def build_pdf(d: dict, overview: dict | None) -> bytes:
    """d: data.collect(...)  overview: overview.write(...) or None."""
    _fonts()
    st = _styles()
    res = d["result"]
    subs = res["subquestions"]
    answered = [s for s in subs if s["status"] == "answered"]
    cov = d["coverage_total"]
    used = cov["accepted"] + cov["redacted"]
    delivered = d["state"] == "DELIVERED"
    full_w = W - 2 * MARGIN
    story: list = []

    # ---------------------------------------------------------------- cover
    story += [Spacer(1, 6 * mm), Paragraph("THE QUESTION", st["eyebrow"]), Paragraph(esc(d["question"]), st["title"]), Spacer(1, 3 * mm)]
    meta = [[Paragraph("Report for", st["small"]), Paragraph(f"Case <font name='PlexMono'>{esc(d['case_id'])}</font>", st["cell"]),
             Paragraph("Status", st["small"]), Paragraph("Delivered, collection closed" if delivered else "Interim: collection still open", st["cell"])],
            [Paragraph("Research started", st["small"]), Paragraph(fmt_date(d["created_at"]), st["cell"]),
             Paragraph("Report generated", st["small"]), Paragraph(fmt_date(d["generated_at"], True), st["cell"])]]
    t = Table(meta, colWidths=[28 * mm, 50 * mm, 28 * mm, full_w - 106 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [t, Spacer(1, 7 * mm)]

    def stat(number, label):
        return [Paragraph(esc(number), st["stat"]), Paragraph(esc(label), st["small"])]
    resolved = sum(1 for c in d["sourcing"]["companies"] if c["resolved"])
    cards = Table([[stat(f"{len(answered)} of {len(subs)}", "sub-questions answered"), stat(str(used), "expert answers used"),
                    stat(str(d["outreach"]["experts_responded"]), "experts who responded"), stat(str(resolved), "companies searched")]],
                  colWidths=[full_w / 4] * 4)
    cards.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 9),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [cards, Spacer(1, 6 * mm), _box([Paragraph("<b>How to read this report.</b> " + esc(d["provenance"]), st["small"])], bg=colors.HexColor("#fbf6ea"), bar=GOLD), Spacer(1, 7 * mm)]
    story += [Paragraph("CONTENTS", st["eyebrow"])]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("toc1", fontName="Plex-Medium", fontSize=9.5, leading=15, textColor=INK, leftIndent=0, spaceBefore=3),
                       ParagraphStyle("toc2", fontName="Plex", fontSize=8.5, leading=12, textColor=MUTED, leftIndent=12)]
    toc.dotsMinLevel = 0
    story += [toc, NextPageTemplate("body"), PageBreak()]

    # ------------------------------------------------------- executive summary
    story += [Heading("1. Executive summary", st["h1"], 0)]
    head = (overview or {}).get("headline")
    if head:
        story += [_box([Paragraph(esc(head["text"]), st["headline"]), Spacer(1, 3), Paragraph(cite(head["cites"]), st["small"])], bg=PANEL, bar=GOLD, pad=11), Spacer(1, 4)]
    else:
        tally = ", ".join(f"{n} {k}" for k, n in d["tally"].items() if n) or "no confidence levels yet"
        story += [Paragraph(f"{len(answered)} of {len(subs)} sub-questions have at least one accepted expert answer ({cov['accepted']} accepted, "
                            f"{cov['redacted']} with words removed). Confidence: {esc(tally)}. "
                            "A written overview was not available when this report was generated; the findings below are the experts' own answers and the figures computed from them.", st["body"])]
    findings = (overview or {}).get("key_findings") or []
    if findings:
        story += [Paragraph("Key findings", st["h3"])]
        for f in findings:
            story += [Paragraph(f"{esc(f['text'])} {cite(f['cites'])}", st["bullet"], bulletText="•")]

    story += [Paragraph("Evidence at a glance", st["h3"])]
    rows = [[Paragraph(x, st["cellb"]) for x in ("#", "Sub-question", "Answers used", "Indep. sources", "Agreement", "Confidence")]]
    extra = []
    for n, s in enumerate(subs, start=1):
        used_n = s["coverage"]["accepted"] + s["coverage"]["redacted"]
        label = {"single source": "Single source", "consensus": "Consensus", "split": "Experts disagree",
                 "multiple sources, agreement not assessed": "Not assessed", "multiple sources, different aspects": "Different aspects"}.get(s["label"] or "", "-")
        conf = s["confidence"]
        rows.append([Paragraph(str(s["index"]), st["cell"]), Paragraph(esc(_short(s["text"], 120)), st["cell"]),
                     Paragraph(f"{used_n} of {s['coverage']['received']} received" if s["status"] != "not sourced" else "not searched", st["cell"]),
                     Paragraph(str(s["independent_sources"]) if s["status"] == "answered" else "-", st["cell"]), Paragraph(esc(label), st["cell"]),
                     Paragraph(pill(conf.upper(), CONF_COLOR[conf]) if conf else "-", st["cell"])])
    story += [_table(rows, [8 * mm, 66 * mm, 28 * mm, 20 * mm, 28 * mm, full_w - 150 * mm], extra=extra)]
    story += [Paragraph("Confidence is computed in code, not by the model: High needs three or more independent sources, Medium two, Low one. "
                        "Two experts count as one source when they worked at the same company, in the same function and city, with at least three months of overlap.", st["small"])]

    thin = []
    for s in subs:
        if s["status"] == "not sourced":
            thin.append(f"Sub-question {s['index']} was not searched in this run, so no expert was invited for it.")
        elif s["status"] != "answered":
            c = s["coverage"]
            thin.append(f"Sub-question {s['index']} has no accepted answer yet ({c['received']} received: {c['pending']} being screened, {c['held']} held, {c['rejected']} rejected).")
        elif s["independent_sources"] == 1:
            thin.append(f"Sub-question {s['index']} rests on a single independent source.")
        elif s["label"] == "split":
            thin.append(f"On sub-question {s['index']} the experts disagree; both views are shown.")
    if thin:
        story += [Paragraph("Where the evidence is thin", st["h3"])] + [Paragraph(esc(x), st["bullet"], bulletText="•") for x in thin]
    nq = (overview or {}).get("next_questions") or []
    if nq:
        story += [Paragraph("Suggested next questions", st["h3"])] + [Paragraph(esc(q), st["bullet"], bulletText="•") for q in nq]

    # ------------------------------------------------------------- findings
    story += [PageBreak(), Heading("2. Findings by sub-question", st["h1"], 0)]
    for s in subs:
        c = s["coverage"]
        pills = []
        if s["confidence"]:
            pills.append(pill(f"{s['confidence'].upper()} CONFIDENCE", CONF_COLOR[s["confidence"]]))
        if s["label"]:
            pills.append(pill({"single source": "SINGLE SOURCE", "consensus": "CONSENSUS", "split": "EXPERTS DISAGREE",
                               "multiple sources, agreement not assessed": "AGREEMENT NOT ASSESSED", "multiple sources, different aspects": "DIFFERENT ASPECTS"}.get(s["label"], s["label"].upper()), BLUE))
        block = [Heading(f"Sub-question {s['index']}", st["h2"], 1), Paragraph(esc(s["text"]), st["qtext"]), Spacer(1, 2)]
        if s.get("expertise"):
            block += [Paragraph(f"Expertise sought: {esc(s['expertise'])}", st["small"])]
        if pills:
            block += [Spacer(1, 5), Paragraph(" &nbsp; ".join(pills), st["body"]), Spacer(1, 3)]
        story += [KeepTogether(block)]
        if s["status"] == "not sourced":
            story += [Paragraph("This sub-question was not searched in this run (development limits), so no expert was invited for it.", st["small"])]
            continue
        if s["status"] != "answered":
            story += [Paragraph(f"No accepted answer. {c['received']} received: {c['pending']} being screened, {c['held']} held for review, {c['rejected']} rejected.", st["body"])]
            continue
        story += [Paragraph(f"{len(s['answers'])} accepted answer{'s' if len(s['answers']) != 1 else ''} from {s['independent_sources']} independent source"
                            f"{'s' if s['independent_sources'] != 1 else ''}. Received {c['received']}: {c['accepted']} accepted, {c['redacted']} with words removed, "
                            f"{c['held']} held, {c['rejected']} rejected, {c['pending']} pending.", st["small"])]
        summ = s.get("summary")
        if summ and summ["sentences"]:
            clean = " ".join(f"{esc(_strip_refs(x['text']))} {cite(x['cites'])}" for x in summ["sentences"])
            story += [Spacer(1, 4), _box([Paragraph("SUMMARY", st["eyebrow"]), Paragraph(clean, st["body"])], bg=PANEL, bar=NAVY)]
            if summ["dropped_uncited"]:
                story += [Paragraph(f"{summ['dropped_uncited']} generated sentence(s) without a valid citation were removed before this report was written.", st["tiny"])]
        else:
            story += [Paragraph("No written summary for this sub-question; the experts' answers follow.", st["small"])]
        story += [Paragraph("What the experts said", st["h3"])]
        for a in s["answers"]:
            meta_line = f'{esc(a["role"] or "Former employee")}' + (f' · {esc(a["company"])}' if a["company"] else "")
            tag = pill("WORDS REMOVED", GOLD) if a["verdict"] == "redacted" else pill("ACCEPTED", GREEN)
            left = [Paragraph(f'<font name="PlexMono" size="7.5" color="#2b5fa6">{esc(a["ref"])}</font>', st["cell"]), Paragraph(meta_line, st["small"])]
            right = [Paragraph(para_text(a["text"]), st["quote"]), Spacer(1, 3),
                     Paragraph(f'{tag} &nbsp;<font size="7.5" color="#5a6472">answered by {esc(a["mode"])} · self-rated confidence {esc(a["confidence"] or "not given")} · '
                               f'record <font name="PlexMono">{esc(a["response_id"])}</font></font>', st["small"])]
            row = Table([[left, right]], colWidths=[40 * mm, full_w - 40 * mm])
            row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            story += [KeepTogether([row])]
        notes = [g for g in s["groups"] if len(g["refs"]) > 1]
        if notes or s["independence_unchecked"]:
            story += [Paragraph("How the sources were counted", st["h3"])]
            for g in notes:
                story += [Paragraph(f"{cite(g['refs'])}: {esc(g['evidence'])}", st["small"])]
            for u in s["independence_unchecked"]:
                story += [Paragraph(f"{cite([u['ref']])}: counted as a separate source because the profile lacks {esc(', '.join(u['missing']))}.", st["small"])]

    # --------------------------------------------------------------- appendices
    story += [PageBreak(), Heading("Appendix A. Method and scope", st["h1"], 0)]
    sc, out, sg = d["screen"], d["outreach"], d["sourcing"]
    story += [Paragraph("The steps below describe what the system did for this question. Every figure comes from the case's own records.", st["body"]), Spacer(1, 4)]
    steps = [("1. Question screen", f"Verdict: {esc(sc['verdict'] or 'n/a')}. " + esc(sc["reason"] or "") + (f" The question was rewritten before planning: {esc(sc['effective_question'])}" if sc["verdict"] == "rewrite" else "")),
             ("2. Plan", f"The question was split into {len(d['plan'])} sub-question{'s' if len(d['plan']) != 1 else ''}, each with the expertise sought and the companies whose former employees would know."),
             ("3. Sourcing", f"Former employees were searched in Crustdata's live people data, by company and role, for people whose role ended between {d['window']['min_left']} and {d['window']['max_left']} months ago and who spent at least {d['window']['min_years']} year in it. {sg['people_found']} distinct people were found."),
             ("4. People screen", "Each person was checked by fixed rules in code (not a current employee, cooling-off, freshness, minimum tenure, competitor conflict, restricted list). A person who could not be verified, or whose company record was ambiguous, was left out rather than guessed. Sensitive roles were flagged for a human decision."),
             ("5. Ranking", "A small model scored each remaining person against the sub-question and had to quote evidence from the profile; code dropped any quote that was not in the profile."),
             ("6. Invitations", f"{out['invited']} anonymised invitation{'s' if out['invited'] != 1 else ''} were drafted" + (f", each with {out['questions']['questions_per_expert']} questions matched to the expert's role" if out.get("questions") else "") +
              f". The customer approved them before anything was sent. Status: {esc(', '.join(f'{n} {k.lower()}' for k, n in out['by_status'].items()))}."),
             ("7. Response screen", f"Every answer was screened before it reached this report: {cov['accepted']} accepted, {cov['redacted']} accepted with words removed, {cov['held']} held for a team member, {cov['rejected']} rejected, {cov['pending']} still pending."),
             ("8. Result", "Sources, agreement and confidence were computed from the accepted answers and the experts' work history. The summaries were written by a small model; a sentence without a valid citation was dropped.")]
    story += [Table([[Paragraph(f"<b>{a}</b>", st["cell"]), Paragraph(b, st["cell"])] for a, b in steps], colWidths=[34 * mm, full_w - 34 * mm],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))]
    story += [Paragraph("Companies searched", st["h3"])]
    comp_rows = [[Paragraph(x, st["cellb"]) for x in ("Company", "Why it was searched", "Result")]]
    for c in sg["companies"]:
        result = (f"{esc(c['name'])}" + (f" ({c['matches']} matching people)" if c["matches"] else "")) if c["resolved"] else esc(c["note"] or "Not searched: the company record could not be confirmed")
        comp_rows.append([Paragraph(esc(c["asked"]), st["cell"]), Paragraph("Named in the question" if c["basis"] == "named" else "Suggested as a comparable employer", st["cell"]), Paragraph(result, st["cell"])])
    story += [_table(comp_rows, [45 * mm, 50 * mm, full_w - 95 * mm])]

    story += [PageBreak(), Heading("Appendix B. Experts who answered", st["h1"], 0),
              Paragraph("Experts appear only by an anonymous reference, a broad role label, their former employer, a tenure band and the year they left. "
                        "A title is shown exactly only when at least three experts in the case share it.", st["body"]), Spacer(1, 4)]
    ex_rows = [[Paragraph(x, st["cellb"]) for x in ("Ref", "Role", "Company", "Tenure", "Left", "Country", "Answers")]]
    for e in d["experts"]:
        ex_rows.append([Paragraph(f'<font name="PlexMono" size="7.2">{esc(e["ref"])}</font>', st["cell"]), Paragraph(esc(e["role"] or "-"), st["cell"]), Paragraph(esc(e["company"] or "-"), st["cell"]),
                        Paragraph(esc(e["tenure"]), st["cell"]), Paragraph(esc(e["left"] or "-"), st["cell"]), Paragraph(esc(e["country"] or "-"), st["cell"]), Paragraph(str(e["answers"]), st["cell"])])
    story += [_table(ex_rows, [24 * mm, 42 * mm, 36 * mm, 24 * mm, 14 * mm, 18 * mm, full_w - 158 * mm])] if d["experts"] else [Paragraph("No expert answer has been accepted yet.", st["body"])]

    story += [Heading("Appendix C. People screening", st["h1"], 0),
              Paragraph(f"{sg['people_found']} distinct people were found across the sub-questions. The table counts people per sub-question (a person can be found for several).", st["body"]), Spacer(1, 4)]
    sr = [[Paragraph(x, st["cellb"]) for x in ("Sub-question", "Considered", "Passed", "Flagged for review", "Removed", "Could not verify")]]
    for r in sg["per_subquestion"]:
        sr.append([Paragraph(str(r["index"]), st["cell"])] + [Paragraph(str(r[k]), st["cell"]) for k in ("considered", "pass", "review", "fail", "cannot_verify")])
    story += [_table(sr, [24 * mm, 26 * mm, 24 * mm, 36 * mm, 26 * mm, full_w - 136 * mm])]
    if sg["removed_by_rule"]:
        story += [Paragraph("Why people were removed", st["h3"])]
        story += [_table([[Paragraph("Reason", st["cellb"]), Paragraph("People", st["cellb"])]] + [[Paragraph(esc(k), st["cell"]), Paragraph(str(v), st["cell"])] for k, v in sg["removed_by_rule"].items()], [full_w - 30 * mm, 30 * mm])]

    au, calls, cost = d["audit"], d["calls"], d["cost"]
    story += [PageBreak(), Heading("Appendix D. Audit trail and cost", st["h1"], 0)]
    ok = au["chain_ok"]
    story += [_box([Paragraph(("<b>Audit chain verified.</b> " if ok else "<b>Audit chain check failed.</b> ") +
                              f"Every step of this case is recorded as an event that stores the hash of the one before it. At the moment this report was generated, "
                              f"the chain of all {au['chain_events_checked']} events in the system was recomputed and " + ("found intact." if ok else f"first differed at event {au['chain_first_bad']}."), st["body"]),
                    Spacer(1, 3), Paragraph(f"This case: {au['events']} events, from {fmt_date(au['started_at'], True)} to {fmt_date(au['last_event_at'], True)}", st["small"]),
                    Paragraph(f"First hash <font name='PlexMono'>{esc((au['first_hash'] or '')[:32])}</font>", st["small"]),
                    Paragraph(f"Latest hash <font name='PlexMono'>{esc((au['last_hash'] or '')[:32])}</font>", st["small"])], bg=colors.HexColor("#eef6f1") if ok else colors.HexColor("#fbeeee"), bar=GREEN if ok else RED)]
    story += [Paragraph("Model calls", st["h3"])]
    mrows = [[Paragraph(x, st["cellb"]) for x in ("Purpose", "Calls", "Tokens in", "Tokens out", "Cost (USD)")]]
    for r in calls["model"]:
        mrows.append([Paragraph(esc(r["purpose"].replace("_", " ")), st["cell"]), Paragraph(str(r["calls"]), st["cell"]), Paragraph(f"{r['tin']:,}", st["cell"]), Paragraph(f"{r['tout']:,}", st["cell"]), Paragraph(f"{r['usd']:.4f}", st["cell"])])
    mrows.append([Paragraph("<b>Total</b>", st["cell"]), Paragraph(f"<b>{sum(r['calls'] for r in calls['model'])}</b>", st["cell"]), Paragraph("", st["cell"]), Paragraph("", st["cell"]), Paragraph(f"<b>{sum(r['usd'] for r in calls['model']):.4f}</b>", st["cell"])])
    story += [_table(mrows, [62 * mm, 20 * mm, 30 * mm, 30 * mm, full_w - 142 * mm])]
    story += [Paragraph("Crustdata calls", st["h3"])]
    crows = [[Paragraph(x, st["cellb"]) for x in ("Purpose", "Calls", "Credits")]]
    for r in calls["crustdata"]:
        crows.append([Paragraph(esc(r["purpose"].replace("_", " ")), st["cell"]), Paragraph(str(r["calls"]), st["cell"]), Paragraph(f"{r['credits']:.1f}", st["cell"])])
    crows.append([Paragraph("<b>Total</b>", st["cell"]), Paragraph(f"<b>{sum(r['calls'] for r in calls['crustdata'])}</b>", st["cell"]), Paragraph(f"<b>{sum(r['credits'] for r in calls['crustdata']):.1f}</b>", st["cell"])])
    story += [_table(crows, [62 * mm, 30 * mm, full_w - 92 * mm])]
    story += [Paragraph(f"Cost of the model calls in rupees at the system's configured rate: ₹{cost.get('model_inr', 'n/a')}. No payment is taken for this research; a price shown in the application is a quote only.", st["small"])]

    story += [Heading("Appendix E. Limitations", st["h1"], 0)]
    for text in ("Expert answers are opinions from a small number of people. Independent sources are counted from work history and the count is approximate: Crustdata does not give the city of each past role, so the profile's current city is used, and a missing field counts the expert as a separate source.",
                 "A model wrote the summaries and the overview. Each sentence must cite an answer and code removes any that does not, but a cited sentence can still read more strongly than the answers behind it. Check the cited answers before relying on a point.",
                 "Answers that contained confidential or non-public material were removed or left out by the response screen; this report shows only what passed it.",
                 "Only people whose profile data was available and verifiable were considered. Companies whose records could not be confirmed were not searched, so the panel may under-represent them.",
                 d["provenance"]):
        story += [Paragraph(esc(text), st["bullet"], bulletText="•")]

    buf = io.BytesIO()
    doc = ReportDoc(buf, d["case_id"])
    doc.multiBuild(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def _strip_refs(text: str) -> str:
    """The summary sentences end with their [ref] markers; the PDF shows the refs once, from the cites list."""
    import re
    return re.sub(r"\s*\[E[0-9a-f]{8}\]", "", text).strip()
