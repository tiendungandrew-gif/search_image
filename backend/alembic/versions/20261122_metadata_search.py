"""Indexed, accent-insensitive names and descriptions for image search."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

from alembic import op

revision = "20261122_metadata_search"
down_revision = "20261120_public_datasets"
branch_labels = None
depends_on = None


def _fold_v1(expression):
    return (
        "btrim(regexp_replace("
        "regexp_replace(normalize(lower(translate("
        f"coalesce({expression}, ''), 'đĐ', 'dD')), NFD), '[\u0300-\u036f]', '', 'g'), "
        "'[^[:alnum:]]+', ' ', 'g'))"
    )


# Frozen v1 expression: future migrations must not change this definition.
DOCUMENT = (
    "setweight(to_tsvector('simple'::regconfig, "
    + _fold_v1(
        "coalesce(title, '') || ' ' || "
        "coalesce(jsonb_path_query_array(extra, '$.approved_csv_rows[*].entity_name')::text, '')"
    )
    + "), 'A') || setweight(to_tsvector('simple'::regconfig, "
    + _fold_v1("coalesce(caption, '') || ' ' || coalesce(description, '')")
    + "), 'B')"
)


def upgrade():
    op.add_column(
        "image_metadata",
        sa.Column(
            "search_document", TSVECTOR(), sa.Computed(DOCUMENT, persisted=True), nullable=False
        ),
    )
    op.create_index(
        "ix_image_metadata_search_document",
        "image_metadata",
        ["search_document"],
        postgresql_using="gin",
    )


def downgrade():
    op.drop_index("ix_image_metadata_search_document", table_name="image_metadata")
    op.drop_column("image_metadata", "search_document")
