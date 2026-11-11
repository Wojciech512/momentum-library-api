from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Book


async def test_borrow_fields_must_be_set_together(session):
    session.add(
        Book(
            serial_number="000123",
            title="T",
            author="A",
            borrowed_at=datetime.now(UTC),
            borrower_card_number=None,
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_serial_number_preserves_leading_zeros(session):
    session.add(Book(serial_number="000123", title="T", author="A"))
    await session.flush()
    book = await session.get(Book, "000123", populate_existing=True)
    assert book.serial_number == "000123"
    assert book.is_borrowed is False
