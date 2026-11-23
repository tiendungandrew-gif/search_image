"""Versioned, accent-insensitive PostgreSQL search document for image metadata."""


def _fold_v1(expression):
    return (
        "btrim(regexp_replace("
        "regexp_replace(normalize(lower(translate("
        f"coalesce({expression}, ''), 'đĐ', 'dD')), NFD), '[\u0300-\u036f]', '', 'g'), "
        "'[^[:alnum:]]+', ' ', 'g'))"
    )


SEARCH_DOCUMENT_V1 = (
    "setweight(to_tsvector('simple'::regconfig, "
    + _fold_v1(
        "coalesce(title, '') || ' ' || "
        "coalesce(jsonb_path_query_array(extra, '$.approved_csv_rows[*].entity_name')::text, '')"
    )
    + "), 'A') || setweight(to_tsvector('simple'::regconfig, "
    + _fold_v1("coalesce(caption, '') || ' ' || coalesce(description, '')")
    + "), 'B')"
)
