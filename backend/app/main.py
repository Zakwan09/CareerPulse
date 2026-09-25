from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.database import init_db
from backend.app.routers import auth, dashboard, jobs, skills, analytics, ml, forecast, skill_gap

ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "frontend" / "templates"
STATIC_DIR = ROOT_DIR / "frontend" / "static"

app = FastAPI(title="CareerPulse", description="Data-Driven Job Market & Skill Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Routers (API only auto-creates tables; it never retrains models)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(jobs.router)
app.include_router(skills.router)
app.include_router(analytics.router)
app.include_router(ml.router)
app.include_router(forecast.router)
app.include_router(skill_gap.router)


@app.on_event("startup")
def on_startup():
    # Only ensures tables exist; does NOT ingest data or train models.
    # Run scripts/run_pipeline.py separately to (re)build data + models.
    init_db()


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces / secrets to the client.
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# ------------------------------------------------------------------
# Frontend page routes (static shells; JS handles auth + data fetching)
# ------------------------------------------------------------------
def _page(name: str):
    def handler(request: Request):
        return templates.TemplateResponse(request, f"{name}.html", {})
    return handler


app.get("/", response_class=HTMLResponse)(_page("login"))
app.get("/login", response_class=HTMLResponse)(_page("login"))
app.get("/register", response_class=HTMLResponse)(_page("register"))
app.get("/dashboard", response_class=HTMLResponse)(_page("dashboard"))
app.get("/market", response_class=HTMLResponse)(_page("market"))
app.get("/skills", response_class=HTMLResponse)(_page("skills"))
app.get("/trends", response_class=HTMLResponse)(_page("trends"))
app.get("/skill-gap", response_class=HTMLResponse)(_page("skill_gap"))
app.get("/profile", response_class=HTMLResponse)(_page("profile"))
