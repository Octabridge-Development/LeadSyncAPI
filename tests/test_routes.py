# tests/test_routes.py

def test_list_routes(client):
    routes = [route.path for route in client.app.routes]
    print("\nRutas registradas:", routes)
    assert "/api/v1/manychat/campaign-contacts/update-by-manychat-id" in routes, (
        "El endpoint PUT /api/v1/manychat/campaign-contacts/update-by-manychat-id no está registrado en la app."
    )


def test_list_all_routes(client):
    print("\nTodas las rutas registradas:")
    for route in client.app.routes:
        print(route.path)
