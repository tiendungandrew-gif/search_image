"""Provision/revoke dedicated local demo accounts; no credentials leave the server."""

import argparse
import asyncio
import json
import secrets

from sqlalchemy import delete, func, select, text

from app.core.config import Settings
from app.core.container import Services
from app.core.passwords import hash_password
from app.core.quick_login import DEMO_ACCOUNTS, quick_login_enabled
from app.db.models.access import AccessDataset, AuthSession, DatasetGrant, User
from app.services.accounts import audit
from app.services.catalog import sync_catalog


async def provision(services, *, enable):
    cfg = services.settings.model_copy(update={"auth_quick_login_enabled": True})
    if not quick_login_enabled(cfg):
        raise ValueError("LOCAL_DEVELOPMENT_OR_TEST_REQUIRED")
    encoded = await asyncio.to_thread(hash_password, secrets.token_urlsafe(48)) if enable else None
    result = []
    async with services.database.sessions() as session, session.begin():
        await session.execute(text("SELECT pg_advisory_xact_lock(731208122)"))
        if enable:
            admins = await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == "admin", User.is_active.is_(True), User.is_demo.is_(False))
            )
            if not admins:
                raise ValueError("BOOTSTRAP_A_REAL_ADMIN_FIRST")
            await sync_catalog(session)
        for role, (username, display_name) in DEMO_ACCOUNTS.items():
            user = await session.scalar(
                select(User).where(User.username == username).with_for_update()
            )
            if user is not None and (not user.is_demo or user.role != role):
                raise ValueError("DEMO_USERNAME_CONFLICT_NO_ACCOUNT_CHANGED")
            created = user is None
            if user is None:
                if not enable:
                    continue
                user = User(
                    username=username,
                    display_name=display_name,
                    password_hash=encoded,
                    role=role,
                    is_demo=True,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
                if role == "user":
                    ids = (
                        await session.scalars(
                            select(AccessDataset.id).where(AccessDataset.is_active.is_(True))
                        )
                    ).all()
                    session.add_all(
                        DatasetGrant(user_id=user.id, dataset_id=identity) for identity in ids
                    )
            user.is_active = enable
            await session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
            audit(
                session,
                None,
                "operator.quick_login_enabled" if enable else "operator.quick_login_disabled",
                user.id,
                role=role,
                created=created,
            )
            result.append({"id": str(user.id), "username": username, "role": role})
    return {"status": "enabled" if enable else "disabled", "accounts": result}


async def execute(args):
    services = Services(Settings())
    try:
        return await provision(services, enable=args.action == "enable")
    finally:
        await services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["enable", "disable"])
    args = parser.parse_args()
    try:
        print(json.dumps(asyncio.run(execute(args))))
    except Exception as issue:
        message = str(issue)
        print(
            json.dumps(
                {
                    "status": "failed",
                    "code": message
                    if message.replace("_", "").isalnum() and message.isupper()
                    else "QUICK_LOGIN_SETUP_FAILED",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
