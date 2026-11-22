from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core import config
from .actions.routes import router as approvals_router
from .jobs.audit_routes import router as audit_router
from .jobs.routes import router as cases_router

app = FastAPI(title="Synex")
# the Next.js app runs on another port in development
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(cases_router)
app.include_router(approvals_router)
app.include_router(audit_router)


@app.get("/health")
def health():
    return {"ok": True, "demo_mode": config.demo_mode()}
