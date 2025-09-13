def test_home_serves(template_client):
    r = template_client.get('/')
    assert r.status_code == 200

def test_bundle_ui_serves(template_client):
    r = template_client.get('/bundle-ui')
    assert r.status_code == 200
    assert b'/static/js/bundle-ui.js' in r.data or b'bundle-ui.js' in r.data

def test_static_assets_content_type(template_client):
    js = template_client.get('/static/js/status.js')
    assert js.status_code == 200
    # Werkzeug may use different mimetypes; just ensure it's JS-like
    assert 'javascript' in js.headers.get('Content-Type', '') or js.headers.get('Content-Type','').endswith('/x-javascript')

def test_api_docs_uses_external_js(template_client):
    r = template_client.get('/api-docs')
    assert r.status_code == 200
    assert b'/static/js/api-console.js' in r.data or b'api-console.js' in r.data
