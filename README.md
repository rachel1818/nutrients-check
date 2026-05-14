# Nutrient Check

A Python/FastAPI web app that helps you understand nutrients: what foods provide them, what improves or reduces their absorption, and why your body needs them.

All data is sourced from trusted references: NIH ODS, USDA FoodData Central, Harvard T.H. Chan School of Public Health, Cleveland Clinic, and Mayo Clinic. Every data point links to its source.

---

## Setup

### 1. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` as needed:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./nutrients.db` | SQLAlchemy database URL |
| `DEBUG` | `true` | Enable debug mode and plain-text logging |
| `APP_HOST` | `127.0.0.1` | Host to bind the server to |
| `APP_PORT` | `8000` | Port to bind the server to |

### 4. Run database migrations

```bash
alembic upgrade head
```

This creates all 8 database tables with indexes.

### 5. Seed the database

```bash
python tools/seed_data.py
```

Seeds 10 nutrients (Vitamins A, D, E, C, B12, B9; Iron, Calcium, Zinc, Magnesium) with food sources, absorption data, body roles, and RDA values — all from trusted sources. Safe to re-run.

### 6. Start the development server

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Running Tests

```bash
pytest --cov=app --cov-fail-under=80
```

Tests use an in-memory SQLite database — no state is shared between test functions.

---

## Linting

```bash
ruff check app/ tools/ tests/
```

---

## Production

Run with Gunicorn + Uvicorn workers:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### CORS for Production

In `app/main.py`, the CORS middleware uses:

```python
allow_origin_regex=r"https?://localhost(:\d+)?"
```

For production, replace this with your actual domain:

```python
allow_origins=["https://yourdomain.com"]
```

---

## API Reference

| Endpoint | Description |
|---|---|
| `GET /` | Home page |
| `GET /search?nutrient=iron` | Search result page |
| `GET /nutrients` | All nutrients grouped by category |
| `GET /nutrients/{id}` | Nutrient detail page |
| `GET /health` | Health check: `{"status": "ok"}` |
| `GET /sitemap.xml` | Dynamic sitemap |
| `GET /robots.txt` | Robots file |
| `GET /api/nutrients` | Paginated nutrient list (`offset`, `limit`) |
| `GET /api/nutrients/suggest?q=...` | Autocomplete (≤8 results, rate-limited 30/min) |
| `GET /api/nutrients/by-slug/{slug}` | Full nutrient detail by slug |
| `GET /api/nutrients/{id}` | Full nutrient detail by ID |
| `GET /api/nutrients/{id}/foods` | Paginated food sources |

---

## Architecture

This project follows the WAT framework (Workflows, Agents, Tools):

- **Workflows** (`workflows/`): Markdown SOPs defining objectives and steps
- **Tools** (`tools/`): Python scripts for deterministic execution (seed data, etc.)
- **Agent**: FastAPI app — reads workflows, calls tools, handles requests
