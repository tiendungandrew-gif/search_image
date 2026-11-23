"""Account boundary tests without external services."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import dialect

from app.core.access import Principal, current_principal, source_clause
from app.core.passwords import hash_password, verify_password
from app.schemas.access import CreateUser, DatasetInput, UpdateUser
from app.schemas.filters import Filters
from app.services.search.vector_retriever import payload_filter


def test_password_salt_verification_and_untrusted_work_factors():
    first = hash_password("a sufficiently long password")
    second = hash_password("a sufficiently long password")
    assert first != second and "sufficiently" not in first
    assert verify_password("a sufficiently long password", first)
    assert not verify_password("wrong", first)
    assert not verify_password("x", first.replace("131072", "1073741824"))
    for invalid in ["", "garbage", "scrypt$131072$8$1$xx$" + "0" * 64]:
        assert not verify_password("x", invalid)


@pytest.mark.parametrize("body", [{"display_name": "   "}, {"display_name": "a\nname"}])
def test_update_names_cannot_be_blank_or_control_characters(body):
    with pytest.raises(ValidationError):
        UpdateUser.model_validate(body)


def test_account_creation_and_dataset_names_validate():
    user = CreateUser(
        username="Reader", display_name="  Một người dùng  ", password="a-long-password"
    )
    assert user.username == "reader" and user.display_name == "Một người dùng"
    with pytest.raises(ValidationError):
        CreateUser(username="reader", display_name="Reader", password="short")
    with pytest.raises(ValidationError):
        DatasetInput(key="valid", name=" ")


def test_acl_empty_and_unassigned_scope_in_both_stores():
    token = current_principal.set(Principal(uuid4(), "reader", "user"))
    try:
        assert str(source_clause().compile(dialect=dialect())) == "false"
        assert payload_filter(Filters()).must[0].has_id == []
        current_principal.set(
            Principal(uuid4(), "reader", "user", (), ("private", "__unassigned__"))
        )
        sql = str(
            source_clause().compile(dialect=dialect(), compile_kwargs={"literal_binds": True})
        )
        assert "'private'" in sql and "IS NULL" in sql
        assert len(payload_filter(Filters()).must[0].should) == 2
    finally:
        current_principal.reset(token)
