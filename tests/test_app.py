"""
Unit tests for RestoKyiv Flask application.
AI-assisted: test structure, edge-case suggestions and fixture design by Claude.
All tests reviewed and validated manually.
"""

import json
import pytest
from app import create_app, db, User, Review, Favourite
from app import sanitize, validate_username, validate_password, RESTAURANTS


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Isolated test client backed by in-memory SQLite."""
    test_app = create_app({
        "TESTING":                    True,
        "SQLALCHEMY_DATABASE_URI":    "sqlite:///:memory:",
        "WTF_CSRF_ENABLED":           False,
        "SECRET_KEY":                 "test-secret-key",
        "RATELIMIT_ENABLED":          False,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })
    with test_app.app_context():
        db.create_all()
        yield test_app.test_client()
        db.drop_all()


@pytest.fixture
def registered_user(client):
    client.post("/register", data={
        "username": "testuser", "password": "Password1", "confirm": "Password1"
    })
    return {"username": "testuser", "password": "Password1"}


@pytest.fixture
def logged_in_client(client, registered_user):
    client.post("/login", data=registered_user)
    return client


# ─── Helper ──────────────────────────────────────────────────────────────────

def post_review(c, resto_id=1, text="Great food here!", rating=5, anonymous=False):
    return c.post(
        "/api/reviews",
        data=json.dumps({"resto_id": resto_id, "text": text,
                         "rating": rating, "anonymous": anonymous}),
        content_type="application/json",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateUsername:
    def test_valid_username(self):
        assert validate_username("john_doe99") is None

    def test_too_short(self):
        assert validate_username("ab") is not None

    def test_too_long(self):
        assert validate_username("a" * 33) is not None

    def test_empty(self):
        assert validate_username("") is not None

    def test_none(self):
        assert validate_username(None) is not None

    def test_special_chars_rejected(self):
        assert validate_username("bad user!") is not None

    def test_exact_min_length(self):
        assert validate_username("abc") is None

    def test_exact_max_length(self):
        assert validate_username("a" * 32) is None


class TestValidatePassword:
    def test_valid_password(self):
        assert validate_password("Secure99") is None

    def test_too_short(self):
        assert validate_password("Ab1") is not None

    def test_no_uppercase(self):
        assert validate_password("password1") is not None

    def test_no_digit(self):
        assert validate_password("Password") is not None

    def test_empty(self):
        assert validate_password("") is not None

    def test_none(self):
        assert validate_password(None) is not None

    def test_exactly_8_chars_valid(self):
        assert validate_password("Abcdef1!") is None


class TestSanitize:
    def test_strips_html(self):
        assert "&lt;script&gt;" in sanitize("<script>")

    def test_truncates_to_max_len(self):
        assert len(sanitize("x" * 1000, 100)) == 100

    def test_strips_whitespace(self):
        assert sanitize("  hello  ") == "hello"

    def test_default_max_500(self):
        assert len(sanitize("x" * 600)) == 500


# ═══════════════════════════════════════════════════════════════════════════════
# 2. REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegister:
    def test_register_success(self, client):
        rv = client.post("/register", data={
            "username": "newuser", "password": "Password1", "confirm": "Password1"
        })
        assert rv.status_code in (200, 302)

    def test_register_duplicate_username(self, client, registered_user):
        rv = client.post("/register", data={
            "username": "testuser", "password": "Password1", "confirm": "Password1"
        })
        assert b"already taken" in rv.data

    def test_register_password_mismatch(self, client):
        rv = client.post("/register", data={
            "username": "newuser2", "password": "Password1", "confirm": "WrongPass1"
        })
        assert b"match" in rv.data

    def test_register_weak_password(self, client):
        rv = client.post("/register", data={
            "username": "newuser3", "password": "weakpass", "confirm": "weakpass"
        })
        assert rv.status_code == 200  # re-renders form with error

    def test_register_bad_username(self, client):
        rv = client.post("/register", data={
            "username": "ab", "password": "Password1", "confirm": "Password1"
        })
        assert rv.status_code == 200  # re-renders form with error


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LOGIN / LOGOUT
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginLogout:
    def test_login_success(self, client, registered_user):
        rv = client.post("/login", data=registered_user)
        assert rv.status_code == 302  # redirect to index

    def test_login_wrong_password(self, client, registered_user):
        rv = client.post("/login", data={"username": "testuser", "password": "WrongPass9"})
        assert b"Invalid" in rv.data

    def test_login_nonexistent_user(self, client):
        rv = client.post("/login", data={"username": "ghost", "password": "Password1"})
        assert b"Invalid" in rv.data

    def test_logout_requires_login(self, client):
        rv = client.get("/logout")
        assert rv.status_code == 302  # redirect to login

    def test_logout_clears_session(self, logged_in_client):
        logged_in_client.get("/logout")
        # After logout, protected endpoints redirect to login
        rv = logged_in_client.get("/api/favourites")
        assert rv.status_code == 302

    def test_session_set_after_login(self, client, registered_user):
        client.post("/login", data=registered_user)
        with client.session_transaction() as sess:
            assert "user_id" in sess
            assert sess["username"] == "testuser"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RESTAURANT API
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestaurantsAPI:
    def test_get_restaurants_returns_list(self, client):
        rv = client.get("/api/restaurants")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert isinstance(data, list)
        assert len(data) == len(RESTAURANTS)

    def test_restaurants_have_required_fields(self, client):
        data = json.loads(client.get("/api/restaurants").data)
        for r in data:
            assert "id" in r
            assert "name" in r
            assert "lat" in r
            assert "lng" in r
            assert "avg_rating" in r
            assert "review_count" in r

    def test_restaurant_avg_rating_none_with_no_reviews(self, client):
        data = json.loads(client.get("/api/restaurants").data)
        assert data[0]["avg_rating"] is None
        assert data[0]["review_count"] == 0

    def test_restaurant_avg_rating_updates_after_review(self, logged_in_client):
        post_review(logged_in_client, resto_id=1, rating=4)
        data = json.loads(logged_in_client.get("/api/restaurants").data)
        resto = next(r for r in data if r["id"] == 1)
        assert resto["avg_rating"] == 4.0
        assert resto["review_count"] == 1

    def test_avg_rating_average_of_multiple_reviews(self, client):
        for uname, pwd, rating in [("user_a", "PasswordA1", 4), ("user_b", "PasswordB1", 2)]:
            client.post("/register", data={"username": uname, "password": pwd, "confirm": pwd})
            client.post("/login", data={"username": uname, "password": pwd})
            post_review(client, resto_id=2, rating=rating)
            client.get("/logout")
        data = json.loads(client.get("/api/restaurants").data)
        resto = next(r for r in data if r["id"] == 2)
        assert resto["avg_rating"] == 3.0
        assert resto["review_count"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 5. REVIEWS — CREATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestPostReview:
    def test_post_review_success(self, logged_in_client):
        rv = post_review(logged_in_client)
        assert rv.status_code == 200
        assert json.loads(rv.data)["ok"] is True

    def test_post_review_requires_login(self, client):
        rv = post_review(client)
        assert rv.status_code == 302  # redirect to login

    def test_post_review_invalid_rating_zero(self, logged_in_client):
        rv = post_review(logged_in_client, rating=0)
        assert rv.status_code == 400

    def test_post_review_invalid_rating_six(self, logged_in_client):
        rv = post_review(logged_in_client, rating=6)
        assert rv.status_code == 400

    def test_post_review_text_too_short(self, logged_in_client):
        rv = post_review(logged_in_client, text="ok")
        assert rv.status_code == 400

    def test_post_review_unknown_restaurant(self, logged_in_client):
        rv = post_review(logged_in_client, resto_id=9999)
        assert rv.status_code == 400

    def test_post_review_duplicate_rejected(self, logged_in_client):
        post_review(logged_in_client)
        rv = post_review(logged_in_client)
        assert rv.status_code == 409

    def test_post_anonymous_review(self, logged_in_client):
        rv = post_review(logged_in_client, anonymous=True)
        assert rv.status_code == 200
        reviews = json.loads(logged_in_client.get("/api/reviews/1").data)
        assert reviews[0]["author"] == "Anonymous"

    def test_post_named_review_shows_username(self, logged_in_client):
        post_review(logged_in_client, anonymous=False)
        reviews = json.loads(logged_in_client.get("/api/reviews/1").data)
        assert reviews[0]["author"] == "testuser"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. REVIEWS — READ
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetReviews:
    def test_get_reviews_empty(self, client):
        rv = client.get("/api/reviews/1")
        assert rv.status_code == 200
        assert json.loads(rv.data) == []

    def test_get_reviews_returns_posted(self, logged_in_client):
        post_review(logged_in_client, text="Fantastic place here!", rating=5)
        reviews = json.loads(logged_in_client.get("/api/reviews/1").data)
        assert len(reviews) == 1
        assert reviews[0]["rating"] == 5

    def test_get_reviews_mine_flag_true_for_owner(self, logged_in_client):
        post_review(logged_in_client)
        reviews = json.loads(logged_in_client.get("/api/reviews/1").data)
        assert reviews[0]["mine"] is True

    def test_get_reviews_mine_flag_false_for_others(self, client, registered_user):
        client.post("/login", data=registered_user)
        post_review(client)
        client.get("/logout")
        client.post("/register", data={"username": "viewer", "password": "ViewPass1", "confirm": "ViewPass1"})
        client.post("/login", data={"username": "viewer", "password": "ViewPass1"})
        reviews = json.loads(client.get("/api/reviews/1").data)
        assert reviews[0]["mine"] is False

    def test_reviews_ordered_newest_first(self, client):
        """Verify newest reviews appear first by injecting rows with explicit timestamps."""
        from datetime import datetime, timedelta
        from app import db, User, Review
        import bcrypt as _bcrypt

        with client.application.app_context():
            pw = _bcrypt.hashpw(b"PassU1word", _bcrypt.gensalt()).decode()
            u1 = User(username="u1_ord", password_hash=pw)
            u2 = User(username="u2_ord", password_hash=pw)
            db.session.add_all([u1, u2])
            db.session.flush()
            t_old = datetime(2024, 1, 1, 10, 0, 0)
            t_new = datetime(2024, 1, 1, 11, 0, 0)
            r1 = Review(text="Older review text ok", rating=3, resto_id=1, user_id=u1.id, anonymous=False, created_at=t_old)
            r2 = Review(text="Newer review text ok", rating=4, resto_id=1, user_id=u2.id, anonymous=False, created_at=t_new)
            db.session.add_all([r1, r2])
            db.session.commit()

        reviews = json.loads(client.get("/api/reviews/1").data)
        assert reviews[0]["author"] == "u2_ord"
        assert reviews[1]["author"] == "u1_ord"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. REVIEWS — EDIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestEditReview:
    def _get_review_id(self, c):
        reviews = json.loads(c.get("/api/reviews/1").data)
        return reviews[0]["id"]

    def test_edit_own_review(self, logged_in_client):
        post_review(logged_in_client)
        rid = self._get_review_id(logged_in_client)
        rv = logged_in_client.put(
            f"/api/reviews/{rid}",
            data=json.dumps({"text": "Updated review text here", "rating": 3, "anonymous": False}),
            content_type="application/json",
        )
        assert rv.status_code == 200
        updated = json.loads(logged_in_client.get("/api/reviews/1").data)
        assert updated[0]["rating"] == 3

    def test_edit_others_review_forbidden(self, client, registered_user):
        client.post("/login", data=registered_user)
        post_review(client)
        rid = self._get_review_id(client)
        client.get("/logout")
        client.post("/register", data={"username": "hacker", "password": "HackPass1", "confirm": "HackPass1"})
        client.post("/login", data={"username": "hacker", "password": "HackPass1"})
        rv = client.put(
            f"/api/reviews/{rid}",
            data=json.dumps({"text": "Hacked content here", "rating": 1, "anonymous": False}),
            content_type="application/json",
        )
        assert rv.status_code == 403

    def test_edit_with_invalid_rating(self, logged_in_client):
        post_review(logged_in_client)
        rid = self._get_review_id(logged_in_client)
        rv = logged_in_client.put(
            f"/api/reviews/{rid}",
            data=json.dumps({"text": "Valid text here ok", "rating": 10, "anonymous": False}),
            content_type="application/json",
        )
        assert rv.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 8. REVIEWS — DELETE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeleteReview:
    def _get_review_id(self, c):
        reviews = json.loads(c.get("/api/reviews/1").data)
        return reviews[0]["id"]

    def test_delete_own_review(self, logged_in_client):
        post_review(logged_in_client)
        rid = self._get_review_id(logged_in_client)
        rv = logged_in_client.delete(f"/api/reviews/{rid}")
        assert rv.status_code == 200
        assert json.loads(logged_in_client.get("/api/reviews/1").data) == []

    def test_delete_others_review_forbidden(self, client, registered_user):
        client.post("/login", data=registered_user)
        post_review(client)
        rid = self._get_review_id(client)
        client.get("/logout")
        client.post("/register", data={"username": "deleter", "password": "DelPass1x", "confirm": "DelPass1x"})
        client.post("/login", data={"username": "deleter", "password": "DelPass1x"})
        rv = client.delete(f"/api/reviews/{rid}")
        assert rv.status_code == 403

    def test_delete_nonexistent_review(self, logged_in_client):
        rv = logged_in_client.delete("/api/reviews/99999")
        assert rv.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 9. MY-REVIEW ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestMyReview:
    def test_my_review_none_before_posting(self, logged_in_client):
        rv = logged_in_client.get("/api/my-review/1")
        assert rv.status_code == 200
        assert json.loads(rv.data) is None

    def test_my_review_returns_review(self, logged_in_client):
        post_review(logged_in_client, text="My personal review text!", rating=4)
        rv = logged_in_client.get("/api/my-review/1")
        data = json.loads(rv.data)
        assert data["rating"] == 4

    def test_my_review_requires_login(self, client):
        rv = client.get("/api/my-review/1")
        assert rv.status_code == 302  # redirect to login


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        rv = client.get("/api/restaurants")
        assert rv.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        rv = client.get("/api/restaurants")
        assert rv.headers.get("X-Frame-Options") == "DENY"

    def test_csp_header_present(self, client):
        rv = client.get("/api/restaurants")
        assert "Content-Security-Policy" in rv.headers

    def test_referrer_policy(self, client):
        rv = client.get("/api/restaurants")
        assert rv.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ═══════════════════════════════════════════════════════════════════════════════
# 11. STATIC DATA INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestaurantsData:
    def test_all_restaurants_have_id(self):
        for r in RESTAURANTS:
            assert "id" in r and r["id"] > 0

    def test_all_restaurants_have_coordinates(self):
        for r in RESTAURANTS:
            assert -90 <= r["lat"] <= 90
            assert -180 <= r["lng"] <= 180

    def test_all_restaurants_have_hours(self):
        for r in RESTAURANTS:
            open_h, close_h = r["hours"]
            assert 0 <= open_h < close_h <= 24

    def test_all_ids_unique(self):
        ids = [r["id"] for r in RESTAURANTS]
        assert len(ids) == len(set(ids))

    def test_all_restaurants_have_multilang_desc(self):
        for r in RESTAURANTS:
            assert r.get("desc")
            assert r.get("desc_en")

    def test_restaurant_count(self):
        assert len(RESTAURANTS) == 20


# ═══════════════════════════════════════════════════════════════════════════════
# 12. CSRF TOKEN ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class TestCsrfToken:
    def test_csrf_token_endpoint_returns_token(self, client):
        rv = client.get("/api/csrf-token")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert "token" in data
        assert len(data["token"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 13. STATISTICS API
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatisticsAPI:
    def test_stats_endpoint_exists(self, client):
        rv = client.get("/api/stats")
        assert rv.status_code == 200

    def test_stats_total_restaurants(self, client):
        data = json.loads(client.get("/api/stats").data)
        assert data["total_restaurants"] == len(RESTAURANTS)

    def test_stats_total_reviews_zero_initially(self, client):
        data = json.loads(client.get("/api/stats").data)
        assert data["total_reviews"] == 0

    def test_stats_total_reviews_after_posting(self, logged_in_client):
        post_review(logged_in_client)
        data = json.loads(logged_in_client.get("/api/stats").data)
        assert data["total_reviews"] == 1

    def test_stats_top_rated_none_with_no_reviews(self, client):
        data = json.loads(client.get("/api/stats").data)
        assert data["top_rated"] is None

    def test_stats_top_rated_after_review(self, logged_in_client):
        post_review(logged_in_client, resto_id=1, rating=5)
        data = json.loads(logged_in_client.get("/api/stats").data)
        assert data["top_rated"]["id"] == 1

    def test_stats_cuisine_breakdown_present(self, client):
        data = json.loads(client.get("/api/stats").data)
        assert "cuisine_breakdown" in data
        assert isinstance(data["cuisine_breakdown"], dict)

    def test_stats_total_users_count(self, client, registered_user):
        data = json.loads(client.get("/api/stats").data)
        assert data["total_users"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 14. FAVOURITES API
# ═══════════════════════════════════════════════════════════════════════════════

class TestFavouritesAPI:
    def test_add_favourite_requires_login(self, client):
        rv = client.post("/api/favourites/1")
        assert rv.status_code == 302  # redirect to login

    def test_add_favourite_success(self, logged_in_client):
        rv = logged_in_client.post("/api/favourites/1")
        assert rv.status_code == 200
        assert json.loads(rv.data)["ok"] is True

    def test_get_favourites_empty(self, logged_in_client):
        rv = logged_in_client.get("/api/favourites")
        assert rv.status_code == 200
        assert json.loads(rv.data) == []

    def test_get_favourites_after_add(self, logged_in_client):
        logged_in_client.post("/api/favourites/1")
        data = json.loads(logged_in_client.get("/api/favourites").data)
        assert any(f["id"] == 1 for f in data)

    def test_remove_favourite(self, logged_in_client):
        logged_in_client.post("/api/favourites/1")
        rv = logged_in_client.delete("/api/favourites/1")
        assert rv.status_code == 200
        data = json.loads(logged_in_client.get("/api/favourites").data)
        assert data == []

    def test_add_invalid_restaurant_favourite(self, logged_in_client):
        rv = logged_in_client.post("/api/favourites/9999")
        assert rv.status_code == 400

    def test_add_duplicate_favourite_returns_ok(self, logged_in_client):
        logged_in_client.post("/api/favourites/1")
        rv = logged_in_client.post("/api/favourites/1")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert data.get("already") is True

    def test_remove_nonexistent_favourite(self, logged_in_client):
        rv = logged_in_client.delete("/api/favourites/1")
        assert rv.status_code == 404
