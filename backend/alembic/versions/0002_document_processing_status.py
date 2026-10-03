"""Add documents.processing_status and documents.processing_error.

Idempotent: databases where the step 3 manual ALTER was already run have the
columns, so each one is only added when missing. Existing rows are then
backfilled: embedded documents become "ready", and documents still marked
"processing" that never finished embedding become "failed" with a message
asking the user to reprocess (they were uploaded before text was stored).
Rows that step 3 code already marked "failed" keep their own error.

Revision ID: 0002_document_processing_status
Revises: 0001_baseline
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0002_document_processing_status"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_ERROR = "Uploaded before processing fix; please reprocess"


def _document_columns() -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns("documents")}


def upgrade() -> None:
    if context.is_offline_mode():
        # `alembic upgrade --sql` has no database to inspect; emit the
        # equivalent Postgres-only idempotent DDL instead.
        op.execute(
            "ALTER TABLE documents "
            "ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) NOT NULL DEFAULT 'processing', "
            "ADD COLUMN IF NOT EXISTS processing_error TEXT"
        )
        existing = {"processing_status", "processing_error"}
    else:
        existing = _document_columns()

    if "processing_status" not in existing:
        op.add_column(
            "documents",
            sa.Column(
                "processing_status",
                sa.String(length=20),
                nullable=False,
                server_default="processing",
            ),
        )
    if "processing_error" not in existing:
        op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))

    op.execute(
        "UPDATE documents SET processing_status = 'ready', processing_error = NULL "
        "WHERE embedding_complete"
    )
    op.execute(
        sa.text(
            "UPDATE documents SET processing_status = 'failed', processing_error = :error "
            "WHERE embedding_complete IS NOT TRUE AND processing_status = 'processing'"
        ).bindparams(error=LEGACY_ERROR)
    )


def downgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "ALTER TABLE documents DROP COLUMN IF EXISTS processing_error, "
            "DROP COLUMN IF EXISTS processing_status"
        )
        return
    existing = _document_columns()
    if "processing_error" in existing:
        op.drop_column("documents", "processing_error")
    if "processing_status" in existing:
        op.drop_column("documents", "processing_status")
