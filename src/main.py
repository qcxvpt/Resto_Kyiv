"""Main blueprint: index page and security headers."""

from flask import Blueprint, render_template, session

main_bp = Blueprint("main", __name__)


@main_bp.after_app_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://unpkg.com https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' https://unpkg.com 'unsafe-inline'; "
        "img-src 'self' data: https://*.tile.openstreetmap.org;"
    )
    return response


@main_bp.route("/")
def index():
    return render_template(
        "main.html",
        logged_in="user_id" in session,
        username=session.get("username", ""),
    )
