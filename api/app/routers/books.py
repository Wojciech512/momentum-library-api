from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Book
from app.schemas import BookCreate, BookOut, BorrowRequest, SixDigits, StatusUpdate

SessionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/books", tags=["books"])

BOOK_NOT_FOUND = "Book not found"
DUPLICATE_SERIAL = "Book with this serial number already exists"
ALREADY_BORROWED = "Book is already borrowed"
NOT_BORROWED = "Book is not borrowed"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BookOut,
    responses={409: {"description": DUPLICATE_SERIAL}},
)
async def create_book(payload: BookCreate, session: SessionDep) -> Book:
    book = Book(**payload.model_dump())
    session.add(book)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=DUPLICATE_SERIAL) from None
    return book


@router.get("", response_model=list[BookOut])
async def list_books(session: SessionDep) -> list[Book]:
    result = await session.execute(select(Book).order_by(Book.serial_number))
    return list(result.scalars())


@router.patch(
    "/{serial_number}/status",
    response_model=BookOut,
    responses={
        404: {"description": BOOK_NOT_FOUND},
        409: {"description": f"{ALREADY_BORROWED} / {NOT_BORROWED}"},
    },
)
async def update_book_status(
    serial_number: SixDigits,
    payload: StatusUpdate,
    session: SessionDep,
) -> Book:
    result = await session.execute(
        select(Book).where(Book.serial_number == serial_number).with_for_update()
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=BOOK_NOT_FOUND)

    if isinstance(payload, BorrowRequest):
        if book.is_borrowed:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=ALREADY_BORROWED)
        book.borrower_card_number = payload.borrower_card_number
        book.borrowed_at = datetime.now(UTC)
    else:
        if not book.is_borrowed:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=NOT_BORROWED)
        book.borrower_card_number = None
        book.borrowed_at = None

    await session.commit()
    return book


@router.delete(
    "/{serial_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": BOOK_NOT_FOUND}},
)
async def delete_book(serial_number: SixDigits, session: SessionDep) -> None:
    result = await session.execute(
        delete(Book).where(Book.serial_number == serial_number)
    )
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=BOOK_NOT_FOUND)
    await session.commit()
