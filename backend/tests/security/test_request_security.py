"""Isolated API/security cases; no network services or real credentials."""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.schemas.filters import Filters
from app.schemas.ingestion import ImageMetadataInput


@pytest.mark.parametrize("length", ["9" * 5000, "-1", "invalid", b"\xb2", ""])
async def test_invalid_content_length_never_becomes_internal_error(app, length):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://unit") as client:
        result = await client.post(
            "/api/v1/search", content=b"{}", headers={"Content-Length": length}
        )
    assert result.status_code == 413
    assert result.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("city", "Paris\x00"),
        ("source_dataset", "source\x00"),
        ("tags_any", ["tag\x00"]),
        ("tags_all", ["tag\n"]),
        ("city", "   "),
    ],
)
def test_metadata_filters_reject_control_characters_before_database(field, value):
    with pytest.raises(ValidationError):
        Filters.model_validate({field: value})


def test_metadata_filters_keep_legitimate_unicode_and_sql_punctuation():
    assert Filters(city=" Ha\u0300 No\u0323\u0302i ").city == "Hà Nội"
    value = "O'Reilly'); SELECT 1 --"
    assert Filters(city=value).city == value


@pytest.mark.parametrize("body", [b"{", b"\xff", b'{"top_k":NaN}', b"[]", b"null"])
async def test_malformed_search_json_is_safe_validation_error(app, auth_headers, body):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://unit") as client:
        response = await client.post(
            "/api/v1/search",
            content=body,
            headers={**auth_headers, "Content-Type": "application/json"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"
    assert "Traceback" not in response.text


@pytest.mark.parametrize("field", ["title", "caption", "source_dataset", "license", "rights_ref"])
def test_upload_metadata_cannot_send_nul_to_postgresql(field):
    values = {"source_dataset": "qa", "license": "fixture", "rights_ref": "fixture://qa"}
    values[field] = "value\x00"
    with pytest.raises(ValidationError):
        ImageMetadataInput.model_validate(values)


def test_multiline_caption_and_existing_metadata_hash_input_are_preserved():
    caption = "  Caption line one\nline two  "
    value = ImageMetadataInput(
        source_dataset="qa", license="fixture", rights_ref="fixture://qa", caption=caption
    )
    assert value.caption == caption
    assert value.fingerprint_data()["caption"] == caption
