import logging
import os
import traceback
from contextlib import asynccontextmanager
from xml.etree.ElementTree import Element, SubElement, tostring

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pythonjsonlogger import jsonlogger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import Base, engine, get_db
from app.models import Nutrient, NutrientFoodSource, NutrientSynonym
from app.schemas import (
    NutrientDetailSchema,
    PaginatedFoodsSchema,
    PaginatedNutrientsSchema,
    SuggestItemSchema,
)
from app.search import search_nutrient

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Logging setup
logger = logging.getLogger("app")
_handler = logging.StreamHandler()
if DEBUG:
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
else:
    _handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(_handler)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info("Request: %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            logger.error("Unhandled exception:\n%s", traceback.format_exc())
            raise
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Nutrient Check", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://localhost(:\d+)?",
    allow_methods=["GET"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "..", "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ─── Custom error handlers ───────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(request, "404.html", {}, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse(request, "500.html", {}, status_code=500)


# ─── Health / utility ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/robots.txt", response_class=Response)
async def robots():
    content = "User-agent: *\nDisallow: /api/\n"
    return Response(content=content, media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap(request: Request, db: Session = Depends(get_db)):
    nutrients = db.query(Nutrient).order_by(Nutrient.name).all()
    root = Element("urlset")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    base_url = str(request.base_url).rstrip("/")
    for n in nutrients:
        url_el = SubElement(root, "url")
        loc = SubElement(url_el, "loc")
        loc.text = f"{base_url}/nutrients/{n.id}"
    xml_bytes = tostring(root, encoding="unicode", xml_declaration=False)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    return Response(content=xml_str, media_type="application/xml")


# ─── API routes (MUST be in this order to prevent route swallowing) ──────────

@app.get("/api/nutrients/suggest", response_model=list[SuggestItemSchema])
@limiter.limit("30/minute")
async def suggest_nutrients(request: Request, q: str = "", db: Session = Depends(get_db)):
    if len(q.strip()) < 2:
        return []
    results: list[Nutrient] = []
    seen_ids: set[int] = set()

    name_matches = (
        db.query(Nutrient).filter(Nutrient.name.ilike(f"%{q}%")).order_by(Nutrient.name).all()
    )
    for n in name_matches:
        if n.id not in seen_ids:
            results.append(n)
            seen_ids.add(n.id)

    if len(results) < 8:
        syn_matches = (
            db.query(NutrientSynonym)
            .filter(NutrientSynonym.synonym.ilike(f"%{q}%"))
            .all()
        )
        for s in syn_matches:
            if s.nutrient_id not in seen_ids and len(results) < 8:
                results.append(s.nutrient)
                seen_ids.add(s.nutrient_id)

    return results[:8]


@app.get("/api/nutrients/by-slug/{slug}", response_model=NutrientDetailSchema)
async def get_nutrient_by_slug(slug: str, db: Session = Depends(get_db)):
    nutrient = db.query(Nutrient).filter(Nutrient.slug == slug).first()
    if not nutrient:
        raise HTTPException(status_code=404, detail="Nutrient not found")
    return nutrient


@app.get("/api/nutrients", response_model=PaginatedNutrientsSchema)
async def list_nutrients(offset: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    total = db.query(Nutrient).count()
    items = (
        db.query(Nutrient).order_by(Nutrient.category, Nutrient.name).offset(offset).limit(limit).all()
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@app.get("/api/nutrients/{nutrient_id}/foods", response_model=PaginatedFoodsSchema)
async def get_nutrient_foods(
    nutrient_id: int, offset: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    nutrient = db.query(Nutrient).filter(Nutrient.id == nutrient_id).first()
    if not nutrient:
        raise HTTPException(status_code=404, detail="Nutrient not found")
    total = (
        db.query(NutrientFoodSource).filter(NutrientFoodSource.nutrient_id == nutrient_id).count()
    )
    items = (
        db.query(NutrientFoodSource)
        .filter(NutrientFoodSource.nutrient_id == nutrient_id)
        .order_by(NutrientFoodSource.amount.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@app.get("/api/nutrients/{nutrient_id}", response_model=NutrientDetailSchema)
async def get_nutrient(nutrient_id: int, db: Session = Depends(get_db)):
    nutrient = db.query(Nutrient).filter(Nutrient.id == nutrient_id).first()
    if not nutrient:
        raise HTTPException(status_code=404, detail="Nutrient not found")
    return nutrient


# ─── HTML routes ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, nutrient: str = "", db: Session = Depends(get_db)):
    result = {"nutrient": None, "suggestions": []}
    if nutrient.strip():
        result = search_nutrient(db, nutrient)

    top_foods: list[NutrientFoodSource] = []
    total_foods = 0
    if result["nutrient"]:
        n = result["nutrient"]
        total_foods = (
            db.query(NutrientFoodSource).filter(NutrientFoodSource.nutrient_id == n.id).count()
        )
        top_foods = (
            db.query(NutrientFoodSource)
            .filter(NutrientFoodSource.nutrient_id == n.id)
            .order_by(NutrientFoodSource.amount.desc())
            .limit(10)
            .all()
        )

    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "query": nutrient,
            "nutrient": result["nutrient"],
            "suggestions": result["suggestions"],
            "top_foods": top_foods,
            "total_foods": total_foods,
        },
    )


@app.get("/nutrients", response_class=HTMLResponse)
async def all_nutrients(request: Request, db: Session = Depends(get_db)):
    nutrients = db.query(Nutrient).order_by(Nutrient.category, Nutrient.name).all()
    return templates.TemplateResponse(request, "all_nutrients.html", {"nutrients": nutrients})


@app.get("/nutrients/{nutrient_id}", response_class=HTMLResponse)
async def nutrient_detail(request: Request, nutrient_id: int, db: Session = Depends(get_db)):
    nutrient = db.query(Nutrient).filter(Nutrient.id == nutrient_id).first()
    if not nutrient:
        raise HTTPException(status_code=404, detail="Nutrient not found")

    total_foods = (
        db.query(NutrientFoodSource).filter(NutrientFoodSource.nutrient_id == nutrient_id).count()
    )
    top_foods = (
        db.query(NutrientFoodSource)
        .filter(NutrientFoodSource.nutrient_id == nutrient_id)
        .order_by(NutrientFoodSource.amount.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "query": nutrient.name,
            "nutrient": nutrient,
            "suggestions": [],
            "top_foods": top_foods,
            "total_foods": total_foods,
        },
    )


@app.get("/nutrients/{nutrient_id}/foods", response_class=HTMLResponse)
async def nutrient_detail_foods(
    request: Request, nutrient_id: int, db: Session = Depends(get_db)
):
    """Redirect to detail page — this route exists only for completeness."""
    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=DEBUG)
