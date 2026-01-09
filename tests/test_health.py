def test_health(client):
    r = client.get("/health")
    # Health check returns 503 when RabbitMQ is not available
    assert r.status_code in [200, 503]
    data = r.json()
    assert "status" in data
    assert "database" in data
    assert "rabbitmq" in data
