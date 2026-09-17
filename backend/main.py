from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database.db import init_db
from routes.export_routes import router as export_router
from routes.live_scrape_routes import router as live_scrape_router
from routes.scrape_routes import router as scrape_router
from routes.template_routes import router as template_router


app = FastAPI(
    title="Jason's Web Scraper Bot API",
    description="A prototype AI-guided, compliance-aware public web scraping assistant.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BACKEND_DIR / "static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "Jason's Web Scraper Bot API"}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(scrape_router)
app.include_router(live_scrape_router)
app.include_router(template_router)
app.include_router(export_router)
