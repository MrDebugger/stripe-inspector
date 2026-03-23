"""FastAPI web application for StripeInspector."""

import json
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from stripe_inspector import __version__
from stripe_inspector.core import StripeInspector, ALL_MODULES
from stripe_inspector.report import generate_html_report

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

            # Send final complete result
            done_event = {"type": "done", "result": result}
            yield f"data: {json.dumps(done_event, default=str)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/api/report")
    async def generate_report(req: ReportRequest, authorization: Optional[str] = Header(None)):
        verify_token(authorization)
        html = generate_html_report(req.result)
        return HTMLResponse(content=html)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        index_path = os.path.join(STATIC_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app
