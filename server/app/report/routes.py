"""Report routes (customer-safe): prepare the written parts, then download the PDF."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..core import db
from ..core.events import append_event
from ..stages import s8_result
from . import data, overview, pdf

router = APIRouter()


@router.post("/customer/cases/{case_id}/report/prepare")
def prepare_report(case_id: str):
    """Make sure the summary and the overview exist for the current answers. Safe to repeat: the same answers make
    no new model call. A model failure does not block the report; the status says what is missing."""
    conn = db.connect()
    try:
        try:
            status = overview.prepare(conn, case_id)
        except s8_result.NoAnswers:
            raise HTTPException(409, "no accepted answer yet")
        except KeyError:
            raise HTTPException(404, "no such case")
        return {"case_id": case_id, **status, "ready": True}
    finally:
        conn.close()


@router.get("/customer/cases/{case_id}/report.pdf")
def download_report(case_id: str):
    """The client report as a PDF, built from the case's current screened answers. 409 until one answer is accepted."""
    conn = db.connect()
    try:
        d = data.collect(conn, case_id)           # 404 for an unknown case
        if not any(sq["status"] == "answered" for sq in d["result"]["subquestions"]):
            raise HTTPException(409, "no accepted answer yet")
        ov = overview.stored(conn, case_id, d["result"])
        content = pdf.build_pdf(d, ov)
        append_event(conn, case_id, "report.generated", {
            "bytes": len(content), "with_overview": ov is not None, "summary_status": d["result"]["summary_status"],
            "answers_used": d["coverage_total"]["accepted"] + d["coverage_total"]["redacted"]})
        return Response(content, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="synex-report-{case_id}.pdf"', "Cache-Control": "no-store"})
    finally:
        conn.close()
