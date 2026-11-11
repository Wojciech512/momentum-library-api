from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SixDigits = Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]
Title = Annotated[str, StringConstraints(max_length=500, pattern=r"^[^\x00]+$")]
Author = Annotated[str, StringConstraints(max_length=200, pattern=r"^[^\x00]+$")]


class BookCreate(BaseModel):
    serial_number: SixDigits = Field(examples=["000123"])
    title: Title = Field(examples=["AI Engineering"])
    author: Author = Field(examples=["Chip Huyen"])


class BorrowRequest(BaseModel):
    status: Literal["borrowed"]
    borrower_card_number: SixDigits = Field(examples=["654321"])


class ReturnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available"]


StatusUpdate = Annotated[BorrowRequest | ReturnRequest, Field(discriminator="status")]


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serial_number: str
    title: str
    author: str
    is_borrowed: bool
    borrowed_at: datetime | None
    borrower_card_number: str | None
