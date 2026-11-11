"""create books

Revision ID: 733d252dfd7c
Revises:
Create Date: 2026-11-11 07:51:09.318402

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "733d252dfd7c"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("serial_number", sa.String(length=6), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=False),
        sa.Column("borrower_card_number", sa.String(length=6), nullable=True),
        sa.Column("borrowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(borrowed_at IS NULL) = (borrower_card_number IS NULL)",
            name="ck_books_borrow_fields_together",
        ),
        sa.PrimaryKeyConstraint("serial_number"),
    )


def downgrade() -> None:
    op.drop_table("books")
