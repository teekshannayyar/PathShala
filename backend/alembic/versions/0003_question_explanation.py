"""Add questions.explanation so quiz explanations from the LLM are kept.

Nullable: questions generated before this revision have no explanation.

Revision ID: 0003_question_explanation
Revises: 0002_document_processing_status
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_question_explanation"
down_revision: Union[str, Sequence[str], None] = "0002_document_processing_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("explanation", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "explanation")
