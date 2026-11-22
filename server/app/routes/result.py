"""Customer-safe result routes (stage 8). No names, links, addresses, cities or person ids."""
from fastapi import APIRouter, HTTPException

from ..core import db
from ..stages import s8_result

router = APIRouter()


@router.get("/customer/cases/{case_id}/result")
def get_result(case_id: str):
    conn = db.connect()
    try:
        return s8_result.compute(conn, case_id)
    except KeyError:
        raise HTTPException(404, "no such case")
    finally:
        conn.close()


@router.post("/customer/cases/{case_id}/result/summary")
def write_summary(case_id: str):
    conn = db.connect()
    try:
        return s8_result.write_summary(conn, case_id)
    except KeyError:
        raise HTTPException(404, "no such case")
    except s8_result.NoAnswers:
        raise HTTPException(409, "no accepted answer yet")
    except Exception as e:  # model failure or budget reached: the structured result still stands
        raise HTTPException(503, f"summary not written ({type(e).__name__}); the structured result is still valid")
    finally:
        conn.close()
