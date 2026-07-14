"""update skin profile fields to support multi-select and additional text

Revision ID: c1f7d2b9a8f0
Revises: 3053a11c34fe
Create Date: 2026-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1f7d2b9a8f0'
down_revision = '3053a11c34fe'
branch_labels = None
depends_on = None


def upgrade():
    # For existing string columns, cast to JSON where possible using USING
    # Convert text fields into JSON arrays by splitting on commas (handles single or comma-separated values)
    op.execute("ALTER TABLE skin_profiles ALTER COLUMN skin_concerns TYPE JSON USING to_json(string_to_array(skin_concerns, ','))")
    op.execute("ALTER TABLE skin_profiles ALTER COLUMN under_eye_issue TYPE JSON USING to_json(string_to_array(under_eye_issue, ','))")
    op.execute("ALTER TABLE skin_profiles ALTER COLUMN lip_condition TYPE JSON USING to_json(string_to_array(lip_condition, ','))")
    with op.batch_alter_table('skin_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('additional_concern', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('skin_profiles', schema=None) as batch_op:
        batch_op.drop_column('additional_concern')
    # Convert JSON back to text where needed
    op.execute("ALTER TABLE skin_profiles ALTER COLUMN lip_condition TYPE VARCHAR(50) USING lip_condition::text")
    op.execute("ALTER TABLE skin_profiles ALTER COLUMN under_eye_issue TYPE VARCHAR(50) USING under_eye_issue::text")
    op.execute("ALTER TABLE skin_profiles ALTER COLUMN skin_concerns TYPE VARCHAR(255) USING skin_concerns::text")
