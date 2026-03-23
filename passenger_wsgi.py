"""Passenger WSGI entry point for cPanel Python hosting.

Pure WSGI — no async, no a2wsgi needed. Works with LiteSpeed/Passenger on shared hosting.
Serves static files and API endpoints directly.

Usage:
1. Setup Python App in cPanel
2. pip install stripe-inspector
3. Copy this file to your app root
4. Set startup file: passenger_wsgi.py, entry point: application
5. Restart
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))


def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')

    # Find static files directory from installed package
    static_dir = None
    for sp in sys.path:
        test_dir = os.path.join(sp, 'stripe_inspector', 'web', 'static')
        if os.path.isdir(test_dir):
            static_dir = test_dir
            break

    # Also check relative to this file
    if not static_dir:
        local = os.path.join(os.path.dirname(__file__), 'stripe_inspector', 'web', 'static')
        if os.path.isdir(local):
            static_dir = local

    # ─── Static files ─────────────────────────────────────────
    if path.startswith('/static/') and static_dir:
        filename = path[8:]
        filepath = os.path.join(static_dir, filename)
        if os.path.isfile(filepath):
            ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
            content_types = {
                'html': 'text/html; charset=utf-8',
                'css': 'text/css; charset=utf-8',
                'js': 'application/javascript; charset=utf-8',
                'svg': 'image/svg+xml',
                'png': 'image/png',
                'ico': 'image/x-icon',
            }
            ct = content_types.get(ext, 'application/octet-stream')
            with open(filepath, 'rb') as f:
                data = f.read()
            start_response('200 OK', [('Content-Type', ct), ('Content-Length', str(len(data)))])
            return [data]

    # ─── Index page ───────────────────────────────────────────
    if path == '/' and method == 'GET' and static_dir:
        index_path = os.path.join(static_dir, 'index.html')
        if os.path.isfile(index_path):
            with open(index_path, 'rb') as f:
                data = f.read()
            start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
            return [data]

    # ─── API: health ──────────────────────────────────────────
    if path == '/api/health' and method == 'GET':
        from stripe_inspector import __version__
        body = json.dumps({"status": "ok", "version": __version__}).encode()
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [body]

    # ─── API: inspect ─────────────────────────────────────────
    if path == '/api/inspect' and method == 'POST':
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            raw = environ['wsgi.input'].read(content_length)
            req = json.loads(raw)

            from stripe_inspector.core import StripeInspector
            inspector = StripeInspector(
                req['key'],
                modules=req.get('modules'),
                deep=req.get('deep', False),
            )
            if not inspector.validate_key():
                resp = json.dumps({"detail": "Invalid key format"}).encode()
                start_response('400 Bad Request', [('Content-Type', 'application/json')])
                return [resp]

            result = inspector.inspect()
            resp = json.dumps(result, default=str).encode()
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [resp]
        except Exception as e:
            resp = json.dumps({"detail": str(e)}).encode()
            start_response('500 Internal Server Error', [('Content-Type', 'application/json')])
            return [resp]

    # ─── API: report ──────────────────────────────────────────
    if path == '/api/report' and method == 'POST':
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            raw = environ['wsgi.input'].read(content_length)
            req = json.loads(raw)
            from stripe_inspector.report import generate_html_report
            html = generate_html_report(req['result'])
            start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
            return [html.encode()]
        except Exception as e:
            resp = json.dumps({"detail": str(e)}).encode()
            start_response('500 Internal Server Error', [('Content-Type', 'application/json')])
            return [resp]

    # ─── API: share inspection ────────────────────────────────
    if path == '/api/inspection/share' and method == 'POST':
        try:
            import uuid, time
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            raw = environ['wsgi.input'].read(content_length)
            req = json.loads(raw)
            from stripe_inspector.report import generate_html_report
            html = generate_html_report(req['result'])
            report_id = uuid.uuid4().hex[:12]
            # Save to tmp directory
            reports_dir = os.path.join(os.path.dirname(__file__), 'tmp', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            with open(os.path.join(reports_dir, f'{report_id}.html'), 'w') as f:
                f.write(html)
            resp = json.dumps({"id": report_id, "url": f"/inspection/{report_id}"}).encode()
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [resp]
        except Exception as e:
            resp = json.dumps({"detail": str(e)}).encode()
            start_response('500 Internal Server Error', [('Content-Type', 'application/json')])
            return [resp]

    # ─── Shared inspection view ───────────────────────────────
    if path.startswith('/inspection/') and method == 'GET':
        report_id = path.split('/')[-1]
        reports_dir = os.path.join(os.path.dirname(__file__), 'tmp', 'reports')
        filepath = os.path.join(reports_dir, f'{report_id}.html')
        if os.path.isfile(filepath):
            with open(filepath, 'rb') as f:
                data = f.read()
            start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
            return [data]
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'Inspection not found or expired']

    # ─── 404 ──────────────────────────────────────────────────
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'Not Found']
