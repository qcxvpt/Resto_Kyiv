"""
RestoKyiv — Flask restaurant guide for Kyiv.
Refactored with application-factory pattern for proper test isolation.
AI-assisted: factory pattern, Favourite model, stats/favourites endpoints suggested by Claude.
"""

import os
import re
import html
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Extension objects — initialised later inside create_app()
db = SQLAlchemy()
bcrypt = Bcrypt()
csrf = CSRFProtect()
limiter = Limiter(get_remote_address, default_limits=["300 per day"])

# ─── Models ──────────────────────────────────────────────────────────────────


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    reviews = db.relationship(
        "Review", backref="author", lazy=True, cascade="all, delete-orphan"
    )


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    resto_id = db.Column(db.Integer, nullable=False)
    anonymous = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Favourite(db.Model):
    """User's saved / favourite restaurants."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    resto_id = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "resto_id",
            name="uq_user_resto"),
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

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
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)

    return decorated


# ─── Restaurant data ─────────────────────────────────────────────────────────

RESTAURANTS = [{"id": 1,
                "name": "Kanapa",
                "lat": 50.4547,
                "lng": 30.5238,
                "cuisine": "Українська",
                "address": "вул. Андріївський узвіз, 19",
                "url": "https://kanapa-restaurant.com.ua",
                "hours": [12,
                          23],
                "schedule": "all",
                "desc": "Відомий ресторан української кухні з автентичними стравами та стильним інтер'єром на Андріївському узвозі.",
                "desc_en": "Famous Ukrainian cuisine restaurant with authentic dishes and a stylish interior on Andriyivsky Uzviz.",
                "desc_ru": "Известный ресторан украинской кухни с аутентичными блюдами и стильным интерьером на Андреевском спуске.",
                },
               {"id": 2,
                "name": "Osteria Pantagruel",
                "lat": 50.4530,
                "lng": 30.5201,
                "cuisine": "Італійська",
                "address": "вул. Lva Tolstoho, 1",
                "url": "https://pantagruel.ua",
                "hours": [12,
                          23],
                "schedule": "all",
                "desc": "Вишукана остерія з класичною італійською кухнею, свіжою пастою та великим вибором вин.",
                "desc_en": "Refined osteria with classic Italian cuisine, fresh pasta and an extensive wine selection.",
                "desc_ru": "Изысканная остерия с классической итальянской кухней, свежей пастой и большим выбором вин.",
                },
               {"id": 3,
                "name": "Hutorok na Dnipri",
                "lat": 50.4602,
                "lng": 30.5180,
                "cuisine": "Українська",
                "address": "пров. Ланцюгова, 1",
                "url": "https://hutoroky.com.ua",
                "hours": [10,
                          22],
                "schedule": "all",
                "desc": "Затишний ресторан з видом на Дніпро, домашньою українською їжею та живою музикою у вихідні.",
                "desc_en": "Cozy restaurant with a Dnipro view, homestyle Ukrainian food and live music on weekends.",
                "desc_ru": "Уютный ресторан с видом на Днепр, домашней украинской едой и живой музыкой по выходным.",
                },
               {"id": 4,
                "name": "The Burger",
                "lat": 50.4461,
                "lng": 30.5234,
                "cuisine": "Американська",
                "address": "вул. Baseina, 1/2",
                "url": "https://theburger.ua",
                "hours": [10,
                          22],
                "schedule": "all",
                "desc": "Культовий бургер-бар з крафтовими бургерами, хрусткою картоплею фрі та великим вибором крафтового пива.",
                "desc_en": "Cult burger bar with craft burgers, crispy fries and a wide selection of craft beer.",
                "desc_ru": "Культовый бургер-бар с крафтовыми бургерами, хрустящей картошкой фри и большим выбором крафтового пива.",
                },
               {"id": 5,
                "name": "Tarantino Family",
                "lat": 50.4408,
                "lng": 30.5193,
                "cuisine": "Середземноморська",
                "address": "вул. Велика Васильківська, 55",
                "url": "https://tarantino.ua",
                "hours": [11,
                          23],
                "schedule": "all",
                "desc": "Сімейний ресторан середземноморської кухні з великою терасою, ідеальний для сімей із дітьми.",
                "desc_en": "Family Mediterranean restaurant with a large terrace, perfect for families with children.",
                "desc_ru": "Семейный ресторан средиземноморской кухни с большой террасой, идеальный для семей с детьми.",
                },
               {"id": 6,
                "name": "Spotykach",
                "lat": 50.4476,
                "lng": 30.5153,
                "cuisine": "Українська",
                "address": "вул. Volodymyrska, 16",
                "url": "",
                "hours": [11,
                          22],
                "schedule": "all",
                "desc": "Демократичний ресторан традиційної української кухні у самому серці Києва, поруч із Золотими воротами.",
                "desc_en": "Affordable traditional Ukrainian restaurant in the heart of Kyiv, next to the Golden Gate.",
                "desc_ru": "Демократичный ресторан традиционной украинской кухни в самом центре Киева, рядом с Золотыми воротами.",
                },
               {"id": 7,
                "name": "Сирна",
                "lat": 50.4519,
                "lng": 30.5236,
                "cuisine": "Українська",
                "address": "вул. Хрещатик, 27",
                "url": "",
                "hours": [9,
                          21],
                "schedule": "all",
                "desc": "Спеціалізований ресторан з понад 50 видами українських та імпортних сирів, фондю та сирними десертами.",
                "desc_en": "Specialty restaurant with over 50 types of Ukrainian and imported cheeses, fondue and cheese desserts.",
                "desc_ru": "Специализированный ресторан с более чем 50 видами украинских и импортных сыров, фондю и сырными десертами.",
                },
               {"id": 8,
                "name": "Musafir",
                "lat": 50.4558,
                "lng": 30.5267,
                "cuisine": "Кримськотатарська",
                "address": "вул. Desiatynna, 11",
                "url": "",
                "hours": [12,
                          22],
                "schedule": "all",
                "desc": "Єдиний у Києві ресторан кримськотатарської кухні — чебуреки, лагман та манти у національному колориті.",
                "desc_en": "The only Crimean Tatar restaurant in Kyiv — chebureki, lagman and manti in authentic national style.",
                "desc_ru": "Единственный в Киеве ресторан крымскотатарской кухни — чебуреки, лагман и манты в национальном колорите.",
                },
               {"id": 9,
                "name": "PapaJons",
                "lat": 50.4382,
                "lng": 30.5107,
                "cuisine": "Піца",
                "address": "вул. Chervonoarmijska, 4",
                "url": "",
                "hours": [10,
                          22],
                "schedule": "all",
                "desc": "Популярна піцерія з дровʼяною піччю, неаполітанським тістом та щедрими топінгами.",
                "desc_en": "Popular pizzeria with a wood-fired oven, Neapolitan dough and generous toppings.",
                "desc_ru": "Популярная пиццерия с дровяной печью, неаполитанским тестом и щедрыми топпингами.",
                },
               {"id": 10,
                "name": "Сushimaster",
                "lat": 50.4495,
                "lng": 30.5244,
                "cuisine": "Японська",
                "address": "вул. Хрещатик, 19",
                "url": "https://sushimaster.ua",
                "hours": [10,
                          22],
                "schedule": "all",
                "desc": "Мережевий суші-ресторан з широким меню японської кухні, доступними цінами та швидкою доставкою.",
                "desc_en": "Chain sushi restaurant with an extensive Japanese menu, affordable prices and fast delivery.",
                "desc_ru": "Сетевой суши-ресторан с широким меню японской кухни, доступными ценами и быстрой доставкой.",
                },
               {"id": 11,
                "name": "Barvy",
                "lat": 50.4629,
                "lng": 30.5226,
                "cuisine": "Фʼюжн",
                "address": "вул. Vozdvyzhenska, 10",
                "url": "",
                "hours": [11,
                          23],
                "schedule": "all",
                "desc": "Арт-ресторан із фʼюжн-кухнею, яскравим дизайном та регулярними виставками сучасного мистецтва.",
                "desc_en": "Art restaurant with fusion cuisine, vibrant design and regular contemporary art exhibitions.",
                "desc_ru": "Арт-ресторан с фьюжн-кухней, ярким дизайном и регулярными выставками современного искусства.",
                },
               {"id": 12,
                "name": "Piel'meni Project",
                "lat": 50.4351,
                "lng": 30.5165,
                "cuisine": "Слов'янська",
                "address": "вул. Велика Васильківська, 90",
                "url": "",
                "hours": [10,
                          22],
                "schedule": "all",
                "desc": "Концептуальний ресторан з понад 20 видами пельменів, вареників та мантів за рецептами різних слов'янських народів.",
                "desc_en": "Concept restaurant with 20+ types of dumplings and varenyky following recipes from various Slavic peoples.",
                "desc_ru": "Концептуальный ресторан с более чем 20 видами пельменей, вареников и мантов по рецептам разных славянских народов.",
                },
               {"id": 13,
                "name": "O'Panas",
                "lat": 50.4571,
                "lng": 30.5299,
                "cuisine": "Українська",
                "address": "вул. Михайлівська, 22/3",
                "url": "",
                "hours": [11,
                          23],
                "schedule": "all",
                "desc": "Стилізований ресторан у козацькому дусі з борщем, варениками та горілчаною картою.",
                "desc_en": "Styled restaurant in Cossack spirit with borscht, varenyky and an extensive vodka menu.",
                "desc_ru": "Стилизованный ресторан в казацком духе с борщом, варениками и обширной картой горилки.",
                },
               {"id": 14,
                "name": "Arena Bar & Grill",
                "lat": 50.4331,
                "lng": 30.5220,
                "cuisine": "Гриль",
                "address": "вул. Велика Васильківська, 120",
                "url": "",
                "hours": [11,
                          23],
                "schedule": "all",
                "desc": "Спортивний бар та гриль — трансляції матчів, стейки на грилі та великий вибір бургерів.",
                "desc_en": "Sports bar and grill — live match screenings, grilled steaks and a wide selection of burgers.",
                "desc_ru": "Спортивный бар и гриль — трансляции матчей, стейки на гриле и большой выбор бургеров.",
                },
               {"id": 15,
                "name": "Ribs & Beer",
                "lat": 50.4415,
                "lng": 30.5178,
                "cuisine": "Гриль / Пиво",
                "address": "пл. Перемоги, 1",
                "url": "",
                "hours": [12,
                          23],
                "schedule": "all",
                "desc": "Ресторан для любителів ребер та пива — соковиті свинячі ребра на грилі та 16 сортів крафтового пива на кранах.",
                "desc_en": "A rib and beer lover's paradise — juicy grilled pork ribs and 16 craft beers on tap.",
                "desc_ru": "Ресторан для любителей рёбер и пива — сочные свиные рёбра на гриле и 16 сортов крафтового пива на кранах.",
                },
               {"id": 16,
                "name": "Golden Gate",
                "lat": 50.4503,
                "lng": 30.5135,
                "cuisine": "Паб / Гриль",
                "address": "вул. Volodymyrska, 40а",
                "url": "",
                "hours": [10,
                          23],
                "schedule": "all",
                "desc": "Класичний ірландський паб із живою музикою щовечора, імпортним пивом та грилем.",
                "desc_en": "Classic Irish pub with live music every evening, imported beer and a grill.",
                "desc_ru": "Классический ирландский паб с живой музыкой каждый вечер, импортным пивом и грилем.",
                },
               {"id": 17,
                "name": "Hibachi",
                "lat": 50.4559,
                "lng": 30.5311,
                "cuisine": "Японська",
                "address": "вул. Мала Житомирська, 3",
                "url": "",
                "hours": [12,
                          23],
                "schedule": "all",
                "desc": "Ресторан з японським грилем теппаньяки — шеф-кухар готує прямо за вашим столом у видовищному стилі.",
                "desc_en": "Japanese teppanyaki grill restaurant — the chef cooks right at your table in a spectacular show-style.",
                "desc_ru": "Ресторан с японским грилем теппаньяки — шеф-повар готовит прямо за вашим столом в эффектном стиле.",
                },
               {"id": 18,
                "name": "Twins",
                "lat": 50.4486,
                "lng": 30.5258,
                "cuisine": "Сучасна",
                "address": "вул. Хрещатик, 25",
                "url": "",
                "hours": [11,
                          23],
                "schedule": "all",
                "desc": "Сучасний ресторан від шеф-кухарів-близнюків з авторськими стравами, сезонним меню та великою винною картою.",
                "desc_en": "Modern restaurant by twin chefs with signature dishes, seasonal menu and an extensive wine list.",
                "desc_ru": "Современный ресторан от шеф-поваров-близнецов с авторскими блюдами, сезонным меню и большой винной картой.",
                },
               {"id": 19,
                "name": "Pizzeria Napule",
                "lat": 50.4462,
                "lng": 30.5140,
                "cuisine": "Неаполітанська піца",
                "address": "вул. Baseina, 5",
                "url": "",
                "hours": [10,
                          22],
                "schedule": "mon-sat",
                "desc": "Автентична неаполітанська піцерія — тісто на заквасці, томати Сан-Марцано та моцарела фіор ді латте.",
                "desc_en": "Authentic Neapolitan pizzeria — sourdough crust, San Marzano tomatoes and fior di latte mozzarella.",
                "desc_ru": "Аутентичная неаполитанская пиццерия — тесто на закваске, томаты Сан-Марцано и моцарелла фиор ди латте.",
                },
               {"id": 20,
                "name": "Bonsai Sushi",
                "lat": 50.4320,
                "lng": 30.5191,
                "cuisine": "Японська",
                "address": "вул. Велика Васильківська, 143",
                "url": "",
                "hours": [10,
                          22],
                "schedule": "all",
                "desc": "Суші-бар з преміальними інгредієнтами, церемонією чаю та медитативною атмосферою японського саду.",
                "desc_en": "Sushi bar with premium ingredients, a tea ceremony and the meditative atmosphere of a Japanese garden.",
                "desc_ru": "Суши-бар с премиальными ингредиентами, чайной церемонией и медитативной атмосферой японского сада.",
                },
               ]


def get_resto(rid):
    return next((r for r in RESTAURANTS if r["id"] == rid), None)


# ─── Blueprint ───────────────────────────────────────────────────────────────

main = Blueprint("main", __name__)


@main.after_app_request
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
        "img-src 'self' data: https://*.tile.openstreetmap.org;")
    return response


@main.route("/")
def index():
    return render_template(
        "main.html",
        logged_in="user_id" in session,
        username=session.get("username", ""),
    )


@main.route("/api/restaurants")
def api_restaurants():
    result = []
    for r in RESTAURANTS:
        reviews = Review.query.filter_by(resto_id=r["id"]).all()
        avg = (
            round(sum(rv.rating for rv in reviews) / len(reviews), 1)
            if reviews
            else None
        )
        result.append({**r, "avg_rating": avg, "review_count": len(reviews)})
    return jsonify(result)


@main.route("/api/reviews/<int:resto_id>")
def api_reviews(resto_id):
    reviews = (
        Review.query.filter_by(resto_id=resto_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return jsonify(
        [
            {
                "id": rv.id,
                "text": rv.text,
                "rating": rv.rating,
                "author": "Anonymous" if rv.anonymous else rv.author.username,
                "anonymous": rv.anonymous,
                "user_id": rv.user_id,
                "created_at": rv.created_at.strftime("%d.%m.%Y"),
                "mine": rv.user_id == session.get("user_id"),
            }
            for rv in reviews
        ]
    )


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        err = validate_username(username) or validate_password(password)
        if err:
            flash(err, "danger")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("register.html")
        pw_hash = bcrypt.generate_password_hash(
            password, rounds=12).decode("utf-8")
        db.session.add(User(username=username, password_hash=pw_hash))
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome, {user.username}!", "success")
            return redirect(url_for("main.index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@main.route("/api/reviews", methods=["POST"])
@login_required
def post_review():
    data = request.get_json(force=True) or {}
    resto_id = int(data.get("resto_id", 0))
    text = sanitize(str(data.get("text", "")), 500)
    rating = int(data.get("rating", 0))
    anonymous = bool(data.get("anonymous", False))

    if not get_resto(resto_id):
        return jsonify({"error": "Unknown restaurant"}), 400
    if not text or len(text) < 3:
        return jsonify({"error": "Review too short"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be 1-5"}), 400

    existing = Review.query.filter_by(
        resto_id=resto_id, user_id=session["user_id"]
    ).first()
    if existing:
        return jsonify({"error": "already_reviewed",
                       "review_id": existing.id}), 409

    db.session.add(
        Review(
            text=text,
            rating=rating,
            resto_id=resto_id,
            user_id=session["user_id"],
            anonymous=anonymous,
        )
    )
    db.session.commit()
    return jsonify({"ok": True})


@main.route("/api/reviews/<int:review_id>", methods=["PUT"])
@login_required
def edit_review(review_id):
    rv = db.get_or_404(Review, review_id)
    if rv.user_id != session["user_id"]:
        abort(403)
    data = request.get_json(force=True) or {}
    text = sanitize(str(data.get("text", "")), 500)
    rating = int(data.get("rating", 0))
    anonymous = bool(data.get("anonymous", False))
    if not text or len(text) < 3:
        return jsonify({"error": "Review too short"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be 1-5"}), 400
    rv.text = text
    rv.rating = rating
    rv.anonymous = anonymous
    db.session.commit()
    return jsonify({"ok": True})


@main.route("/api/reviews/<int:review_id>", methods=["DELETE"])
@login_required
def delete_review(review_id):
    rv = db.get_or_404(Review, review_id)
    if rv.user_id != session["user_id"]:
        abort(403)
    db.session.delete(rv)
    db.session.commit()
    return jsonify({"ok": True})


@main.route("/api/my-review/<int:resto_id>")
@login_required
def my_review(resto_id):
    rv = Review.query.filter_by(
        resto_id=resto_id,
        user_id=session["user_id"]).first()
    if not rv:
        return jsonify(None)
    return jsonify({"id": rv.id,
                    "text": rv.text,
                    "rating": rv.rating,
                    "anonymous": rv.anonymous})


@main.route("/api/csrf-token")
def csrf_token():
    return jsonify({"token": generate_csrf()})


# ─── Statistics endpoint ────────────────────────────────────────────────


@main.route("/api/stats")
def api_stats():
    """Aggregate statistics: totals, top-rated restaurant, cuisine breakdown."""
    total_reviews = Review.query.count()
    total_users = User.query.count()

    top_rated = None
    best_avg = -1.0
    for r in RESTAURANTS:
        reviews = Review.query.filter_by(resto_id=r["id"]).all()
        if reviews:
            avg = sum(rv.rating for rv in reviews) / len(reviews)
            if avg > best_avg:
                best_avg = avg
                top_rated = {
                    "id": r["id"],
                    "name": r["name"],
                    "avg": round(
                        avg,
                        2)}

    cuisine_counts: dict = {}
    for r in RESTAURANTS:
        c = r["cuisine"]
        cuisine_counts[c] = cuisine_counts.get(c, 0) + 1

    return jsonify(
        {
            "total_restaurants": len(RESTAURANTS),
            "total_reviews": total_reviews,
            "total_users": total_users,
            "top_rated": top_rated,
            "cuisine_breakdown": cuisine_counts,
        }
    )


# ─── Favourites endpoints ───────────────────────────────────────────────


@main.route("/api/favourites", methods=["GET"])
@login_required
def get_favourites():
    """Return the current user's favourite restaurants with live ratings."""
    favs = Favourite.query.filter_by(user_id=session["user_id"]).all()
    result = []
    for f in favs:
        r = get_resto(f.resto_id)
        if r:
            reviews = Review.query.filter_by(resto_id=r["id"]).all()
            avg = (
                round(sum(rv.rating for rv in reviews) / len(reviews), 1)
                if reviews
                else None
            )
            result.append(
                {**r, "avg_rating": avg, "review_count": len(reviews)})
    return jsonify(result)


@main.route("/api/favourites/<int:resto_id>", methods=["POST"])
@login_required
def add_favourite(resto_id):
    """Add a restaurant to the current user's favourites."""
    if not get_resto(resto_id):
        return jsonify({"error": "Unknown restaurant"}), 400
    existing = Favourite.query.filter_by(
        user_id=session["user_id"], resto_id=resto_id
    ).first()
    if existing:
        return jsonify({"ok": True, "already": True})
    db.session.add(Favourite(user_id=session["user_id"], resto_id=resto_id))
    db.session.commit()
    return jsonify({"ok": True})


@main.route("/api/favourites/<int:resto_id>", methods=["DELETE"])
@login_required
def remove_favourite(resto_id):
    """Remove a restaurant from the current user's favourites."""
    fav = Favourite.query.filter_by(
        user_id=session["user_id"], resto_id=resto_id
    ).first_or_404()
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"ok": True})


# ─── Application factory ─────────────────────────────────────────────────────


def create_app(test_config=None):
    """
    Application factory.
    Pass test_config dict to override settings in tests (e.g. in-memory SQLite).
    AI-assisted: factory pattern suggested by Claude for proper test isolation.
    """
    application = Flask(__name__)
    application.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-change-in-prod"
    )
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///restok.db"
    application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    application.config["SESSION_COOKIE_HTTPONLY"] = True
    application.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    application.config["WTF_CSRF_ENABLED"] = True

    if test_config:
        application.config.update(test_config)

    db.init_app(application)
    bcrypt.init_app(application)
    csrf.init_app(application)
    limiter.init_app(application)

    application.register_blueprint(main)

    return application


# Module-level app for direct execution and Gunicorn
app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False, host="127.0.0.1", port=5000)
