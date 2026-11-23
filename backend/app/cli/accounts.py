"""Private operator bootstrap/recovery. Password is read from stdin, never argv/logs."""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, text

from app.core.config import Settings
from app.core.container import Services
from app.core.passwords import hash_password
from app.db.models.access import AuditEvent, AuthSession, User
from app.schemas.access import CreateUser


async def execute(args):
    password = sys.stdin.read(1024).rstrip("\r\n")
    body = CreateUser(
        username=args.username,
        display_name=args.display_name or args.username,
        password=password,
        role="admin",
    )
    services = Services(Settings())
    try:
        encoded = await asyncio.to_thread(hash_password, body.password.get_secret_value())
        async with services.database.sessions() as session, session.begin():
            await session.execute(text("SELECT pg_advisory_xact_lock(731208122)"))
            user = await session.scalar(
                select(User).where(User.username == body.username).with_for_update()
            )
            if args.command == "bootstrap":
                count = await session.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.role == "admin", User.is_active.is_(True), User.is_demo.is_(False))
                )
                if count:
                    print(json.dumps({"status": "already_configured"}))
                    return
                if user is not None:
                    raise ValueError("USERNAME_EXISTS")
                user = User(
                    username=body.username,
                    display_name=body.display_name,
                    password_hash=encoded,
                    role="admin",
                    is_active=True,
                )
                session.add(user)
                await session.flush()
                action = "operator.admin_bootstrapped"
            else:
                if user is None:
                    raise ValueError("USER_NOT_FOUND")
                user.password_hash = encoded
                await session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
                action = "operator.password_reset"
            session.add(
                AuditEvent(actor_id=None, action=action, resource_id=str(user.id), details={})
            )
        print(
            json.dumps(
                {
                    "status": "created" if args.command == "bootstrap" else "reset",
                    "username": user.username,
                    "user_id": str(user.id),
                    "at_utc": datetime.now(UTC).isoformat(),
                }
            )
        )
    finally:
        await services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["bootstrap", "reset"])
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name")
    args = parser.parse_args()
    try:
        asyncio.run(execute(args))
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "message": "Check account arguments and database migration status",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
