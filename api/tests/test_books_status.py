async def test_borrow_sets_card_and_server_timestamp(client, create_book):
    await create_book()
    resp = await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "654321"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_borrowed"] is True
    assert body["borrower_card_number"] == "654321"
    assert body["borrowed_at"] is not None


async def test_borrow_requires_card_number(client, create_book):
    await create_book()
    resp = await client.patch("/books/000123/status", json={"status": "borrowed"})
    assert resp.status_code == 422


async def test_return_forbids_card_number(client, create_book):
    await create_book()
    await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "654321"},
    )
    resp = await client.patch(
        "/books/000123/status",
        json={"status": "available", "borrower_card_number": "654321"},
    )
    assert resp.status_code == 422


async def test_return_clears_borrow_fields(client, create_book):
    await create_book()
    await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "654321"},
    )
    resp = await client.patch("/books/000123/status", json={"status": "available"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_borrowed"] is False
    assert body["borrowed_at"] is None and body["borrower_card_number"] is None


async def test_borrow_already_borrowed_is_409_and_unchanged(client, create_book):
    await create_book()
    await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "111111"},
    )
    resp = await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "222222"},
    )
    assert resp.status_code == 409
    book = (await client.get("/books")).json()[0]
    assert book["borrower_card_number"] == "111111"


async def test_return_available_book_is_409(client, create_book):
    await create_book()
    resp = await client.patch("/books/000123/status", json={"status": "available"})
    assert resp.status_code == 409


async def test_status_update_unknown_serial_is_404(client):
    resp = await client.patch("/books/999999/status", json={"status": "available"})
    assert resp.status_code == 404


async def test_borrow_rejects_non_ascii_card_number(client, create_book):
    await create_book()
    resp = await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "١٢٣٤٥٦"},
    )
    assert resp.status_code == 422


async def test_status_update_malformed_serial_is_422(client):
    resp = await client.patch("/books/abc/status", json={"status": "available"})
    assert resp.status_code == 422


async def test_unknown_status_value_is_422(client, create_book):
    await create_book()
    resp = await client.patch("/books/000123/status", json={"status": "lost"})
    assert resp.status_code == 422


async def test_reborrow_after_return_gets_new_card(client, create_book):
    await create_book()
    await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "111111"},
    )
    first_borrowed_at = (await client.get("/books")).json()[0]["borrowed_at"]
    await client.patch("/books/000123/status", json={"status": "available"})
    resp = await client.patch(
        "/books/000123/status",
        json={"status": "borrowed", "borrower_card_number": "222222"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["borrower_card_number"] == "222222"
    assert body["borrowed_at"] >= first_borrowed_at
