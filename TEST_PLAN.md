# TEST_PLAN.md — RestoKyiv

## 1. Scope and Objectives

This test plan covers unit and integration testing of the RestoKyiv Flask web application.
The application provides restaurant listings, user authentication, reviews, favourites, and statistics.
Testing targets the Python back-end (`app.py`) exclusively; front-end JavaScript and HTML templates are out of scope.

**Coverage target:** ≥ 70% line coverage of `app.py`, measured by `pytest-cov`.

---

## 2. Testing Framework and Tools

| Tool | Purpose |
|---|---|
| `pytest` | Test runner and fixture management |
| `pytest-cov` | Line and branch coverage reporting |
| Flask test client | HTTP-level integration without a running server |
| SQLite in-memory | Isolated per-test database (no file I/O) |

Run tests and generate coverage:
```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 3. Test Structure

```
tests/
├── __init__.py
└── test_app.py      # All test classes, ~590 lines
```

Tests are organised into classes that map one-to-one with application concerns:

| Class | Responsibility |
|---|---|
| `TestValidateUsername` | Black-box: username validation rules |
| `TestValidatePassword` | Black-box: password validation rules |
| `TestSanitize` | White-box: HTML escaping and truncation |
| `TestRegister` | Black-box: registration endpoint |
| `TestLoginLogout` | Black-box: authentication lifecycle |
| `TestRestaurantsAPI` | Black-box: `/api/restaurants` endpoint |
| `TestPostReview` | Black-box: review creation, validation, deduplication |
| `TestGetReviews` | Black-box: review retrieval and ownership flags |
| `TestEditReview` | Black-box: review update, authorisation |
| `TestDeleteReview` | Black-box: review deletion, authorisation |
| `TestMyReview` | Black-box: per-user review query |
| `TestSecurityHeaders` | White-box: HTTP security header middleware |
| `TestRestaurantsData` | White-box: integrity of `RESTAURANTS` static data |
| `TestCsrfToken` | Black-box: CSRF token endpoint |
| `TestStatisticsAPI` | Black-box: `/api/stats` aggregation |
| `TestFavouritesAPI` | Black-box: favourites CRUD |

---

## 4. Black-Box Tests

Black-box tests are derived from the **external specification** (API contracts, validation rules, HTTP status codes) without knowledge of internal implementation. The tester only observes inputs and outputs.

### BB-01 — Valid username accepted
**Input:** `"john_doe99"` → `validate_username` returns `None` (no error).

### BB-02 — Username too short rejected
**Input:** `"ab"` (2 chars) → error message returned.

### BB-03 — Weak password (no uppercase) rejected
**Input:** `"password1"` → error returned.

### BB-04 — Registration duplicate username rejected
A second `POST /register` with the same username returns HTTP 200 with an error flash (no duplicate user created).

### BB-05 — Login with wrong password rejected
`POST /login` with correct username but wrong password → redirect back to login, no session created.

### BB-06 — Review post requires authentication
`POST /api/reviews` without a session → HTTP 401 returned.

### BB-07 — Rating out of range rejected
`POST /api/reviews` with `rating=0` or `rating=6` → HTTP 400 returned.

### BB-08 — Duplicate review rejected
A second review by the same user for the same restaurant → HTTP 409 returned.

### BB-09 — Statistics endpoint: review count increments
`GET /api/stats` returns `total_reviews: 0` before posting, then `total_reviews: 1` after.

### BB-10 — Favourite requires authentication
`POST /api/favourites` without session → HTTP 401 returned.

### BB-11 — Invalid restaurant favourite rejected
`POST /api/favourites` with a non-existent `resto_id` → HTTP 404 returned.

### BB-12 — Anonymous review hides author
`POST /api/reviews` with `anonymous: true` → GET response returns `"author": "Анонім"`, not the real username.

---

## 5. White-Box Tests

White-box tests are derived from **code structure** — branches, conditions, and internal state — to achieve branch coverage of helper functions and middleware.

### WB-01 — `sanitize`: HTML entities escaped
**Technique:** Statement coverage of the `html.escape` call.
`sanitize("<script>")` → `"&lt;script&gt;"`.

### WB-02 — `sanitize`: truncation at custom max_len
**Technique:** Branch coverage — the slice `[:max_len]` branch where `len > max_len`.
`sanitize("x" * 600, max_len=10)` → 10-character string.

### WB-03 — `sanitize`: whitespace stripped before truncation
**Technique:** Statement coverage — `text.strip()` is always called before slicing.

### WB-04 — `validate_username`: exact boundary min (3 chars) passes
**Technique:** Boundary value — hits the `len >= 3` branch exactly.

### WB-05 — `validate_username`: exact boundary max (32 chars) passes
**Technique:** Boundary value — hits the `len <= 32` branch exactly.

### WB-06 — `validate_password`: exactly 8 chars valid
**Technique:** Branch coverage — `len(p) < 8` is False at length 8.

### WB-07 — Security headers middleware: all four headers present
**Technique:** Statement coverage of the `after_request` hook; each `response.headers[...] = ...` line is executed.
Four assertions: `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Referrer-Policy`.

### WB-08 — `RESTAURANTS` data integrity: all IDs unique
**Technique:** Path coverage of data-loading logic — verifies no ID appears twice in the static list.

### WB-09 — `RESTAURANTS` data integrity: all entries have multilingual descriptions
**Technique:** Statement coverage — iterates all restaurants, asserts `desc`, `desc_en`, `desc_ru` keys are present.

### WB-10 — Average rating calculation: mean of multiple values
**Technique:** Branch coverage — the averaging branch is only reached when `len(reviews) > 0`; two reviews with ratings 3 and 5 must yield average 4.0.

---

## 6. Coverage Strategy

- **Target:** ≥ 70% line coverage of `app.py`.
- **Excluded:** Flask template rendering paths (these require a real browser context); Docker-only startup code in `if __name__ == "__main__"`.
- **Measurement:** `pytest --cov=app --cov-report=term-missing` after every CI run.
- The coverage XML artifact is uploaded in CI for audit.

---

## 7. Test Isolation

Each test uses a fresh in-memory SQLite database created by the `client` fixture:
```python
@pytest.fixture
def client():
    test_app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", ...})
    with test_app.app_context():
        db.create_all()
        yield test_app.test_client()
        db.drop_all()
```
CSRF protection is disabled in tests (`WTF_CSRF_ENABLED: False`).
Rate limiting is disabled (`RATELIMIT_ENABLED: False`).
No test shares state with another.
