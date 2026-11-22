import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core import config
from .actions.routes import router as approvals_router
from .jobs.audit_routes import router as audit_router
from .jobs.routes import router as cases_router
from .routes.expert import router as expert_router
from .routes.result import router as result_router
from .stages import s7_response_screen

@asynccontextmanager
async def lifespan(_app):
    # answers whose screening died with a restart get screened now (stage 7, safe to repeat)
    threading.Thread(target=s7_response_screen.sweep_unscreened, daemon=True).start()
    yield


app = FastAPI(title="Synex", lifespan=lifespan)
# the Next.js app runs on another port in development
app.add_middleware(CORSMiddleware, allow_origins=config.web_origins(),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(cases_router)
app.include_router(approvals_router)
app.include_router(audit_router)
app.include_router(expert_router)
app.include_router(result_router)


@app.get("/health")
def health():
    return {"ok": True, "demo_mode": config.demo_mode()}
