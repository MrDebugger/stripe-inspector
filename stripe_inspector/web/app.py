"""FastAPI web application for StripeInspector."""

import json
import os
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from stripe_inspector import __version__
from stripe_inspector.core import StripeInspector, ALL_MODULES
from stripe_inspector.report import generate_html_report

# In-memory report store {id: {"html": str, "created": float}}
_reports: dict[str, dict] = {}
REPORT_MAX_AGE = 86400  # 24 hours

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class InspectRequest(BaseModel):
    key: str
    modules: Optional[list[str]] = None
    deep: bool = False


class ReportRequest(BaseModel):
    result: dict


def create_app(token: Optional[str] = None) -> FastAPI:
    app = FastAPI(
        title="StripeInspector",
        description="Security research tool for Stripe API key enumeration",
        version=__version__,
    )

    def verify_token(authorization: Optional[str] = Header(None)):
        if token is None:
            return
        if not authorization or authorization != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="Invalid or missing token")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.post("/api/inspect")
    async def inspect_key(req: InspectRequest, authorization: Optional[str] = Header(None)):
        verify_token(authorization)

        inspector = StripeInspector(req.key, modules=req.modules, deep=req.deep)
        if not inspector.validate_key():
            raise HTTPException(status_code=400, detail="Invalid key format")

        result = inspector.inspect()
        return JSONResponse(content=result)

    @app.post("/api/inspect/stream")
    async def inspect_key_stream(req: InspectRequest, authorization: Optional[str] = Header(None)):
        """SSE endpoint that streams module results as they complete."""
        verify_token(authorization)

        inspector = StripeInspector(req.key, modules=req.modules, deep=req.deep)

        if not inspector.validate_key():
            raise HTTPException(status_code=400, detail="Invalid key format")

        def event_stream():
            import inspect as _inspect
            from stripe_inspector.modules._base import get_rate_limit_info

            start_time = time.time()

            result = {
                "key_type": inspector.key_type,
                "masked_key": inspector.masked_key,
                "is_live": "live" in inspector.key_type,
                "is_restricted": "restricted" in inspector.key_type,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "modules": {},
                "permissions": {},
            }

            total = len(inspector.modules_to_run)

            for i, name in enumerate(inspector.modules_to_run):
                if name not in ALL_MODULES:
                    continue

                module = ALL_MODULES[name]

                # Send progress event
                progress = {"type": "progress", "module": name, "current": i + 1, "total": total}
                yield f"data: {json.dumps(progress)}\n\n"

                try:
                    sig = _inspect.signature(module.inspect)
                    if 'deep' in sig.parameters:
                        data = module.inspect(inspector.key, deep=inspector.deep)
                    else:
                        data = module.inspect(inspector.key)

                    mod_result = {"success": True, "data": data}
                    result["modules"][name] = mod_result
                    result["permissions"][name] = "allowed"
                except PermissionError:
                    mod_result = {"success": False, "error": "Permission denied (403)"}
                    result["modules"][name] = mod_result
                    result["permissions"][name] = "denied"
                except ConnectionError as e:
                    mod_result = {"success": False, "error": f"Connection error: {e}"}
                    result["modules"][name] = mod_result
                    result["permissions"][name] = "error"
                except Exception as e:
                    mod_result = {"success": False, "error": str(e)}
                    result["modules"][name] = mod_result
                    result["permissions"][name] = "error"

                # Send module result
                module_event = {"type": "module", "name": name, "result": mod_result}
                yield f"data: {json.dumps(module_event, default=str)}\n\n"

            # PII scan
            from stripe_inspector.pii import scan_pii
            result["pii"] = scan_pii(result)
            result["rate_limit"] = get_rate_limit_info()
            result["duration_seconds"] = round(time.time() - start_time, 2)

            # Send final complete result
            done_event = {"type": "done", "result": result}
            yield f"data: {json.dumps(done_event, default=str)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/api/report")
    async def generate_report(req: ReportRequest, authorization: Optional[str] = Header(None)):
        verify_token(authorization)
        html = generate_html_report(req.result)
        return HTMLResponse(content=html)

    @app.post("/api/inspection/share")
    async def share_inspection(req: ReportRequest, authorization: Optional[str] = Header(None)):
        """Save inspection on server and return a shareable URL."""
        verify_token(authorization)

        # Clean expired
        now = time.time()
        expired = [k for k, v in _reports.items() if now - v["created"] > REPORT_MAX_AGE]
        for k in expired:
            del _reports[k]

        html = generate_html_report(req.result)

        # Inject toolbar into the report
        toolbar_html = '''
        <div style="position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;align-items:center;justify-content:space-between;">
            <div style="font-size:14px;font-weight:600;color:var(--bright,#fafafa);">Stripe<span style="color:#6c63ff;">Inspector</span> &mdash; Shared Inspection</div>
            <div style="display:flex;gap:8px;">
                <a href="/" style="font-size:12px;color:#6c63ff;text-decoration:none;padding:6px 14px;border:1px solid #2d3140;border-radius:6px;">New Inspection</a>
                <a href="https://github.com/mrdebugger/stripe-inspector" target="_blank" style="font-size:12px;color:#71717a;text-decoration:none;padding:6px 14px;border:1px solid #2d3140;border-radius:6px;">GitHub</a>
            </div>
        </div>
        '''
        # Insert toolbar after <body>
        html = html.replace('<body>', '<body>' + toolbar_html, 1)

        report_id = uuid.uuid4().hex[:12]
        _reports[report_id] = {"html": html, "created": now}

        return JSONResponse({"id": report_id, "url": f"/inspection/{report_id}"})

    @app.get("/inspection/{report_id}", response_class=HTMLResponse)
    async def view_shared_inspection(report_id: str):
        """View a shared inspection by ID."""
        report = _reports.get(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Inspection not found or expired")

        if time.time() - report["created"] > REPORT_MAX_AGE:
            del _reports[report_id]
            raise HTTPException(status_code=404, detail="Inspection expired")

        return HTMLResponse(content=report["html"])

    @app.get("/", response_class=HTMLResponse)
    async def index():
        index_path = os.path.join(STATIC_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app
