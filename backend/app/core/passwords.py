"""Salted scrypt passwords; fixed work factors bound verification resource usage."""

import hashlib
import secrets

N, R, P = 2**17, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(
        password.encode(), salt=salt, n=N, r=R, p=P, dklen=32, maxmem=256 * 1024**2
    )
    return f"scrypt${N}${R}${P}${salt.hex()}${value.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        name, n, r, p, salt, expected = encoded.split("$")
        if (name, int(n), int(r), int(p)) != ("scrypt", N, R, P):
            return False
        if len(salt) != 32 or len(expected) != 64:
            return False
        value = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt),
            n=N,
            r=R,
            p=P,
            dklen=32,
            maxmem=256 * 1024**2,
        )
        return secrets.compare_digest(value.hex(), expected)
    except (ValueError, TypeError):
        return False
