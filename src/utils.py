"""Shared helpers: validators, sanitizer, login decorator."""

import re
import html
from functools import wraps

from flask import session, flash, redirect, url_for

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def validate_username(u):
    if not u:
        return "Username is required."
    if not USERNAME_RE.match(u):
        return "3-32 chars: letters, digits, underscores."
    return None


def validate_password(p):
    if not p or len(p) < 8:
        return "Min 8 characters."
    if not re.search(r"[A-Z]", p):
        return "Need at least one uppercase letter."
    if not re.search(r"[0-9]", p):
        return "Need at least one digit."
    return None


def sanitize(text, max_len=500):
    return html.escape(text.strip())[:max_len]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated
