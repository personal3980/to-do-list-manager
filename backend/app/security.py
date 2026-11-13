"""Small helpers for password hashing, random tokens, and local throttling."""
import hashlib
import secrets
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class RateLimiter:
    """Single-process local limit. Use a shared store for multiple workers."""
    def __init__(self):
        self.events = defaultdict(deque)
        self.lock = Lock()

    def check(self, request: Request, action: str, limit: int):
        now = monotonic()
        key = (request.client.host if request.client else 'unknown', action)
        with self.lock:
            for old_key in list(self.events):
                if not self.events[old_key] or self.events[old_key][-1] <= now - 900:
                    del self.events[old_key]
            recent = self.events[key]
            while recent and recent[0] <= now - 900:
                recent.popleft()
            if len(recent) >= limit:
                raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.', headers={'Retry-After': '900'})
            recent.append(now)


limiter = RateLimiter()
