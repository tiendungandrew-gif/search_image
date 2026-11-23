"""Profile and favorite boundaries on disposable PostgreSQL and private MinIO."""

import io
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image as PillowImage
from sqlalchemy import select

from app.db.models import Image, ImageMetadata
from app.db.models.access import AccessDataset, ImageModeration, User
from tests.integration.test_chat import chat_accounts as chat_accounts
from tests.integration.test_chat import png

pytestmark = pytest.mark.integration


async def test_own_profile_update_is_private_and_does_not_allow_role_changes(chat_accounts):
    app, alice, bob, _ = chat_accounts
    profile = await alice.get("/api/v1/profile")
    assert profile.status_code == 200, profile.text
    assert profile.json()["user"]["username"] == "alice"
    updated = await alice.patch(
        "/api/v1/profile", json={"display_name": "  Alice mới  ", "bio": "Thích chụp ảnh"}
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["user"]["display_name"] == "Alice mới"
    assert updated.json()["bio"] == "Thích chụp ảnh"
    assert (await alice.get("/api/v1/auth/me")).json()["user"]["display_name"] == "Alice mới"
    assert (await bob.get("/api/v1/profile")).json()["bio"] == ""
    assert (
        await alice.patch("/api/v1/profile", json={"display_name": "x", "role": "admin"})
    ).status_code == 422
    assert (
        await alice.patch(
            "/api/v1/profile", json={"display_name": "x"}, headers={"X-CSRF-Token": "wrong"}
        )
    ).status_code == 403
    assert (
        await alice.patch("/api/v1/profile", json={"display_name": " ", "bio": ""})
    ).status_code == 422
    assert (
        await alice.patch("/api/v1/profile", json={"display_name": "Alice", "bio": "x" * 501})
    ).status_code == 422


async def test_avatar_upload_is_sanitized_and_shared_in_account_and_chat(chat_accounts):
    app, alice, bob, _ = chat_accounts
    uploaded = await alice.post(
        "/api/v1/profile/avatar", files={"image": ("portrait.png", png(), "image/png")}
    )
    assert uploaded.status_code == 200, uploaded.text
    url = uploaded.json()["user"]["avatar_url"]
    assert url.startswith(f"/api/v1/profiles/{alice.user_id}/avatar?v=")
    response = await bob.get(url)
    assert response.status_code == 200, response.text
    assert (
        response.headers["content-type"] == "image/jpeg"
        and "no-store" in response.headers["cache-control"]
    )
    with PillowImage.open(io.BytesIO(response.content)) as image:
        assert image.size == (256, 256) and not image.getexif()
    assert (await alice.get("/api/v1/auth/me")).json()["user"]["avatar_url"] == url
    assert (await bob.get("/api/v1/chat/users", params={"q": "alice"})).json()["users"][0][
        "avatar_url"
    ] == url
    async with AsyncClient(transport=ASGITransport(app), base_url=alice.base_url) as guest:
        assert (await guest.get(url)).status_code == 401
        assert (await guest.get("/api/v1/profile")).status_code == 401
    replacement = await alice.post(
        "/api/v1/profile/avatar", files={"image": ("other.png", png(), "image/png")}
    )
    assert replacement.json()["user"]["avatar_url"] != url
    invalid = await alice.post(
        "/api/v1/profile/avatar", files={"image": ("bad.svg", b"<svg/>", "image/svg+xml")}
    )
    assert invalid.status_code == 422
    oversized = await alice.post(
        "/api/v1/profile/avatar",
        files={"image": ("large.jpg", b"x" * (5 * 1024**2 + 1), "image/jpeg")},
    )
    assert oversized.status_code == 413


async def test_favorites_are_idempotent_private_and_follow_live_library_permissions(chat_accounts):
    app, alice, bob, _ = chat_accounts
    async with app.state.services.database.sessions() as session, session.begin():
        dataset = AccessDataset(key="shared", name="Shared", shared_with_members=True)
        session.add(dataset)
        images = []
        for index, source in enumerate(["shared", "private"]):
            image = Image(
                sha256=str(index) * 64,
                status="available",
                media_type="image/jpeg",
                byte_size=100,
                width=160,
                height=100,
                created_by="fixture",
            )
            session.add(image)
            await session.flush()
            session.add(ImageMetadata(image_id=image.id, title="Ảnh thử", source_dataset=source))
            images.append(image.id)
    public, private = map(str, images)
    path = f"/api/v1/profile/favorites/{public}"
    assert (await alice.put(path)).status_code == 200
    assert (await alice.put(path)).status_code == 200
    saved = await alice.get("/api/v1/profile/favorites")
    assert saved.status_code == 200, saved.text
    assert saved.json()["total_saved"] == 1 and saved.json()["results"][0]["image_id"] == public
    assert (await bob.get("/api/v1/profile/favorites")).json()["results"] == []
    assert (await alice.put(f"/api/v1/profile/favorites/{private}")).status_code == 404
    statuses = await alice.get(
        "/api/v1/profile/favorites/status", params=[("ids", public), ("ids", private)]
    )
    assert statuses.json()["ids"] == [public]
    assert (await alice.get("/api/v1/profile")).json()["favorite_count"] == 1
    async with app.state.services.database.sessions() as session, session.begin():
        session.add(ImageModeration(image_id=UUID(public), hidden=True))
    assert (await alice.get("/api/v1/profile/favorites")).json()["total_saved"] == 0
    assert (await alice.get("/api/v1/profile/favorites/status", params={"ids": public})).json()[
        "ids"
    ] == []
    async with app.state.services.database.sessions() as session, session.begin():
        row = await session.get(ImageModeration, UUID(public))
        row.hidden = False
        library = await session.scalar(select(AccessDataset).where(AccessDataset.key == "shared"))
        library.shared_with_members = False
    assert (await alice.get("/api/v1/profile/favorites")).json()["results"] == []
    assert (await alice.delete(path)).status_code == 200
    async with app.state.services.database.sessions() as session:
        assert (await session.get(User, UUID(alice.user_id))).role == "user"
