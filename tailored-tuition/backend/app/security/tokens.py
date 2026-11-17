"""Random tokens for cookies and email links. Only SHA-256 hashes are stored,
so a database leak does not hand out working logins or links."""

import hashlib
import secrets


def new_token() -> tuple[str, str]:
    """(token for the user, hash for the database)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
