# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from fastapi import Request, HTTPException

# ✅ Basic login check

def require_login(request: Request):
    if "user" not in request.session:
        raise HTTPException(
            status_code=401,
            detail="Not logged in"
        )
    return request.session["user"]

# ✅ Get current user
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user


# ✅ ✅ Admin only (STRICT BLOCK)
def require_admin(request: Request):
    user = get_current_user(request)

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user


# ✅ Admin + PM allowed
def require_pm_or_admin(request: Request):
    user = get_current_user(request)

    if user.get("role") not in ["admin", "pm"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return user


# ✅ All roles can read (for now)
def require_read_access(request: Request):
    return get_current_user(request)