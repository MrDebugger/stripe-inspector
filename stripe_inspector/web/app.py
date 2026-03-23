"""FastAPI web application for StripeInspector."""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from stripe_inspector import __version__
from stripe_inspector.core import StripeInspector
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
