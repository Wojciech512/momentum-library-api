import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.conftest import make_client


@pytest.fixture()
async def race_engine():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM books"))
        yield engine
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM books"))
    finally:
        await engine.dispose()


@pytest.fixture()
async def race_client(race_engine):
    maker = async_sessionmaker(race_engine, expire_on_commit=False)

    async def override_get_session():
        async with maker() as session:
            yield session

    async with make_client(override_get_session) as client:
        yield client


async def test_concurrent_borrows_only_one_succeeds(race_client):
    await race_client.post(
        "/books", json={"serial_number": "900001", "title": "T", "author": "A"}
    )
    first, second = await asyncio.gather(
        race_client.patch(
            "/books/900001/status",
            json={"status": "borrowed", "borrower_card_number": "111111"},
        ),
        race_client.patch(
            "/books/900001/status",
            json={"status": "borrowed", "borrower_card_number": "222222"},
        ),
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    winner = (await race_client.get("/books")).json()[0]
    assert winner["is_borrowed"] is True
    assert winner["borrower_card_number"] in {"111111", "222222"}
