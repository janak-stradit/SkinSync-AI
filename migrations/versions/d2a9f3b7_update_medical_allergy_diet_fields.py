"""add medical_conditions, convert allergy_type to json, add diet preferences and supplements

Revision ID: d2a9f3b7
Revises: c1f7d2b9a8f0
Create Date: 2026-07-14 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd2a9f3b7'
down_revision = 'c1f7d2b9a8f0'
branch_labels = None
depends_on = None


def upgrade():
    # Lifestyle: add medical_conditions and medical_conditions_other
    with op.batch_alter_table('lifestyle_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('medical_conditions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('medical_conditions_other', sa.Text(), nullable=True))

    # Allergy: convert allergy_type to JSON if it's text
    op.execute("ALTER TABLE allergy_profiles ALTER COLUMN allergy_type TYPE JSON USING to_json(string_to_array(allergy_type, ','))")
    with op.batch_alter_table('allergy_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('skin_medication', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('recent_treatment', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('recent_treatment_other', sa.Text(), nullable=True))

    # Diet: add supplements, supplements_text, diet_preferences, diet_additional_notes
    with op.batch_alter_table('diet_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('supplements', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('supplements_text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('diet_preferences', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('diet_additional_notes', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('lifestyle_profiles', schema=None) as batch_op:
        batch_op.drop_column('medical_conditions_other')
        batch_op.drop_column('medical_conditions')

    with op.batch_alter_table('allergy_profiles', schema=None) as batch_op:
        batch_op.drop_column('recent_treatment_other')
        batch_op.drop_column('recent_treatment')
        batch_op.drop_column('skin_medication')
    op.execute("ALTER TABLE allergy_profiles ALTER COLUMN allergy_type TYPE VARCHAR(100) USING allergy_type::text")

    with op.batch_alter_table('diet_profiles', schema=None) as batch_op:
        batch_op.drop_column('diet_additional_notes')
        batch_op.drop_column('diet_preferences')
        batch_op.drop_column('supplements_text')
        batch_op.drop_column('supplements')