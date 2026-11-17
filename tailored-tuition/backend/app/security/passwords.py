"""Password hashing with scrypt (standard library; OWASP-recommended parameters).

Format: scrypt$<n>$<r>$<p>$<salt b64>$<hash b64>. Parameters are stored with
each hash so they can be raised later without breaking existing logins.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

# OWASP Password Storage Cheat Sheet option: N=2^15 (32 MiB), r=8, p=3. Chosen over
# the 128 MiB option so a burst of logins can't exhaust a small server's memory.
N, R, P = 2**15, 8, 3
DKLEN = 32
MAXMEM = 256 * 1024 * 1024


def set_cost_for_tests(n: int) -> None:
    """Tests only: a cheap N keeps the suite fast. Never call this in the app."""
    global N
    N = n


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=DKLEN, maxmem=MAXMEM)
    return f"scrypt${N}${R}${P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(hash_b64)
        digest = hashlib.scrypt(
            password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected), maxmem=MAXMEM
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


# A real hash of a random password: verifying against it costs the same time as
# a real check, so "unknown user" and "wrong password" take equally long.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
