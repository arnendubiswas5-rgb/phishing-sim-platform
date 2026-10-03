"""Tracking-link identifiers: an unguessable UUID plus an HMAC binding it to this server.

A CampaignTarget's tracking_uuid is the public identifier embedded in email
links; tracking_sig lets the tracking endpoints reject a UUID that was never
actually issued (guessed, tampered with, or copied from a different
deployment) before doing any database lookup.
"""

import hashlib
import hmac
import uuid

from app.config import settings


def generate_tracking_uuid() -> uuid.UUID:
    return uuid.uuid4()


def generate_tracking_signature(tracking_uuid: uuid.UUID) -> str:
    return hmac.new(
        settings.TRACKING_HMAC_SECRET.encode("utf-8"),
        str(tracking_uuid).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_tracking_signature(tracking_uuid: uuid.UUID, signature: str) -> bool:
    expected = generate_tracking_signature(tracking_uuid)
    # constant-time comparison - a timing side-channel here would let an
    # attacker forge valid signatures byte-by-byte.
    return hmac.compare_digest(expected, signature)
