import os
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import app

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@asynccontextmanager
async def make_client(session_override):
    app.dependency_overrides[get_session] = session_override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def session(engine):
    async with engine.connect() as conn:
        trans = await conn.begin()
        maker = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with maker() as session:
            yield session
        await trans.rollback()


@pytest.fixture()
async def client(session):
    async def override_get_session():
        yield session

    async with make_client(override_get_session) as client:
        yield client


@pytest.fixture()
def create_book(client):
    async def _create(serial="000123", title="T", author="A"):
        resp = await client.post(
            "/books", json={"serial_number": serial, "title": title, "author": author}
        )
        assert resp.status_code == 201
        return resp

    return _create
