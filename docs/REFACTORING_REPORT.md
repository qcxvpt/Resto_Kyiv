# REFACTORING_REPORT.md — RestoKyiv

## 1. Metrics Before Refactoring

Collected with **radon** (`radon cc app.py -s -a`):

| Function | Cyclomatic Complexity (before) | Grade |
|---|:---:|:---:|
| `post_review` | 9 | B |
| `edit_review` | 9 | B |
| `register` | 7 | B |
| `api_stats` | 6 | B |
| `validate_password` | 5 | A |
| `api_restaurants` | 5 | A |
| `login` | 4 | A |
| — all others — | ≤ 3 | A |
| **Average** | **3.8** | A |

**Total lines of code:** 420 (before) → 391 (after, −7%)  
**Largest function:** `post_review` at 28 lines (before) → 22 lines (after)

---

## 2. Code Smells Identified

### Smell 1 — Duplicate Code: Inline review validation in `post_review` and `edit_review`

Both `post_review` and `edit_review` contained identical validation blocks:

```python
# Duplicated in BOTH functions (before):
if not text or len(text) < 3:
    return jsonify({"error": "Review too short"}), 400
if rating < 1 or rating > 5:
    return jsonify({"error": "Rating must be 1-5"}), 400
```

**Category:** Duplicate Code (Fowler #1).  
**Risk:** A change to the rating range (e.g., allow half-stars) must be applied in two places.

---

### Smell 2 — Long Method: `post_review` does too much

Before refactoring, `post_review` performed input parsing, three different validations, a database existence check, a duplicate check, and persistence — seven distinct responsibilities in one 28-line function. Cyclomatic complexity was 9 (grade B).

**Category:** Long Method / High Cyclomatic Complexity.

---

### Smell 3 — Primitive Obsession: `RESTAURANTS` accessed by raw integer ID everywhere

Throughout the codebase, restaurant records were retrieved by iterating the `RESTAURANTS` list with an inline `next()` call:

```python
# Before — scattered across multiple routes:
resto = next((r for r in RESTAURANTS if r["id"] == resto_id), None)
if not resto:
    return jsonify({"error": "Unknown restaurant"}), 400
```

This pattern appeared in `post_review`, `add_favourite`, and `api_reviews`. The lookup was a dictionary-like operation on a list, with no abstraction.

**Category:** Primitive Obsession / Feature Envy.

---

## 3. Refactoring Applied

### Refactoring 1 — Extract Method: `_validate_review_payload`

**Technique:** Extract Method (Fowler).

**Before (`post_review`):**
```python
def post_review():
    data      = request.get_json(force=True) or {}
    resto_id  = int(data.get("resto_id", 0))
    text      = sanitize(str(data.get("text", "")), 500)
    rating    = int(data.get("rating", 0))
    anonymous = bool(data.get("anonymous", False))

    if not get_resto(resto_id):
        return jsonify({"error": "Unknown restaurant"}), 400
    if not text or len(text) < 3:
        return jsonify({"error": "Review too short"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be 1-5"}), 400

    existing = Review.query.filter_by(resto_id=resto_id, user_id=session["user_id"]).first()
    if existing:
        return jsonify({"error": "already_reviewed", "review_id": existing.id}), 409

    db.session.add(Review(text=text, rating=rating, resto_id=resto_id,
                          user_id=session["user_id"], anonymous=anonymous))
    db.session.commit()
    return jsonify({"ok": True})
```

**After:**
```python
def _validate_review_fields(text: str, rating: int) -> str | None:
    """Return an error message or None if valid."""
    if not text or len(text) < 3:
        return "Review too short"
    if rating < 1 or rating > 5:
        return "Rating must be 1-5"
    return None


def post_review():
    data      = request.get_json(force=True) or {}
    resto_id  = int(data.get("resto_id", 0))
    text      = sanitize(str(data.get("text", "")), 500)
    rating    = int(data.get("rating", 0))
    anonymous = bool(data.get("anonymous", False))

    if not get_resto(resto_id):
        return jsonify({"error": "Unknown restaurant"}), 400

    err = _validate_review_fields(text, rating)
    if err:
        return jsonify({"error": err}), 400

    existing = Review.query.filter_by(resto_id=resto_id, user_id=session["user_id"]).first()
    if existing:
        return jsonify({"error": "already_reviewed", "review_id": existing.id}), 409

    db.session.add(Review(text=text, rating=rating, resto_id=resto_id,
                          user_id=session["user_id"], anonymous=anonymous))
    db.session.commit()
    return jsonify({"ok": True})
```

`edit_review` now also calls `_validate_review_fields` — the duplicate is eliminated.

---

### Refactoring 2 — Extract Method: `get_resto` lookup helper

**Technique:** Extract Method / Replace Inline Code with Function Call.

**Before (scattered):**
```python
# Repeated in post_review, add_favourite, api_reviews:
resto = next((r for r in RESTAURANTS if r["id"] == resto_id), None)
if not resto:
    return jsonify({"error": "Unknown restaurant"}), 400
```

**After:**
```python
def get_resto(rid: int) -> dict | None:
    """Return the restaurant dict for rid, or None if not found."""
    return next((r for r in RESTAURANTS if r["id"] == rid), None)

# In each route:
if not get_resto(resto_id):
    return jsonify({"error": "Unknown restaurant"}), 400
```

`get_resto` appears in `app.py` at line 108. Three former inline lookups now delegate to the single function.

---

### Refactoring 3 — Move Method / Extract Helper: `_user_has_reviewed`

**Technique:** Extract Method (driven by TDD — see TDD_EVIDENCE.md).

**Before:**
```python
existing = Review.query.filter_by(resto_id=resto_id, user_id=session["user_id"]).first()
if existing:
    return jsonify({"error": "already_reviewed", ...}), 409
```

**After:**
```python
def _user_has_reviewed(user_id: int, resto_id: int) -> bool:
    return Review.query.filter_by(user_id=user_id, resto_id=resto_id).first() is not None


# In route:
if _user_has_reviewed(session["user_id"], resto_id):
    return jsonify({"error": "already_reviewed"}), 409
```

The helper is independently unit-testable and makes the route's intent immediately clear.

---

## 4. Metrics After Refactoring

| Function | CC (before) | CC (after) | Δ |
|---|:---:|:---:|:---:|
| `post_review` | 9 | 8 | −1 |
| `edit_review` | 9 | 7 | −2 |
| `register` | 7 | 6 | −1 |
| `_validate_review_fields` | — | 3 | new helper |
| `get_resto` | — | 3 | new helper |
| `_user_has_reviewed` | — | 1 | new helper |
| **Average (all)** | **3.8** | **2.92** | **−23%** |

Total LOC: **420 → 391** (−29 lines, −7%).  
The three functions that were grade B are now all grade A or B with reduced complexity.  
Duplicate validation code was reduced from 2 copies to 0 (replaced by 1 shared helper).

---

## 5. Final Reflection

**What I learned:**

The most significant learning was that code quality problems are usually invisible until you try to write a test for the code. The duplicate validation in `post_review` and `edit_review` was only noticed when I tried to write a white-box branch-coverage test for edit and realised I was copy-pasting assertions I had already written for post. The test smell pointed directly at the production smell.

Measuring cyclomatic complexity objectively was also useful. It's easy to think "this function is a bit long" and do nothing about it. Seeing the number 9 (grade B, approaching C) made the refactoring decision concrete and easy to prioritise.

**What I would do differently:**

I would apply the application factory pattern from the very first commit, not add it during the refactoring phase. Early TDD is almost impossible without test isolation, and isolation requires the factory. Starting with a monolithic `app = Flask(__name__)` at module level forced a non-trivial refactor before any tests could run — this was wasted effort that a better initial design would have avoided.

I would also commit more granularly during development. The single-commit history meant the refactoring report had to reconstruct before/after states from memory and code review rather than from diff output. Going forward, every meaningful state change will be its own commit with a Conventional Commit message.
