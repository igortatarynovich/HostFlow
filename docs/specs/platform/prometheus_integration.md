# Prometheus Integration Plan

## Dependencies

- Add `prometheus-client` to backend requirements.
- Optional: `prometheus-fastapi-instrumentator` for automatic HTTP metrics.

## Backend Changes

1. Initialize Prometheus metrics registry during app startup (`backend/app/main.py`).
2. Expose `/metrics` route:
   ```python
   from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
   @app.get("/metrics")
   async def metrics():
       return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
   ```
3. Register FastAPI middleware to collect request latency (Instrumentator or custom).
4. Ensure custom metrics (documents/reminders) import the shared registry.

## Deployment Hooks

- Update Docker image to include new dependency.
- Kubernetes/Compose:
  - Expose port/path `/metrics`.
  - Add Prometheus scrape config (job `hostflow-backend`, interval 30s).
  - Restrict access via network policy or auth if needed.

## Validation

- Manual: `curl http://backend:8000/metrics` returns `hf_documents_overdue_total` and `hf_reminders_triggered_total`.
- Grafana: new panels for reminder counts and document overdue gauge.
