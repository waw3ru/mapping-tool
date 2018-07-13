"""Add answer to exam result

Revision ID: 4111401839cc
Revises: d37f87222694
Create Date: 2018-06-21 09:28:39.230962

"""

# revision identifiers, used by Alembic.
revision = '4111401839cc'
down_revision = 'd37f87222694'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('exam_results', sa.Column('answer', sa.String(length=45), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('exam_results', 'answer')
    # ### end Alembic commands ###