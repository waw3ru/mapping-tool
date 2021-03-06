"""Added choice id to exam results

Revision ID: 61dc7d07bf3c
Revises: e625e9edaa35
Create Date: 2018-06-28 09:56:16.840092

"""

# revision identifiers, used by Alembic.
revision = '61dc7d07bf3c'
down_revision = 'e625e9edaa35'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('exam_results', sa.Column('choice_id', sa.Integer(), nullable=True))
    op.alter_column(u'exam_results', 'answer', type_=sa.VARCHAR(256))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(u'exam_results', 'answer', type_=sa.VARCHAR(45))
    op.drop_column('exam_results', 'choice_id')
    # ### end Alembic commands ###
