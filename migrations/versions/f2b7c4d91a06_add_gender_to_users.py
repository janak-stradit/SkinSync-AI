"""Add gender to users.

Revision ID: f2b7c4d91a06
Revises: eb773ad7c277
"""

from alembic import op
import sqlalchemy as sa


revision = 'f2b7c4d91a06'
down_revision = 'eb773ad7c277'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gender', sa.String(length=30), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('gender')
