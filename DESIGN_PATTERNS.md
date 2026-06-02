# DESIGN_PATTERNS.md — RestoKyiv

## Summary

| # | Pattern | Category | File | Lines |
|---|---|---|---|---|
| 1 | Application Factory | Creational (Factory Method) | `app.py` | `create_app()` |
| 2 | Strategy | Behavioral | `app.py` | `_user_has_reviewed()`, route guards |
| 3 | Decorator | Structural | `app.py` | `@login_required`, `@after_request` |

---

## Pattern 1 — Application Factory (Factory Method)

### Category
Creational

### Which pattern
**Factory Method.** Instead of constructing the Flask application at module level, a `create_app(config=None)` function acts as the factory: it creates a new `Flask` instance, applies configuration, initialises extensions, and registers blueprints. Callers (the production entry-point and the test suite) receive a fully-configured application object without knowing its construction details.

### Problem it solves
Flask's extension objects (`db`, `bcrypt`, `csrf`, `limiter`) must be initialised *after* the application instance exists. Without the factory, tests that create a second app for an isolated in-memory SQLite database would conflict with the module-level production app. The factory makes it possible to spin up multiple, independent application instances—each with its own configuration—during the test run.

### Benefit (extensibility / decoupling)
- The test client fixture passes `{"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "WTF_CSRF_ENABLED": False}` to get an isolated environment without changing any production code.
- Adding a new environment (staging, CI, production) only requires a new config dict passed to `create_app`; no code changes elsewhere.

### UML Class Diagram

```
+---------------------------+
|       create_app()        |  <<Factory Method>>
|  config: dict | None      |
+---------------------------+
            |
            | creates
            v
+---------------------------+
|     Flask (app)           |
+---------------------------+
            |
            | initialises
            v
+-----+-----+-----+--------+
| db  |bcrypt|csrf |limiter |  <<Extension singletons>>
+-----+-----+-----+--------+
            |
            | registers
            v
+---------------------------+
|   Blueprint: main         |
+---------------------------+
```

### Reference
`app.py`, lines 1–40 (extension instantiation) and the `create_app` function body (extension `.init_app(app)` calls and `app.register_blueprint(main)`).

---

## Pattern 2 — Strategy (Swappable Validation / Guard Logic)

### Category
Behavioral

### Which pattern
**Strategy.** The application defines small, single-purpose validation functions (`validate_username`, `validate_password`, `sanitize`, `_user_has_reviewed`) that encapsulate a specific algorithm. Each route calls whichever validators it needs, and the validators can be swapped, extended, or tested in isolation without modifying the route code.

### Problem it solves
Without the Strategy pattern, validation logic would be duplicated inline across every route that accepts user input. For example, password strength rules would appear in both `/register` and (if added) `/change-password`. By extracting each rule into its own function, changes to the password policy only need to be made in one place.

### Benefit
- `validate_username` and `validate_password` are each tested independently in `TestValidateUsername` and `TestValidatePassword` (16 tests total).
- A different password policy (e.g., adding a special-character requirement) means adding one branch to `validate_password`—no route code changes.
- `_user_has_reviewed` encapsulates the duplicate-review detection strategy; the route simply calls it and acts on the boolean result.

### UML Class Diagram

```
+-----------------------------+
|        Route Handler        |
|  POST /api/reviews          |
+-----------------------------+
     |        |         |
     v        v         v
+--------+ +--------+ +-----------------+
|validate| |sanitize| |_user_has_reviewed|
|_username| |()      | |(user_id, resto) |
+--------+ +--------+ +-----------------+
  Strategy   Strategy      Strategy
```

### Reference
`app.py` — `validate_username()`, `validate_password()`, `sanitize()`, `_user_has_reviewed()` (helper functions section, lines ~55–80 in the refactored version).

---

## Pattern 3 — Decorator (Cross-cutting Concerns)

### Category
Structural

### Which pattern
**Decorator.** Two Python decorators wrap route functions to add behaviour without modifying the functions themselves:
1. `@login_required` — wraps any route that requires an authenticated session. If `user_id` is absent from the session it short-circuits with a 401 JSON response before the route body runs.
2. `@app.after_request` — wraps every response to inject HTTP security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`, `Referrer-Policy`).

### Problem it solves
Without decorators, every protected route would repeat the same `if "user_id" not in session: return abort(401)` guard — a textbook Duplicate Code smell. Similarly, security headers would have to be added manually to every response, making it easy to miss one. The Decorator pattern centralises these cross-cutting concerns in one place.

### Benefit
- Adding a new protected route requires only `@login_required`; the guard logic is maintained once.
- Security headers are guaranteed on *every* response (including error responses) because the `after_request` hook runs unconditionally.
- The decorator is tested in isolation in `TestSecurityHeaders` (4 tests) without needing to test it in every route.

### UML Class Diagram

```
+--------------------------+
|   login_required(f)      |  <<Decorator>>
|  wraps(f)                |
|  if no session → 401     |
|  else → f(*args,**kwargs)|
+--------------------------+
            |
            | decorates
            v
+---------------------------+
|  @main.route("/api/...")  |
|  def protected_route():   |
|      # actual logic       |
+---------------------------+

+--------------------------+
|  @app.after_request      |  <<Decorator>>
|  add_security_headers(r) |
|  r.headers[...] = ...    |
|  return r                |
+--------------------------+
            |
            | wraps every
            v
      [HTTP Response]
```

### Reference
`app.py` — `login_required` function (decorator definition) and `after_request` hook (security headers). Both in the Helpers section.
