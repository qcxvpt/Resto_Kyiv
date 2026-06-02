import re
import html

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def validate_username(username):
    if not username:
        return "Username is required."

    if not USERNAME_RE.match(username):
        return "3-32 chars: letters, digits, underscores."

    return None


def validate_password(password):
    if not password or len(password) < 8:
        return "Min 8 characters."

    if not re.search(r"[A-Z]", password):
        return "Need at least one uppercase letter."

    if not re.search(r"[0-9]", password):
        return "Need at least one digit."

    return None


def sanitize(text, max_len=500):
    return html.escape(text.strip())[:max_len]