from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from btw.agents import register_all_agents
from btw.api.routes import router
from btw.skills import register_all_skills
from btw.storage.db import init_db


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

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
