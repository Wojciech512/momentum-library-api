import pytest


async def test_create_book_returns_201_with_available_state(client):
    resp = await client.post(
        "/books",
        json={"serial_number": "000123", "title": "Solaris", "author": "Lem"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["serial_number"] == "000123"
    assert body["is_borrowed"] is False
    assert body["borrowed_at"] is None and body["borrower_card_number"] is None


@pytest.mark.parametrize("serial", ["12345", "1234567", "12a456", "123 456", ""])
async def test_create_rejects_bad_serial(client, serial):
    resp = await client.post(
        "/books", json={"serial_number": serial, "title": "T", "author": "A"}
    )
    assert resp.status_code == 422


async def test_create_duplicate_serial_returns_409(client):
    payload = {"serial_number": "000123", "title": "T", "author": "A"}
    await client.post("/books", json=payload)
    resp = await client.post("/books", json=payload)
    assert resp.status_code == 409


async def test_list_books_returns_all(client, create_book):
    await create_book("000001", title="A", author="X")
    await create_book("000002", title="B", author="Y")
    resp = await client.get("/books")
    assert resp.status_code == 200
    assert {b["serial_number"] for b in resp.json()} == {"000001", "000002"}


async def test_delete_book_returns_204_then_404(client, create_book):
    await create_book()
    assert (await client.delete("/books/000123")).status_code == 204
    assert (await client.delete("/books/000123")).status_code == 404


@pytest.mark.parametrize("serial", ["١٢٣٤٥٦", "１２３４５６", "१२३४५६"])
async def test_create_rejects_non_ascii_digits(client, serial):
    resp = await client.post(
        "/books", json={"serial_number": serial, "title": "T", "author": "A"}
    )
    assert resp.status_code == 422


async def test_create_rejects_nul_byte_in_title_and_author(client):
    for field in ("title", "author"):
        payload = {"serial_number": "000123", "title": "T", "author": "A"}
        payload[field] = "T\x00x"
        resp = await client.post("/books", json=payload)
        assert resp.status_code == 422


async def test_delete_malformed_serial_is_422(client):
    resp = await client.delete("/books/12a456")
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", ""),
        ("author", ""),
        ("title", True),
        ("author", 123),
        ("serial_number", True),
        ("serial_number", 123456),
    ],
)
async def test_create_rejects_empty_or_wrongly_typed_fields(client, field, value):
    payload = {"serial_number": "000123", "title": "T", "author": "A"}
    payload[field] = value
    resp = await client.post("/books", json=payload)
    assert resp.status_code == 422


async def test_list_empty_database_returns_empty_list(client):
    resp = await client.get("/books")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_rejects_serial_with_trailing_newline(client):
    resp = await client.post(
        "/books", json={"serial_number": "123456\n", "title": "T", "author": "A"}
    )
    assert resp.status_code == 422


async def test_title_length_boundary(client, create_book):
    await create_book("000301", title="x" * 500)
    too_long = await client.post(
        "/books", json={"serial_number": "000302", "title": "x" * 501, "author": "A"}
    )
    assert too_long.status_code == 422


async def test_create_ignores_unknown_fields(client):
    resp = await client.post(
        "/books",
        json={"serial_number": "000303", "title": "T", "author": "A", "price": 10},
    )
    assert resp.status_code == 201
    assert "price" not in resp.json()


async def test_delete_borrowed_book_succeeds(client, create_book):
    await create_book("000304")
    await client.patch(
        "/books/000304/status",
        json={"status": "borrowed", "borrower_card_number": "654321"},
    )
    assert (await client.delete("/books/000304")).status_code == 204
