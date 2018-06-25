"""Add d passmark for specific exam to override the default one

Revision ID: 8d17beb57761
Revises: d37f87222694
Create Date: 2018-06-20 18:30:55.389141

"""

# revision identifiers, used by Alembic.
revision = '8d17beb57761'
down_revision = '4111401839cc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('training_exams', sa.Column('passmark', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('training_exams', 'passmark')
    # ### end Alembic commands ###
