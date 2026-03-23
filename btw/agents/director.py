from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from btw.agents.base import Agent, AgentContext, get_registry
from btw.core.errors import make_error, new_trace_id
from btw.storage import book_store
from btw.storage.book_store import get_component_paths
from btw.storage.db import (
    AgentLogRepository,
    ComponentVersionRepository,
    TaskRepository,
)


class DirectorAgent(Agent):
    """Coordinates the end-to-end workflow across agents."""

    name = "director"
    description = "Orchestrates BTW agent workflows."

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.registry = get_registry()

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = str(input_data.get("action", ""))
        trace_id = str(input_data.get("trace_id") or new_trace_id())
        task_id = str(uuid.uuid4())
        book_id = str(input_data["book_id"]) if "book_id" in input_data else None
        chapter_index = (
            int(input_data["chapter_index"]) if "chapter_index" in input_data else None
        )

        TaskRepository.create_task(
            task_id,
            action,
            trace_id=trace_id,
            book_id=book_id,
            chapter_index=chapter_index,
            status="queued",
        )
        TaskRepository.update_task_status(task_id, "running")

        if action == "upload_book":
            return await self._handle_upload(task_id, trace_id, input_data)
        if action == "generate_component":
            return await self._handle_generate(task_id, trace_id, input_data)
        if action == "get_component":
            return await self._handle_get_component(task_id, trace_id, input_data)

        TaskRepository.update_task_status(
            task_id,
            "failed",
            error_code="unknown_action",
            error_message=f"Unknown action: {action}",
        )
        self._log_stage(
            task_id=task_id,
            trace_id=trace_id,
            stage="dispatch",
            agent_name="director",
            status="failed",
            latency_ms=0.0,
            book_id=book_id,
            chapter_index=chapter_index,
            message=f"Unknown action: {action}",
        )
        return {
            "task_id": task_id,
            "error": make_error(
                code="unknown_action",
                message=f"Unknown action: {action}",
                stage="dispatch",
                retriable=False,
                trace_id=trace_id,
            ),
        }

    async def _handle_upload(
        self, task_id: str, trace_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        book_id = str(input_data["book_id"])
        file_path = str(input_data["file_path"])

        parser = self.registry.create("parser")
        parser.set_context(AgentContext(task_id=task_id, book_id=book_id))

        parse_result = await self._run_stage(
            task_id=task_id,
            trace_id=trace_id,
            stage="parse",
            agent_name="parser",
            book_id=book_id,
            chapter_index=None,
            call=lambda: parser.process({"book_id": book_id, "file_path": file_path}),
            fail_code="upload_pipeline_failed",
            fail_message="Upload pipeline failed",
            fail_stage="upload",
            retriable=True,
        )
        if "error" in parse_result:
            return parse_result

        reader = self.registry.create("reader")
        reader.set_context(AgentContext(task_id=task_id, book_id=book_id))

        read_result = await self._run_stage(
            task_id=task_id,
            trace_id=trace_id,
            stage="read",
            agent_name="reader",
            book_id=book_id,
            chapter_index=None,
            call=lambda: reader.process(
                {"book_id": book_id, "chapters": parse_result.get("chapters", [])}
            ),
            fail_code="upload_pipeline_failed",
            fail_message="Upload pipeline failed",
            fail_stage="upload",
            retriable=True,
        )
        if "error" in read_result:
            return read_result

        TaskRepository.update_task_status(task_id, "succeeded")
        return {
            "task_id": task_id,
            "book_id": book_id,
            "chapters_count": parse_result.get("total_chapters", 0),
            "concepts": read_result.get("concepts", []),
            "status": "completed",
        }

    async def _handle_generate(
        self, task_id: str, trace_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        book_id = str(input_data["book_id"])
        chapter_index = int(input_data["chapter_index"])
        content_path = (
            book_store.DATA_DIR / book_id / "chapters" / f"{chapter_index:02d}" / "content.md"
        )
        if not content_path.exists():
            TaskRepository.update_task_status(
                task_id,
                "failed",
                error_code="chapter_not_found",
                error_message="Chapter not found",
            )
            self._log_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage="generate",
                agent_name="director",
                status="failed",
                latency_ms=0.0,
                book_id=book_id,
                chapter_index=chapter_index,
                message="Chapter not found",
            )
            return {
                "task_id": task_id,
                "error": make_error(
                    code="chapter_not_found",
                    message="Chapter not found",
                    stage="generate",
                    retriable=False,
                    trace_id=trace_id,
                ),
            }

        content = content_path.read_text(encoding="utf-8")
        creator = self.registry.create("creator")
        critic = self.registry.create("critic")
        engineer = self.registry.create("engineer")

        creator.set_context(AgentContext(task_id=task_id, book_id=book_id))
        critic.set_context(AgentContext(task_id=task_id, book_id=book_id))
        engineer.set_context(AgentContext(task_id=task_id, book_id=book_id))

        quality_retry_count = 0
        max_quality_retries = 1
        create_result: dict[str, Any] | None = None
        critic_result: dict[str, Any] | None = None
        quality_feedback: str | None = None

        while True:
            create_result = await self._run_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage="create",
                agent_name="creator",
                book_id=book_id,
                chapter_index=chapter_index,
                call=lambda: creator.process(
                    {
                        "book_id": book_id,
                        "chapter_index": chapter_index,
                        "content": content,
                        "quality_feedback": quality_feedback,
                    }
                ),
                fail_code="create_failed",
                fail_message="Create stage failed",
                fail_stage="create",
                retriable=True,
            )
            if "error" in create_result:
                return create_result

            critic_result = await self._run_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage="critic",
                agent_name="critic",
                book_id=book_id,
                chapter_index=chapter_index,
                call=lambda: critic.process(
                    {
                        "book_id": book_id,
                        "chapter_index": chapter_index,
                        "component_type": create_result.get("component_type", "narrative"),
                        "jsx_code": create_result.get("jsx_code", ""),
                    }
                ),
                fail_code="critic_failed",
                fail_message="Critic stage failed",
                fail_stage="critic",
                retriable=True,
            )
            if "error" in critic_result:
                return critic_result

            if critic_result.get("approved"):
                break

            if quality_retry_count >= max_quality_retries:
                issues = list(critic_result.get("issues", []))
                message = "Component did not pass quality review"
                TaskRepository.upsert_step(
                    task_id,
                    "critic",
                    "failed",
                    error_code="quality_gate_failed",
                    error_message=message,
                )
                TaskRepository.update_task_status(
                    task_id,
                    "failed",
                    error_code="quality_gate_failed",
                    error_message=message,
                )
                self._log_stage(
                    task_id=task_id,
                    trace_id=trace_id,
                    stage="critic",
                    agent_name="director",
                    status="failed",
                    latency_ms=0.0,
                    book_id=book_id,
                    chapter_index=chapter_index,
                    message="quality gate failed",
                )
                return {
                    "task_id": task_id,
                    "error": make_error(
                        code="quality_gate_failed",
                        message=message,
                        stage="critic",
                        retriable=True,
                        trace_id=trace_id,
                        details={"issues": issues},
                    ),
                }

            quality_retry_count += 1
            quality_feedback = str(critic_result.get("repair_prompt") or "")
            TaskRepository.upsert_step(task_id, "critic", "retrying")
            self._log_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage="critic",
                agent_name="director",
                status="retrying",
                latency_ms=0.0,
                book_id=book_id,
                chapter_index=chapter_index,
                message="quality retry requested",
            )

        TaskRepository.upsert_step(task_id, "validate", "running")
        TaskRepository.upsert_step(task_id, "compile", "running")
        engineer_start = time.perf_counter()
        engineer_result = await engineer.process(
            {
                "book_id": book_id,
                "chapter_index": chapter_index,
                "jsx_code": create_result["jsx_code"],
            }
        )
        engineer_latency = (time.perf_counter() - engineer_start) * 1000

        if not engineer_result.get("success", False):
            stage = str(engineer_result.get("stage") or "compile")
            code = "compile_failed" if stage == "compile" else "validation_failed"
            details = None
            message = str(engineer_result.get("error") or "Generation failed")

            if stage == "validation":
                details = {"issues": list(engineer_result.get("issues", []))}
                message = "Validation failed"
                TaskRepository.upsert_step(
                    task_id,
                    "validate",
                    "failed",
                    error_code=code,
                    error_message=message,
                )
                TaskRepository.upsert_step(task_id, "compile", "queued")
            else:
                TaskRepository.upsert_step(task_id, "validate", "succeeded")
                self._log_stage(
                    task_id=task_id,
                    trace_id=trace_id,
                    stage="validate",
                    agent_name="engineer",
                    status="succeeded",
                    latency_ms=engineer_latency,
                    token_cost=0.0,
                    book_id=book_id,
                    chapter_index=chapter_index,
                    message="validation succeeded",
                )
                TaskRepository.upsert_step(
                    task_id,
                    "compile",
                    "failed",
                    error_code=code,
                    error_message=message,
                )

            TaskRepository.update_task_status(
                task_id,
                "failed",
                error_code=code,
                error_message=message,
            )
            self._log_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage=stage,
                agent_name="engineer",
                status="failed",
                latency_ms=engineer_latency,
                token_cost=0.0,
                book_id=book_id,
                chapter_index=chapter_index,
                message=message,
            )
            return {
                "task_id": task_id,
                "error": make_error(
                    code=code,
                    message=message,
                    stage=stage,
                    retriable=True,
                    trace_id=trace_id,
                    details=details,
                ),
            }

        TaskRepository.upsert_step(task_id, "validate", "succeeded")
        TaskRepository.upsert_step(task_id, "compile", "succeeded")
        self._log_stage(
            task_id=task_id,
            trace_id=trace_id,
            stage="validate",
            agent_name="engineer",
            status="succeeded",
            latency_ms=engineer_latency,
            token_cost=0.0,
            book_id=book_id,
            chapter_index=chapter_index,
            message="validation succeeded",
        )

        self._log_stage(
            task_id=task_id,
            trace_id=trace_id,
            stage="compile",
            agent_name="engineer",
            status="succeeded",
            latency_ms=engineer_latency,
            token_cost=0.0,
            book_id=book_id,
            chapter_index=chapter_index,
            message="compile succeeded",
        )

        js_code = self._safe_read(engineer_result.get("js_path"))
        jsx_code = self._safe_read(engineer_result.get("jsx_path")) or str(
            create_result.get("jsx_code", "")
        )
        if not js_code:
            js_code = self._safe_read(get_component_paths(book_id, chapter_index)[1])

        version = ComponentVersionRepository.create_version(
            book_id=book_id,
            chapter_index=chapter_index,
            jsx_code=jsx_code,
            js_code=js_code,
            bundle_size=int(engineer_result.get("bundle_size", 0) or 0),
        )

        TaskRepository.update_task_status(task_id, "succeeded")
        return {
            "task_id": task_id,
            "book_id": book_id,
            "chapter_index": chapter_index,
            "quality_retry_count": quality_retry_count,
            "version": {
                "version_num": version.get("version_num"),
                "is_latest": version.get("is_latest"),
                "is_stable": version.get("is_stable"),
            },
            **engineer_result,
        }

    async def _handle_get_component(
        self, task_id: str, trace_id: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        book_id = str(input_data["book_id"])
        chapter_index = int(input_data["chapter_index"])
        version = str(input_data.get("version") or "latest")

        TaskRepository.upsert_step(task_id, "render", "running")

        resolved = ComponentVersionRepository.get_component(
            book_id=book_id,
            chapter_index=chapter_index,
            version=version,
        )
        if resolved is not None:
            TaskRepository.upsert_step(task_id, "render", "succeeded")
            TaskRepository.update_task_status(task_id, "succeeded")
            self._log_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage="render",
                agent_name="director",
                status="succeeded",
                latency_ms=0.0,
                book_id=book_id,
                chapter_index=chapter_index,
                message=f"component version {resolved['version_num']} loaded",
            )
            return {
                "task_id": task_id,
                "exists": True,
                "type": "js",
                "code": resolved["js_code"],
                "version": {
                    "version_num": resolved["version_num"],
                    "is_latest": resolved["is_latest"],
                    "is_stable": resolved["is_stable"],
                },
            }

        jsx_path, js_path = get_component_paths(book_id, chapter_index)
        if js_path.exists():
            TaskRepository.upsert_step(task_id, "render", "succeeded")
            TaskRepository.update_task_status(task_id, "succeeded")
            return {
                "task_id": task_id,
                "exists": True,
                "type": "js",
                "code": js_path.read_text(encoding="utf-8"),
            }
        if jsx_path.exists():
            TaskRepository.upsert_step(task_id, "render", "succeeded")
            TaskRepository.update_task_status(task_id, "succeeded")
            return {
                "task_id": task_id,
                "exists": True,
                "type": "jsx",
                "code": jsx_path.read_text(encoding="utf-8"),
            }

        TaskRepository.upsert_step(
            task_id,
            "render",
            "failed",
            error_code="component_not_ready",
            error_message="Component not generated yet",
        )
        TaskRepository.update_task_status(
            task_id,
            "failed",
            error_code="component_not_ready",
            error_message="Component not generated yet",
        )
        self._log_stage(
            task_id=task_id,
            trace_id=trace_id,
            stage="render",
            agent_name="director",
            status="failed",
            latency_ms=0.0,
            book_id=book_id,
            chapter_index=chapter_index,
            message="component not generated yet",
        )
        return {
            "task_id": task_id,
            "error": make_error(
                code="component_not_ready",
                message="Component not generated yet",
                stage="render",
                retriable=True,
                trace_id=trace_id,
            ),
        }

    async def _run_stage(
        self,
        *,
        task_id: str,
        trace_id: str,
        stage: str,
        agent_name: str,
        book_id: str,
        chapter_index: int | None,
        call,
        fail_code: str,
        fail_message: str,
        fail_stage: str,
        retriable: bool,
    ) -> dict[str, Any]:
        TaskRepository.upsert_step(task_id, stage, "running")
        started = time.perf_counter()
        try:
            result = await call()
            latency = (time.perf_counter() - started) * 1000
            token_cost = float(result.get("token_cost", 0.0) or 0.0)
            self._log_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage=stage,
                agent_name=agent_name,
                status="succeeded",
                latency_ms=latency,
                token_cost=token_cost,
                book_id=book_id,
                chapter_index=chapter_index,
                message=f"{stage} succeeded",
            )
            TaskRepository.upsert_step(task_id, stage, "succeeded")
            return result
        except Exception as exc:  # pragma: no cover - defensive boundary
            del exc
            latency = (time.perf_counter() - started) * 1000
            self._log_stage(
                task_id=task_id,
                trace_id=trace_id,
                stage=stage,
                agent_name=agent_name,
                status="failed",
                latency_ms=latency,
                book_id=book_id,
                chapter_index=chapter_index,
                message=fail_message,
            )
            TaskRepository.upsert_step(
                task_id,
                stage,
                "failed",
                error_code=fail_code,
                error_message=fail_message,
            )
            TaskRepository.update_task_status(
                task_id,
                "failed",
                error_code=fail_code,
                error_message=fail_message,
            )
            return {
                "task_id": task_id,
                "error": make_error(
                    code=fail_code,
                    message=fail_message,
                    stage=fail_stage,
                    retriable=retriable,
                    trace_id=trace_id,
                ),
            }

    def _log_stage(
        self,
        *,
        task_id: str,
        trace_id: str,
        stage: str,
        agent_name: str,
        status: str,
        latency_ms: float,
        token_cost: float = 0.0,
        book_id: str | None,
        chapter_index: int | None,
        message: str,
    ) -> None:
        AgentLogRepository.create(
            task_id=task_id,
            trace_id=trace_id,
            agent_name=agent_name,
            stage=stage,
            status=status,
            latency_ms=latency_ms,
            token_cost=token_cost,
            book_id=book_id,
            chapter_index=chapter_index,
            message=message,
        )

    def _safe_read(self, path_like: Any) -> str:
        if not path_like:
            return ""
        path = Path(str(path_like))
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
