"""Add the three planned knowledge tables; no image/index mutations or seeded facts."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20261106_agent_knowledge"
down_revision = "928b88dc3f68"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("name_key", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("locale", sa.Text(), nullable=False),
        sa.Column("external_key", sa.Text()),
        sa.Column("aliases", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("provenance", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("canonical_name", "entity_type", "locale"),
        sa.UniqueConstraint("external_key"),
        sa.CheckConstraint(
            "entity_type IN ('city','landmark','country','location','person','object',"
            "'organization','category','other')",
            name="entity_type",
        ),
    )
    op.create_index("ix_entities_name_key", "entities", ["name_key"])
    op.create_index("ix_entities_aliases", "entities", ["aliases"], postgresql_using="gin")
    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("predicate", sa.Text(), nullable=False),
        sa.Column("object_id", sa.Uuid(), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("subject_id", "predicate", "object_id", "source_ref"),
        sa.CheckConstraint(
            "predicate IN ('located_in','contains','part_of','has_landmark',"
            "'depicts','related_to','associated_with')",
            name="predicate",
        ),
        sa.CheckConstraint("subject_id != object_id", name="distinct_entities"),
    )
    op.create_index(
        "ix_relationships_subject_predicate", "entity_relationships", ["subject_id", "predicate"]
    )
    op.create_index(
        "ix_relationships_object_predicate", "entity_relationships", ["object_id", "predicate"]
    )
    op.create_table(
        "image_entities",
        sa.Column("image_id", sa.Uuid(), sa.ForeignKey("images.id"), primary_key=True),
        sa.Column("entity_id", sa.Uuid(), sa.ForeignKey("entities.id"), primary_key=True),
        sa.Column("relation", sa.Text(), primary_key=True),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint(
            "relation IN ('depicts','located_in','associated_with')", name="relation"
        ),
    )
    op.create_index(
        "ix_image_entities_entity_relation", "image_entities", ["entity_id", "relation", "image_id"]
    )


def downgrade():
    op.drop_table("image_entities")
    op.drop_table("entity_relationships")
    op.drop_table("entities")
