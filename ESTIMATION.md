# ESTIMATION.md — RestoKyiv

## Estimation Approach

Story points use the Fibonacci scale (1, 2, 3, 5, 8, 13). One point ≈ roughly one focused hour of work for this developer at this skill level. Estimates were made *before* implementation; actuals were recorded after each feature was complete.

---

## User Stories and Estimates

| # | User Story | Estimate (SP) | Actual (SP) | Notes |
|---|---|:---:|:---:|---|
| US-01 | As a visitor, I can view a list of Kyiv restaurants on a map so I can discover places near me. | 5 | 8 | Leaflet.js integration took longer than expected; marker clustering required extra research. |
| US-02 | As a visitor, I can filter restaurants by cuisine type so I only see relevant options. | 2 | 2 | Straightforward front-end filter on static data. |
| US-03 | As a visitor, I can see a restaurant's average rating before reading reviews so I can make a quick decision. | 3 | 3 | Required a SQL aggregate; wired into `/api/restaurants` response. |
| US-04 | As a new user, I can register with a username and password so I can leave reviews. | 3 | 5 | Added bcrypt hashing, validation, CSRF protection, and duplicate-username handling — more than anticipated. |
| US-05 | As a registered user, I can log in and out so my session is persistent. | 2 | 2 | Standard Flask session; straightforward. |
| US-06 | As a logged-in user, I can post a review (text + rating) for a restaurant so other users can benefit from my experience. | 5 | 5 | Included duplicate-review guard (TDD feature) and input sanitisation. |
| US-07 | As a logged-in user, I can edit my own review so I can correct mistakes. | 2 | 3 | Authorisation check and partial-update logic added extra complexity. |
| US-08 | As a logged-in user, I can delete my own review so I can remove outdated opinions. | 1 | 1 | Simple DELETE route with ownership check. |
| US-09 | As a logged-in user, I can post a review anonymously so my identity is not revealed. | 2 | 2 | Boolean flag on the model; minimal extra work. |
| US-10 | As a logged-in user, I can save restaurants as favourites so I can find them later. | 3 | 3 | Unique constraint on `(user_id, resto_id)` to prevent duplicates. |
| US-11 | As any visitor, I can view aggregate statistics (total restaurants, reviews, top-rated) so I understand the platform at a glance. | 3 | 4 | Cuisine breakdown required grouping query; slightly more than estimated. |
| US-12 | As a developer, I need a CI pipeline (lint + tests + Docker build) so quality is enforced automatically. | 5 | 8 | Docker Hub push, matrix Python versions, coverage upload, and fixing one flake8 issue consumed extra time. |
| US-13 | As a developer, I need HTTP security headers on every response so the app follows OWASP best practices. | 1 | 1 | Single `after_request` hook. |
| US-14 | As a developer, I need rate limiting on auth endpoints so brute-force attacks are mitigated. | 2 | 2 | Flask-Limiter integration with per-route overrides. |

**Total estimated:** 39 SP  
**Total actual:** 49 SP  
**Variance:** +10 SP (+26%)

---

## Reflection on Estimation Accuracy

The overall estimate was 26% below actual effort — a common pattern for student projects.

**What went over budget:**
- **US-01 (Map integration, +3 SP):** Underestimated the complexity of Leaflet.js configuration, tile-layer attribution, and the geolocation fallback. External JavaScript libraries always carry hidden integration cost.
- **US-04 (Registration, +2 SP):** Security work (bcrypt, CSRF, validation edge cases) expanded the scope from "make a form" to "make a secure form."
- **US-12 (CI pipeline, +3 SP):** The Docker build job introduced secrets management and GHCR authentication that were not accounted for in the initial estimate. Debugging the `if: github.event_name == 'push'` condition guard took a full hour.

**What was accurate:**
- CRUD features (US-07, US-08, US-09, US-10, US-13, US-14) hit their estimates almost exactly because the application factory was already set up and the pattern was repetitive.

**What I would do differently:**
- Add a 30% buffer to any story involving a new external library or service (maps, CI providers, Docker registries).
- Split US-01 into two stories: "Static restaurant list on page" (1 SP) and "Interactive Leaflet map with geolocation" (5 SP). The compound story masked complexity.
- Timebox research spikes to 1 SP each, separate from implementation.
