from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from btw.agents import register_all_agents
from btw.api.routes import router
from btw.core.errors import (
    BTWError,
    ensure_error_payload,
    infer_stage_from_path,
    is_error_payload,
    make_error,
    new_trace_id,
)
from btw.skills import register_all_skills
from btw.storage.db import init_db

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    init_db()
    register_all_agents()
    register_all_skills()

    app = FastAPI(title="BTW API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")

    @app.middleware("http")
    async def attach_trace_id(request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or new_trace_id()
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response

    @app.exception_handler(BTWError)
    async def handle_btw_error(request: Request, exc: BTWError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", new_trace_id())
        payload = exc.to_payload(trace_id)
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
            headers={"x-trace-id": payload["trace_id"]},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", new_trace_id())
        detail = exc.detail
        if is_error_payload(detail):
            payload = dict(detail)
            payload["trace_id"] = payload.get("trace_id") or trace_id
        else:
            payload = ensure_error_payload(
                str(detail),
                default_code="http_error",
                default_stage=infer_stage_from_path(request.url.path),
                default_retriable=False,
                trace_id=trace_id,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
            headers={"x-trace-id": payload["trace_id"]},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", new_trace_id())
        logger.exception(
            "Unhandled BTW exception",
            extra={"trace_id": trace_id, "path": request.url.path},
        )
        payload = make_error(
            code="internal_error",
            message="Internal server error",
            stage=infer_stage_from_path(request.url.path),
            retriable=True,
            trace_id=trace_id,
        )
        return JSONResponse(
            status_code=500,
            content=payload,
            headers={"x-trace-id": payload["trace_id"]},
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
