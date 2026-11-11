from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint(
            "(borrowed_at IS NULL) = (borrower_card_number IS NULL)",
            name="ck_books_borrow_fields_together",
        ),
    )

    serial_number: Mapped[str] = mapped_column(String(6), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(200))
    borrower_card_number: Mapped[str | None] = mapped_column(String(6))
    borrowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_borrowed(self) -> bool:
        return self.borrowed_at is not None
