"""Atomic media attachment claims and profile avatar foreign key."""

from alembic import op
import sqlalchemy as sa

revision = "a892be9c1041"
down_revision = "3ff31791c013"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("media_assets", sa.Column("claimed", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute(
        "UPDATE media_assets SET claimed = true WHERE EXISTS (SELECT 1 FROM post_media WHERE media_id=media_assets.id) OR EXISTS (SELECT 1 FROM stories WHERE media_id=media_assets.id) OR EXISTS (SELECT 1 FROM message_attachments WHERE media_id=media_assets.id) OR EXISTS (SELECT 1 FROM user_profiles WHERE avatar_id=media_assets.id)"
    )
    with op.batch_alter_table("user_profiles") as batch:
        batch.create_foreign_key("fk_profile_avatar", "media_assets", ["avatar_id"], ["id"], ondelete="SET NULL")


def downgrade():
    with op.batch_alter_table("user_profiles") as batch:
        batch.drop_constraint("fk_profile_avatar", type_="foreignkey")
    op.drop_column("media_assets", "claimed")
