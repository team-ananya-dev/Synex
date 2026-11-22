from fastapi import FastAPI

from .core import config

app = FastAPI(title="Synex")


@app.get("/health")
def health():
    return {"ok": True, "demo_mode": config.demo_mode()}
