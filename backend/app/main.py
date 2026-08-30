from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.db.session import init_db
from app.participation.router import router as participation_router
from app.verify.router import router as verify_router
from app.web.router import router as web_router

app = FastAPI(title="RE-ACT 리액트봇")

app.mount(
    "/static", StaticFiles(directory=str(Path(__file__).parent / "web" / "static")), name="static"
)

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(verify_router)
app.include_router(participation_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
