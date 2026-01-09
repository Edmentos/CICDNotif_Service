def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "database" in data
    assert "rabbitmq" in data
