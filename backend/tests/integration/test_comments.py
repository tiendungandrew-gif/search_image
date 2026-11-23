from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Image, ImageMetadata
from app.db.models.access import AccessDataset, ImageModeration, User
from tests.integration.test_chat import chat_accounts as chat_accounts

pytestmark = pytest.mark.integration


@pytest.fixture
async def commented_images(chat_accounts):
    app, alice, bob, carol = chat_accounts
    async with app.state.services.database.sessions() as session, session.begin():
        library = AccessDataset(
            key="comment_public", name="Public", shared_with_members=True, is_public=True
        )
        session.add(library)
        images = []
        for n, source in enumerate(["comment_public", "comment_private"]):
            image = Image(
                sha256=str(n + 1) * 64,
                status="available",
                media_type="image/jpeg",
                byte_size=100,
                width=160,
                height=100,
                created_by="fixture",
            )
            session.add(image)
            await session.flush()
            session.add(
                ImageMetadata(image_id=image.id, title="Ảnh bình luận", source_dataset=source)
            )
            images.append(image.id)
    yield app, alice, bob, carol, images, library.id


def body(text="Ảnh đẹp quá!", nonce=None):
    return {"body": text, "client_id": str(nonce or uuid4())}


async def test_comments_author_identity_idempotency_guests_and_csrf(commented_images):
    app, alice, bob, _, images, _ = commented_images
    path = f"/api/v1/images/{images[0]}/comments"
    payload = body("  Ảnh đẹp quá!  ")
    added = await alice.post(path, json=payload)
    assert added.status_code == 201, added.text
    comment = added.json()
    assert comment["body"] == "Ảnh đẹp quá!" and comment["author"]["id"] == alice.user_id
    assert comment["can_delete"] is True
    assert (await alice.post(path, json=payload)).json()["id"] == comment["id"]
    conflict = await alice.post(path, json={**payload, "body": "Khác nội dung"})
    assert conflict.status_code == 409
    listed = await bob.get(path)
    assert listed.status_code == 200 and listed.json()["total"] == 1
    assert listed.json()["comments"][0]["can_delete"] is False
    assert "no-store" in listed.headers["cache-control"]
    assert (await bob.delete(path + "/" + comment["id"])).status_code == 404
    assert (
        await alice.post(path, json=body(), headers={"X-CSRF-Token": "wrong"})
    ).status_code == 403
    for payload in [body("  "), body("x" * 2001), {**body(), "user_id": bob.user_id}]:
        assert (await alice.post(path, json=payload)).status_code == 422
    async with AsyncClient(transport=ASGITransport(app), base_url=alice.base_url) as guest:
        listed = await guest.get(path)
        assert listed.status_code == 200 and listed.json()["comments"][0]["can_delete"] is False
        assert (await guest.post(path, json=body())).status_code == 401
    assert (await alice.delete(path + "/" + comment["id"])).status_code == 200
    assert (await bob.get(path)).json()["total"] == 0


async def test_pagination_rate_limit_and_live_visibility(commented_images):
    app, alice, bob, _, images, library_id = commented_images
    path = f"/api/v1/images/{images[0]}/comments"
    for n in range(25):
        response = await alice.post(path, json=body(str(n)))
        assert response.status_code == 201, response.text
    first = (await bob.get(path)).json()
    assert first["total"] == 25 and len(first["comments"]) == 20 and first["has_more"]
    second = (await bob.get(path, params={"before": first["next_cursor"]})).json()
    assert len(second["comments"]) == 5 and not second["has_more"]
    assert not {c["id"] for c in first["comments"]} & {c["id"] for c in second["comments"]}
    for n in range(5):
        assert (await alice.post(path, json=body(str(n)))).status_code == 201
    assert (await alice.post(path, json=body())).status_code == 429
    denied = f"/api/v1/images/{images[1]}/comments"
    assert (await alice.get(denied)).status_code == 404
    assert (await bob.post(denied, json=body())).status_code == 404
    async with app.state.services.database.sessions() as session, session.begin():
        session.add(ImageModeration(image_id=images[0], hidden=True))
    assert (await bob.get(path)).status_code == 404
    async with app.state.services.database.sessions() as session, session.begin():
        hidden = await session.get(ImageModeration, images[0])
        hidden.hidden = False
        library = await session.get(AccessDataset, library_id)
        library.shared_with_members = False
        library.is_public = False
    assert (await bob.get(path)).status_code == 404
    assert (await bob.post(path, json=body())).status_code == 404


async def test_admin_moderation_cannot_delete_a_comment_through_another_image(commented_images):
    app, alice, _, admin, images, _ = commented_images
    path = f"/api/v1/images/{images[0]}/comments"
    comment = (await alice.post(path, json=body())).json()
    async with app.state.services.database.sessions() as session, session.begin():
        user = await session.get(User, UUID(admin.user_id))
        user.role = "admin"
    assert (await admin.get(path)).json()["comments"][0]["can_delete"] is True
    assert (
        await admin.delete(f"/api/v1/images/{images[1]}/comments/{comment['id']}")
    ).status_code == 404
    assert (await admin.delete(path + "/" + comment["id"])).status_code == 200
    assert (await alice.get(path)).json()["total"] == 0
