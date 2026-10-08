def test_home_page(client):
    # Must redirect to login because home has @login_required
    response = client.get('/', follow_redirects=True)
    assert response.request.path == "/auth/login"
    html = response.get_data(as_text=True)
    assert "Iniciar sesión" in html
    assert "Cerrar sesión" not in html


def test_dashboard_requires_login(client):
    response = client.get('/dashboard', follow_redirects=True)
    assert response.request.path == "/auth/login"
    assert "Iniciar sesión" in response.get_data(as_text=True)
