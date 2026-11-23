"""Private chat lifecycle and negative authorization on disposable databases."""

import asyncio
import io
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import func, select

from app.db.models import Image as CatalogImage
from app.main import create_app

pytestmark = pytest.mark.integration
PASSWORD = "Chat-test-only-password-2026!"


@pytest.fixture
async def chat_accounts(qa_resources):
    cfg = qa_resources.settings
    cfg.auth_legacy_tokens_enabled = False
    cfg.request_timeout_seconds = 15
    app = create_app(cfg)
    app.state.services = qa_resources.services
    origin = cfg.cors_origins[0]
    clients = []
    try:
        for name in ["alice", "bobby", "carol"]:
            client = AsyncClient(
                transport=ASGITransport(app), base_url=origin, headers={"Origin": origin}
            )
            clients.append(client)
            result = await client.post(
                "/api/v1/auth/register",
                json={"username": name, "display_name": name.title(), "password": PASSWORD},
            )
            assert result.status_code == 201, result.text
            login = await client.post(
                "/api/v1/auth/login", json={"username": name, "password": PASSWORD}
            )
            assert login.status_code == 200, login.text
            client.headers["X-CSRF-Token"] = client.cookies["lens_csrf"]
            client.user_id = login.json()["user"]["id"]
        yield app, *clients
    finally:
        await asyncio.gather(*(client.aclose() for client in clients))


def message(body="Hello", nonce=None):
    return {"body": body, "client_id": str(nonce or uuid4())}


def png():
    buffer = io.BytesIO()
    Image.new("RGB", (160, 100), "red").save(buffer, format="PNG")
    return buffer.getvalue()


async def start(client, peer):
    response = await client.post("/api/v1/chat/conversations", json={"user_id": peer.user_id})
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def test_private_messages_unread_read_receipts_and_nonce(chat_accounts):
    app, alice, bob, carol = chat_accounts
    people = await alice.get("/api/v1/chat/users")
    assert people.status_code == 200, people.text
    assert {user["username"] for user in people.json()["users"]} == {"bobby", "carol"}
    assert "password" not in people.text
    conversation = await start(alice, bob)
    assert await start(bob, alice) == conversation
    path = f"/api/v1/chat/conversations/{conversation}/messages"
    body = message("Xin chào")
    sent = await alice.post(path, data=body)
    assert sent.status_code == 201, sent.text
    assert (await alice.post(path, data=body)).json()["id"] == sent.json()["id"]
    inbox = (await bob.get("/api/v1/chat/conversations")).json()["conversations"]
    assert inbox[0]["unread"] == 1 and inbox[0]["peer"]["id"] == alice.user_id
    history = await bob.get(path)
    assert history.status_code == 200 and len(history.json()["messages"]) == 1
    assert history.json()["messages"][0]["body"] == "Xin chào"
    assert (await carol.get(path)).status_code == 404
    assert (await carol.post(path, data=message())).status_code == 404
    assert (
        await carol.post(
            f"/api/v1/chat/conversations/{conversation}/read",
            json={"message_id": sent.json()["id"]},
        )
    ).status_code == 404
    assert (
        await bob.post(
            f"/api/v1/chat/conversations/{conversation}/read",
            json={"message_id": sent.json()["id"]},
        )
    ).status_code == 200
    assert (await bob.get("/api/v1/chat/conversations")).json()["conversations"][0]["unread"] == 0
    assert (
        await alice.post(path, data=message(), headers={"X-CSRF-Token": "wrong"})
    ).status_code == 403
    assert (
        await alice.post("/api/v1/chat/conversations", json={"user_id": alice.user_id})
    ).status_code == 422


async def test_attachment_is_private_reencoded_and_outside_search_corpus(chat_accounts):
    app, alice, bob, carol = chat_accounts
    conversation = await start(alice, bob)
    path = f"/api/v1/chat/conversations/{conversation}/messages"
    response = await alice.post(
        path, data=message("Ảnh gửi riêng"), files={"image": ("sample.png", png(), "image/png")}
    )
    assert response.status_code == 201, response.text
    image_url = response.json()["image_url"]
    content = await bob.get(image_url)
    assert content.status_code == 200, content.text
    assert content.headers["content-type"] == "image/jpeg"
    assert content.headers["cache-control"] == "private, no-store"
    with Image.open(io.BytesIO(content.content)) as image:
        assert image.format == "JPEG" and image.size == (160, 100)
    assert (await carol.get(image_url)).status_code == 404
    async with AsyncClient(transport=ASGITransport(app), base_url=alice.base_url) as guest:
        assert (await guest.get(image_url)).status_code == 401
    async with app.state.services.database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(CatalogImage)) == 0
    invalid = await alice.post(
        path, data=message(), files={"image": ("bad.svg", b"<svg/>", "image/svg+xml")}
    )
    assert invalid.status_code == 422
    oversized = await alice.post(
        path,
        data=message(),
        files={"image": ("large.jpg", b"x" * (10 * 1024 * 1024 + 1), "image/jpeg")},
    )
    assert oversized.status_code == 413


async def test_message_history_pages_without_gaps_and_rejects_cross_conversation_receipts(
    chat_accounts,
):
    _, alice, bob, carol = chat_accounts
    first = await start(alice, bob)
    path = f"/api/v1/chat/conversations/{first}/messages"
    for n in range(52):
        result = await alice.post(path, data=message(str(n)))
        assert result.status_code == 201, result.text
    recent = (await bob.get(path)).json()
    assert len(recent["messages"]) == 50 and recent["has_more"]
    older = (await bob.get(path, params={"before": recent["messages"][0]["id"]})).json()
    assert [item["body"] for item in older["messages"]] == ["0", "1"]
    assert not older["has_more"]
    after = (await bob.get(path, params={"after": older["messages"][-1]["id"]})).json()
    assert after["messages"] == recent["messages"]
    other = await start(alice, carol)
    assert (
        await alice.post(
            f"/api/v1/chat/conversations/{other}/read",
            json={"message_id": recent["messages"][0]["id"]},
        )
    ).status_code == 404
