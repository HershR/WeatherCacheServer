"""empty message

Revision ID: 6789d97625d4
Revises: 
Create Date: 2022-09-27 20:52:47.819429

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6789d97625d4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('owm_current_weather', sa.Column('wind_direction_value_deg', sa.Integer(), nullable=False))
    op.add_column('owm_current_weather', sa.Column('lastupdate_value', sa.DateTime(), nullable=False))
    op.drop_column('owm_current_weather', 'lastupdate')
    op.add_column('owm_hourly_weather_forecast', sa.Column('wind_direction_value_deg', sa.Integer(), nullable=False))
    op.add_column('owm_hourly_weather_forecast', sa.Column('lastupdate_value', sa.DateTime(), nullable=True))
    op.drop_column('owm_hourly_weather_forecast', 'lastupdate')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('owm_hourly_weather_forecast', sa.Column('lastupdate', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_column('owm_hourly_weather_forecast', 'lastupdate_value')
    op.drop_column('owm_hourly_weather_forecast', 'wind_direction_value_deg')
    op.add_column('owm_current_weather', sa.Column('lastupdate', postgresql.TIMESTAMP(), autoincrement=False, nullable=False))
    op.drop_column('owm_current_weather', 'lastupdate_value')
    op.drop_column('owm_current_weather', 'wind_direction_value_deg')
    # ### end Alembic commands ###
