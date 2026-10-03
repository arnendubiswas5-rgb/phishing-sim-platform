"""add pages.page_type

Revision ID: b37e28ee3bc6
Revises: fdacc5a0125b
Create Date: 2026-10-02 16:11:35.938409

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b37e28ee3bc6'
down_revision = 'fdacc5a0125b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pagetype = sa.Enum('CREDENTIAL', 'EDUCATION', 'REDIRECT', name='pagetype')
    pagetype.create(op.get_bind(), checkfirst=True)
    # Add with a server_default so existing rows satisfy NOT NULL, then drop the
    # default so the column matches the model (which sets the default in Python).
    op.add_column(
        'pages',
        sa.Column(
            'page_type',
            sa.Enum('CREDENTIAL', 'EDUCATION', 'REDIRECT', name='pagetype', create_type=False),
            nullable=False,
            server_default='CREDENTIAL',
        ),
    )
    op.alter_column('pages', 'page_type', server_default=None)


def downgrade() -> None:
    op.drop_column('pages', 'page_type')
    sa.Enum(name='pagetype').drop(op.get_bind(), checkfirst=True)
