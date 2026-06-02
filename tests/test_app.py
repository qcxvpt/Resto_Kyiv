"""
Unit tests for RestoKyiv Flask application.
"""

import json
import pytest
from app import create_app
from src.extensions import db
from src.models.user import User
from src.models.review import Review
from src.models.favourite import Favourite
from src.utils import sanitize, validate_username, validate_password
from src.data import RESTAURANTS


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    test_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        "RATELIMIT_ENABLED": False,
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
    def test_valid_username(self):        assert validate_username("john_doe99") is None
    def test_too_short(self):             assert validate_username("ab") is not None
    def test_too_long(self):              assert validate_username("a" * 33) is not None
    def test_empty(self):                 assert validate_username("") is not None
    def test_none(self):                  assert validate_username(None) is not None
    def test_special_chars_rejected(self): assert validate_username("bad user!") is not None
    def test_exact_min_length(self):      assert validate_username("abc") is None
    def test_exact_max_length(self):      assert validate_username("a" * 32) is None


class TestValidatePassword:
    def test_valid_password(self):        assert validate_password("Secure99") is None
    def test_too_short(self):             assert validate_password("Ab1") is not None
    def test_no_uppercase(self):          assert validate_password("password1") is not None
    def test_no_digit(self):              assert validate_password("Password") is not None
    def test_empty(self):                 assert validate_password("") is not None
    def test_none(self):                  assert validate_password(None) is not None
    def test_exactly_8_chars_valid(self): assert validate_password("Abcdef1!") is None


class TestSanitize:
    def test_strips_html(self):       assert "&lt;script&gt;" in sanitize("<script>")
    def test_truncates(self):         assert len(sanitize("x" * 1000, 100)) == 100
    def test_strips_whitespace(self): assert sanitize("  hello  ") == "hello"
    def test_default_max_500(self):   assert len(sanitize("x" * 600)) == 500


# ═══════════════════════════════════════════════════════════════════════════════
# 2. REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegister:
    def test_register_success(self, client):
        rv = client.post("/register", data={"username": "newuser", "password": "Password1", "confirm": "Password1"})
        assert rv.status_code in (200, 302)

    def test_register_duplicate_username(self, client, registered_user):
        rv = client.post("/register", data={"username": "testuser", "password": "Password1", "confirm": "Password1"})
        assert b"already taken" in rv.data

    def test_register_password_mismatch(self, client):
        rv = client.post("/register", data={"username": "newuser2", "password": "Password1", "confirm": "WrongPass1"})
        assert b"match" in rv.data

    def test_register_weak_password(self, client):
        rv = client.post("/register", data={"username": "newuser3", "password": "weakpass", "confirm": "weakpass"})
        assert rv.status_code == 200

    def test_register_bad_username(self, client):
        rv = client.post("/register", data={"username": "ab", "password": "Password1", "confirm": "Password1"})
        assert rv.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LOGIN / LOGOUT
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginLogout:
    def test_login_success(self, client, registered_user):
        rv = client.post("/login", data=registered_user)
        assert rv.status_code == 302

    def test_login_wrong_password(self, client, registered_user):
        rv = client.post("/login", data={"username": "testuser", "password": "WrongPass9"})
        assert b"Invalid" in rv.data

    def test_login_nonexistent_user(self, client):
        rv = client.post("/login", data={"username": "ghost", "password": "Password1"})
        assert b"Invalid" in rv.data

    def test_logout_requires_login(self, client):
        rv = client.get("/logout")
        assert rv.status_code == 302

    def test_logout_clears_session(self, logged_in_client):
        logged_in_client.get("/logout")
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
            for field in ("id", "name", "lat", "lng", "avg_rating", "review_count"):
                assert field in r

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
        assert rv.status_code == 302

    def test_post_review_invalid_rating_zero(self, logged_in_client):
        assert post_review(logged_in_client, rating=0).status_code == 400

    def test_post_review_invalid_rating_six(self, logged_in_client):
        assert post_review(logged_in_client, rating=6).status_code == 400

    def test_post_review_text_too_short(self, logged_in_client):
        assert post_review(logged_in_client, text="ok").status_code == 400

    def test_post_review_unknown_restaurant(self, logged_in_client):
        assert post_review(logged_in_client, resto_id=9999).status_code == 400

    def test_post_review_duplicate_rejected(self, logged_in_client):
        post_review(logged_in_client)
        assert post_review(logged_in_client).status_code == 409

    def test_post_anonymous_review(self, logged_in_client):
        post_review(logged_in_client, anonymous=True)
        reviews = json.loads(logged_in_client.get("/api/reviews/1").data)
        assert reviews[0]["author"] == "Anonymous"

    def test_post_named_review_shows_username(self, logged_in_client):
        post_review(logged_in_client, anonymous=False)
        reviews = json.loads(logged_in_client.get("/api/reviews/1").data)
        assert reviews[0]["author"] == "testuser"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. REVIEWS — EDIT / DELETE
# ═══════════════════════════════════════════════════════════════════════════════

class TestEditReview:
    def _get_review_id(self, c):
        return json.loads(c.get("/api/reviews/1").data)[0]["id"]

    def test_edit_own_review(self, logged_in_client):
        post_review(logged_in_client)
        rid = self._get_review_id(logged_in_client)
        rv = logged_in_client.put(
            f"/api/reviews/{rid}",
            data=json.dumps({"text": "Updated review text here", "rating": 3, "anonymous": False}),
            content_type="application/json",
        )
        assert rv.status_code == 200

    def test_edit_others_review_forbidden(self, client, registered_user):
        client.post("/login", data=registered_user)
        post_review(client)
        rid = json.loads(client.get("/api/reviews/1").data)[0]["id"]
        client.get("/logout")
        client.post("/register", data={"username": "hacker", "password": "HackPass1", "confirm": "HackPass1"})
        client.post("/login", data={"username": "hacker", "password": "HackPass1"})
        rv = client.put(f"/api/reviews/{rid}",
                        data=json.dumps({"text": "Hacked content here", "rating": 1, "anonymous": False}),
                        content_type="application/json")
        assert rv.status_code == 403


class TestDeleteReview:
    def test_delete_own_review(self, logged_in_client):
        post_review(logged_in_client)
        rid = json.loads(logged_in_client.get("/api/reviews/1").data)[0]["id"]
        assert logged_in_client.delete(f"/api/reviews/{rid}").status_code == 200

    def test_delete_nonexistent_review(self, logged_in_client):
        assert logged_in_client.delete("/api/reviews/99999").status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 7. STATISTICS API
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatisticsAPI:
    def test_stats_endpoint_exists(self, client):
        assert client.get("/api/stats").status_code == 200

    def test_stats_total_restaurants(self, client):
        data = json.loads(client.get("/api/stats").data)
        assert data["total_restaurants"] == len(RESTAURANTS)

    def test_stats_total_reviews_zero_initially(self, client):
        assert json.loads(client.get("/api/stats").data)["total_reviews"] == 0

    def test_stats_top_rated_none_with_no_reviews(self, client):
        assert json.loads(client.get("/api/stats").data)["top_rated"] is None

    def test_stats_top_rated_after_review(self, logged_in_client):
        post_review(logged_in_client, resto_id=1, rating=5)
        assert json.loads(logged_in_client.get("/api/stats").data)["top_rated"]["id"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 8. FAVOURITES API
# ═══════════════════════════════════════════════════════════════════════════════

class TestFavouritesAPI:
    def test_add_favourite_requires_login(self, client):
        assert client.post("/api/favourites/1").status_code == 302

    def test_add_favourite_success(self, logged_in_client):
        rv = logged_in_client.post("/api/favourites/1")
        assert rv.status_code == 200
        assert json.loads(rv.data)["ok"] is True

    def test_get_favourites_empty(self, logged_in_client):
        assert json.loads(logged_in_client.get("/api/favourites").data) == []

    def test_get_favourites_after_add(self, logged_in_client):
        logged_in_client.post("/api/favourites/1")
        data = json.loads(logged_in_client.get("/api/favourites").data)
        assert any(f["id"] == 1 for f in data)

    def test_remove_favourite(self, logged_in_client):
        logged_in_client.post("/api/favourites/1")
        assert logged_in_client.delete("/api/favourites/1").status_code == 200
        assert json.loads(logged_in_client.get("/api/favourites").data) == []

    def test_add_invalid_restaurant(self, logged_in_client):
        assert logged_in_client.post("/api/favourites/9999").status_code == 400

    def test_add_duplicate_favourite_returns_ok(self, logged_in_client):
        logged_in_client.post("/api/favourites/1")
        rv = logged_in_client.post("/api/favourites/1")
        assert json.loads(rv.data).get("already") is True


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        assert client.get("/api/restaurants").headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        assert client.get("/api/restaurants").headers.get("X-Frame-Options") == "DENY"

    def test_csp_header_present(self, client):
        assert "Content-Security-Policy" in client.get("/api/restaurants").headers

    def test_referrer_policy(self, client):
        assert client.get("/api/restaurants").headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. STATIC DATA INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestRestaurantsData:
    def test_all_restaurants_have_id(self):
        for r in RESTAURANTS: assert "id" in r and r["id"] > 0

    def test_all_restaurants_have_coordinates(self):
        for r in RESTAURANTS:
            assert -90 <= r["lat"] <= 90
            assert -180 <= r["lng"] <= 180

    def test_all_ids_unique(self):
        ids = [r["id"] for r in RESTAURANTS]
        assert len(ids) == len(set(ids))

    def test_all_restaurants_have_multilang_desc(self):
        for r in RESTAURANTS:
            assert r.get("desc") and r.get("desc_en")

    def test_restaurant_count(self):
        assert len(RESTAURANTS) == 20
