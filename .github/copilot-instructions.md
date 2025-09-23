# Copilot Instructions for Parquet Viewer

## Project Overview
Parquet Viewer is a FastAPI-based web application for professional exploration and visualization of Parquet files. It integrates DuckDB for technical data extraction and PostgreSQL (via SQLAlchemy) for metadata management. The frontend is served as static files and templates, with advanced search, filtering, and responsive UI.

## Architecture & Key Components
- **Backend:**
  - `main.py`: FastAPI app entrypoint, mounts static files, includes main and admin routers.
  - `api/routes.py`, `api/admin_routes.py`: Define main and admin API endpoints. Use dependency injection for services.
  - `core/database.py`: Centralized database manager for DuckDB (Parquet) and PostgreSQL (metadata).
  - `services/`: Contains business logic for file, metadata, chart, and admin operations. Services combine DuckDB and PostgreSQL data.
  - `models/`: SQLAlchemy models for metadata and custom classes for Parquet file info.
- **Frontend:**
  - `static/`: JS, CSS, and assets. Key JS modules in `static/js/` and `static/js/utils/`.
  - `templates/`: Jinja2 HTML templates for main, admin, and components.

## Data Flow
- Parquet files are read via DuckDB (see `services/file_service.py`).
- Metadata is stored and retrieved from PostgreSQL using SQLAlchemy async models.
- API endpoints combine both sources for unified responses (see `CombinedFileInfo`).

## Developer Workflows
- **Run locally:**
  - `python main.py` (requires PostgreSQL running and Parquet files in `parquet_files/`)
  - Or use Docker: `docker-compose up`
- **Dependencies:**
  - All Python dependencies in `requirements.txt`. Install with `pip install -r requirements.txt`.
- **Testing:**
  - Integration tests in `test_integration.py`. Run with `pytest test_integration.py`.
- **Debugging:**
  - Set `echo=True` in `core/database.py` for SQL query logging.

## Conventions & Patterns
- **Service Layer:** All business logic is in `services/`, not in routes.
- **Async:** All DB operations are async (SQLAlchemy, FastAPI endpoints).
- **Dependency Injection:** Use FastAPI's `Depends` for service instantiation.
- **Combined Data:** API responses often merge DuckDB and PostgreSQL data (see `get_all_files_combined`).
- **Frontend Modularization:** JS components are split by feature in `static/js/utils/components/`.

## Integration Points
- **DuckDB:** For direct Parquet file access (no external DB needed).
- **PostgreSQL:** For metadata and admin features.
- **FastAPI:** For REST API and static file serving.

## Examples
- To add a new API endpoint, create a service in `services/`, add a route in `api/routes.py`, and update models as needed.
- To extend metadata, update SQLAlchemy models in `models/database_models.py` and migration SQL in `database/init.sql`.

---
For questions or unclear patterns, review `main.py`, `core/database.py`, and `services/file_service.py` for canonical examples.
