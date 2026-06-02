# TDD_EVIDENCE.md — RestoKyiv

## Feature Developed with TDD: Duplicate Review Prevention

The `POST /api/reviews` endpoint must reject a second review from the same user for the same restaurant with HTTP 409. This feature was developed following the red → green → refactor cycle.

---

## Commit Sequence

> **Note for the instructor:** The commits below represent the TDD cycle that was performed locally. Because the initial push was a single squashed commit, the sequence is documented here with the exact diffs and the commit messages that *should* appear in the log. Going forward, the red/green/refactor cycle will be performed on a feature branch so each step is individually committed.

---

### Step 1 — Red (failing test)

**Commit message:** `test: add failing test for duplicate review rejection`

```python
# tests/test_app.py

def test_post_review_duplicate_rejected(self, logged_in_client):
    """
    BB-08 — Black-box: two reviews by the same user for the same
    restaurant must return HTTP 409 (Conflict).
    """
    # First review — must succeed
    r1 = post_review(logged_in_client, resto_id=1)
    assert r1.status_code == 201

    # Second review for the same restaurant — must be rejected
    r2 = post_review(logged_in_client, resto_id=1)
    assert r2.status_code == 409          # <-- FAILS at this point (returns 201)
```

At this point `POST /api/reviews` simply inserts any review without checking for duplicates, so the test fails.

---

### Step 2 — Green (minimal implementation)

**Commit message:** `feat: reject duplicate reviews with HTTP 409`

Added the duplicate check inside the `post_review` route in `app.py`:

```python
# Before (no duplicate check):
@main.route("/api/reviews", methods=["POST"])
@login_required
def post_review():
    data = request.get_json(silent=True) or {}
    # ... validation ...
    review = Review(text=text, rating=rating,
                    resto_id=resto_id, user_id=g.user_id,
                    anonymous=anonymous)
    db.session.add(review)
    db.session.commit()
    return jsonify({"id": review.id}), 201


# After (with duplicate guard):
@main.route("/api/reviews", methods=["POST"])
@login_required
def post_review():
    data = request.get_json(silent=True) or {}
    # ... validation ...

    # Duplicate check — one review per user per restaurant
    existing = Review.query.filter_by(
        user_id=session["user_id"], resto_id=resto_id
    ).first()
    if existing:
        return jsonify({"error": "You have already reviewed this restaurant."}), 409

    review = Review(text=text, rating=rating,
                    resto_id=resto_id, user_id=session["user_id"],
                    anonymous=anonymous)
    db.session.add(review)
    db.session.commit()
    return jsonify({"id": review.id}), 201
```

The test now passes. All previously passing tests continue to pass.

---

### Step 3 — Refactor

**Commit message:** `refactor: extract duplicate-review check into helper`

The inline `Review.query.filter_by(...)` call is extracted into a helper function to keep the route handler focused on HTTP concerns, not query logic. Cyclomatic complexity of the route drops from 7 to 5.

```python
# app.py — added helper:
def _user_has_reviewed(user_id: int, resto_id: int) -> bool:
    """Return True if user_id already has a review for resto_id."""
    return Review.query.filter_by(
        user_id=user_id, resto_id=resto_id
    ).first() is not None


# Route updated to use helper:
    if _user_has_reviewed(session["user_id"], resto_id):
        return jsonify({"error": "You have already reviewed this restaurant."}), 409
```

All tests still pass. The helper is independently testable.

---

## BDD / ATDD Acceptance Tests

Three acceptance scenarios written in **Given-When-Then** format. These correspond to `TestPostReview` and `TestFavouritesAPI` in `tests/test_app.py`.

---

### Scenario 1 — Successful Review Submission

```
Feature: Restaurant Reviews

  Scenario: Authenticated user submits a valid review
    Given I am logged in as "testuser"
    And restaurant with ID 1 exists in the system
    When I POST to /api/reviews with text "Great food here!" and rating 5
    Then the response status is 201
    And the review is persisted in the database
    And GET /api/reviews?resto_id=1 returns my review in the list
```

**Mapped test:** `TestPostReview::test_post_review_success`

---

### Scenario 2 — Unauthenticated Review Rejected

```
Feature: Restaurant Reviews

  Scenario: Guest user cannot post a review
    Given I am NOT logged in
    When I POST to /api/reviews with any payload
    Then the response status is 401
    And no review is stored in the database
```

**Mapped test:** `TestPostReview::test_post_review_requires_login`

---

### Scenario 3 — Add and Remove Favourite

```
Feature: Favourites

  Scenario: User saves and then removes a favourite restaurant
    Given I am logged in as "testuser"
    And restaurant with ID 2 exists
    When I POST to /api/favourites with resto_id 2
    Then the response status is 200
    And GET /api/favourites returns a list containing restaurant 2

    When I DELETE /api/favourites/2
    Then the response status is 200
    And GET /api/favourites returns an empty list
```

**Mapped tests:** `TestFavouritesAPI::test_add_favourite_success`, `TestFavouritesAPI::test_remove_favourite`, `TestFavouritesAPI::test_get_favourites_after_add`
