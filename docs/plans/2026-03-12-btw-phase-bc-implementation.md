# BTW Phase B/C Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the remaining roadmap items (B2/B3/C1/C2/C3) with production-facing safety, observability, and UX improvements.

**Architecture:** Extend the existing Director-centered pipeline with persisted task state, structured stage logs/metrics, retry-safe storage constraints, and a bounded Creator->Critic->Engineer quality loop. Keep runtime behavior deterministic with offline-friendly defaults while exposing explicit API surfaces for status, retries, and versioned component retrieval.

**Tech Stack:** FastAPI, SQLite, React/Vite, Playwright, pytest.

### Task 1: Observability Baseline (B2)
- Add structured agent log persistence with fields `task_id/agent_name/stage/latency_ms/status/token_cost`.
- Add task metrics aggregation endpoint with success rate, retry rate, compile failure rate, and p95 latency.
- Record stage-level logs inside Director for parse/read/create/critic/validate/compile/render.

### Task 2: Storage Consistency & Constraints (B3)
- Add uniqueness constraints and indexes (`chapters(book_id,index_num)`, `paragraphs(chapter_id,index_num)`).
- Add transactional helpers for task and step updates.
- Introduce explicit vector-store mode setting (`memory` vs `persistent`) and deterministic fallback behavior.

### Task 3: Generation Quality Loop (C1)
- Implement `CriticAgent` as a concrete reviewer.
- Add bounded repair loop in Director: `Creator -> Critic -> Engineer`, with one controlled fix attempt.
- Add content-type template prompt selection for narrative/chart/formula/code.

### Task 4: Frontend Experience + Versioning (C2)
- Add task progress UI states (generate/create/critic/compile, retry hints).
- Add component version metadata and API (`latest` / `stable`) with rollback endpoint.
- Keep iframe sandbox renderer and map backend stage errors to user-facing status.

### Task 5: Cost & Throughput Controls (C3)
- Add prompt/result cache usage in creator pipeline.
- Add model routing policy (`fast` then `strong` fallback).
- Add in-process per-user/per-task concurrency limits and request queueing in API layer.

### Task 6: Verification
- Add/extend pytest coverage for new repositories, Director flow, API routes, and rollback behavior.
- Extend e2e smoke to include generation progress and stable-version fallback.
- Run full backend and frontend verification and report residual risks.
