def test_preflight_from_allowed_origin_allows_bearer_requests(client):
    response = client.options(
        "/api/v1/assignments",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "authorization" in response.headers["Access-Control-Allow-Headers"].lower()


def test_unknown_origin_gets_no_cors_headers(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert "Access-Control-Allow-Origin" not in response.headers
