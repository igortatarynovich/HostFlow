from fastapi.routing import APIRoute

from backend.app.main import app


def test_documents_routes_present():
    paths = [route.path for route in app.routes if "documents" in route.path]
    assert any(path.startswith("/api/v1/documents") for path in paths), f"Documents routes missing, found: {paths}"


def test_documents_router_expected_endpoints():
    expected = {
        ("GET", "/api/v1/documents/"),
        ("POST", "/api/v1/documents/"),
        ("GET", "/api/v1/documents/expiring"),
        ("GET", "/api/v1/documents/{document_id}"),
        ("PATCH", "/api/v1/documents/{document_id}"),
        ("DELETE", "/api/v1/documents/{document_id}"),
    }

    actual = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and "documents" in route.path
        for method in (route.methods or [])
    }

    missing = expected - actual
    assert not missing, f"Documents endpoints missing: {sorted(missing)}"
