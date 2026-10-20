"""baseline existing NexaDesk database

Revision ID: ef7df0928c76
Revises: 
Create Date: 2026-10-19 19:20:50.338907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef7df0928c76'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    pass


def downgrade() -> None:
    
    pass
