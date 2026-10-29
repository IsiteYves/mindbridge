from app import create_app


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/v1/missing")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Not Found"


def test_wrong_method_returns_json_405(client):
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.get_json()["error"] == "Method Not Allowed"


def test_unhandled_exception_returns_json_500_without_details(app):
    app.testing = False

    @app.get("/boom")
    def boom():
        raise RuntimeError("internal detail")

    response = app.test_client().get("/boom")

    assert response.status_code == 500
    assert response.get_json()["error"] == "Internal Server Error"
    assert "internal detail" not in response.get_data(as_text=True)


def test_health_returns_503_when_database_is_unreachable():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "postgresql+psycopg://mindbridge:mindbridge@127.0.0.1:1/mindbridge"})

    response = app.test_client().get("/api/v1/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unavailable"}
