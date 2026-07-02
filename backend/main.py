from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.deps import repo_root_on_path

repo_root_on_path()

from agent import build_ask_agent, build_check_agent  # noqa: E402
from agent.ingestion.embeddings import Embedder  # noqa: E402
from config import load_config  # noqa: E402

from backend.routes import router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config()
    app.state.embedder = Embedder.from_pretrained()
    app.state.ask_agent = build_ask_agent(app.state.config)
    app.state.check_agent = build_check_agent(app.state.config)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Compliance RAG API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
