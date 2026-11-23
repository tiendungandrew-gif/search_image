"""Add accounts/sessions and dataset ACLs without changing image/vector identities."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20261108_access_control"
down_revision = "20261106_agent_knowledge"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("role IN ('user','admin')", name="role"),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.Text(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("csrf_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_table(
        "access_datasets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for name, left, target in [
        ("dataset_grants", "user_id", "users.id"),
        ("entity_datasets", "entity_id", "entities.id"),
        ("relation_datasets", "relation_id", "entity_relationships.id"),
    ]:
        op.create_table(
            name,
            sa.Column(left, sa.Uuid(), sa.ForeignKey(target, ondelete="CASCADE"), primary_key=True),
            sa.Column(
                "dataset_id",
                sa.Uuid(),
                sa.ForeignKey("access_datasets.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )
    op.create_table(
        "image_moderation",
        sa.Column(
            "image_id", sa.Uuid(), sa.ForeignKey("images.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "auth_usage",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("kind", sa.Text(), primary_key=True),
        sa.Column("bucket", sa.Text(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "login_throttles",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text()),
        sa.Column("details", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_events_created_id", "audit_events", ["created_at", "id"])
    # UUID generation is PostgreSQL-native. Existing metadata/revisions/point IDs stay unchanged.
    op.execute("""
        INSERT INTO access_datasets (id, key, name)
        SELECT gen_random_uuid(), key,
               CASE WHEN key='__unassigned__' THEN 'Chưa phân loại' ELSE key END
        FROM (SELECT DISTINCT COALESCE(m.source_dataset,'__unassigned__') AS key
              FROM images i LEFT JOIN image_metadata m ON m.image_id=i.id) catalog
    """)
    op.execute("""
        INSERT INTO entity_datasets (dataset_id,entity_id)
        SELECT DISTINCT d.id, ie.entity_id FROM image_entities ie
        LEFT JOIN image_metadata m ON m.image_id=ie.image_id
        JOIN access_datasets d ON d.key=COALESCE(m.source_dataset,'__unassigned__')
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO relation_datasets (dataset_id,relation_id)
        SELECT DISTINCT ed.dataset_id,r.id FROM entity_relationships r
        JOIN entity_datasets ed ON ed.entity_id=r.subject_id
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO entity_datasets (dataset_id,entity_id)
        SELECT rd.dataset_id,r.object_id FROM relation_datasets rd
        JOIN entity_relationships r ON r.id=rd.relation_id
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    # Downgrade is only for disposable verification, never an automatic production rollback.
    for name in [
        "audit_events",
        "login_throttles",
        "auth_usage",
        "image_moderation",
        "relation_datasets",
        "entity_datasets",
        "dataset_grants",
        "auth_sessions",
        "access_datasets",
        "users",
    ]:
        op.drop_table(name)
