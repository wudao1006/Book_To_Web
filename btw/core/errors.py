from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

ErrorPayload = dict[str, Any]
REQUIRED_ERROR_FIELDS = ("code", "message", "stage", "retriable", "trace_id")


def new_trace_id() -> str:
    return uuid.uuid4().hex


def make_error(
    *,
    code: str,
    message: str,
    stage: str,
    retriable: bool,
    trace_id: str,
    details: dict[str, Any] | None = None,
) -> ErrorPayload:
    payload: ErrorPayload = {
        "code": code,
        "message": message,
        "stage": stage,
        "retriable": retriable,
        "trace_id": trace_id,
    }
    if details is not None:
        payload["details"] = details
    return payload


def ensure_error_payload(
    error: str | ErrorPayload,
    *,
    default_code: str,
    default_stage: str,
    default_retriable: bool,
    trace_id: str,
) -> ErrorPayload:
    if isinstance(error, dict):
        payload: ErrorPayload = dict(error)
    else:
        payload = {"message": str(error)}

    payload.setdefault("code", default_code)
    payload.setdefault("stage", default_stage)
    payload.setdefault("retriable", default_retriable)
    payload.setdefault("trace_id", trace_id)
    payload.setdefault("message", default_code.replace("_", " "))
    return payload


def is_error_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and all(field in payload for field in REQUIRED_ERROR_FIELDS)


def infer_stage_from_path(path: str) -> str:
    if "/upload" in path:
        return "upload"
    if "/generate" in path:
        return "generate"
    if "/component" in path:
        return "render"
    if "/chapters" in path:
        return "read"
    return "dispatch"


@dataclass(slots=True)
class BTWError(Exception):
    code: str
    message: str
    stage: str
    retriable: bool
    status_code: int = 400
    trace_id: str | None = None
    details: dict[str, Any] | None = None

    def to_payload(self, fallback_trace_id: str) -> ErrorPayload:
        return make_error(
            code=self.code,
            message=self.message,
            stage=self.stage,
            retriable=self.retriable,
            trace_id=self.trace_id or fallback_trace_id,
            details=self.details,
        )
