def test_csp_headers(template_client):
    for path in ['/', '/bundle-ui']:
        r = template_client.get(path)
        csp = r.headers.get('Content-Security-Policy')
        assert csp and "default-src 'self'" in csp
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'
        assert r.headers.get('X-Frame-Options') == 'DENY'

