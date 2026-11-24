import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .core import config, keys
from .actions.routes import router as approvals_router
from .core.operator_auth import require_operator_key
from .jobs.audit_routes import router as audit_router
from .jobs.mailbox_routes import router as mailbox_router
from .jobs.routes import router as cases_router
from .routes.expert import router as expert_router
from .routes.result import router as result_router
from .jobs import runner
from .stages import s7_response_screen

@asynccontextmanager
async def lifespan(_app):
    # answers whose screening died with a restart get screened now (stage 7, safe to repeat)
    threading.Thread(target=s7_response_screen.sweep_unscreened, daemon=True).start()
    # cases and approved invitations that a restart interrupted continue now, each action exactly once
    threading.Thread(target=runner.resume_on_startup, daemon=True).start()
    yield


app = FastAPI(title="Synex", lifespan=lifespan)
# the Next.js app runs on another port in development
@app.middleware("http")
async def remember_keys(request: Request, call_next):
    """The browser's own API keys ride along on every request; hold them (memory only) for the case in the path."""
    cid = keys.case_id_from_path(request.url.path)
    if cid:
        keys.remember(cid, keys.from_headers(request.headers))
    return await call_next(request)


app.middleware("http")(require_operator_key)   # added before CORS, so CORS wraps it and a 401 still carries CORS headers
app.add_middleware(CORSMiddleware, allow_origins=config.web_origins(),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(cases_router)
app.include_router(approvals_router)
app.include_router(audit_router)
app.include_router(mailbox_router)
app.include_router(expert_router)
app.include_router(result_router)


@app.exception_handler(keys.MissingKey)
async def missing_key(_request: Request, exc: keys.MissingKey):
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": str(exc), "code": "missing_key"}, status_code=400)


@app.get("/health")
def health():
    # which keys the server already has in .env (a local clone): the web page asks visitors only for the missing ones
    return {"ok": True, "demo_mode": config.demo_mode(),
            "server_keys": {"anthropic": bool(keys._find("anthropic", None)[0]), "crustdata": bool(keys._find("crustdata", None)[0])}}
