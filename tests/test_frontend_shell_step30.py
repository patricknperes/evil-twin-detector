from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

def test_frontend_stack_uses_tailwind_not_material_ui():
    package = (FRONTEND / "package.json").read_text(encoding="utf-8")
    vite = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")
    css = (FRONTEND / "src/index.css").read_text(encoding="utf-8")
    assert "tailwindcss" in package
    assert "@tailwindcss/vite" in package
    assert "@tailwindcss/vite" in vite
    assert '@import "tailwindcss"' in css
    assert "@mui" not in package
    assert "material-ui" not in package.lower()

def test_frontend_routes_exist():
    app_source = (FRONTEND / "src/App.tsx").read_text(encoding="utf-8")
    for route in ["/scan", "/networks", "/history", "/model", "/settings"]:
        assert f'path:"{route}"' in app_source

def test_frontend_api_points_to_local_backend():
    source = (FRONTEND / "src/lib/api.ts").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8765" in source

def test_backend_allows_vite_local_origin():
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
