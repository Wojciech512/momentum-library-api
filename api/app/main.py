from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import engine
from app.routers.books import router as books_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="Library API", lifespan=lifespan)
app.include_router(books_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
