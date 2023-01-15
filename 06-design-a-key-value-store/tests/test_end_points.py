def test_healthcheck(client):
    # when
    response = client.get("/healthcheck")

    # then
    assert response.status_code == 200


def test_put_and_get_item(client):
    # given
    key = "this is key"
    value = "this is value"

    # when
    response = client.put(f"/items/{key}", json={"value": value})

    # then
    assert response.status_code == 201

    # when
    response = client.get(f"/items/{key}")

    # then
    assert response.status_code == 200
    assert response.json() == {"value": value}
