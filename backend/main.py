from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.deps import repo_root_on_path

repo_root_on_path()

from agent.ingestion.embeddings import Embedder  # noqa: E402
from config import load_config  # noqa: E402

from backend.routes import router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config()
    app.state.embedder = Embedder.from_pretrained()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Compliance RAG API", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
