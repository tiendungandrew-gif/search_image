"""Explicit local demo login policy; ordinary accounts never qualify."""

from urllib.parse import urlsplit

DEMO_ACCOUNTS = {
    "admin": ("demo_admin", "Admin trải nghiệm"),
    "user": ("demo_user", "User trải nghiệm"),
}


def quick_login_enabled(settings):
    return (
        settings.auth_quick_login_enabled
        and settings.app_env in {"development", "test"}
        and bool(settings.cors_origins)
        and all(
            urlsplit(origin).hostname in {"localhost", "127.0.0.1", "::1"}
            for origin in settings.cors_origins
        )
    )
