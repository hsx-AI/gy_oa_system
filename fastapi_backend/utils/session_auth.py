# -*- coding: utf-8 -*-
"""
Resolve current user from verified login access token.
Sensitive APIs must use this module; never trust request current_user/approver for authz.
"""
from typing import Optional

from fastapi import Header, HTTPException


def require_login_user(
    authorization: Optional[str] = Header(None),
    x_oa_token: Optional[str] = Header(None, alias="X-OA-Token"),
) -> str:
    """FastAPI dependency: return logged-in user name; 401 if missing/invalid token."""
    from routers.auth import _require_access_user

    return _require_access_user(authorization, x_oa_token)


def resolve_actor_name(
    claimed: Optional[str],
    login_user: str,
    *,
    allow_mismatch: bool = False,
) -> str:
    """Prefer token identity over client-claimed current_user/approver."""
    actor = (login_user or "").strip()
    if not actor:
        raise HTTPException(status_code=401, detail="not logged in or session expired")
    claimed_name = (claimed or "").strip()
    if claimed_name and claimed_name != actor and not allow_mismatch:
        return actor
    return actor
